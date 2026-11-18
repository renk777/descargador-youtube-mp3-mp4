$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$buildPython = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $buildPython)) {
    python -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno de compilación." }
}
foreach ($binary in @("ffmpeg.exe", "ffprobe.exe")) {
    if (-not (Test-Path -LiteralPath (Join-Path "ffmpeg\bin" $binary))) {
        throw "Falta ffmpeg\bin\$binary."
    }
}
if (-not (Test-Path -LiteralPath "runtime\deno.exe")) { throw "Falta runtime\deno.exe." }
$previousPath = $env:PATH
try {
    $basePythonDir = & $buildPython -c "import sys; print(sys.base_prefix)"
    # Do not collect incompatible Qt/ICU/OpenSSL DLLs from unrelated tools on PATH.
    $env:PATH = (Split-Path -Parent $buildPython), $basePythonDir, (Join-Path $env:SystemRoot "System32"), $env:SystemRoot -join ";"
    & $buildPython -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de compilación." }
    New-Item -ItemType Directory -Path "build" -Force | Out-Null
    & $buildPython -c "from PIL import Image; Image.open('logo.png').save('build/logo.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el icono." }
    & $buildPython -m PyInstaller --noconfirm --clean --onefile --windowed --name Descargador `
        --icon "build\logo.ico" --add-data "logo.png;." --add-data "ffmpeg;ffmpeg" `
        --add-binary "runtime/deno.exe;runtime" --add-data "runtime/LICENSE.md;runtime" `
        --add-data "runtime/VERSION.txt;runtime" --collect-data yt_dlp_ejs --hidden-import descargador launch_app.py
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el ejecutable." }
    $executable = Join-Path $PSScriptRoot "dist\Descargador.exe"
    $diagnostic = Join-Path $PSScriptRoot "build\diagnostic.json"
    & $buildPython -c "import subprocess,sys,tempfile; from pathlib import Path; exe=Path(sys.argv[1]); report=Path(sys.argv[2]); tmp=tempfile.TemporaryDirectory(); result=subprocess.run([str(exe),'--check','--diagnostic-report',str(report)],cwd=tmp.name,timeout=60); tmp.cleanup(); print(report.read_text(encoding='utf-8') if report.exists() else 'No se generó el diagnóstico'); raise SystemExit(result.returncode)" $executable $diagnostic
    if ($LASTEXITCODE -ne 0) { throw "El ejecutable compilado no superó el diagnóstico aislado. No se publicará." }
    Copy-Item -LiteralPath "README.md", "LICENSE", "RELEASE_NOTES.md", "THIRD_PARTY_NOTICES.md" -Destination "dist" -Force
    Copy-Item -LiteralPath "licenses" -Destination "dist" -Recurse -Force
    Write-Host "Listo y validado: dist\Descargador.exe"
}
finally {
    $env:PATH = $previousPath
}
