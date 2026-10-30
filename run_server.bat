@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist ".env" (
  echo No hay .env. Copiando .env.example...
  copy .env.example .env >nul
  echo Edita .env antes de exponer el servidor.
)

echo Servidor Libreta en http://127.0.0.1:8787
".venv\Scripts\uvicorn.exe" server.main:app --host 0.0.0.0 --port 8787
