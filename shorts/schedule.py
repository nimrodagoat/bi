"""How many videos are due right now.

GitHub starts scheduled runs late and sometimes skips them, so instead of
"one video per run", every run (hourly) posts whatever is due and missing:
slots that have passed in the current YouTube quota day (which starts at
midnight California time) minus videos already posted in that quota day.

    python -m shorts.schedule      prints the number of videos due now
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from . import store

QUOTA_TZ = ZoneInfo("America/Los_Angeles")  # YouTube's quota resets at midnight Pacific


def quota_day_start(now: dt.datetime) -> dt.datetime:
    local = now.astimezone(QUOTA_TZ)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)


def due_now(cfg: dict, posted: list[dict], now: dt.datetime | None = None) -> int:
    now = now or dt.datetime.now(dt.timezone.utc)
    sched = cfg.get("schedule", {})
    slots = sched.get("slots_utc") or []
    start = quota_day_start(now)
    passed = 0
    for day in (start.date(), start.date() + dt.timedelta(days=1)):
        for slot in slots:
            hh, mm = (int(x) for x in str(slot).split(":"))
            t = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=dt.timezone.utc)
            if start <= t <= now:
                passed += 1
    done = 0
    for p in posted:
        try:
            when = dt.datetime.strptime(p.get("posted_at", ""), "%Y-%m-%d %H:%M UTC").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        if when >= start:
            done += 1
    cap = sched.get("max_per_day", 6)
    return max(0, min(passed, cap) - done)


if __name__ == "__main__":
    print(due_now(store.load_config(), store.load_posted()))
