@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Primero debes ejecutar setup_windows.bat.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python analyze.py --open-report %*
if errorlevel 1 (
  echo.
  echo El analisis no ha terminado correctamente. Lee el error mostrado arriba.
  pause
  exit /b 1
)

echo.
echo Analisis completado.
pause

