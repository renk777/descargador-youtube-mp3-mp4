"""Friendly error messages shared by the GUI and the download worker."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UserError:
    code: str
    title: str
    message: str


def describe_error(error) -> UserError:
    text = str(error).lower()
    if any(term in text for term in ('app-bound', 'dpapi', 'decrypt', 'cookie database', 'cookies database', 'could not copy chrome')):
        return UserError('session_locked', 'No pudimos conectar la sesión',
                         'Windows o el navegador no permiten leer esa sesión. Prueba el acceso con Firefox. No abriremos otro navegador automáticamente; puedes continuar con los videos que no necesitan sesión.')
    if any(term in text for term in ('getaddrinfo', 'name resolution', 'no such host', '11001', '10051',
                                     'network is unreachable', 'network unreachable', 'no internet', 'sin conexión', 'sin conexion',
                                     'unable to resolve', 'failed to resolve', 'temporary failure in name')):
        return UserError('offline', 'No hay conexión a Internet',
                         'Comprueba el Wi-Fi o el cable de red y vuelve a intentarlo. Tus archivos descargados se conservan.')
    if any(term in text for term in ('timed out', 'timeout', '10060', 'connection reset', 'connection aborted', 'connection refused')):
        return UserError('connection', 'La conexión se interrumpió',
                         'YouTube no respondió a tiempo. Comprueba tu conexión; puedes reintentar los videos fallidos al terminar.')
    if any(term in text for term in ('certificate verify', 'certificate_verify', 'ssl error', 'sslerror', 'tls handshake')):
        return UserError('secure_connection', 'No pudimos establecer una conexión segura',
                         'Comprueba la fecha del equipo y la conexión de red. Puedes volver a intentarlo sin cambiar la seguridad del navegador.')
    if any(term in text for term in ('no space left', 'disk full', 'espacio en el disco', 'winerror 112', 'errno 28')):
        return UserError('disk_full', 'No queda espacio en la carpeta',
                         'Libera espacio o elige otra unidad antes de volver a descargar.')
    if any(term in text for term in ('permission denied', 'access is denied', 'acceso denegado', 'winerror 5')):
        return UserError('permission', 'No podemos guardar en esa carpeta',
                         'Elige una carpeta donde puedas guardar archivos, como Música o Descargas.')
    if any(term in text for term in ('age-restricted', 'age restricted', 'confirm your age', 'sign in', 'login required', 'authentication', 'not a bot')):
        return UserError('authentication', 'Este video necesita una sesión de YouTube',
                         'Pulsa Iniciar sesión en YouTube y entra con una cuenta que pueda ver el video. Después podrás reintentarlo.')
    if any(term in text for term in ('private video', 'video unavailable', 'not available', 'removed', 'copyright', '404', 'video privado')) and 'format' not in text:
        return UserError('unavailable', 'Este video no está disponible',
                         'Puede ser privado, haber sido eliminado o no estar disponible en tu región. Continuaremos con los demás.')
    if any(term in text for term in ('requested format', 'no video formats', 'format is not available')):
        return UserError('format', 'No está disponible ese formato o calidad',
                         'Prueba otra calidad o un formato diferente. Los demás videos seguirán descargándose.')
    if any(term in text for term in ('429', 'too many requests', 'rate limit')):
        return UserError('rate_limit', 'YouTube pide esperar un momento',
                         'Se han recibido demasiadas solicitudes. Espera unos minutos antes de reintentar los fallos.')
    if any(term in text for term in ('ffmpeg', 'postprocessing', 'conversion')):
        return UserError('conversion', 'No pudimos preparar el archivo final',
                         'Hubo un problema al convertir el archivo. Prueba otro formato; los detalles están en el registro.')
    return UserError('download', 'No pudimos descargar este video',
                     'Continuaremos con los demás. Podrás reintentarlo al terminar y consultar el TXT de fallos.')
