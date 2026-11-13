# v0.4.1 · Restaurar el inicio de sesión con Firefox

Se restaura el flujo de inicio de sesión anterior a v0.4.0: se prefiere Firefox,
en lugar del navegador predeterminado, para evitar los problemas de sesión
reportados con Brave.

- Se abre únicamente el navegador seleccionado; no se abre Brave además de Firefox.
- Los clics repetidos y la comprobación al volver no abren un segundo navegador.
- Se mantienen el botón Ya inicié sesión y la detección de sesión al volver.
- Si Firefox no está instalado, se intenta con Edge o Chrome como antes; si no
  hay un navegador compatible, se muestra un aviso para instalar Firefox gratis.
- Se conservan la ventana centrada, Acrylic por foco, animaciones, bloqueo de
  controles, formatos de audio/video y el TXT de fallos.

Descarga `Descargador-v0.4.1-Windows.zip`, extrae sus archivos y abre
`Descargador.exe` después de cerrar la versión anterior. Se incluye SHA256SUMS.txt
para verificar la descarga.

Las pruebas de sesión se realizan con datos simulados, sin usar cuentas reales.
La cuenta debe poder ver el contenido en YouTube; no se omiten verificaciones
de edad ni permisos de acceso. Windows controla la disponibilidad de Acrylic.
