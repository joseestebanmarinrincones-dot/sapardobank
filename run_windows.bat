@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual con Python 3.12...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo Abriendo Libreta...
".venv\Scripts\python.exe" main.py
