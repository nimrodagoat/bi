"""Builds content/drafts/explainer-bunker.yaml: a how-it-works test video.
Each step keeps the parts already built (shown at once) and adds new ones on a cue."""
import yaml
from pathlib import Path

L = 820 / 1920  # lawn line as a share of the height
FLOOR = 0.694   # inside the pipe

HOLE = {"type": "hole", "x": 0.06, "y": 0.43, "w": 0.88, "h": 0.36}
FILL = {"type": "backfill", "x": 0.06, "y": 0.43, "w": 0.88, "h": 0.36}
PIPE = {"type": "pipe", "x": 0.1, "y": 0.55, "w": 0.8, "h": 0.2}
SHAFT = {"type": "shaft", "x": 0.12, "y": 0.41, "w": 0.09, "h": 0.2}
VENT = {"type": "vent", "x": 0.82, "top": 0.38, "bottom": 0.6, "filter": True, "fan": True, "flow": 0}
BUNKS = {"type": "bunks", "x": 0.5, "y": FLOOR, "n": 2}
SUPPLIES = {"type": "supplies", "x": 0.25, "y": FLOOR, "n": 6}

INSIDE = [{"x": 0.3, "y": FLOOR, "action": "idle", "facing": 1},
          {"x": 0.45, "y": FLOOR, "action": "idle", "facing": -1},
          {"x": 0.68, "y": FLOOR, "action": "idle", "facing": -1}]
LAWN = [{"x": 0.2, "y": L, "action": "idle", "facing": 1, "scale": 0.6},
        {"x": 0.35, "y": L, "action": "idle", "facing": 1, "scale": 0.6},
        {"x": 0.8, "y": L, "action": "idle", "facing": -1, "scale": 0.6}]
CLOSE = {"zoom": [1.2, 1.3], "focus": [0.5, 0.62]}


def built(*parts):
    """Parts already on screen: no entrance animation."""
    return [{**p, "cue": 0, "anim": "none"} for p in parts]


def new(part, cue, **kw):
    return {**part, "cue": cue, **kw}


