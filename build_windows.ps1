$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron instalar las dependencias."
}

if (-not (Test-Path -LiteralPath "ffmpeg\bin\ffmpeg.exe")) {
    throw "Coloca una distribución de FFmpeg en ffmpeg\bin antes de compilar."
}

Remove-Item -LiteralPath "build", "dist", "Descargador.spec" -Recurse -Force -ErrorAction SilentlyContinue
pyinstaller --noconfirm --clean --onefile --windowed --name Descargador `
    --add-data "ffmpeg;ffmpeg" descargador.py

Copy-Item -LiteralPath "README.md", "LICENSE" -Destination "dist" -Force
Write-Host "Listo: dist\Descargador.exe"
