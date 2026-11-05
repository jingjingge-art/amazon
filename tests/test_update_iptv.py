import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_iptv import parse_playlist, normalize_category


class ParsePlaylistTests(unittest.TestCase):
    def test_parses_plain_groups_and_uses_default_for_generic_group(self):
        text = """iptv,#genre#
8tv,https://example.test/8tv.m3u8
江苏,#genre#
南京新闻,http://example.test/news.m3u8
"""
        self.assertEqual(
            list(parse_playlist(text, "马来西亚频道")),
            [
                ("马来西亚频道", "8tv", "https://example.test/8tv.m3u8"),
                ("江苏", "南京新闻", "http://example.test/news.m3u8"),
            ],
        )

    def test_parses_m3u_quoted_and_unquoted_group_titles(self):
        text = """#EXTM3U
#EXTINF:-1 group-title="新闻",Channel A
#EXTVLCOPT:http-user-agent=test
https://example.test/a.m3u8
#EXTINF:-1 group-title=Sports,Channel B
http://example.test/b.m3u8
"""
        self.assertEqual(
            list(parse_playlist(text, "默认")),
            [
                ("新闻", "Channel A", "https://example.test/a.m3u8"),
                ("Sports", "Channel B", "http://example.test/b.m3u8"),
            ],
        )

    def test_ignores_invalid_rows_and_normalizes_output_fields(self):
        text = """A,B,#genre#
 Bad, Name ,https://example.test/a.m3u8
not a channel
"""
        self.assertEqual(
            list(parse_playlist(text)),
            [("A，B", "Bad， Name", "https://example.test/a.m3u8")],
        )

    def test_generic_group_falls_back_to_source_group(self):
        self.assertEqual(normalize_category(" iptv ", "江苏频道"), "江苏频道")


if __name__ == "__main__":
    unittest.main()
