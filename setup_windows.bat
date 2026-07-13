@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python no esta instalado o no esta en el PATH.
  echo Descarga Python 3.11 o superior desde https://www.python.org/downloads/
  echo Durante la instalacion marca "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creando el entorno virtual...
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)

echo Instalando dependencias...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -e .
if errorlevel 1 goto :error

echo.
echo INSTALACION COMPLETADA.
echo Ahora copia el JSON o CSV de Apify dentro de data\input y ejecuta run_analysis.bat.
pause
exit /b 0

:error
echo.
echo ERROR: no se pudo completar la instalacion. Revisa el mensaje anterior.
pause
exit /b 1
