# Chatbot local de documentos (sin APIs externas)

Responde en español usando solo los archivos de `documentos/` (.txt, .md, .pdf, .docx).
Todo corre en la máquina con [Ollama](https://ollama.com).

## Cómo funciona (RAG)
1. `documentos.py` lee los archivos y los corta en fragmentos.
2. `buscador.py` convierte cada fragmento en un vector (modelo `bge-m3`) y lo guarda en `datos/indice.json`.
3. Al preguntar, se buscan los fragmentos más parecidos a la pregunta.
4. `chat.py` se los pasa a `qwen3:4b-instruct` con la orden de responder solo con ese contexto.

## Desarrollo (este PC)
```powershell
ollama pull qwen3:4b-instruct
ollama pull bge-m3
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```
1. Cada subcarpeta de `documentos/` es un **tema** del menú lateral (ej. `documentos/parte_diario/manual.pdf`).
   Los archivos sueltos en `documentos/` van al tema "general".
2. Opcional: `faq.json` dentro de un tema con preguntas frecuentes de respuesta fija
   (`[{"pregunta": "...", "respuesta": "..."}]`). Salen como botones y no usan la IA.
3. Ejecuta `iniciar.bat` y abre http://localhost:8000
4. **Cada vez que cambies documentos o FAQ**, pulsa "Actualizar documentos" en la pantalla
   (o `Invoke-RestMethod -Method Post http://localhost:8000/api/reindexar`).

La interfaz está en `public/` (index.html, estilos.css, app.js, logos y la fuente, todo local: no necesita internet).
Los colores se cambian en la sección `:root` de `public/estilos.css`.
El tema "Todos" consulta todos los documentos a la vez.

Ajustes (modelos, tamaño de fragmentos, umbral): `app/config.py`.

## Llevarlo al servidor Windows (pendrive, sin internet)
En este PC, con internet:
```powershell
.\.venv\Scripts\pip download -r requirements.txt -d paquetes
```
Copia al pendrive:
- La carpeta del proyecto **sin** `.venv` (incluye `paquetes/`, `documentos/`, `datos/`).
- `OllamaSetup.exe` (descárgalo de ollama.com).
- Instalador de **la misma versión de Python** (3.14.x) si el servidor no lo tiene.
- Los modelos: la carpeta `C:\Users\<usuario>\.ollama\models` completa.

En el servidor:
1. Instala Python y Ollama.
2. Copia `models` a `C:\Users\<usuario-del-servicio>\.ollama\models` (verifica con `ollama list`).
3. En la carpeta del proyecto:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip install --no-index --find-links paquetes -r requirements.txt
   ```
4. Ejecuta `iniciar.bat`. Se accede desde la red en `http://IP-DEL-SERVIDOR:8000` (abre el puerto 8000 en el firewall).
# chatbot
