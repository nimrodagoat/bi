"""Background music: well-known meme tracks that are free to use.

The cartoonish tracks heard under countless viral videos ("Sneaky Snitch",
"Monkeys Spinning Monkeys", "Fluffing a Duck", ...) are by Kevin MacLeod and
licensed CC BY 4.0: free for any use, including monetized videos, as long as he
is credited. Tracks are downloaded from incompetech.com on first use and cached;
the credit line is added to the video description automatically.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from urllib.parse import quote

import requests

CACHE = Path(__file__).resolve().parent.parent / ".cache" / "music"
BASE = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"
CREDIT = (
    '"{title}" Kevin MacLeod (incompetech.com)\n'
    "Licensed under Creative Commons: By Attribution 4.0 License\n"
    "http://creativecommons.org/licenses/by/4.0/"
)


def _download(title: str) -> Path | None:
    path = CACHE / f"{title}.mp3"
    if path.exists() and path.stat().st_size > 50_000:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(BASE + quote(title) + ".mp3", timeout=60, headers={"User-Agent": "Mozilla/5.0 (shorts-autopilot)"})
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith(("audio", "application/octet")) or len(r.content) < 50_000:
            raise ValueError(f"not an mp3 ({r.headers.get('content-type')}, {len(r.content)} bytes)")
        path.write_bytes(r.content)
        return path
    except Exception as e:
        print(f"  music: couldn't get '{title}' ({str(e)[:120]})", file=sys.stderr)
        return None


def pick(seed: str, tracks: list[str]) -> tuple[Path, str] | None:
    """A track for this video (the same video always gets the same one), plus its credit."""
    order = list(tracks)
    random.Random(f"music-{seed}").shuffle(order)
    for title in order:
        path = _download(title)
        if path:
            return path, CREDIT.format(title=title)
    return None
