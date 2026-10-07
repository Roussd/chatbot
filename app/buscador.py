"""Índice de búsqueda: convierte textos en vectores y encuentra los más parecidos a una pregunta."""
import json
import threading

import numpy as np
import ollama

from app import config, documentos
from app.ortografia import Corrector


def _vectorizar(textos: list[str]) -> np.ndarray:
    """Convierte textos en vectores normalizados (así, similitud = producto punto)."""
    if not textos:
        return np.empty((0, 0), dtype=np.float32)
    # num_gpu=0: el modelo de búsqueda corre en CPU para no sacar al modelo de chat de la GPU
    respuesta = ollama.embed(model=config.MODELO_EMBEDDINGS, input=textos, options={"num_gpu": 0}, keep_alive="30m")
    vectores = np.array(respuesta["embeddings"], dtype=np.float32)
    return vectores / np.linalg.norm(vectores, axis=1, keepdims=True)


def _vectorizar_en_lotes(textos: list[str], tamano_lote: int = 32) -> np.ndarray:
    lotes = [_vectorizar(textos[i : i + tamano_lote]) for i in range(0, len(textos), tamano_lote)]
    return np.vstack(lotes) if lotes else _vectorizar([])


class Buscador:
    def __init__(self):
        self.fragmentos: list[dict] = []
        self.vectores = _vectorizar([])
        self.faq: list[dict] = []
        self.vectores_faq = _vectorizar([])
        self.huella = ""  # estado de la carpeta cuando se creó el índice
        self.corrector = Corrector([])
        self._candado = threading.RLock()
        self._cargar_indice()

    def corregir(self, pregunta: str) -> str:
        """Arregla errores de tipeo usando el vocabulario de los documentos."""
        return self.corrector.corregir(pregunta)

    def _crear_corrector(self):
        textos = [f["texto"] for f in self.fragmentos] + [f["pregunta"] for f in self.faq]
        self.corrector = Corrector(textos)

    def actualizar_si_cambio(self) -> bool:
        """Reindexa solo si los documentos cambiaron desde el último índice. Devuelve si reindexó."""
        with self._candado:
            if documentos.huella() == self.huella:
                return False
            self.reindexar()
            return True

    def reindexar(self) -> dict:
        """Lee documentos y FAQ, los vectoriza y guarda el índice."""
        with self._candado:
            return self._reindexar()

    def _reindexar(self) -> dict:
        self.huella = documentos.huella()
        self.fragmentos = documentos.cargar_fragmentos()
        self.vectores = _vectorizar_en_lotes([f["texto"] for f in self.fragmentos])
        self.faq = documentos.cargar_faq()
        self.vectores_faq = _vectorizar_en_lotes([f["pregunta"] for f in self.faq])
        self._crear_corrector()
        self._guardar_indice()
        return {"fragmentos": len(self.fragmentos), "faq": len(self.faq)}

    def buscar(self, pregunta: str, tema: str) -> dict:
        """Devuelve {'faq': respuesta fija o None, 'fragmentos': [más relevantes del tema]}."""
        vector = _vectorizar([pregunta])[0]

        faq = self._ordenar_por_similitud(self.faq, self.vectores_faq, vector, tema)
        if faq and faq[0][1] >= config.SIMILITUD_FAQ:
            return {"faq": faq[0][0], "fragmentos": []}

        fragmentos = self._ordenar_por_similitud(self.fragmentos, self.vectores, vector, tema)
        relevantes = [f for f, similitud in fragmentos if similitud >= config.SIMILITUD_MINIMA]
        return {"faq": None, "fragmentos": relevantes[: config.FRAGMENTOS_A_USAR]}

    @staticmethod
    def _ordenar_por_similitud(items, vectores, vector_pregunta, tema) -> list[tuple[dict, float]]:
        """Los items del tema, de más a menos parecido a la pregunta: [(item, similitud), ...]."""
        posiciones = [i for i, item in enumerate(items) if tema in (documentos.TODOS, item["tema"])]
        if not posiciones:
            return []
        similitudes = vectores[posiciones] @ vector_pregunta
        orden = np.argsort(similitudes)[::-1]
        return [(items[posiciones[k]], float(similitudes[k])) for k in orden]

    def _guardar_indice(self):
        config.ARCHIVO_INDICE.parent.mkdir(exist_ok=True)
        datos = {
            "fragmentos": self.fragmentos,
            "vectores": self.vectores.tolist(),
            "faq": self.faq,
            "vectores_faq": self.vectores_faq.tolist(),
            "huella": self.huella,
        }
        config.ARCHIVO_INDICE.write_text(json.dumps(datos), encoding="utf-8")

    def _cargar_indice(self):
        if not config.ARCHIVO_INDICE.exists():
            return
        datos = json.loads(config.ARCHIVO_INDICE.read_text(encoding="utf-8"))
        self.fragmentos = datos["fragmentos"]
        self.vectores = np.array(datos["vectores"], dtype=np.float32)
        self.faq = datos["faq"]
        self.vectores_faq = np.array(datos["vectores_faq"], dtype=np.float32)
        self.huella = datos.get("huella", "")
        self._crear_corrector()
