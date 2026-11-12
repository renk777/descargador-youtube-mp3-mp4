from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from user_errors import describe_error

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

BG, PANEL, FIELD = "#101017", "#191923", "#222230"
TEXT, MUTED, ACCENT = "#f3f0f7", "#a6a2b8", "#e34260"
AUDIO_FORMATS = ("mp3", "m4a", "opus", "flac", "wav", "webm_audio")
VIDEO_FORMATS = ("mp4", "webm", "mkv")
AUDIO_QUALITY = ("192 kbps", "320 kbps", "256 kbps", "128 kbps", "96 kbps")
VIDEO_QUALITY = ("Mejor disponible", "2160p", "1440p", "1080p", "720p", "480p", "360p")
QUALITY = {fmt: AUDIO_QUALITY for fmt in AUDIO_FORMATS}
QUALITY.update({fmt: VIDEO_QUALITY for fmt in VIDEO_FORMATS})
QUALITY.update({"flac": ("Sin pérdida adicional",), "wav": ("Sin pérdida adicional",),
                "webm_audio": ("Audio original (Opus/Vorbis)",)})
FORMAT_NAMES = {"webm_audio": "WebM (audio)", **{fmt: fmt.upper() for fmt in AUDIO_FORMATS + VIDEO_FORMATS if fmt != "webm_audio"}}



def _application_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _default_output_dir() -> Path:
    home = Path.home()
    music = next((home / name for name in ("Music", "Música")
                  if (home / name).is_dir()), home / "Music")
    return music / "canciones"


def _config_path() -> Path:
    base = Path(os.environ["APPDATA"]) if os.environ.get("APPDATA") else Path.home() / ".config"
    return base / "DescargadorYouTube" / "config.json"


def _load_settings() -> dict:
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _load_output_dir() -> Path:
    value = _load_settings().get("output_dir")
    return Path(value) if isinstance(value, str) and value.strip() else _default_output_dir()


def _save_settings(settings: dict) -> None:
    target = _config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def _save_output_dir(output_dir: Path) -> None:
    _save_settings({**_load_settings(), "output_dir": str(output_dir)})


def _ffmpeg_location() -> str | None:
    locations = [_application_dir() / "ffmpeg" / "bin"]
    if getattr(sys, "frozen", False):
        locations.append(Path(sys.executable).resolve().parent / "ffmpeg" / "bin")
    for location in locations:
        if (location / "ffmpeg.exe").is_file() or (location / "ffmpeg").is_file():
            return str(location)
    executable = shutil.which("ffmpeg")
    return str(Path(executable).parent) if executable else None


def _is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in {"http", "https"} and not parsed.username
                and not parsed.password and parsed.port in {None, 80, 443}
                and (host in {"youtu.be", "youtube.com", "youtube-nocookie.com"}
                     or host.endswith(".youtube.com"))
                and parsed.path not in {"", "/"})
    except ValueError:
        return False


def _parse_urls(text: str) -> list[str]:
    return list(dict.fromkeys(re.split(r"\s+", text.strip()))) if text.strip() else []


@dataclass(frozen=True)
class DownloadSettings:
    output: Path
    media_format: str = "mp3"
    quality: str = "192 kbps"
    playlist: bool = True
    skip_completed: bool = True
    cookie_file: str = ""
    cookie_browser: str = ""


class DownloadCancelled(yt_dlp.utils.DownloadCancelled if yt_dlp else Exception):
    pass



def _js_runtime():
    for name in ('deno', 'node'):
        bundled = _application_dir() / 'runtime' / (name + '.exe' if sys.platform == 'win32' else name)
        executable = str(bundled) if bundled.is_file() else shutil.which(name)
        if executable:
            return {name: {'path': executable}}
    return {}


