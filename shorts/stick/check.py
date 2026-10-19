"""Catch mistakes in a stickman story before it's rendered."""

from __future__ import annotations

from .scenes import SCENES

MAX_WORDS = 240  # about 100 seconds of narration


def problems(item: dict) -> list[str]:
    out = []
    shots = item.get("shots") or []
    if not shots:
        return ["needs at least one shot"]
    if not item.get("series"):
        out.append("needs 'series' (the series name shown on the title and end card)")
    words = 0
    for n, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            out.append(f"shot {n} is not a key/value block")
            continue
        sc = shot.get("scene", "room")
        if sc not in SCENES:
            out.append(f"shot {n}: unknown scene '{sc}' (choose from {', '.join(sorted(SCENES))})")
        say = shot.get("say") or []
        for line in [say] if isinstance(say, str) else say:
            if isinstance(line, dict):
                if set(line) - {"radio", "narr"}:
                    out.append(f"shot {n}: a 'say' line {line!r} should be text or {{radio: text}}")
                line = " ".join(str(v) for v in line.values())
            words += len(str(line).split())
        rule = shot.get("rule")
        if rule and not (isinstance(rule, dict) and rule.get("text")):
            out.append(f"shot {n}: rule should look like {{n: 1, text: Keep a light on}}")
        if sc == "choice" and len(shot.get("options") or []) != 2:
            out.append(f"shot {n}: a choice needs exactly two options")
    if words > MAX_WORDS:
        out.append(f"narration has {words} words; keep it under ~{MAX_WORDS - 40} so the video stays under ~100 seconds")
    return out
