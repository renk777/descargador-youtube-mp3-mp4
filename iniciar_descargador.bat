@echo off
setlocal
cd /d "%~dp0"

where pythonw >nul 2>&1
if errorlevel 1 (
    echo No se encontro Python en el PATH.
    echo Instala Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

pythonw "%~dp0descargador.py"
if errorlevel 1 (
    echo El programa termino con un error.
    pause
)