def _download_options(settings, progress_hook, postprocessor_hook, logger, cancel_event):
    quality = settings.quality.split()[0].removesuffix('p')
    profile_quality = quality if quality.isdigit() else ('original' if settings.media_format in AUDIO_FORMATS else 'best')
    profile = f'{settings.media_format}-{profile_quality}'

    def check_cancel(_info, *, incomplete=False):
        if cancel_event.is_set():
            raise DownloadCancelled('Cancelado por el usuario')
        return None

    options = {
        'outtmpl': str(settings.output / f'%(title).140B [%(id)s] [{profile}].%(ext)s'),
        'noplaylist': not settings.playlist, 'ignoreerrors': False,
        'quiet': True, 'no_warnings': False, 'continuedl': True, 'overwrites': False,
        'windowsfilenames': True, 'retries': 3, 'fragment_retries': 3, 'socket_timeout': 15,
        'progress_hooks': [progress_hook], 'postprocessor_hooks': [postprocessor_hook],
        'match_filter': check_cancel, 'logger': logger, 'js_runtimes': _js_runtime(),
    }
    if settings.cookie_file:
        options['cookiefile'] = settings.cookie_file
    elif settings.cookie_browser:
        options['cookiesfrombrowser'] = (settings.cookie_browser,)
    if settings.skip_completed:
        options['download_archive'] = str(settings.output / f'.youtube-archive-{profile}.txt')
    location = _ffmpeg_location()
    if location:
        options['ffmpeg_location'] = location
    fmt = settings.media_format
    if fmt in AUDIO_FORMATS:
        options['format'] = 'bestaudio[ext=webm]' if fmt == 'webm_audio' else 'bestaudio/best'
        if fmt == 'webm_audio':
            options['postprocessors'] = []
        else:
            processor = {'key': 'FFmpegExtractAudio', 'preferredcodec': fmt}
            if quality.isdigit():
                processor['preferredquality'] = quality
            options['postprocessors'] = [processor]
    else:
        limit = f'[height<={quality}]' if quality.isdigit() else ''
        if fmt == 'webm':
            options['format'] = f'bestvideo[ext=webm]{limit}+bestaudio[ext=webm]/best[ext=webm]{limit}'
        elif fmt == 'mp4':
            options['format'] = f'bestvideo[ext=mp4]{limit}+bestaudio[ext=m4a]/best[ext=mp4]{limit}'
        else:
            options['format'] = f'bestvideo{limit}+bestaudio/best{limit}'
        options['merge_output_format'] = fmt
        options['postprocessors'] = [{'key': 'FFmpegVideoRemuxer', 'preferedformat': fmt}]
    options['postprocessors'].append({'key': 'FFmpegMetadata'})
    return options


def _entry_url(entry):
    """Flat YouTube entries retain IDs even when a video is private/deleted."""
    if not isinstance(entry, dict):
        return None
    video_id = entry.get('id')
    if video_id and re.fullmatch(r'[A-Za-z0-9_-]{11}', str(video_id)):
        return f'https://www.youtube.com/watch?v={video_id}'
    value = entry.get('webpage_url') or entry.get('url')
    if isinstance(value, str) and value.startswith(('https://', 'http://')):
        return value
    return None


def _write_failure_report(output: Path, failed: list[str]) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    report = output / f"fallidos_{datetime.now():%Y%m%d_%H%M%S_%f}.txt"
    with report.open('x', encoding='utf-8') as handle:
        handle.write(''.join(url + '\n' for url in dict.fromkeys(failed)))
    return report


