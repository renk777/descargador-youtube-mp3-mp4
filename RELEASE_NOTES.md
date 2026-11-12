# v0.4.0 · Navegador predeterminado y ventana centrada

La sesión de YouTube abre únicamente el navegador predeterminado del dispositivo.
Se elimina la preferencia por Firefox y se evitan aperturas adicionales al repetir
el clic o volver a la aplicación. La ventana aparece centrada en el área útil del
monitor y se adapta a pantallas pequeñas.

## Novedades desde v0.3.0

- Nueva interfaz Qt con Acrylic según el foco, fondo gris al salir, animaciones
  y avisos de error propios. El logo aparece en la barra superior y en el ejecutable.
- Inicio de sesión gratuito desde el navegador predeterminado, incluido Brave;
  comprobación al volver a la aplicación, sin exportar archivos de cookies.
- Audio MP3, M4A, Opus, FLAC, WAV y WebM; video MP4, WebM y MKV, con calidad seleccionable.
- Procesamiento independiente de los videos de playlists: un error no detiene los demás.
- TXT automático con los enlaces individuales fallidos y opción para reintentarlos.
- Controles bloqueados durante la descarga, con Cancelar disponible; comprobación
  de conexión previa y mensajes para red, formato, sesión, permisos y espacio.
- Registros separados por formato/calidad, reanudación y preferencias guardadas.
- Paquete de Windows con FFmpeg, FFprobe y Deno incluidos.

## Uso

Descarga `Descargador-v0.4.0-Windows.zip`, extrae todos sus archivos y abre
`Descargador.exe`. Cierra la versión anterior antes de abrir esta.

## Verificación y límites

39 pruebas aprobadas, incluidas conversiones reales con contenido sintético local,
fallos de playlists, bloqueo de controles, navegador predeterminado y centrado.
El ejecutable se valida con `--check` antes de adjuntarlo.

Windows controla la disponibilidad de Acrylic; la captura nativa de este entorno
no permitió confirmar visualmente el desenfoque compuesto final. La lectura de
sesiones protegidas por el navegador/Windows puede no estar disponible; en ese
caso se avisa y no se abre otro navegador. Iniciar sesión no omite verificaciones
de edad ni permisos de YouTube. No se han utilizado cuentas reales en las pruebas.
