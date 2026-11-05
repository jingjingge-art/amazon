#!/usr/bin/env python3
"""Fetch M3U or comma-separated playlists and export iptv.txt."""

from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

SOURCES = (
    "https://raw.githubusercontent.com/akiralereal/iptv/refs/heads/main/IPTV.m3u",
    "https://raw.githubusercontent.com/akiralereal/iptv/refs/heads/main/IPTV-overseas.m3u",
    "https://raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "https://raw.githubusercontent.com/YanG-1989/m3u/refs/heads/main/Migu.m3u",
    "https://raw.githubusercontent.com/jingjingge-art/tvmalay/refs/heads/main/8tv.txt",
    "https://raw.githubusercontent.com/jingjingge-art/youtube/refs/heads/main/%E6%B1%9F%E8%8B%8F%E9%A2%91%E9%81%93.txt",
)
OUTPUT = Path(__file__).resolve().parents[1] / "iptv.txt"
GROUP_RE = re.compile(r'''(?:^|\s)group-title\s*=\s*(["'])(.*?)\1''', re.IGNORECASE)


def clean_field(value: str) -> str:
    return " ".join(value.replace(",", "，").split())


def parse_playlist(text: str):
    """Yield (category, channel, URL) from M3U or name,URL text playlists."""
    category = "未分类"
    pending = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF:"):
            metadata, separator, name = line.partition(",")
            match = GROUP_RE.search(metadata)
            item_category = clean_field(match.group(2)) if match else "未分类"
            pending = (
                item_category or "未分类",
                clean_field(name) if separator else "未命名频道",
            )
            continue

        # Other M3U directives and playlist headers are not channel entries.
        if line.startswith("#"):
            continue

        # In M3U, an #EXTINF record is followed by its URL on the next line.
        if pending:
            if line.startswith(("http://", "https://")):
                yield pending[0], pending[1], line
            pending = None
            continue

        # Also accept common IPTV text lines: channel name,URL. A #genre#
        # line changes the category for subsequent entries in that source.
        name, separator, value = line.partition(",")
        if not separator:
            continue
        name = clean_field(name)
        value = value.strip()
        if value.lower() == "#genre#":
            category = name or "未分类"
        elif name and value.startswith(("http://", "https://")):
            yield category, name, value


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "iptv-playlist-updater/1.0"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def main() -> int:
    categories = OrderedDict()
    succeeded = 0
    for source in SOURCES:
        try:
            text = fetch(source)
            records = list(parse_playlist(text))
            succeeded += 1
            for category, name, url in records:
                categories.setdefault(category, []).append((name, url))
            print(f"Loaded {len(records)} channels from {source}")
        except (URLError, TimeoutError, OSError, ValueError) as error:
            print(f"Warning: could not load {source}: {error}", file=sys.stderr)

    if succeeded == 0:
        print("All playlist sources failed; keeping the existing iptv.txt unchanged.", file=sys.stderr)
        return 1

    date = datetime.now(timezone.utc).date().isoformat()
    lines = [f"iptv({date}),#genre#"]
    for category, channels in categories.items():
        lines.append(f"{category},#genre#")
        lines.extend(f"{name},{url}" for name, url in channels)

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {sum(map(len, categories.values()))} channels in {len(categories)} categories to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
