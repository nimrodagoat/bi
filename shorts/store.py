"""Loading settings, the video queue, and the posted log."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
QUEUE_PATH = ROOT / "content" / "queue.yaml"
POSTED_PATH = ROOT / "content" / "posted.yaml"

QUEUE_HEADER = """\
# Videos waiting to be posted, top to bottom. The daily job takes the first one.
# Each entry:
#   id            unique name (letters, numbers, dashes)
#   niche         optional; overrides the niche in config.yaml for this video
#   title         YouTube title (max 100 characters)
#   script        what the voice says (aim for 35-55 seconds, ~90-140 words)
#   search_terms  words used to find matching stock footage, one per scene
#   tags          YouTube tags
#   description   optional; generated from the script if missing
"""

POSTED_HEADER = """\
# Videos already uploaded (newest last). Written automatically by the daily job.
"""

REQUIRED_FIELDS = ("id", "title", "script")


class _Dumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper: yaml.SafeDumper, data: str):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_Dumper.add_representer(str, _str_presenter)


def _load(path: Path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump(path: Path, header: str, data) -> None:
    body = yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(header + "\n" + body, encoding="utf-8")


def load_config() -> dict:
    return _load(CONFIG_PATH) or {}


def load_queue() -> list[dict]:
    return _load(QUEUE_PATH) or []


def save_queue(items: list[dict]) -> None:
    _dump(QUEUE_PATH, QUEUE_HEADER, items)


def load_posted() -> list[dict]:
    return _load(POSTED_PATH) or []


def mark_posted(item: dict, video_id: str) -> None:
    """Move a video from the queue to the posted log."""
    queue = [q for q in load_queue() if q.get("id") != item["id"]]
    posted = load_posted()
    entry = {"id": item["id"], "title": item["title"]}
    if item.get("niche"):
        entry["niche"] = item["niche"]
    posted.append(
        {
            **entry,
            "video_id": video_id,
            "url": f"https://youtube.com/shorts/{video_id}",
            "posted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
    )
    save_queue(queue)
    _dump(POSTED_PATH, POSTED_HEADER, posted)


def validate_queue(items: list[dict]) -> list[str]:
    """Return a list of human-readable problems with the queue (empty = fine)."""
    problems = []
    seen = {p.get("id") for p in load_posted()}
    for n, item in enumerate(items, 1):
        label = f"entry #{n} ({item.get('id', 'no id')})"
        if not isinstance(item, dict):
            problems.append(f"entry #{n} is not a key/value block")
            continue
        for field in REQUIRED_FIELDS:
            if not str(item.get(field, "")).strip():
                problems.append(f"{label}: missing '{field}'")
        if item.get("id") in seen:
            problems.append(f"{label}: id is used twice (or was already posted)")
        seen.add(item.get("id"))
        if len(str(item.get("title", ""))) > 100:
            problems.append(f"{label}: title is longer than 100 characters")
        words = len(str(item.get("script", "")).split())
        if words > 170:
            problems.append(f"{label}: script has {words} words; keep it under ~150 so the Short stays under a minute")
    return problems
