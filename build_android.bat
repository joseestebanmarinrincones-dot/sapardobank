@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

set PYTHONIOENCODING=utf-8
set FLET_CLI_NO_RICH_OUTPUT=1
if exist "%ProgramFiles%\Git\cmd" set PATH=%ProgramFiles%\Git\cmd;%PATH%

echo Compilando APK con widget nativo...
echo La primera vez descarga Flutter, JDK y Android SDK; puede tardar.
".venv\Scripts\flet.exe" build apk --template "%~dp0android_template" --yes --no-rich-output %*
if errorlevel 1 (
  echo.
  echo El build fallo. Si fue por symlinks de Flutter, reintento con junctions...
  ".venv\Scripts\python.exe" tools\prepare_plugin_junctions.py
  ".venv\Scripts\flet.exe" build apk --template "%~dp0android_template" --yes --no-rich-output %*
)

echo.
echo Busca el APK en build\apk\
