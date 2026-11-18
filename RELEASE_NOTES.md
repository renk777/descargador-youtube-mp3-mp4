# v0.5.1 · Correcciones visuales y controles de descarga

- Corregidos los controles duplicados de la barra de título sin quitar los estilos
  nativos necesarios para las animaciones de Windows y Windhawk.
- Eliminado el efecto de opacidad persistente en tarjetas que causaba recortes.
  El área transparente se repinta al desplazar y redimensionar la ventana.
  Se mantienen las animaciones de botones, avisos, progreso y cambio de foco.
- Un solo botón principal: Descargar → Pausar → Reanudar. Cancelar aparece durante
  un lote y desaparece al terminar; los ajustes permanecen bloqueados mientras descarga.
- Ver TXT de fallos y Reintentar fallidos aparecen al terminar únicamente si hay fallos.
- Los lotes sin errores ya no generan informes TXT vacíos ni muestran un aviso
  incorrecto de error al guardar el reporte.
- El historial interno para evitar duplicados se guarda en los datos de la aplicación,
  fuera de la carpeta de canciones, separado por destino, formato y calidad.
  Se trasladan los archivos de historial antiguos conservando sus entradas.

## Verificación

54 pruebas automatizadas, incluidas las conversiones reales con yt-dlp/FFmpeg,
pausa, cancelación, visibilidad de controles, informes y traslado del historial.
Inspección de capturas de una ventana nativa al redimensionar y desplazar:
sin controles duplicados ni franjas desaparecidas. Se conserva Acrylic y el HWND
sin WS_EX_LAYERED; la captura de ventana no incluye el desenfoque del compositor.
Diagnóstico de arranque del ejecutable compilado en entorno aislado y normal.
La animación final depende del mod y sus ajustes; no se han probado todos los mods.

Descarga Descargador-v0.5.1-Windows.zip, extrae el contenido y abre Descargador.exe
tras cerrar la versión anterior. Se incluye SHA256SUMS.txt para verificar el ZIP.
