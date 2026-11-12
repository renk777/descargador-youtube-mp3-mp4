import unittest
from http.cookiejar import Cookie
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import browser_login
from user_errors import describe_error


class ErrorMessagesTests(unittest.TestCase):
    def test_known_failures_have_actionable_messages(self):
        cases = {'getaddrinfo failed': 'offline', 'timed out': 'connection',
                 'No space left on device': 'disk_full', 'Permission denied': 'permission',
                 'Sign in to confirm your age': 'authentication', 'Private video': 'unavailable',
                 'Requested format is not available': 'format', 'HTTP Error 429': 'rate_limit',
                 'Failed to decrypt with DPAPI': 'session_locked',
                 'CERTIFICATE_VERIFY_FAILED': 'secure_connection'}
        for error, code in cases.items():
            with self.subTest(error=error):
                issue = describe_error(error)
                self.assertEqual(issue.code, code)
                self.assertTrue(issue.title)
                self.assertTrue(issue.message)

    def test_connectivity_refusal_is_not_reported_as_no_internet(self):
        with patch.object(browser_login, 'urlopen', side_effect=HTTPError('https://youtube.com', 403, 'Forbidden', {}, None)):
            browser_login.check_connection()

    def test_dns_error_is_connection_failure(self):
        with patch.object(browser_login, 'urlopen', side_effect=URLError('getaddrinfo failed')):
            with self.assertRaises(ConnectionError):
                browser_login.check_connection()

    def test_external_browser_uses_exactly_one_system_default_dispatch(self):
        with patch.object(browser_login.sys, 'platform', 'win32'), \
             patch.object(browser_login.os, 'startfile', create=True) as launch:
            browser_login.open_sign_in()
        launch.assert_called_once_with(browser_login.LOGIN_URL)
        self.assertNotIn('password', browser_login.LOGIN_URL)

    def test_detects_brave_as_default_without_preferring_installed_firefox(self):
        with patch.object(browser_login, '_default_browser_executable', return_value=r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'):
            self.assertEqual(browser_login.available_browser(), ('brave', 'Brave'))

    def test_unknown_default_is_not_replaced_with_another_browser(self):
        with patch.object(browser_login, '_default_browser_executable', return_value='unrecognized.exe'):
            self.assertEqual(browser_login.available_browser()[0], '')
        with patch.object(browser_login.sys, 'platform', 'win32'), \
             patch.object(browser_login.os, 'startfile', create=True, side_effect=OSError('No association')) as launch:
            with self.assertRaises(OSError):
                browser_login.open_sign_in()
        launch.assert_called_once()

    def test_session_checks_only_youtube_authentication_cookies(self):
        def cookie(host, name):
            return Cookie(0, name, 'fake-value', None, False, host, True, True, '/', True,
                          True, None, True, None, None, {})
        with patch('yt_dlp.cookies.extract_cookies_from_browser', return_value=[cookie('.example.com', 'SAPISID')]):
            self.assertFalse(browser_login.verify_browser_session('firefox'))
        with patch('yt_dlp.cookies.extract_cookies_from_browser', return_value=[cookie('.youtube.com', 'SAPISID')]):
            self.assertTrue(browser_login.verify_browser_session('firefox'))


if __name__ == '__main__':
    unittest.main()
