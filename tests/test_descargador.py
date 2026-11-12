import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import download_core as app


class YouTubeUrlTests(unittest.TestCase):
    def test_accepts_supported_hosts(self):
        for url in ('https://www.youtube.com/watch?v=abc', 'https://youtu.be/abc',
                    'https://m.youtube.com/shorts/abc', 'https://youtube.com/playlist?list=abc'):
            with self.subTest(url=url):
                self.assertTrue(app._is_youtube_url(url))

    def test_rejects_spoofed_and_malformed_urls(self):
        for url in ('https://example.com/video', 'ftp://youtube.com/video', 'not-a-url',
                    'https://youtube.com.evil.test/watch', 'https://evil.test@youtube.com/watch',
                    'https://youtube.com:bad/watch', 'https://[youtube.com/watch', 'https://youtube.com/'):
            with self.subTest(url=url):
                self.assertFalse(app._is_youtube_url(url))

    def test_multiline_and_duplicate_paste(self):
        self.assertEqual(app._parse_urls(' \nhttps://youtu.be/a\thttps://youtu.be/b\nhttps://youtu.be/a '),
                         ['https://youtu.be/a', 'https://youtu.be/b'])
        self.assertEqual(app._parse_urls(' \n '), [])


class SettingsTests(unittest.TestCase):
    def test_corrupt_or_wrong_type_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'config.json'
            with patch.object(app, '_config_path', return_value=target):
                for value in ('null', '[]', '42', '{broken'):
                    target.write_text(value)
                    self.assertEqual(app._load_settings(), {})

    def test_save_and_legacy_output_dir(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'nested' / 'config.json'
            with patch.object(app, '_config_path', return_value=target):
                app._save_settings({'quality': '320 kbps'})
                app._save_output_dir(Path(temp) / 'música')
                self.assertEqual(app._load_settings()['quality'], '320 kbps')
                self.assertEqual(app._load_output_dir(), Path(temp) / 'música')
                self.assertFalse(target.with_suffix('.tmp').exists())

    def test_ffmpeg_found_in_path(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(app, '_application_dir', return_value=Path(temp)), \
                 patch.object(app.shutil, 'which', return_value='C:/tools/bin/ffmpeg.exe'):
                self.assertEqual(Path(app._ffmpeg_location()), Path('C:/tools/bin'))

    def test_ffmpeg_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(app, '_application_dir', return_value=Path(temp)), \
                 patch.object(app.shutil, 'which', return_value=None):
                self.assertIsNone(app._ffmpeg_location())


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def options(self, fmt='mp3', quality='192 kbps', **kwargs):
        return app._download_options(app.DownloadSettings(self.output, fmt, quality, **kwargs),
            lambda _: None, lambda _: None, MagicMock(), threading.Event())

    def test_archives_and_files_separated(self):
        opts = [self.options(), self.options('mp4', '1080p'), self.options('mp3', '320 kbps')]
        self.assertEqual(len({o['download_archive'] for o in opts}), 3)
        self.assertEqual(len({o['outtmpl'] for o in opts}), 3)
        self.assertTrue(all(o['continuedl'] for o in opts))

    def test_formats_bitrates_containers(self):
        self.assertEqual(self.options(quality='320 kbps')['postprocessors'][0]['preferredquality'], '320')
        for fmt in ('m4a', 'opus', 'flac', 'wav'):
            opts = self.options(fmt, app.QUALITY[fmt][0])
            self.assertEqual(opts['postprocessors'][0]['preferredcodec'], fmt)
        self.assertEqual(self.options('webm_audio', app.QUALITY['webm_audio'][0])['format'], 'bestaudio[ext=webm]')
        self.assertIn('[height<=720]', self.options('mp4', '720p')['format'])
        self.assertIn('[ext=webm]', self.options('webm', '1080p')['format'])
        for fmt in app.VIDEO_FORMATS:
            self.assertEqual(self.options(fmt, 'Mejor disponible')['merge_output_format'], fmt)

    def test_playlist_archive_and_auth_options(self):
        self.assertTrue(self.options(playlist=False)['noplaylist'])
        self.assertNotIn('download_archive', self.options(skip_completed=False))
        self.assertEqual(self.options(cookie_browser='firefox')['cookiesfrombrowser'], ('firefox',))
        opts = self.options(cookie_file='cookies.txt', cookie_browser='chrome')
        self.assertEqual(opts['cookiefile'], 'cookies.txt')
        self.assertNotIn('cookiesfrombrowser', opts)
        self.assertFalse(opts['ignoreerrors'])

    def test_options_accepted_by_real_yt_dlp(self):
        if app.yt_dlp is None:
            self.skipTest('yt-dlp no instalado')
        for fmt in app.AUDIO_FORMATS + app.VIDEO_FORMATS:
            with app.yt_dlp.YoutubeDL(self.options(fmt, app.QUALITY[fmt][0])):
                pass

    def run_fake(self, urls, extract, settings=None):
        events = queue.Queue()
        fake = MagicMock()
        downloader = fake.YoutubeDL.return_value.__enter__.return_value
        downloader.params = {}
        downloader.extract_info.side_effect = extract
        with patch.object(app, 'yt_dlp', fake):
            app.DownloadWorker(events, threading.Event()).run(urls, settings or app.DownloadSettings(self.output))
        return list(events.queue), downloader

    def test_failed_job_continues_and_report_has_only_failed_link(self):
        messages, downloader = self.run_fake(['https://youtu.be/bad', 'https://youtu.be/good'],
                                            [RuntimeError('Sin conexión'), {'id': 'good'}])
        self.assertIn(('job', (0, 'Error')), messages)
        self.assertIn(('job', (1, 'Completado / existente')), messages)
        result = messages[-1][1]
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['failed'], ['https://youtu.be/bad'])
        self.assertEqual(Path(result['report']).read_text(), 'https://youtu.be/bad\n')
        self.assertEqual(downloader.extract_info.call_count, 2)

    def test_playlist_reports_specific_failed_video_and_continues(self):
        playlist = 'https://youtube.com/playlist?list=test'
        urls = [f'https://www.youtube.com/watch?v={letter * 11}' for letter in 'abc']
        def extract(url, download):
            if not download:
                return {'entries': [{'id': letter * 11, 'title': 'Private' if letter == 'b' else letter} for letter in 'abc']}
            if url == urls[1]:
                raise RuntimeError('Video privado')
            return {'id': url}
        messages, _ = self.run_fake([playlist], extract)
        result = messages[-1][1]
        self.assertEqual(result['completed'], 2)
        self.assertEqual(result['failed'], [urls[1]])
        self.assertEqual(Path(result['report']).read_text(), urls[1] + '\n')
        self.assertIn(('job', (2, 'Completado / existente')), messages)

    def test_playlist_read_error_does_not_stop_next_input(self):
        messages, _ = self.run_fake(['https://youtube.com/playlist?list=test', 'https://youtu.be/good'],
                                    [RuntimeError('Lista no disponible'), {'id': 'good'}])
        self.assertEqual(messages[-1][1]['completed'], 1)
        self.assertIn('playlist', messages[-1][1]['failed'][0])

    def test_playlist_disabled_never_downloads_collection_as_one_job(self):
        playlist = 'https://youtube.com/playlist?list=test'
        settings = app.DownloadSettings(self.output, playlist=False)
        messages, downloader = self.run_fake([playlist, 'https://youtu.be/good'], [{'id': 'good'}], settings)
        self.assertEqual(messages[-1][1]['failed'], [playlist])
        self.assertEqual(messages[-1][1]['completed'], 1)
        downloader.extract_info.assert_called_once_with('https://youtu.be/good', download=True)

    def test_source_cookies_are_not_modified(self):
        cookie = self.output / 'source.txt'
        cookie.write_text('original', encoding='utf-8')
        fake = MagicMock()
        copied = []
        def create(options):
            copied.append(options['cookiefile'])
            self.assertNotEqual(Path(options['cookiefile']), cookie)
            Path(options['cookiefile']).write_text('modified')
            manager = MagicMock()
            manager.__enter__.return_value.params = {}
            manager.__enter__.return_value.extract_info.return_value = {}
            return manager
        fake.YoutubeDL.side_effect = create
        events = queue.Queue()
        with patch.object(app, 'yt_dlp', fake):
            app.DownloadWorker(events, threading.Event()).run(['url'], app.DownloadSettings(self.output, cookie_file=str(cookie)))
        self.assertEqual(cookie.read_text(), 'original')
        self.assertFalse(Path(copied[0]).exists())

    def test_cancel_and_unknown_size(self):
        events, cancel = queue.Queue(), threading.Event()
        cancel.set()
        worker = app.DownloadWorker(events, cancel)
        with self.assertRaises(app.DownloadCancelled):
            worker.progress({'status': 'downloading'})
        worker.run(['url'], app.DownloadSettings(self.output))
        self.assertTrue(list(events.queue)[-1][1]['cancelled'])
        events = queue.Queue()
        worker = app.DownloadWorker(events, threading.Event())
        worker.progress({'status': 'downloading', 'downloaded_bytes': 50})
        self.assertEqual(events.get_nowait()[1][0], 0)

    def test_report_is_unique_and_deduplicated(self):
        first = app._write_failure_report(self.output, ['a', 'a', 'b'])
        second = app._write_failure_report(self.output, [])
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_text(), 'a\nb\n')
        self.assertEqual(second.read_text(), '')


if __name__ == '__main__':
    unittest.main()
