# v0.5.0 · Pausa y cierre nativo

- Nuevo botón Pausar/Reanudar junto al progreso. La descarga se detiene
  cooperativamente en el siguiente bloque o entre videos/etapas, sin perder
  archivos parciales. La interfaz distingue pausa solicitada y pausa aplicada.
- Cancelar funciona también durante la pausa. Una consulta de red o conversión
  de FFmpeg en curso termina antes de aplicar la pausa; no se suspende a la fuerza.
- Ventana Windows con marco nativo real, alfa y Acrylic sin WS_EX_LAYERED.
- Cierre compatible con los hooks que necesitan capturar una ventana visible:
  se evita que Qt oculte el HWND antes de su destrucción nativa.
- Se habilitan las transiciones nativas sin añadir una animación propia de
  cierre ni cambiar ajustes de Windows o Windhawk.
- Se conservan el acceso con Firefox, los formatos, las playlists, el centrado,
  las animaciones de la interfaz, los avisos y el TXT de fallos.

## Corrección del fallo de arranque

La compilación anterior podía recoger una `icuuc.dll` incompatible desde el PATH
del equipo, lo que impedía importar QtCore. Ahora se usa un entorno de compilación
separado con versiones fijadas y PATH controlado. El ejecutable debe superar un
diagnóstico de arranque aislado antes de publicarse. Los fallos de diagnóstico
se registran en JSON y terminan con error sin abrir un traceback modal.

## Verificación

48 pruebas, incluidas pausa/reanudación con hilos, cancelación durante la pausa,
bloqueo del siguiente video, filtro de metadatos y la protección de cierre.
Conversiones reales con medios sintéticos locales y diagnóstico del ejecutable.
También se verificó en Windows: marco nativo, canal alfa de 8 bits, ausencia de
WS_EX_LAYERED, HWND visible durante la ocultación solicitada por Qt y destrucción final.

El resultado visual de Windhawk depende del mod concreto y sus ajustes/exclusiones;
no se han validado todos los mods ni se modifican sus preferencias.
Las pruebas de sesión no utilizan cuentas reales.

Descarga Descargador-v0.5.0-Windows.zip, extrae el contenido y abre Descargador.exe
tras cerrar la versión anterior. Se incluye SHA256SUMS.txt para verificar el ZIP.
