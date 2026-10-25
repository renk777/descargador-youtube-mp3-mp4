import unittest

from descargador import DescargadorApp


class YouTubeUrlTests(unittest.TestCase):
    def test_accepts_supported_youtube_hosts(self):
        self.assertTrue(DescargadorApp._is_youtube_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(DescargadorApp._is_youtube_url("https://youtu.be/abc"))

    def test_rejects_other_hosts_and_schemes(self):
        self.assertFalse(DescargadorApp._is_youtube_url("https://example.com/video"))
        self.assertFalse(DescargadorApp._is_youtube_url("ftp://youtube.com/video"))
        self.assertFalse(DescargadorApp._is_youtube_url("not-a-url"))


if __name__ == "__main__":
    unittest.main()
