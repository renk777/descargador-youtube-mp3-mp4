@echo off
cd /d "%~dp0"

where pythonw >nul 2>&1
if errorlevel 1 (
    msg * "No se encontro Python. Instala Python desde https://www.python.org/downloads/"
    exit /b 1
)

pythonw "%~dp0descargador.py"
