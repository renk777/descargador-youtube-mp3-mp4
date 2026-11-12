"""Free browser sign-in flow. Passwords are entered only in the external browser."""
import os
import socket
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LOGIN_URL = 'https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F'


def _default_browser_executable():
    """Read Windows' effective HTTPS association without launching any application."""
    if sys.platform != 'win32':
        return ''
    try:
        import ctypes
        from ctypes import wintypes
        query = ctypes.WinDLL('shlwapi').AssocQueryStringW
        query.argtypes = [wintypes.DWORD, ctypes.c_int, wintypes.LPCWSTR, wintypes.LPCWSTR,
                          wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        query.restype = ctypes.c_long
        length = wintypes.DWORD()
        query(0x1000, 2, 'https', None, None, ctypes.byref(length))
        if not 0 < length.value < 32768:
            return ''
        buffer = ctypes.create_unicode_buffer(length.value)
        if query(0x1000, 2, 'https', None, buffer, ctypes.byref(length)) == 0:
            return buffer.value
    except (OSError, AttributeError):
        pass
    return ''


def available_browser():
    # Detection is solely for reading that same browser's session. Never pick another browser.
    from pathlib import PureWindowsPath
    executable = PureWindowsPath(_default_browser_executable().strip('"')).name.lower()
    known = {
        'brave.exe': ('brave', 'Brave'), 'chrome.exe': ('chrome', 'Chrome'),
        'msedge.exe': ('edge', 'Edge'), 'firefox.exe': ('firefox', 'Firefox'),
        'opera.exe': ('opera', 'Opera'), 'vivaldi.exe': ('vivaldi', 'Vivaldi'),
        'chromium.exe': ('chromium', 'Chromium'), 'whale.exe': ('whale', 'Whale'),
    }
    return known.get(executable, ('', 'tu navegador predeterminado'))


def open_sign_in(browser=None):
    """Exactly one system-default URL dispatch; no executable launches or fallbacks."""
    if sys.platform == 'win32':
        os.startfile(LOGIN_URL)
    else:
        import webbrowser
        if not webbrowser.open(LOGIN_URL, new=2):
            raise OSError('El sistema no pudo abrir el navegador predeterminado.')


def verify_browser_session(browser_name):
    # Called only after the user explicitly confirms finishing sign-in.
    from yt_dlp.cookies import extract_cookies_from_browser
    jar = extract_cookies_from_browser(browser_name)
    names = {'SAPISID', '__Secure-3PAPISID', '__Secure-1PAPISID', 'LOGIN_INFO'}
    for cookie in jar:
        host = cookie.domain.lstrip('.').lower()
        if (host == 'youtube.com' or host.endswith('.youtube.com')) and cookie.name in names and cookie.value and not cookie.is_expired():
            return True
    return False


def check_connection():
    """Background-only probe. HTTP refusal still proves there is a connection."""
    try:
        request = Request('https://www.youtube.com/robots.txt', method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=5):
            pass
    except HTTPError:
        return
    except (OSError, socket.timeout) as error:
        raise ConnectionError(str(error)) from error