class DownloadWorker:
    """Sequential video jobs, independent of the GUI; one failure never aborts the batch."""

    def __init__(self, events, cancel):
        self.events, self.cancel = events, cancel
        self.last_progress = 0.0
        self.errors = []

    def debug(self, message):
        pass

    def warning(self, message):
        self.events.put(('log', f'Aviso: {message}'))

    def error(self, message):
        self.errors.append(str(message))
        self.events.put(('log', str(message)))

    def _check_cancel(self):
        if self.cancel.is_set():
            raise DownloadCancelled('Cancelado por el usuario')

    def progress(self, data):
        self._check_cancel()
        if data.get('status') == 'downloading':
            now = time.monotonic()
            if now - self.last_progress < 0.15:
                return
            self.last_progress = now
            total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
            percent = min(100, (data.get('downloaded_bytes') or 0) / total * 100) if total else 0
            title = (data.get('info_dict') or {}).get('title') or Path(data.get('filename', '')).name
            speed, eta = data.get('speed'), data.get('eta')
            detail = f'{speed / 1048576:.1f} MB/s' if speed else 'Calculando velocidad'
            if isinstance(eta, (float, int)):
                detail += f'  ·  {int(eta) // 60:02}:{int(eta) % 60:02} restantes'
            self.events.put(('progress', (percent, str(title), detail)))
        elif data.get('status') == 'finished':
            self.events.put(('status', 'Archivo recibido · preparando el formato final…'))

    def postprocess(self, data):
        self._check_cancel()
        if data.get('status') in {'started', 'processing'}:
            self.events.put(('status', 'Procesando audio / video con FFmpeg…'))

    def _expand(self, url, downloader, settings):
        parsed = urlparse(url)
        collection_path = parsed.path.startswith(('/playlist', '/@', '/channel/', '/user/'))
        is_list = 'list' in parse_qs(parsed.query) or collection_path
        if not settings.playlist and collection_path:
            raise RuntimeError('Activa Incluir listas de reproducción para procesar este enlace de colección.')
        if not settings.playlist or not is_list:
            yield url
            return
        self.events.put(('status', 'Leyendo videos de la playlist…'))
        info = downloader.extract_info(url, download=False)
        if not isinstance(info, dict):
            raise RuntimeError('No se pudo consultar la playlist.')
        if 'entries' not in info:
            yield _entry_url(info) or url
            return

        def walk(entries):
            for entry in entries:
                self._check_cancel()
                if isinstance(entry, dict) and 'entries' in entry:
                    yield from walk(entry['entries'])
                else:
                    video_url = _entry_url(entry)
                    if video_url:
                        yield video_url
                    else:
                        raise RuntimeError('YouTube no proporcionó el ID de una entrada de la playlist.')
        found = False
        for value in walk(info['entries']):
            found = True
            yield value
        if not found:
            raise RuntimeError('La playlist está vacía o sus videos no están disponibles.')

    def run(self, urls: list[str], settings: DownloadSettings):
        failed, completed, cancelled, seen = [], 0, False, set()
        report = None
        index = 0
        try:
            settings.output.mkdir(parents=True, exist_ok=True)
            # yt-dlp saves its cookie jar on exit. Never overwrite the user's source file.
            with tempfile.TemporaryDirectory(prefix='descargador-session-') as temporary:
                if settings.cookie_file:
                    cookie_copy = Path(temporary) / 'cookies.txt'
                    shutil.copyfile(settings.cookie_file, cookie_copy)
                    settings = replace(settings, cookie_file=str(cookie_copy))
                options = _download_options(settings, self.progress, self.postprocess, self, self.cancel)
                with yt_dlp.YoutubeDL(options) as downloader:
                    for submitted in urls:
                        self._check_cancel()
                        try:
                            # Flat entries let the worker isolate errors to individual videos.
                            original_flat = downloader.params.get('extract_flat', False)
                            downloader.params['extract_flat'] = 'in_playlist'
                            targets = self._expand(submitted, downloader, settings)
                            for url in targets:
                                self._check_cancel()
                                if url in seen:
                                    continue
                                seen.add(url)
                                job = index
                                index += 1
                                self.events.put(('job_add', (job, url)))
                                self.events.put(('job', (job, 'Procesando')))
                                self.events.put(('status', f'Video {index} · consultando YouTube…'))
                                self.errors = []
                                try:
                                    downloader.params['extract_flat'] = False
                                    downloader.extract_info(url, download=True)
                                    self._check_cancel()
                                    if self.errors:
                                        raise RuntimeError(self.errors[-1] if self.errors else 'La descarga no pudo completarse.')
                                except Exception as error:
                                    if self.cancel.is_set():
                                        self.events.put(('job', (job, 'Cancelado')))
                                        raise DownloadCancelled() from error
                                    failed.append(url)
                                    self.events.put(('download_error', (url, describe_error(error))))
                                    self.events.put(('job', (job, 'Error')))
                                    self.events.put(('log', f'{url}\n{error}'))
                                else:
                                    completed += 1
                                    self.events.put(('job', (job, 'Completado / existente')))
                                finally:
                                    downloader.params['extract_flat'] = 'in_playlist'
                                self.events.put(('batch', (completed, len(failed), index)))
                            downloader.params['extract_flat'] = original_flat
                        except DownloadCancelled:
                            raise
                        except Exception as error:
                            failed.append(submitted)
                            self.events.put(('download_error', (submitted, describe_error(error))))
                            self.events.put(('job_add', (index, submitted)))
                            self.events.put(('job', (index, 'Error al leer lista')))
                            index += 1
                            self.events.put(('log', f'No se pudo leer {submitted}: {error}'))
        except DownloadCancelled:
            cancelled = True
        except Exception as error:
            if self.cancel.is_set():
                cancelled = True
            else:
                failed.extend(url for url in urls if url not in seen and url not in failed)
                self.events.put(('download_error', ('', describe_error(error))))
                self.events.put(('log', str(error)))
        finally:
            failed = list(dict.fromkeys(failed))
            try:
                report = _write_failure_report(settings.output, failed)
                self.events.put(('log', f'Reporte de enlaces fallidos: {report}'))
            except OSError as error:
                self.events.put(('log', f'No se pudo guardar el TXT de fallos: {error}'))
            self.events.put(('finished', {'completed': completed, 'failed': failed,
                                          'cancelled': cancelled, 'report': str(report) if report else None}))
