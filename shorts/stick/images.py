"""Real pictures for fact videos, from Wikimedia Commons: only public-domain or
openly licensed (CC0 / CC BY / CC BY-SA) images, with the credit kept next to the
file so it can go in the video description.

A picture is given in a queue entry as {search: "words"} (the first suitable
result) or {file: "File:Exact name.jpg"}. Downloads are cached in
assets/cache/images/ (not committed)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "assets" / "cache" / "images"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "ShortsBot/1.0 (https://github.com/nimrodagoat/bi; educational shorts)"}
OK_LICENSES = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? [\d.]+)", re.I)


def _key(spec) -> str:
    raw = json.dumps(spec, sort_keys=True) if isinstance(spec, dict) else str(spec)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def path_for(spec) -> Path:
    return CACHE / f"{_key(spec)}.jpg"


def credit(spec) -> str | None:
    side = path_for(spec).with_suffix(".json")
    if side.exists():
        return json.loads(side.read_text()).get("credit")
    return None


def _clean(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


def ensure(spec) -> Path | None:
    """Download the picture once; returns its path (None if nothing suitable)."""
    try:
        return _fetch(spec)
    except Exception as e:  # network trouble must never stop a render
        print(f"  picture fetch failed for {spec}: {e}")
        return None


def _fetch(spec) -> Path | None:
    out = path_for(spec)
    if out.exists():
        return out
    import requests  # only needed when actually fetching
    spec = spec if isinstance(spec, dict) else {"search": str(spec)}
    titles = [spec["file"]] if spec.get("file") else []
    if not titles:
        r = requests.get(API, params={"action": "query", "list": "search", "srsearch": spec["search"],
                                      "srnamespace": 6, "srlimit": 12, "format": "json"},
                         headers=HEADERS, timeout=30)
        titles = [h["title"] for h in r.json().get("query", {}).get("search", [])]
    if not titles:
        print(f"  no picture found for {spec}")
        return None
    r = requests.get(API, params={"action": "query", "titles": "|".join(titles[:12]), "prop": "imageinfo",
                                  "iiprop": "url|extmetadata|mime", "iiurlwidth": 1400, "format": "json"},
                     headers=HEADERS, timeout=30)
    pages = r.json().get("query", {}).get("pages", {}).values()
    order = {t: i for i, t in enumerate(titles)}
    for page in sorted(pages, key=lambda p: order.get(p.get("title"), 99)):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = _clean((meta.get("LicenseShortName") or {}).get("value", ""))
        if info.get("mime") not in ("image/jpeg", "image/png") or not OK_LICENSES.match(lic):
            continue
        url = info.get("thumburl") or info.get("url")
        data = requests.get(url, headers=HEADERS, timeout=60).content
        CACHE.mkdir(parents=True, exist_ok=True)
        from PIL import Image
        import io
        Image.open(io.BytesIO(data)).convert("RGB").save(out, "JPEG", quality=92)
        artist = _clean((meta.get("Artist") or {}).get("value", ""))[:80]
        name = page["title"].removeprefix("File:")
        text = f"{name}" + (f" by {artist}" if artist else "") + f" ({lic}, Wikimedia Commons)"
        out.with_suffix(".json").write_text(json.dumps({"credit": text, "title": page["title"]}))
        print(f"  picture: {text}")
        return out
    print(f"  no openly licensed picture for {spec}")
    return None


def specs_in(item: dict) -> list:
    out = []
    for shot in item.get("shots") or []:
        for p in shot.get("pictures") or []:
            if p.get("image"):
                out.append(p["image"])
    return out
