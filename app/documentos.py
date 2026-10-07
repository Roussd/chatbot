"""Lee los archivos de la carpeta, los agrupa por tema y los divide en fragmentos.

Estructura:  documentos/<tema>/archivo.pdf  y  documentos/<tema>/faq.json
Los archivos sueltos en la raíz de documentos/ van al tema "general".
"""
import json
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app import config

TEMA_GENERAL = "general"
TODOS = "todos"  # tema especial: consulta todos los documentos a la vez


def leer_texto(ruta: Path) -> str:
    """Devuelve el texto de un archivo según su extensión."""
    extension = ruta.suffix.lower()
    if extension in {".txt", ".md"}:
        return ruta.read_text(encoding="utf-8", errors="ignore")
    if extension == ".pdf":
        return "\n".join(pagina.extract_text() or "" for pagina in PdfReader(ruta).pages)
    if extension == ".docx":
        return "\n".join(parrafo.text for parrafo in Document(ruta).paragraphs)
    return ""


def dividir_en_fragmentos(texto: str) -> list[str]:
    """Corta el texto en trozos con un pequeño solapamiento entre ellos."""
    texto = re.sub(r"(\.\s?){4,}", " ", texto)  # quita las líneas de puntos de los índices
    texto = " ".join(texto.split())  # limpia saltos de línea y espacios repetidos
    paso = config.TAMANO_FRAGMENTO - config.SOLAPAMIENTO
    fragmentos = [texto[i : i + config.TAMANO_FRAGMENTO] for i in range(0, len(texto), paso)]
    return [f for f in fragmentos if f.strip()]


def tema_de(ruta: Path) -> str:
    """El tema es la primera carpeta dentro de documentos/."""
    partes = ruta.relative_to(config.CARPETA_DOCUMENTOS).parts
    return partes[0] if len(partes) > 1 else TEMA_GENERAL


def listar_archivos() -> list[Path]:
    rutas = config.CARPETA_DOCUMENTOS.rglob("*")
    return sorted(r for r in rutas if r.suffix.lower() in config.EXTENSIONES)


def huella() -> str:
    """Identifica el estado actual de la carpeta: cambia si se agrega, edita o borra un archivo."""
    archivos = listar_archivos() + sorted(config.CARPETA_DOCUMENTOS.rglob(config.NOMBRE_FAQ))
    return "|".join(f"{r}:{r.stat().st_size}:{r.stat().st_mtime_ns}" for r in archivos)


def cargar_fragmentos() -> list[dict]:
    """Devuelve [{'tema', 'fuente', 'texto'}, ...] de todos los documentos."""
    resultado = []
    for ruta in listar_archivos():
        for fragmento in dividir_en_fragmentos(leer_texto(ruta)):
            resultado.append({"tema": tema_de(ruta), "fuente": ruta.name, "texto": fragmento})
    return resultado


def cargar_faq() -> list[dict]:
    """Devuelve [{'tema', 'pregunta', 'respuesta'}, ...] leyendo cada faq.json."""
    resultado = []
    for ruta in sorted(config.CARPETA_DOCUMENTOS.rglob(config.NOMBRE_FAQ)):
        for entrada in json.loads(ruta.read_text(encoding="utf-8")):
            resultado.append({"tema": tema_de(ruta), **entrada})
    return resultado


def listar_temas() -> list[dict]:
    """Datos para el menú: [{'id', 'documentos': [...], 'faq': [preguntas]}, ...]."""
    temas: dict[str, dict] = {}

    def tema(id_: str) -> dict:
        return temas.setdefault(id_, {"id": id_, "documentos": [], "faq": []})

    todos = {"id": TODOS, "documentos": [], "faq": []}
    for ruta in listar_archivos():
        tema(tema_de(ruta))["documentos"].append(ruta.name)
        todos["documentos"].append(ruta.name)
    for entrada in cargar_faq():
        tema(entrada["tema"])["faq"].append(entrada["pregunta"])
        todos["faq"].append(entrada["pregunta"])
    return [todos, *sorted(temas.values(), key=lambda t: t["id"])]


def textos_del_tema(tema_id: str) -> dict[str, str]:
    """{nombre_del_archivo: texto completo} de los documentos de un tema."""
    return {r.name: leer_texto(r) for r in listar_archivos() if tema_id in (TODOS, tema_de(r))}