shots = [
    dict(say="A hole in your back yard could keep you safe from nuclear fallout. Here's how a backyard shelter works.",
         wizards=[{**w, "cue": "back"} for w in LAWN], parts=[{"type": "big", "text": "?", "y": 0.2, "cue": "how"}]),
    dict(say="First, the wizards dig a trench, about four meters deep.",
         wizards=[{**w, "action": "cast", "spell": 0.3} for w in LAWN],
         parts=[new(HOLE, "dig", anim="dig", dur=2.0),
                {"type": "measure", "x": 0.97, "y1": L, "y2": 0.79, "label": "4 m", "cue": "four", "color": "#ffd34d"}]),
    dict(say="Then they drop in a giant steel pipe, three meters wide. That's the room.",
         wizards=LAWN, parts=built(HOLE) + [new(PIPE, "drop"),
                {"type": "measure", "y": 0.53, "x1": 0.1, "x2": 0.9, "label": "3 m", "cue": "three"}]),
    dict(say="Now they bury it, under at least one meter of dirt. This is the important part.",
         wizards=[{**w, "action": "cast", "spell": 0.3} for w in LAWN],
         parts=built(HOLE) + [new(FILL, "bury", anim="rise", dur=1.6)] + built(PIPE) +
               [{"type": "measure", "x": 0.95, "y1": L, "y2": 0.55, "label": "1 m", "cue": "meter"}]),
    dict(say="Every nine centimeters of packed dirt cuts radiation in half. So one meter of soil blocks about ninety nine point nine percent.",
         parts=built(HOLE, FILL, PIPE) + [{"type": "shield", "cue": 0, "x": 0.1, "x2": 0.9, "bottom": 0.55, "layers": 11},
                {"type": "big", "text": "99.9%", "y": 0.18, "cue": "ninety"}], wizards=INSIDE),
    dict(say="After a blast, radioactive dust can fall from the sky for hours. It lands on the grass, but it can't reach you down here.",
         parts=built(HOLE, FILL, PIPE) + [{"type": "dust", "cue": "dust", "n": 80}],
         wizards=INSIDE),
    dict(say="But you need air. A vent pipe brings air down through a filter that catches the dust. A hand cranked fan keeps it moving, even without power.",
         parts=built(HOLE, FILL, PIPE) + [new({**VENT, "flow": "air", "spin": "fan"}, "vent"),
                {"type": "label", "text": "Filter", "x": 0.62, "y": 0.47, "to": [0.79, 0.52], "cue": "filter"},
                {"type": "label", "text": "Fan", "x": 0.64, "y": 0.62, "to": [0.79, 0.58], "cue": "fan"}],
         wizards=[INSIDE[0], INSIDE[1], {**INSIDE[2], "x": 0.76, "action": "cast", "facing": 1, "spell": 0}],
         camera={"zoom": [1.0, 1.25], "focus": [0.7, 0.55]}),
    dict(say="The way in is a shaft with a ladder, and a heavy hatch on top. The entrance bends, so radiation can't shine straight in.",
         parts=built(HOLE, FILL, PIPE, VENT) + [new({**SHAFT, "open": "hatch"}, "shaft"),
                {"type": "label", "text": "Bend", "x": 0.33, "y": 0.5, "to": [0.17, 0.585], "cue": "bends"}],
         wizards=INSIDE, camera={"zoom": [1.0, 1.25], "focus": [0.25, 0.55]}),
    dict(say="The good news? Fallout gets weaker fast. After seven hours, it's about ten times weaker. After two days, about a hundred times.",
         parts=built(HOLE, FILL, PIPE, VENT, SHAFT) + [{"type": "dust", "cue": 0, "n": 50},
                {"type": "big", "text": "10x weaker", "y": 0.16, "size": 130, "cue": "ten"},
                {"type": "big", "text": "100x weaker", "y": 0.27, "size": 130, "cue": "hundred", "color": "#7fe0ff"}],
         wizards=INSIDE),
    dict(say="So plan for about two weeks. Four liters of water per person, per day. Food. Bunk beds. And some board games.",
         parts=built(HOLE, FILL, PIPE, VENT, SHAFT) + [new(SUPPLIES, "food"), new(BUNKS, "bunk"),
                {"type": "label", "text": "4 L / person / day", "x": 0.5, "y": 0.5, "cue": "four"}],
         wizards=[{**INSIDE[0], "x": 0.18, "to": 0.4, "go": 0.5, "dur": 3}], camera=CLOSE),
    dict(say="Congratulations, wizards. You just built a backyard fallout shelter.",
         parts=built(HOLE, FILL, PIPE, VENT, SHAFT, SUPPLIES, BUNKS),
         wizards=[{**w, "action": "cast", "spell": 0.2} for w in INSIDE], camera=CLOSE),
]

item = {
    "id": "explainer-bunker",
    "format": "stickman",
    "style": "explainer",
    "series": "HOW IT WORKS",
    "day": 1,
    "title": "Wizards built a fallout shelter in a back yard. Here's how it works 🧙",
    "tags": ["howitworks", "engineering", "bunker", "science", "animation", "wizards"],
    "shots": [{"scene": "cutaway", "time": "12:00 PM", "camera": {"zoom": [1.12, 1.18], "focus": [0.5, 0.5]}, **s}
              for s in shots] + [
        {"scene": "endcard", "hold": 1.8, "big": "NEXT: SUBMARINES?", "say": "Follow for more ways things work."}],
}
Path("content/drafts").mkdir(parents=True, exist_ok=True)
Path("content/drafts/explainer-bunker.yaml").write_text(
    "# HOW IT WORKS test: a backyard fallout shelter, built by stickman wizards.\n"
    "# Generated by tools/explainer_bunker.py\n" + yaml.safe_dump([item], sort_keys=False, allow_unicode=True, width=120))
print("ok")
