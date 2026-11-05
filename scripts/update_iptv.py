#!/usr/bin/env python3
"""Fetch M3U playlists and export them as a categorized iptv.txt file."""

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
)
OUTPUT = Path(__file__).resolve().parents[1] / "iptv.txt"
GROUP_RE = re.compile(r'''(?:^|\s)group-title\s*=\s*(["'])(.*?)\1''', re.IGNORECASE)


def clean_field(value: str) -> str:
    return " ".join(value.replace(",", "，").split())


def parse_playlist(text: str):
    pending = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#EXTINF:"):
            metadata, separator, name = line.partition(",")
            match = GROUP_RE.search(metadata)
            category = clean_field(match.group(2)) if match else "未分类"
            pending = (category or "未分类", clean_field(name) if separator else "未命名频道")
        elif line and not line.startswith("#") and pending:
            if line.startswith(("http://", "https://")):
                yield pending[0], pending[1], line
            pending = None


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
