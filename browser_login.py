"""Free browser sign-in flow. Passwords are entered only in the external browser."""
import os
import socket
import shutil
import subprocess
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LOGIN_URL = 'https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F'


def available_browser():
    """Restore Firefox-first session sharing without opening the default browser."""
    for key, exe, locations in (
        ('firefox', 'firefox.exe', ('Mozilla Firefox/firefox.exe',)),
        ('edge', 'msedge.exe', ('Microsoft/Edge/Application/msedge.exe',)),
        ('chrome', 'chrome.exe', ('Google/Chrome/Application/chrome.exe',)),
    ):
        found = shutil.which(exe)
        if found:
            return key, found
        for base in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)'), os.environ.get('LOCALAPPDATA')):
            if base:
                for relative in locations:
                    candidate = Path(base) / relative
                    if candidate.is_file():
                        return key, str(candidate)
    return None


def open_sign_in(browser):
    """Launch only the selected browser once; never also dispatch to the default."""
    if not browser:
        raise OSError('No se encontró un navegador compatible. Instala Firefox para conectar tu sesión.')
    key, executable = browser
    args = [executable, '-new-tab', LOGIN_URL] if key == 'firefox' else [executable, LOGIN_URL]
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
