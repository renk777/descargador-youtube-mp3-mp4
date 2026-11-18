"""Small startup boundary: diagnostics must fail with an exit code, not a modal traceback."""
import json
from pathlib import Path
import sys
import traceback


def load_application():
    # Static import is visible to PyInstaller while remaining inside the error boundary.
    import descargador
    return descargador


def main():
    check = '--check' in sys.argv
    report = None
    if '--diagnostic-report' in sys.argv:
        index = sys.argv.index('--diagnostic-report')
        if index + 1 < len(sys.argv):
            report = Path(sys.argv[index + 1])
    try:
        application = load_application()
        application.main()
        result = {'ok': True}
        from app_version import __version__
        result['version'] = __version__
        code = 0
    except Exception as error:
        result = {'ok': False, 'error': type(error).__name__, 'detail': str(error), 'traceback': traceback.format_exc()}
        code = 1
        if not check and sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,
                'No se pudo iniciar Descargador. Descarga de nuevo el paquete de Windows y extrae todos sus archivos.\n\n'
                'No necesitas copiar DLL ni cambiar la seguridad de Windows.', 'No se pudo iniciar Descargador', 0x10)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
