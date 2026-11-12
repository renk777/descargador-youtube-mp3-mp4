"""Real FFmpeg/yt-dlp integration using synthetic media and localhost only."""
import functools
import http.server
import json
import queue
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

import download_core as app


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(app.yt_dlp and app._ffmpeg_location(), 'Requiere yt-dlp y FFmpeg')
class LocalConversionTests(unittest.TestCase):
    def test_audio_video_and_repeat_archive(self):
        location = Path(app._ffmpeg_location())
        ffmpeg = location / ('ffmpeg.exe' if app.sys.platform == 'win32' else 'ffmpeg')
        ffprobe = location / ('ffprobe.exe' if app.sys.platform == 'win32' else 'ffprobe')
        if not ffprobe.is_file():
            self.skipTest('Requiere FFprobe para comprobar los archivos finales')
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
                            '-f', 'lavfi', '-i', 'color=c=purple:s=160x120:r=10',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                            '-t', '0.5', '-c:v', 'mpeg4', '-c:a', 'aac', str(base / 'sample.mp4')],
                           check=True, capture_output=True, timeout=30)
            handler = functools.partial(QuietHandler, directory=temp)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/sample.mp4'
                for fmt, quality in (('mp3', '192 kbps'), ('mp4', 'Mejor disponible')):
                    events = queue.Queue()
                    settings = app.DownloadSettings(base / 'output', fmt, quality)
                    settings.output.mkdir(exist_ok=True)
                    for attempt in range(2):
                        app.DownloadWorker(events, threading.Event()).run([url], settings)
                        messages = list(events.queue)
                        self.assertEqual(messages[-1][1]['completed'], 1, messages)
                        self.assertEqual(messages[-1][1]['failed'], [], messages)
                    files = list(settings.output.glob(f'*.{fmt}'))
                    self.assertEqual(len(files), 1)
                    self.assertGreater(files[0].stat().st_size, 100)
                    result = subprocess.run([str(ffprobe), '-v', 'error', '-show_streams',
                                             '-of', 'json', str(files[0])],
                                            check=True, capture_output=True, text=True, timeout=15)
                    streams = json.loads(result.stdout)['streams']
                    self.assertTrue(any(s['codec_type'] == 'audio' for s in streams))
                    if fmt == 'mp3':
                        self.assertEqual(streams[0]['codec_name'], 'mp3')
                    else:
                        self.assertTrue(any(s['codec_type'] == 'video' for s in streams))
                self.assertEqual(len(list((base / 'output').glob('.youtube-archive-*.txt'))), 2)
                # A real HTTP failure must not stop a later valid video.
                events = queue.Queue()
                bad = f'http://127.0.0.1:{server.server_port}/missing.mp4'
                app.DownloadWorker(events, threading.Event()).run([bad, url], settings)
                finished = list(events.queue)[-1][1]
                self.assertEqual(finished['failed'], [bad])
                self.assertEqual(finished['completed'], 1)
                self.assertEqual(Path(finished['report']).read_text(), bad + '\n')

                # Exercise every file format using real FFmpeg and known stream metadata.
                subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
                                '-i', str(base / 'sample.mp4'), '-c:v', 'libvpx-vp9',
                                '-c:a', 'libopus', str(base / 'sample.webm')],
                               check=True, capture_output=True, timeout=30)
                subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
                                '-i', str(base / 'sample.mp4'), '-vn', '-c:a', 'libopus', str(base / 'audio.webm')],
                               check=True, capture_output=True, timeout=30)
                for fmt in app.AUDIO_FORMATS + app.VIDEO_FORMATS:
                    settings_all = app.DownloadSettings(base / 'all-formats', fmt, app.QUALITY[fmt][0])
                    settings_all.output.mkdir(exist_ok=True)
                    worker = app.DownloadWorker(queue.Queue(), threading.Event())
                    opts = app._download_options(settings_all, worker.progress, worker.postprocess, worker, worker.cancel)
                    is_audio_webm = fmt == 'webm_audio'
                    ext = 'webm' if fmt in ('webm', 'webm_audio') else 'mp4'
                    filename = 'audio.webm' if is_audio_webm else 'sample.' + ext
                    info = {'id': fmt, 'title': 'Sintético', 'extractor_key': 'LocalTest',
                            'formats': [{'format_id': 'source', 'url': f'http://127.0.0.1:{server.server_port}/{filename}',
                                         'ext': ext, 'vcodec': 'none' if is_audio_webm else ('vp9' if ext == 'webm' else 'mpeg4'),
                                         'acodec': 'opus' if ext == 'webm' else 'aac', 'height': None if is_audio_webm else 120}]}
                    with app.yt_dlp.YoutubeDL(opts) as real_downloader:
                        real_downloader.process_ie_result(info, download=True)
                    expected_ext = 'webm' if is_audio_webm else fmt
                    media = [item for item in settings_all.output.iterdir()
                             if item.suffix == '.' + expected_ext and f'[{fmt}-' in item.name]
                    self.assertEqual(len(media), 1, (fmt, worker.errors))
                    result = subprocess.run([str(ffprobe), '-v', 'error', '-show_streams', '-of', 'json', str(media[0])],
                                            check=True, capture_output=True, text=True, timeout=15)
                    streams = json.loads(result.stdout)['streams']
                    self.assertTrue(any(stream['codec_type'] == 'audio' for stream in streams), fmt)
                    if fmt in app.AUDIO_FORMATS:
                        self.assertFalse(any(stream['codec_type'] == 'video' for stream in streams), fmt)

            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)



if __name__ == '__main__':
    unittest.main()
