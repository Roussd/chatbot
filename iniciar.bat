@echo off
cd /d "%~dp0"
echo Chatbot en http://localhost:8000
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
