"""Command line entry point.

    python -m shorts run              render + upload the next video(s) in the queue
    python -m shorts run --dry-run    render only, don't upload or change the queue
    python -m shorts preview [ID]     render one video to output/ to look at it
    python -m shorts status           show what's queued and check the queue for mistakes
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import store
from .render import render

OUTPUT = store.ROOT / "output"


def _pick(queue: list[dict], wanted_id: str | None) -> dict | None:
    if wanted_id:
        return next((q for q in queue if q.get("id") == wanted_id), None)
    return queue[0] if queue else None


def _render_one(item: dict, cfg: dict) -> Path:
    print(f"▶ {item['id']}: {item['title']}")
    work = OUTPUT / "work" / item["id"]
    if work.exists():
        shutil.rmtree(work)
    out = render(item, OUTPUT / f"{item['id']}.mp4", work, cfg)
    print(f"  rendered {out.relative_to(store.ROOT)}")
    return out


def cmd_status(_args) -> int:
    queue = store.load_queue()
    posted = store.load_posted()
    cfg = store.load_config()
    per_run = cfg.get("schedule", {}).get("uploads_per_run", 1)
    print(f"Default niche : {cfg.get('channel', {}).get('niche')}")
    print(f"Posted so far : {len(posted)}")
    print(f"In queue      : {len(queue)}  (~{len(queue) // max(per_run, 1)} days at {per_run}/day)")
    for q in queue[:5]:
        niche = f"  [{q['niche']}]" if q.get("niche") else ""
        print(f"   • {q.get('id')}: {q.get('title')}{niche}")
    problems = store.validate_queue(queue)
    for p in problems:
        print(f"PROBLEM: {p}")
    return 1 if problems else 0


def cmd_preview(args) -> int:
    queue = store.load_queue()
    item = _pick(queue, args.id)
    if not item:
        print("Nothing to preview: queue is empty or id not found.", file=sys.stderr)
        return 1
    _render_one(item, store.load_config())
    return 0


def cmd_run(args) -> int:
    from . import upload

    cfg = store.load_config()
    queue = store.load_queue()
    problems = store.validate_queue(queue)
    if problems:
        print("The queue has problems, fix them first:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if not queue:
        print("The queue is empty: there's nothing to post. Ask Claude for a new batch of scripts.", file=sys.stderr)
        return 1
    if not args.dry_run and (missing := upload.missing_secrets()):
        print(f"Missing secrets: {', '.join(missing)}. See SETUP.md.", file=sys.stderr)
        return 1

    per_run = args.count or cfg.get("schedule", {}).get("uploads_per_run", 1)
    for item in queue[:per_run]:
        video = _render_one(item, cfg)
        if args.dry_run:
            continue
        try:
            video_id = upload.upload(video, item, cfg)
        except upload.QuotaExceeded as e:
            print(f"  {e}", file=sys.stderr)
            break
        store.mark_posted(item, video_id)
        print(f"  ✔ posted: https://youtube.com/shorts/{video_id}")

    left = len(store.load_queue())
    warn_at = cfg.get("schedule", {}).get("low_queue_warning", 7)
    if left < warn_at:
        print(f"::warning::Only {left} videos left in the queue. Ask Claude for a new batch.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="shorts")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--count", type=int)
    r.set_defaults(fn=cmd_run)
    pv = sub.add_parser("preview")
    pv.add_argument("id", nargs="?")
    pv.set_defaults(fn=cmd_preview)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
