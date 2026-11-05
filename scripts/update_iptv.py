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
GROUP_RE = re.compile(
    r'''(?:^|\s)group-title\s*=\s*(?:"([^"]*)"|'([^']*)'|([^,\s]*))''',
    re.IGNORECASE,
)
GENERIC_GROUPS = {"iptv", "playlist", "频道列表"}


def clean_field(value: str) -> str:
    """Normalize a text field for the comma-separated output format."""
    return " ".join(value.replace(",", "，").replace("\r", " ").replace("\n", " ").split())


def normalize_category(value: str, default_category: str) -> str:
    category = clean_field(value).strip()
    if not category or category.casefold() in GENERIC_GROUPS:
        return clean_field(default_category) or "未分类"
    return category


def parse_playlist(text: str, default_category: str = "未分类"):
    """Yield (category, channel, URL) from M3U or name,URL text playlists."""
    default_category = clean_field(default_category) or "未分类"
    category = default_category
    pending = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF:"):
            metadata, separator, name = line.partition(",")
            match = GROUP_RE.search(metadata)
            group = next((part for part in match.groups() if part is not None), "") if match else ""
            item_category = normalize_category(group, default_category)
            pending = (
                item_category,
                clean_field(name) if separator and clean_field(name) else "未命名频道",
            )
            continue

        # Playlist directives (e.g. #EXTVLCOPT) are allowed between EXTINF and URL.
        if line.startswith("#"):
            if line.lower().endswith(",#genre#"):
                group_name = line[:-len(",#genre#")].lstrip("#").strip()
                category = normalize_category(group_name, default_category)
            continue

        # In M3U, an #EXTINF record is followed by its URL on the next line.
        if pending:
            if line.startswith(("http://", "https://")):
                yield pending[0], pending[1], line
            pending = None
            continue

        # Plain IPTV text: channel name,URL. A #genre# row starts a group.
        name, separator, value = line.partition(",")
        if not separator:
            continue
        name = clean_field(name)
        value = value.strip()
        if value.casefold() == "#genre#":
            category = normalize_category(name, default_category)
        elif name and value.startswith(("http://", "https://")):
            yield category, name, value


def default_category_for_source(source: str) -> str:
    """Use readable source-specific groups when a list only says 'iptv'."""
    if "/8tv.txt" in source:
        return "马来西亚频道"
    if "youtube/refs/heads/main/" in source:
        return "江苏频道"
    return "未分类"


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "iptv-playlist-updater/1.0"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def main() -> int:
    categories = OrderedDict()
    category_keys = {}
    seen_urls = set()
    succeeded = 0

    for source in SOURCES:
        try:
            text = fetch(source)
            records = list(parse_playlist(text, default_category_for_source(source)))
            succeeded += 1
            added = 0
            for category, name, url in records:
                # Deduplicate exact stream URLs across sources, preserving the first occurrence.
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                key = clean_field(category).casefold()
                display_category = category_keys.setdefault(key, clean_field(category) or "未分类")
                categories.setdefault(display_category, []).append((name, url))
                added += 1
            print(f"Loaded {len(records)} channels ({added} new) from {source}")
        except (URLError, TimeoutError, OSError, ValueError) as error:
            print(f"Warning: could not load {source}: {error}", file=sys.stderr)

    channel_count = sum(map(len, categories.values()))
    if succeeded == 0:
        print("All playlist sources failed; keeping the existing iptv.txt unchanged.", file=sys.stderr)
        return 1
    if channel_count == 0:
        print("No valid channels were parsed; keeping the existing iptv.txt unchanged.", file=sys.stderr)
        return 1

    date = datetime.now(timezone.utc).date().isoformat()
    lines = [f"iptv({date}),#genre#"]
    for category, channels in categories.items():
        lines.append(f"{category},#genre#")
        lines.extend(f"{name},{url}" for name, url in channels)

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {channel_count} channels in {len(categories)} categories to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
