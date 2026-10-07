"""Habla con el modelo: responde preguntas usando los fragmentos encontrados y resume textos."""
import ollama

from app import config

SIN_INFORMACION = "No encontré esa información en los documentos."

INSTRUCCIONES_PREGUNTA = (
    "Eres un asistente que responde SIEMPRE en español, de forma clara y breve. "
    "Responde únicamente con la información del CONTEXTO. "
    f"Si la respuesta no está en el contexto, di exactamente: '{SIN_INFORMACION}' "
    "No inventes datos."
)

INSTRUCCIONES_RESUMEN = (
    "Eres un asistente que resume textos SIEMPRE en español. "
    "Escribe un resumen claro con las ideas principales en viñetas que empiecen con '- '. "
    "No uses formato Markdown (nada de **, # ni tablas). No agregues información que no esté en el texto."
)


def _generar(instrucciones: str, mensaje: str) -> str:
    respuesta = ollama.chat(
        model=config.MODELO_CHAT,
        keep_alive="30m",  # mantiene el modelo cargado entre preguntas
        options={"temperature": 0.2},
        messages=[
            {"role": "system", "content": instrucciones},
            {"role": "user", "content": mensaje},
        ],
    )
    return respuesta["message"]["content"].strip()


def responder(pregunta: str, fragmentos: list[dict]) -> str:
    if not fragmentos:
        return SIN_INFORMACION
    contexto = "\n\n".join(f"[{f['fuente']}] {f['texto']}" for f in fragmentos)
    return _generar(INSTRUCCIONES_PREGUNTA, f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}")


def resumir(texto: str) -> str:
    """Resume cualquier largo de texto: si no cabe de una vez, resume por partes y luego resume los resúmenes."""
    if not texto.strip():
        return "No se pudo extraer texto de este documento (¿es un PDF escaneado?)."
    if len(texto) <= config.LIMITE_RESUMEN:
        return _generar(INSTRUCCIONES_RESUMEN, f"Resume este texto:\n\n{texto}")

    partes = [texto[i : i + config.LIMITE_RESUMEN] for i in range(0, len(texto), config.LIMITE_RESUMEN)]
    unido = "\n\n".join(resumir(parte) for parte in partes)
    if len(unido) >= len(texto):  # el modelo no logró acortar: evitamos repetir sin fin
        return unido[: config.LIMITE_RESUMEN]
    return resumir(unido)
