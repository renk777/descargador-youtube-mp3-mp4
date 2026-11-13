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

    def test_sign_in_launches_firefox_once_without_opening_default_browser(self):
        with patch.object(browser_login.subprocess, 'Popen') as launch, \
             patch.object(browser_login.os, 'startfile', create=True) as default:
            browser_login.open_sign_in(('firefox', 'firefox.exe'))
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], ['firefox.exe', '-new-tab', browser_login.LOGIN_URL])
        default.assert_not_called()
        self.assertNotIn('password', browser_login.LOGIN_URL)

    def test_firefox_is_preferred_over_other_installed_browsers(self):
        with patch.object(browser_login.shutil, 'which', side_effect=lambda exe: exe):
            self.assertEqual(browser_login.available_browser(), ('firefox', 'firefox.exe'))

    def test_no_compatible_browser_does_not_launch_the_default_as_fallback(self):
        with patch.object(browser_login.shutil, 'which', return_value=None), \
             patch.object(browser_login.Path, 'is_file', return_value=False):
            self.assertIsNone(browser_login.available_browser())
        with patch.object(browser_login.subprocess, 'Popen') as launch:
            with self.assertRaises(OSError):
                browser_login.open_sign_in(None)
        launch.assert_not_called()

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
