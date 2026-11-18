import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import download_core as core


class PauseTests(unittest.TestCase):
    def test_progress_waits_until_resumed(self):
        events, cancel, pause = queue.Queue(), threading.Event(), core.PauseControl()
        worker = core.DownloadWorker(events, cancel, pause)
        pause.pause()
        finished = threading.Event()
        thread = threading.Thread(target=lambda: (worker.progress({'status': 'downloading', 'downloaded_bytes': 5, 'total_bytes': 10}), finished.set()))
        thread.start()
        try:
            self.assertEqual(events.get(timeout=2), ('pause_state', True))
            self.assertFalse(finished.is_set())
            pause.resume()
            thread.join(timeout=2)
            self.assertTrue(finished.is_set())
            remaining = list(events.queue)
            self.assertIn(('pause_state', False), remaining)
            self.assertTrue(any(name == 'progress' for name, _ in remaining))
        finally:
            pause.resume()
            thread.join(timeout=2)

    def test_cancel_while_paused_does_not_require_resume(self):
        events, cancel, pause = queue.Queue(), threading.Event(), core.PauseControl()
        worker = core.DownloadWorker(events, cancel, pause)
        pause.pause()
        errors = []
        def run():
            try:
                worker.progress({'status': 'downloading'})
            except core.DownloadCancelled as error:
                errors.append(error)
        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertEqual(events.get(timeout=2), ('pause_state', True))
            cancel.set()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 1)
        finally:
            pause.resume()
            thread.join(timeout=2)

    def test_batch_does_not_start_next_video_while_paused(self):
        with tempfile.TemporaryDirectory() as directory:
            events, cancel, pause = queue.Queue(), threading.Event(), core.PauseControl()
            fake = MagicMock()
            downloader = fake.YoutubeDL.return_value.__enter__.return_value
            downloader.params = {}
            def extract(url, download):
                if url == 'first':
                    pause.pause()
                return {'id': url}
            downloader.extract_info.side_effect = extract
            with patch.object(core, 'yt_dlp', fake), patch.object(core, '_config_path', return_value=Path(directory) / 'internal' / 'config.json'):
                worker = core.DownloadWorker(events, cancel, pause)
                thread = threading.Thread(target=worker.run, args=(['first', 'second'], core.DownloadSettings(Path(directory))))
                thread.start()
                try:
                    while events.get(timeout=2) != ('pause_state', True):
                        pass
                    self.assertEqual(downloader.extract_info.call_count, 1)
                    pause.resume()
                    thread.join(timeout=3)
                    self.assertFalse(thread.is_alive())
                    result = list(events.queue)[-1][1]
                    self.assertEqual(result['completed'], 2)
                    self.assertEqual(result['failed'], [])
                finally:
                    cancel.set()
                    pause.resume()
                    thread.join(timeout=3)

    def test_metadata_filter_obeys_pause_gate(self):
        pause, cancel, events = core.PauseControl(), threading.Event(), queue.Queue()
        worker = core.DownloadWorker(events, cancel, pause)
        opts = core._download_options(core.DownloadSettings(Path('.')), worker.progress, worker.postprocess, worker, cancel, pause)
        pause.pause()
        done = threading.Event()
        thread = threading.Thread(target=lambda: (opts['match_filter']({}), done.set()))
        thread.start()
        try:
            self.assertEqual(events.get(timeout=2), ('pause_state', True))
            self.assertFalse(done.is_set())
            pause.resume()
            thread.join(timeout=2)
            self.assertTrue(done.is_set())
        finally:
            pause.resume()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
