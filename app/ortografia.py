"""Corrige errores de tipeo en la pregunta usando las palabras de los propios documentos.

Ejemplo: "que es el parte diarii" -> "que es el parte diario".
Una palabra se corrige solo si NO existe en los documentos y se parece mucho a una que sí existe.
"""
import difflib
import re
import unicodedata
from collections import Counter

PALABRA = re.compile(r"[^\W\d_]+")  # solo letras (con tildes y ñ)
LARGO_MINIMO = 4        # las palabras muy cortas no se tocan
PARECIDO_MINIMO = 0.8   # 1.0 = idéntica

# Palabras comunes que no se corrigen aunque no aparezcan en los documentos
COMUNES = {
    "que", "como", "cual", "cuales", "cuanto", "cuanta", "cuantos", "cuantas", "cuando", "donde",
    "quien", "quienes", "para", "porque", "sobre", "desde", "hasta", "entre", "puedo", "puede",
    "pueden", "podria", "hacer", "hace", "hacen", "tengo", "tiene", "tienen", "debo", "debe",
    "deben", "quiero", "necesito", "saber", "significa", "significan", "sirve", "sirven",
    "favor", "hola", "gracias", "dime", "explica", "tambien", "ademas", "ahora", "siempre",
    "nunca", "mucho", "poco", "todo", "toda", "otro", "otra", "algo", "algun", "alguna",
}


def _sin_tildes(palabra: str) -> str:
    descompuesta = unicodedata.normalize("NFD", palabra.lower())
    return "".join(c for c in descompuesta if unicodedata.category(c) != "Mn")


class Corrector:
    def __init__(self, textos: list[str]):
        # {palabra sin tildes: cuántas veces aparece cada forma escrita}
        self.formas: dict[str, Counter] = {}
        for texto in textos:
            for palabra in PALABRA.findall(texto):
                if len(palabra) >= LARGO_MINIMO:
                    self.formas.setdefault(_sin_tildes(palabra), Counter())[palabra.lower()] += 1

    def corregir(self, pregunta: str) -> str:
        return PALABRA.sub(self._corregir_palabra, pregunta)

    def _corregir_palabra(self, coincidencia: re.Match) -> str:
        palabra = coincidencia.group()
        base = _sin_tildes(palabra)
        if len(base) < LARGO_MINIMO or base in self.formas or base in COMUNES:
            return palabra
        candidatas = difflib.get_close_matches(base, self.formas, n=8, cutoff=PARECIDO_MINIMO)
        if not candidatas:
            return palabra
        # Se prefieren palabras que se repiten en los documentos: las que aparecen una sola vez suelen ser ruido del PDF
        usuales = [c for c in candidatas if sum(self.formas[c].values()) >= 2]
        elegida = (usuales or candidatas)[0]  # la lista viene ordenada de más a menos parecida
        return self.formas[elegida].most_common(1)[0][0]
