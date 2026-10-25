# Descargador de YouTube

Aplicación de escritorio para pegar enlaces de YouTube y guardar audio en MP3
o videos en MP4. Acepta videos individuales, listas de reproducción y varios
enlaces pegados uno por línea.

## Requisitos

- Python 3.10 o posterior.
- [FFmpeg](https://ffmpeg.org/download.html), instalado y disponible en el
  `PATH` de Windows. También puedes colocarlo en `ffmpeg\bin` junto al
  programa.

## Instalación en Windows

### Instalar FFmpeg

La forma más sencilla es abrir PowerShell y ejecutar:

```powershell
winget install Gyan.FFmpeg.Shared
```

Cuando termine, cierra y vuelve a abrir PowerShell. Comprueba que quedó
disponible con:

```powershell
ffmpeg -version
```

La aplicación también busca `ffmpeg.exe` en `ffmpeg\bin` junto al programa.
Para crear una versión distribuible, coloca allí `ffmpeg.exe` y `ffprobe.exe`.

Si `winget` no está disponible, descarga una versión de Windows desde
<https://www.gyan.dev/ffmpeg/builds/>. Extrae el archivo y agrega su carpeta
`bin` al `PATH` de Windows. Después vuelve a abrir la terminal y comprueba
`ffmpeg -version`.

### Instalar el programa

Abre PowerShell en esta carpeta y ejecuta:

```powershell
python -m pip install -r requirements.txt
python descargador.py
```

También puedes iniciar el programa haciendo doble clic en `descargador.py`
si `.py` está asociado con Python.

Como alternativa, haz doble clic en `iniciar_descargador.bat`. Este archivo
inicia el programa directamente sin tener que abrir PowerShell.

Si tienes Python instalado y quieres iniciar la aplicación sin que aparezca
una ventana de CMD, haz doble clic en `iniciar_descargador.vbs`.

## Crear el ejecutable de Windows

1. Obtén una distribución legítima de FFmpeg y coloca `ffmpeg.exe` y
   `ffprobe.exe` en `ffmpeg\bin`.
2. Abre PowerShell en esta carpeta.
3. Ejecuta:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

El resultado será `dist\Descargador.exe`, un único archivo que incluye la
aplicación y FFmpeg. Puedes distribuir ese archivo directamente.

## Uso

1. Pega un enlace en el primer campo. Al escribirlo, aparecerá
   automáticamente otro campo para añadir más enlaces.
2. Para una lista de reproducción, pega el enlace de la lista; se procesarán
   todos sus videos.
3. La carpeta predeterminada es `C:\Users\kenne\Music\canciones`. Puedes
   cambiarla con el botón **Buscar...** para seleccionar otra carpeta.
4. En **Formato de salida**, selecciona **MP3 (audio)** o **MP4 (video)**.
5. Pulsa el botón de descarga, que indicará **Descargar MP3** o
   **Descargar MP4** según el formato elegido.

Al elegir MP4, el programa pregunta cómo quieres seleccionar la calidad:

- **Sí**: descarga todos los videos con la máxima calidad disponible.
- **No**: consulta las calidades disponibles y muestra un selector
  independiente para cada video.
- **Cancelar**: vuelve a la pantalla principal sin iniciar la descarga.

También puedes usar **Limpiar enlaces** para quitar todos los campos y empezar
de nuevo.

La aplicación muestra la firma **by kenner manuel varilla fuentes** en la
ventana principal.

El programa crea un archivo oculto `.youtube-download-archive.txt` en la
carpeta de destino para no volver a descargar videos que ya se procesaron.
Los archivos se guardan como `Título [id].mp3` o `Título [id].mp4`.

## Ejecutar pruebas

```powershell
python -m unittest discover -s tests
```

## Publicar una versión

El código fuente puede publicarse en GitHub y el contenido de
`dist\Descargador.exe` puede subirse como un archivo independiente en una
Release. No
incluyas canciones, videos, `__pycache__` ni archivos de compilación en el
repositorio. Comprueba las licencias de FFmpeg y respeta los términos de
servicio de los sitios descargados.

Descarga únicamente contenido que tengas derecho a guardar y respeta los
términos de servicio y las leyes aplicables.

cd "C:\Users\kenne\Music\descargador"
python descargador.py