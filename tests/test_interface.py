import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel
import descargador as ui


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication(['tests', '-platform', 'offscreen'])
        cls.application.setStyle('Fusion')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = patch.object(ui.core, '_config_path', return_value=Path(self.temp.name) / 'config.json')
        self.config.start()
        self.addCleanup(self.config.stop)
        self.window = ui.DescargadorApp()
        self.window.backdrop_initialized = True
        self.window.show()
        self.application.processEvents()
        self.addCleanup(self.window.close)

    def test_logo_only_in_titlebar(self):
        self.assertFalse(self.window.windowIcon().isNull())
        image_labels = [label for label in self.window.findChildren(QLabel) if not label.pixmap().isNull()]
        self.assertEqual(len(image_labels), 1)
        self.assertEqual(image_labels[0].parent(), self.window.titlebar)

    def test_modes_and_format_quality(self):
        self.assertEqual(self.window.format_combo.count(), 6)
        self.window.video_radio.setChecked(True)
        self.assertEqual(self.window.format_combo.count(), 3)
        self.assertEqual(self.window.quality_combo.currentText(), 'Mejor disponible')
        self.window.format_combo.setCurrentIndex(self.window.format_combo.findData('webm'))
        self.assertEqual(self.window.format_combo.currentData(), 'webm')

    def test_paste_queue_finish_and_busy(self):
        self.window.url_text.setPlainText('https://youtu.be/a\nhttps://youtu.be/a\nhttps://youtu.be/b')
        self.assertEqual(self.window.counter.text(), '2 enlaces')
        self.window._set_busy(True)
        self.assertFalse(self.window.format_combo.isEnabled())
        self.assertTrue(self.window.url_text.isReadOnly())
        self.window.events.put(('job_add', (0, 'https://youtu.be/b')))
        self.window.events.put(('job', (0, 'Error')))
        self.window.events.put(('finished', {'failed': ['https://youtu.be/b'], 'completed': 0,
                                           'cancelled': False, 'report': 'fallidos.txt'}))
        self.window._process_events()
        self.assertFalse(self.window.is_downloading)
        self.assertTrue(self.window.retry_button.isEnabled())
        self.assertTrue(self.window.report_button.isEnabled())
        self.assertEqual(self.window.jobs.item(0, 1).text(), 'Error')

    def test_gray_when_inactive_and_transparent_only_in_background(self):
        with patch.object(ui, 'enable_acrylic', return_value=(True, 'ok')), \
             patch.object(ui, 'set_acrylic_active', return_value=(True, 'ok')) as apply:
            self.window._initialize_backdrop()
            self.window._set_window_active(False, force=True)
            self.window._focus_animation.setCurrentTime(self.window._focus_animation.duration())
            inactive = self.window.grab().toImage()
            self.assertEqual(inactive.pixelColor(2, 60).name(), '#454648')
            self.window._set_window_active(True)
            self.window._focus_animation.setCurrentTime(self.window._focus_animation.duration())
            active = self.window.grab().toImage()
            self.assertLess(active.pixelColor(2, 60).alpha(), 255)
            self.assertEqual(self.window.windowOpacity(), 1.0)
            apply.assert_called_with(int(self.window.winId()), True)
            self.window._set_window_active(False)
            self.window._focus_animation.setCurrentTime(self.window._focus_animation.duration())
            apply.assert_called_with(int(self.window.winId()), False)
        self.assertFalse(hasattr(self.window, 'effect_button'))

    def test_session_not_persisted(self):
        self.window.cookie_file = 'private-session.txt'
        self.window.cookie_browser = 'firefox'
        self.window._persist()
        saved = ui.core._load_settings()
        self.assertNotIn('cookie_file', saved)
        self.assertNotIn('cookie_browser', saved)

    def test_all_download_controls_are_locked_but_cancel_is_available(self):
        self.window.report_path = 'previous.txt'
        self.window._set_busy(True)
        self.assertTrue(all(not widget.isEnabled() for widget in self.window.controls))
        self.assertFalse(self.window.report_button.isEnabled())
        self.assertFalse(self.window.retry_button.isEnabled())
        self.assertFalse(self.window.download_button.isEnabled())
        self.assertFalse(self.window.shortcut.isEnabled())
        self.assertTrue(self.window.cancel_button.isEnabled())
        self.window._set_busy(False)
        self.assertTrue(all(widget.isEnabled() for widget in self.window.controls))
        self.assertTrue(self.window.report_button.isEnabled())
        self.assertFalse(self.window.cancel_button.isEnabled())

    def test_offline_preflight_restores_controls_and_preserves_links(self):
        self.window.url_text.setPlainText('https://youtu.be/aaaaaaaaaaa')
        settings = ui.DownloadSettings(Path(self.temp.name))
        with patch.object(ui.core, '_ffmpeg_location', return_value='ffmpeg'), \
             patch.object(ui.core, '_js_runtime', return_value={'deno': {'path': 'deno'}}), \
             patch.object(ui.browser_login, 'check_connection', side_effect=ConnectionError('getaddrinfo failed')), \
             patch.object(ui, 'DownloadWorker') as worker, patch.object(ui.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = lambda: thread.call_args.kwargs['target']()
            self.window._begin_download(['https://youtu.be/aaaaaaaaaaa'], settings)
            self.window._begin_download(['https://youtu.be/aaaaaaaaaaa'], settings)
            self.assertEqual(thread.call_count, 1)
            self.assertTrue(self.window.is_downloading)
            self.window._process_events()
            worker.assert_not_called()
        self.assertFalse(self.window.is_downloading)
        self.assertTrue(self.window.download_button.isEnabled())
        self.assertEqual(self.window.notice.title.text(), 'No hay conexión a Internet')
        self.assertEqual(self.window.notice.action.text(), 'Reintentar')
        self.assertEqual(self.window.url_text.toPlainText(), 'https://youtu.be/aaaaaaaaaaa')

    def test_browser_sign_in_needs_no_cookie_file_or_paid_service(self):
        with patch.object(ui.browser_login, 'available_browser', return_value=('brave', 'Brave')), \
             patch.object(ui.browser_login, 'open_sign_in') as open_browser:
            self.window._session_dialog()
        open_browser.assert_called_once_with()
        self.assertTrue(self.window.session_pending)
        self.assertIn('Ya inicié sesión', self.window.notice.action.text())
        with patch.object(ui.browser_login, 'check_connection'), \
             patch.object(ui.browser_login, 'verify_browser_session', return_value=True) as verify, \
             patch.object(ui.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = lambda: thread.call_args.kwargs['target']()
            self.window._verify_sign_in()
            self.assertFalse(self.window.download_button.isEnabled())
            self.window._process_events()
        verify.assert_called_once_with('brave')
        self.assertEqual(self.window.cookie_browser, 'brave')
        self.assertEqual(self.window.cookie_file, '')
        self.assertFalse(self.window.session_pending)
        self.assertTrue(self.window.download_button.isEnabled())

    def test_custom_errors_are_animated_and_do_not_use_modal_dialogs(self):
        with patch.object(ui.QMessageBox, 'warning') as warning:
            self.window._start_download()
        warning.assert_not_called()
        self.assertEqual(self.window.notice.title.text(), 'Añade un enlace para empezar')
        self.assertTrue(self.window.notice.animation.state() == self.window.notice.animation.State.Running)
        self.assertEqual(self.window.notice.mark.kind, 'warning')


    def test_repeated_login_clicks_and_session_check_never_open_second_browser(self):
        with patch.object(ui.browser_login, 'available_browser', return_value=('brave', 'Brave')), \
             patch.object(ui.browser_login, 'open_sign_in') as launch:
            self.window._session_dialog()
            self.window._session_dialog()
            self.window._session_dialog()
            launch.assert_called_once_with()
        with patch.object(ui.browser_login, 'open_sign_in') as launch, \
             patch.object(ui.browser_login, 'check_connection'), \
             patch.object(ui.browser_login, 'verify_browser_session', side_effect=RuntimeError('DPAPI decrypt failed')), \
             patch.object(ui.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = lambda: thread.call_args.kwargs['target']()
            self.window._verify_sign_in()
            self.window._process_events()
            launch.assert_not_called()
        self.assertEqual(self.window.notice.title.text(), 'No pudimos conectar la sesión')
        self.assertFalse(self.window.notice.action.isVisible())
        self.assertEqual(self.window.login_browser[0], 'brave')

    def test_unknown_default_browser_still_opens_once_without_session_fallback(self):
        with patch.object(ui.browser_login, 'available_browser', return_value=('', 'tu navegador predeterminado')), \
             patch.object(ui.browser_login, 'open_sign_in') as launch, \
             patch.object(ui.browser_login, 'verify_browser_session') as verify:
            self.window._session_dialog()
            self.window._verify_sign_in()
            launch.assert_called_once_with()
            verify.assert_not_called()
        self.assertIn('No podemos conectar', self.window.notice.title.text())

    def test_centers_once_inside_monitor_work_area(self):
        from PySide6.QtCore import QRect
        from unittest.mock import Mock
        window = ui.DescargadorApp()
        area = QRect(-1920, 40, 1920, 1040)
        monitor = Mock()
        monitor.availableGeometry.return_value = area
        with patch.object(window, 'screen', return_value=monitor):
            window._center_on_start()
            self.assertLessEqual((window.frameGeometry().center() - area.center()).manhattanLength(), 1)
            position = window.pos()
            window.move(position.x() + 100, position.y() + 20)
            moved = window.pos()
            window._center_on_start()
            self.assertEqual(window.pos(), moved)
        window.close()

    def test_window_fits_small_monitor_before_centering(self):
        from PySide6.QtCore import QRect
        from unittest.mock import Mock
        window = ui.DescargadorApp()
        area = QRect(0, 0, 800, 600)
        monitor = Mock()
        monitor.availableGeometry.return_value = area
        with patch.object(window, 'screen', return_value=monitor):
            window._center_on_start()
            self.assertEqual(window.size(), area.size())
            self.assertLessEqual((window.frameGeometry().center() - area.center()).manhattanLength(), 1)
        window.close()



if __name__ == '__main__':
    unittest.main()
