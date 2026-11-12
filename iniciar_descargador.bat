@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0dist\Descargador.exe" (
    start "" "%~dp0dist\Descargador.exe"
    exit /b 0
)
where pythonw >nul 2>&1
if errorlevel 1 (
    echo No se encontro el ejecutable ni Python en el PATH.
    echo Compila el proyecto o instala Python y requirements.txt.
    pause
    exit /b 1
)
pythonw "%~dp0descargador.py"
if errorlevel 1 (
    echo El programa termino con un error. Revisa las dependencias.
    pause
)
