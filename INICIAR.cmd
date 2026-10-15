@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Prepare o ambiente seguindo a secao Como executar do README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m notebook Inicio.ipynb
if errorlevel 1 pause
