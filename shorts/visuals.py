"""Background footage: your gameplay videos, free stock clips (Pixabay or
Pexels), or an animated gradient, in that order of preference."""

from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

import requests

from .media import probe_duration

ROOT = Path(__file__).resolve().parent.parent
GAMEPLAY_EXTS = {".mp4", ".mov", ".mkv", ".webm"}

PEXELS_SEARCH = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH = "https://pixabay.com/api/videos/"


def pick_gameplay(duration: float, cfg: dict) -> tuple[Path, float] | None:
    """Pick a random gameplay video and a random start time inside it.

    Gameplay lives in assets/gameplay/ (small files committed to the repo) and
    is also downloaded from the repo's "gameplay" GitHub release by the daily job.
    """
    vis = cfg.get("visuals", {})
    if vis.get("source", "auto") not in ("auto", "gameplay"):
        return None  # stock footage or gradient only
    folder = ROOT / vis.get("gameplay_dir", "assets/gameplay")
    files = [f for f in folder.glob("*") if f.suffix.lower() in GAMEPLAY_EXTS] if folder.exists() else []
    random.shuffle(files)
    for f in files:
        try:
            length = probe_duration(f)
        except Exception as e:
            print(f"  visuals: can't read {f.name} ({e})", file=sys.stderr)
            continue
        if length >= duration + 1:
            start = random.uniform(0, length - duration - 0.5)
            print(f"  visuals: gameplay {f.name} from {start:.0f}s")
            return f, start
        print(f"  visuals: {f.name} is shorter than the video, skipping", file=sys.stderr)
    return None


def fetch_clips(terms: list[str], duration: float, work_dir: Path, cfg: dict) -> list[Path]:
    """Download enough stock clips to cover `duration` seconds.

    Returns an empty list if stock footage isn't available, in which case the
    renderer falls back to an animated gradient.
    """
    source = cfg.get("visuals", {}).get("source", "auto")
    if source == "gradient":
        return []
    providers = []
    if source != "pexels" and os.environ.get("PIXABAY_API_KEY"):
        providers.append(("Pixabay", _pick_pixabay, os.environ["PIXABAY_API_KEY"]))
    if source != "pixabay" and os.environ.get("PEXELS_API_KEY"):
        providers.append(("Pexels", _pick_pexels, os.environ["PEXELS_API_KEY"]))
    if not providers:
        print("  visuals: no PIXABAY_API_KEY / PEXELS_API_KEY set, using gradient background")
        return []

    terms = [t for t in terms if t] or ["nature"]
    scene = cfg.get("video", {}).get("scene_seconds", 2.5)
    scenes = max(len(terms), math.ceil(duration / scene))
    for name, pick, key in providers:
        try:
            clips = _download_scenes(terms, scenes, pick, key, work_dir)
        except requests.RequestException as e:
            print(f"  visuals: {name} failed ({e})", file=sys.stderr)
            continue
        if clips:
            print(f"  visuals: {len(clips)} {name} clips")
            return clips
        print(f"  visuals: {name} found no matching clips", file=sys.stderr)
    print("  visuals: using gradient background", file=sys.stderr)
    return []


def _download_scenes(terms, scenes, pick, key, work_dir: Path) -> list[Path]:
    clips: list[Path] = []
    used: set[int] = set()
    for i in range(scenes):
        url, vid = pick(terms[i % len(terms)], key, used)
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
    return clips


def _pick_pixabay(term: str, key: str, used: set[int]) -> tuple[str | None, int | None]:
    r = requests.get(
        PIXABAY_SEARCH,
        params={"key": key, "q": term[:100], "per_page": 30, "safesearch": "true"},
        timeout=30,
    )
    r.raise_for_status()
    hits = [h for h in r.json().get("hits", []) if h["id"] not in used and h.get("duration", 0) >= 4]
    random.shuffle(hits)
    candidates = []
    for h in hits:
        sizes = h.get("videos", {})
        for size in ("large", "medium"):
            f = sizes.get(size) or {}
            if f.get("url") and (f.get("height") or 0) >= 720:
                candidates.append((f["height"] > f["width"], f["url"], h["id"]))
                break
    if not candidates:
        return None, None
    # Most Pixabay clips are landscape (they get cropped to the centre); prefer portrait ones.
    candidates.sort(key=lambda c: not c[0])
    return candidates[0][1], candidates[0][2]


def _pick_pexels(term: str, key: str, used: set[int]) -> tuple[str | None, int | None]:
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
