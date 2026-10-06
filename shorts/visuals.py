"""Background footage: free Pexels stock clips, or an animated gradient."""

from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

import requests

PEXELS_SEARCH = "https://api.pexels.com/videos/search"
SCENE_SECONDS = 5.5  # roughly how long each stock clip stays on screen


def fetch_clips(terms: list[str], duration: float, work_dir: Path, cfg: dict) -> list[Path]:
    """Download enough portrait stock clips to cover `duration` seconds.

    Returns an empty list if stock footage isn't available, in which case the
    renderer falls back to an animated gradient.
    """
    if cfg.get("visuals", {}).get("source", "pexels") != "pexels":
        return []
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        print("  visuals: no PEXELS_API_KEY set, using gradient background")
        return []
    terms = [t for t in terms if t] or ["nature"]
    scenes = max(len(terms), math.ceil(duration / SCENE_SECONDS))
    clips: list[Path] = []
    used: set[int] = set()
    try:
        for i in range(scenes):
            term = terms[i % len(terms)]
            url, vid = _pick_video(term, key, used)
            if not url:
                continue
            used.add(vid)
            path = work_dir / f"clip{i:02d}.mp4"
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for block in r.iter_content(1 << 16):
                        f.write(block)
            clips.append(path)
    except requests.RequestException as e:
        print(f"  visuals: Pexels failed ({e}), using gradient background", file=sys.stderr)
        return []
    print(f"  visuals: {len(clips)} Pexels clips")
    return clips


def _pick_video(term: str, key: str, used: set[int]) -> tuple[str | None, int | None]:
    r = requests.get(
        PEXELS_SEARCH,
        headers={"Authorization": key},
        params={"query": term, "orientation": "portrait", "per_page": 20},
        timeout=30,
    )
    r.raise_for_status()
    videos = [v for v in r.json().get("videos", []) if v["id"] not in used and v.get("duration", 0) >= 4]
    random.shuffle(videos)
    for v in videos:
        files = [
            f for f in v.get("video_files", [])
            if f.get("file_type") == "video/mp4" and (f.get("height") or 0) >= 1280 and (f.get("height") or 0) <= 2560
        ]
        if files:
            best = min(files, key=lambda f: abs(f["height"] - 1920))
            return best["link"], v["id"]
    return None, None


# Pairs of colours for the gradient fallback.
GRADIENTS = [
    ("0x0f2027", "0x2c5364"),
    ("0x1a2a6c", "0xb21f1f"),
    ("0x232526", "0x414345"),
    ("0x141e30", "0x243b55"),
    ("0x3a1c71", "0xd76d77"),
    ("0x0b486b", "0xf56217"),
]


def gradient_source(duration: float, cfg: dict) -> str:
    v = cfg.get("video", {})
    c0, c1 = random.choice(GRADIENTS)
    return (
        f"gradients=s={v.get('width', 1080)}x{v.get('height', 1920)}:r={v.get('fps', 30)}"
        f":c0={c0}:c1={c1}:nb_colors=2:speed=0.008:d={duration:.2f}"
    )
