# Componentes incluidos en el paquete de Windows

El código de Descargador usa la licencia MIT del archivo LICENSE.
Este paquete también incluye componentes de terceros con sus propias licencias.

- Qt / PySide6 Essentials y Shiboken 6.12.0: se utilizan bibliotecas dinámicas.
  La metadata de la distribución declara LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only.
  Texto LGPL en licenses/Qt-LGPL-3.0.txt.
  Código fuente: https://code.qt.io/cgit/pyside/pyside-setup.git/ y https://code.qt.io/cgit/qt/qtbase.git/.
  Información de distribución: https://doc.qt.io/qtforpython-6/licenses.html.
- yt-dlp 2026.10.26: licencia en licenses/yt-dlp-LICENSE.txt.
  Código fuente: https://github.com/yt-dlp/yt-dlp/tree/2026.10.26.
- FFmpeg y FFprobe 9.0.2, essentials build de Gyan: la configuración incluida
  habilita GPL y version3. Texto GPLv3 en licenses/FFmpeg-GPL-3.0.txt.
  Distribución y fuentes de compilación: https://www.gyan.dev/ffmpeg/builds/.
  Código fuente upstream: https://github.com/FFmpeg/FFmpeg.
- Deno v2.9.8: licencia MIT en licenses/Deno-MIT.txt.
  Código fuente: https://github.com/denoland/deno/tree/v2.9.8.

PyInstaller extrae temporalmente los componentes del ejecutable al abrirlo.
El código fuente de la aplicación, sus instrucciones de compilación y dependencias
están disponibles en https://github.com/renk777/descargador-youtube-mp3-mp4.
