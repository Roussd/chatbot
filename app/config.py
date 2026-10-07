"""Configuración central. Todo lo que quieras ajustar está aquí."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

CARPETA_PUBLICA = RAIZ / "public"          # página web, logos y fuentes
CARPETA_DOCUMENTOS = RAIZ / "documentos"  # cada subcarpeta es un "tema" del menú
ARCHIVO_INDICE = RAIZ / "datos" / "indice.json"  # índice generado automáticamente
NOMBRE_FAQ = "faq.json"                    # preguntas frecuentes de cada tema

# Modelos de Ollama
MODELO_CHAT = "qwen3:4b-instruct"
MODELO_EMBEDDINGS = "bge-m3"

# Troceado de documentos (en caracteres)
TAMANO_FRAGMENTO = 800
SOLAPAMIENTO = 150

# Búsqueda
FRAGMENTOS_A_USAR = 5     # cuántos fragmentos se le pasan al modelo
SIMILITUD_MINIMA = 0.35    # por debajo de esto se considera "no hay información"
SIMILITUD_FAQ = 0.82       # a partir de esto se responde con la pregunta frecuente

# Resúmenes: tamaño máximo de texto que se le da al modelo de una vez
LIMITE_RESUMEN = 5000

EXTENSIONES = {".txt", ".md", ".pdf", ".docx"}
