# Descargador de YouTube · v0.4.1

Aplicación de escritorio en Python con Qt (PySide6), yt-dlp, FFmpeg y Deno.
El logo aparece únicamente en el icono del ejecutable y en la barra de título,
sin una imagen de marca dentro del contenido.

## Descargar para Windows

Obtén el paquete portable en [la última versión](https://github.com/renk777/descargador-youtube-mp3-mp4/releases/latest),
extrae el ZIP y abre `Descargador.exe`. No necesitas instalar Python.

## Iniciar desde código

```powershell
python -m pip install -r requirements.txt
python descargador.py
```

Requiere Python 3.10 o posterior. También puedes abrir
`dist\Descargador.exe`, `iniciar_descargador.bat` o `iniciar_descargador.vbs`.

El ejecutable incluye Qt, FFmpeg, FFprobe, Deno y los scripts EJS de yt-dlp.
Al ejecutar desde código, FFmpeg y FFprobe deben estar en `ffmpeg\bin` o en
el PATH; Deno en `runtime\deno.exe` o en el PATH. También se admite Node
instalado en el PATH si cumple los requisitos de yt-dlp.

## Apariencia y ventana

- Acrylic se activa automáticamente cuando seleccionas la ventana. Al salir
  de ella, el fondo pasa a gris sólido con una transición de 190 ms.
- No hay botón ni preferencia para alternar el efecto. La configuración antigua
  de ese botón se ignora. Los textos y botones mantienen su opacidad completa.
- Se utiliza una política nativa de composición Acrylic para la superficie
  transparente de Qt. Los fondos del área desplazable no tapan esa superficie.
- Windows controla la disponibilidad final del efecto: transparencia,
  accesibilidad, composición del escritorio o escritorio remoto pueden limitarlo.
  Si no está disponible se conserva un fondo gris legible.
- Hay entrada gradual de los paneles, animación de botones al pasar el cursor,
  progreso suave y símbolos animados durante las operaciones.
- Al abrirse, la ventana se centra en el área útil del monitor, sin invadir la
  barra de tareas; se adapta a pantallas pequeñas. No vuelve a centrarse al
  restaurarla después de que la hayas movido.
- La barra de título permite arrastrar, minimizar, maximizar y cerrar. Un doble
  clic maximiza/restaura; el tirador inferior derecho cambia el tamaño.
- Los botones y avisos importantes permanecen fuera del área desplazable.

## Formato y calidad

Selecciona **Solo audio** o **Video + audio**, luego el formato y su calidad.

| Tipo | Formatos |
| --- | --- |
| Audio | MP3, M4A, Opus, FLAC, WAV, WebM de audio |
| Video | MP4, WebM, MKV |

MP3, M4A y Opus permiten elegir bitrate. FLAC y WAV evitan otra compresión con
pérdida, pero no recuperan información perdida en la fuente de YouTube.
WebM de audio conserva el flujo original Opus/Vorbis y no cambia su bitrate.

En video se puede elegir la mejor calidad disponible o un máximo entre 360p
y 2160p. MP4 y WebM seleccionan flujos compatibles con su contenedor; si ese
video no ofrece ese formato, se registra el fallo y se continúa. MKV admite
una selección más amplia de códecs. No se promete una resolución que la
fuente no tenga.

## Iniciar sesión en YouTube (gratuito)

1. Pulsa **Iniciar sesión en YouTube**. Se abre directamente la página de
   acceso de Google/YouTube en un navegador instalado.
2. Inicia sesión allí como siempre. La aplicación no recibe tu contraseña.
3. Vuelve al descargador: se comprueba la sesión automáticamente. También
   puedes pulsar **Ya inicié sesión**.
4. Cuando aparezca **YouTube conectado**, inicia tus descargas.

Se restaura el acceso que prefiere Firefox si está instalado. La página se
abre directamente en ese navegador, sin abrir también Brave ni el navegador
predeterminado. Si Firefox no está instalado, se busca Edge o Chrome como en
el flujo anterior. Si no hay ninguno compatible, se explica que puedes instalar
Firefox gratuitamente.

Los clics repetidos mientras está pendiente el acceso no abren nuevas ventanas.
Al volver al descargador se comprueba la sesión del mismo navegador que se abrió.
Si Windows protege sus cookies, se explica la limitación sin abrir otro navegador
automáticamente. Los videos que no requieren sesión siguen disponibles.

No necesitas exportar cookies, contratar un servicio, configurar claves API ni
pagar por esta función. No se incluye ningún servicio de pago. La selección
actual de sesión no se guarda entre ejecuciones; el navegador conserva su
sesión como lo hace normalmente. La aplicación comprueba solo la presencia de
una sesión de YouTube y utiliza el mecanismo de autenticación de yt-dlp.

Para videos con restricción de edad la cuenta debe poder verlos en YouTube.
No se omiten comprobaciones de edad, permisos, bloqueos regionales ni acceso
a contenido privado. Que la sesión esté conectada no garantiza que YouTube
permita descargar un video concreto.

Referencias de yt-dlp:
[sesiones para contenido restringido](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
y [motor JavaScript y EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

## Controles y avisos animados

Al iniciar una descarga se bloquean el formato, la calidad, los enlaces, la
carpeta, la sesión, los botones de pegar/limpiar/abrir y los reintentos. También
se desactiva Ctrl+Enter para evitar comenzar otro lote. **Cancelar** permanece
disponible. Los controles se recuperan al finalizar, cancelar o fallar la
preparación de la descarga; mover, minimizar y cerrar la ventana sigue permitido.

Antes de comenzar se comprueba la conexión con YouTube en un hilo secundario.
Si no hay conexión se muestra un aviso animado con **Reintentar**, sin perder
los enlaces ni marcar como fallidos videos que aún no se intentaron descargar.
También hay mensajes propios para conexiones interrumpidas, sesiones protegidas,
videos privados/eliminados, restricciones de edad, formatos no disponibles,
carpetas sin permiso, disco lleno, conversiones fallidas y exceso de solicitudes.
El registro conserva el detalle técnico; los avisos explican cómo continuar.

## Lotes, playlists y TXT de fallos

- Pega uno o varios enlaces separados por líneas, espacios o tabulaciones.
  Los enlaces idénticos se eliminan automáticamente.
- **Incluir listas de reproducción** expande una playlist en videos separados.
  Si se desactiva, los enlaces con video y lista descargan solo el video.
- Cada video se procesa de forma independiente. Si falla por restricción,
  privacidad, conexión o conversión, el programa pasa al siguiente.
- Se muestra el estado de cada video, progreso del archivo actual, velocidad,
  tiempo restante y detalles de errores.
- Al finalizar cada lote se crea `fallidos_AAAAMMDD_HHMMSS_microsegundos.txt`
  en la carpeta de destino. Contiene exclusivamente los enlaces fallidos,
  sin duplicados y uno por línea. Si no hubo fallos, el TXT está vacío.
- En playlists se registran los enlaces de los videos concretos, incluidos
  privados o eliminados si YouTube conserva su ID en la lista. Si YouTube
  impide leer toda la playlist o no devuelve el ID de una entrada, se registra
  el enlace de la lista con el error de enumeración en la actividad.
- **Ver TXT de fallos** abre el reporte del último lote. **Reintentar fallidos**
  vuelve a intentarlos con las opciones y sesión del intento original.
- **Cancelar** detiene cooperativamente el lote y también escribe el reporte
  de los fallos ocurridos hasta entonces. Los videos no intentados o cancelados
  no se marcan como fallidos. Una operación de red o conversión puede tardar
  en terminar antes de atender la cancelación.

**Ctrl+Enter** inicia la descarga. **Abrir carpeta** muestra el destino.
La carpeta, el formato, la calidad y las opciones de descarga se recuerdan en
`%APPDATA%\DescargadorYouTube\config.json`. La actividad es de la sesión actual.

Los nombres incluyen título, ID y perfil. Cada formato/calidad tiene su
propio archivo `.youtube-archive-*.txt`, para poder guardar el mismo video
en distintos formatos. Si borraste un archivo y quieres recuperarlo,
desactiva **Omitir descargas completadas**. Los archivos existentes no se
sobrescriben. Los registros del programa anterior se conservan.

## Compilar y verificar

```powershell
python -m unittest discover -s tests -v
python descargador.py --check
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
.\dist\Descargador.exe --check
```

El diagnóstico `--check` comprueba Qt, logo, FFmpeg, FFprobe y motor JavaScript
sin abrir la interfaz. Su código de salida es 0 si todo está disponible.
Las pruebas incluyen conversiones reales de los nueve perfiles de archivo
con contenido sintético local, continuación tras un error HTTP, fallos
individuales de playlists simuladas, mensajes de red, conexión al navegador simulada y estados de UI.
No usan sesiones reales ni cuentas de usuario.

La compilación requiere `logo.png`, `ffmpeg\bin\ffmpeg.exe`,
`ffmpeg\bin\ffprobe.exe` y `runtime\deno.exe`. El runtime incluido proviene de
la distribución oficial Deno v2.9.8; `runtime\VERSION.txt` contiene la suma
SHA256 del archivo original. Su licencia está en `runtime\LICENSE.md`.
El script usa PyInstaller y Pillow (solo para generar el icono), incluye los
recursos y comprueba los códigos de salida sin borrar las carpetas existentes.

La firma del autor se conserva: **by kenner manuel varilla fuentes**.
Descarga contenido que tengas derecho a guardar. Al distribuir el programa,
conserva las licencias de Qt/PySide6, yt-dlp, FFmpeg, Deno y sus componentes.
