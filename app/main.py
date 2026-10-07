"""Servidor web: API del chatbot (/api/...) y la página en /."""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import chat, config, documentos
from app.buscador import Buscador

config.CARPETA_DOCUMENTOS.mkdir(exist_ok=True)

app = FastAPI(title="Chatbot local")
buscador = Buscador()

_resumenes: dict[tuple[str, str], str] = {}  # caché: resumir es lento, no repetirlo


def _sincronizar():
    """Si los documentos cambiaron, reindexa y descarta los resúmenes guardados."""
    if buscador.actualizar_si_cambio():
        _resumenes.clear()


class Pregunta(BaseModel):
    tema: str
    texto: str


class PedidoResumen(BaseModel):
    tema: str
    documento: str | None = None  # None = todos los documentos del tema


@app.get("/api/temas")
def temas():
    return documentos.listar_temas()


@app.post("/api/chat")
def preguntar(pregunta: Pregunta):
    _sincronizar()
    texto = buscador.corregir(pregunta.texto)  # "parte diarii" -> "parte diario"
    entendida = texto if texto != pregunta.texto else None  # para avisar al usuario qué entendimos

    resultado = buscador.buscar(texto, pregunta.tema)
    if resultado["faq"]:  # pregunta frecuente: respuesta fija, sin usar el modelo
        return {"respuesta": resultado["faq"]["respuesta"], "fuentes": [], "entendida": entendida}
    fragmentos = resultado["fragmentos"]
    return {
        "respuesta": chat.responder(texto, fragmentos),
        "fuentes": sorted({f["fuente"] for f in fragmentos}),
        "entendida": entendida,
    }


@app.post("/api/resumir")
def resumir(pedido: PedidoResumen):
    _sincronizar()
    textos = documentos.textos_del_tema(pedido.tema)
    if pedido.documento:
        textos = {n: t for n, t in textos.items() if n == pedido.documento}
    if not textos:
        raise HTTPException(404, "No hay documentos para resumir.")

    partes = []
    for nombre, texto in textos.items():
        if (pedido.tema, nombre) not in _resumenes:
            _resumenes[(pedido.tema, nombre)] = chat.resumir(texto)
        partes.append(f"{nombre}\n{_resumenes[(pedido.tema, nombre)]}")
    return {"resumen": "\n\n".join(partes)}


@app.post("/api/reindexar")
def reindexar():
    """Vuelve a leer documentos y FAQ (úsalo cuando agregues o cambies archivos)."""
    _resumenes.clear()
    return buscador.reindexar()


class ArchivosPublicos(StaticFiles):
    """Sirve public/ pidiendo al navegador que revise si hay versión nueva (evita ver diseños viejos)."""

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


# Va al final: sirve public/ (index.html en "/") sin tapar las rutas /api
app.mount("/", ArchivosPublicos(directory=config.CARPETA_PUBLICA, html=True), name="public")
