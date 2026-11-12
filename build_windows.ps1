$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m pip install -r requirements.txt pyinstaller Pillow
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
foreach ($binary in @("ffmpeg.exe", "ffprobe.exe")) {
    if (-not (Test-Path -LiteralPath (Join-Path "ffmpeg\bin" $binary))) {
        throw "Falta ffmpeg\bin\$binary. Coloca una distribución de FFmpeg antes de compilar."
    }
}
if (-not (Test-Path -LiteralPath "runtime\deno.exe")) { throw "Falta runtime\deno.exe (Deno oficial)." }
if (-not (Test-Path -LiteralPath "logo.png")) { throw "Falta logo.png." }
New-Item -ItemType Directory -Path "build" -Force | Out-Null
python -c "from PIL import Image; Image.open('logo.png').save('build/logo.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el icono." }
python -m PyInstaller --noconfirm --onefile --windowed --name Descargador `
    --icon "build\logo.ico" --add-data "logo.png;." --add-data "ffmpeg;ffmpeg" `
    --add-binary "runtime/deno.exe;runtime" --add-data "runtime/LICENSE.md;runtime" `
    --add-data "runtime/VERSION.txt;runtime" --collect-data yt_dlp_ejs descargador.py
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el ejecutable." }
Copy-Item -LiteralPath "README.md", "LICENSE", "RELEASE_NOTES.md", "THIRD_PARTY_NOTICES.md" -Destination "dist" -Force
Copy-Item -LiteralPath "licenses" -Destination "dist" -Recurse -Force
Write-Host "Listo: dist\Descargador.exe"
