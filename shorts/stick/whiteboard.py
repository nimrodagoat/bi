"""Fact-wizard videos (`style: whiteboard`): a cartoon wizard on a white page tells
a story from history or legend while real pictures pop in beside him. Blue
hand-lettered captions run along the top (see overlay.py)."""

from __future__ import annotations

import math

import cairo

from . import images
from .gfx import H, W, back_out, clamp, draw_surface, ease_out, glow, rounded_rect, set_color, stroke_line, text
from .scenes import fill, scene

INK = "#1b1b1b"
_PICS: dict = {}


def _talking(cv, shot, t) -> float:
    """How open the mouth is: flaps while a word is being spoken."""
    now = shot.start + t
    for w in shot.words:
        if w.start <= now <= w.end:
            return 0.5 + 0.5 * abs(math.sin((now - w.start) * 18))
    return 0.0


def draw_wizard(ctx, x, ground, s=1.0, pose="idle", t=0.0, facing=1, mouth=0.0, robe="#4a3a9a",
                spell=False, point=0.0):
    """A cartoon wizard, feet at `ground`. Poses: idle, point (arm towards
    `point` radians, 0 = straight out), cast (staff raised), shrug."""
    f = facing
    lw = 6 * s
    bob = 3 * s * math.sin(t * 2.2)
    hip_y = ground - 120 * s
    sh_y = ground - 290 * s + bob
    # legs and boots
    for dx in (-26, 26):
        stroke_line(ctx, [(x + dx * s, hip_y), (x + dx * 1.1 * s, ground - 14 * s)], lw, INK)
        ctx.save()
        ctx.translate(x + dx * 1.1 * s + 10 * s * f, ground - 8 * s)
        ctx.scale(1, 0.55)
        ctx.arc(0, 0, 20 * s, 0, 2 * math.pi)
        ctx.restore()
        set_color(ctx, "#5a3a22")
        ctx.fill_preserve()
        set_color(ctx, INK)
        ctx.set_line_width(4 * s)
        ctx.stroke()
    # robe: wide at the hem, narrow at the shoulders
    pts = [(x - 40 * s, sh_y), (x + 40 * s, sh_y), (x + 78 * s, hip_y + 10 * s), (x - 78 * s, hip_y + 10 * s)]
    fill(ctx, pts, robe)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    set_color(ctx, INK)
    ctx.set_line_width(lw)
    ctx.stroke()
    ctx.rectangle(x - 62 * s, hip_y - 70 * s + bob * 0.5, 124 * s, 14 * s)  # belt
    set_color(ctx, "#e0b030")
    ctx.fill()
    for sx, sy in ((-40, -40), (30, -110), (-15, -150), (45, -30), (-55, -95)):  # stars
        _star(ctx, x + sx * s, hip_y + sy * s * 0.6, 9 * s, "#ffd34d")
    # arms
    shoulder_l, shoulder_r = (x - 34 * s * f, sh_y + 14 * s), (x + 34 * s * f, sh_y + 14 * s)
    if pose == "point":
        a = point
        hand = (shoulder_r[0] + f * 130 * s * math.cos(a), shoulder_r[1] - 130 * s * math.sin(a))
        elbow = ((shoulder_r[0] + hand[0]) / 2, (shoulder_r[1] + hand[1]) / 2 - 6 * s)
        staff_hand = (shoulder_l[0] - f * 30 * s, shoulder_l[1] + 110 * s)
    elif pose == "cast":
        hand = (shoulder_r[0] + f * 60 * s, shoulder_r[1] + 90 * s)
        elbow = (shoulder_r[0] + f * 40 * s, shoulder_r[1] + 50 * s)
        staff_hand = (shoulder_l[0] - f * 40 * s, shoulder_l[1] - 60 * s)
    elif pose == "shrug":
        hand = (shoulder_r[0] + f * 90 * s, shoulder_r[1] - 30 * s)
        elbow = (shoulder_r[0] + f * 70 * s, shoulder_r[1] + 30 * s)
        staff_hand = (shoulder_l[0] - f * 90 * s, shoulder_l[1] - 30 * s)
    else:
        hand = (shoulder_r[0] + f * 40 * s, shoulder_r[1] + 110 * s)
        elbow = (shoulder_r[0] + f * 40 * s, shoulder_r[1] + 55 * s)
        staff_hand = (shoulder_l[0] - f * 30 * s, shoulder_l[1] + 110 * s)
    stroke_line(ctx, [shoulder_r, elbow, hand], lw, INK)
    l_elbow = ((shoulder_l[0] + staff_hand[0]) / 2 - f * 14 * s, (shoulder_l[1] + staff_hand[1]) / 2)
    # staff in the other hand, with a glowing orb
    top = (staff_hand[0] - f * 6 * s, staff_hand[1] - 190 * s)
    stroke_line(ctx, [(staff_hand[0] + f * 4 * s, staff_hand[1] + 120 * s), top], 9 * s, "#8a5a32", 1.0, INK,
                outline_extra=5 * s)
    glow(ctx, top[0], top[1], 50 * s, "#7fd0ff", 0.55 + 0.25 * math.sin(t * 4))
    ctx.arc(top[0], top[1], 15 * s, 0, 2 * math.pi)
    set_color(ctx, "#bfe8ff")
    ctx.fill_preserve()
    set_color(ctx, INK)
    ctx.set_line_width(4 * s)
    ctx.stroke()
    stroke_line(ctx, [shoulder_l, l_elbow, staff_hand], lw, INK)
    for hp in (hand, staff_hand):
        ctx.arc(hp[0], hp[1], 10 * s, 0, 2 * math.pi)
        set_color(ctx, "#f1d3b3")
        ctx.fill_preserve()
        set_color(ctx, INK)
        ctx.set_line_width(4 * s)
        ctx.stroke()
    if spell or pose == "cast":
        for i in range(9):
            a = t * 3 + i * 0.7
            d = (30 + (t * 70 + i * 17) % 80) * s
            _star(ctx, top[0] + math.cos(a) * d, top[1] + math.sin(a) * d, 6 * s, "#ffd34d")
    # head
    hx, hy = x, sh_y - 62 * s
    ctx.arc(hx, hy, 48 * s, 0, 2 * math.pi)
    set_color(ctx, "#f1d3b3")
    ctx.fill_preserve()
    set_color(ctx, INK)
    ctx.set_line_width(lw)
    ctx.stroke()
    # beard: a soft white cloud down to the chest
    bx, by = hx + 4 * s * f, hy + 30 * s
    ctx.move_to(bx - 44 * s, by - 14 * s)
    ctx.curve_to(bx - 50 * s, by + 50 * s, bx - 12 * s, by + 92 * s, bx, by + 104 * s)
    ctx.curve_to(bx + 12 * s, by + 92 * s, bx + 50 * s, by + 50 * s, bx + 44 * s, by - 14 * s)
    ctx.curve_to(bx + 20 * s, by + 2 * s, bx - 20 * s, by + 2 * s, bx - 44 * s, by - 14 * s)
    set_color(ctx, "#fbfbfb")
    ctx.fill_preserve()
    set_color(ctx, INK)
    ctx.set_line_width(4.5 * s)
    ctx.stroke()
    # mouth (flaps while talking), eyes, brows, nose
    my = by + 8 * s
    ctx.save()
    ctx.translate(bx, my)
    ctx.scale(1, 0.3 + 0.9 * mouth)
    ctx.arc(0, 0, 11 * s, 0, 2 * math.pi)
    ctx.restore()
    set_color(ctx, "#5a1f1f")
    ctx.fill()
    blink = 0.15 if (t % 3.7) < 0.12 else 1.0
    for ex in (-17, 17):
        ctx.save()
        ctx.translate(hx + (ex + 6 * f) * s, hy - 4 * s)
        ctx.scale(1, blink)
        ctx.arc(0, 0, 6 * s, 0, 2 * math.pi)
        ctx.restore()
        set_color(ctx, INK)
        ctx.fill()
        stroke_line(ctx, [(hx + (ex + 6 * f - 9) * s, hy - 20 * s), (hx + (ex + 6 * f + 9) * s, hy - 22 * s)],
                    4 * s, "#e8e8e8", 1.0, INK, outline_extra=2 * s)
    ctx.arc(hx + 9 * s * f, hy + 10 * s, 9 * s, 0, 2 * math.pi)
    set_color(ctx, "#e6b894")
    ctx.fill()
    # hat with a floppy tip and a star
    ctx.save()
    ctx.translate(hx, hy - 34 * s)
    ctx.save()
    ctx.scale(1, 0.28)
    ctx.arc(0, 0, 86 * s, 0, 2 * math.pi)
    ctx.restore()
    set_color(ctx, robe)
    ctx.fill_preserve()
    set_color(ctx, INK)
    ctx.set_line_width(lw)
    ctx.stroke()
    ctx.move_to(-50 * s, -6 * s)
    ctx.curve_to(-30 * s, -100 * s, 10 * s * f, -170 * s, 60 * s * f, -190 * s)
    ctx.curve_to(30 * s * f, -150 * s, 40 * s, -60 * s, 50 * s, -6 * s)
    ctx.close_path()
    set_color(ctx, robe)
    ctx.fill_preserve()
    set_color(ctx, INK)
    ctx.stroke()
    ctx.restore()
    _star(ctx, hx - 6 * s, hy - 100 * s, 13 * s, "#ffd34d")


def _star(ctx, x, y, r, col):
    ctx.move_to(x, y - r)
    for k in range(1, 10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        ctx.line_to(x + math.cos(a) * rr, y + math.sin(a) * rr)
    ctx.close_path()
    set_color(ctx, col)
    ctx.fill()


def _picture(ctx, spec, t, shot, k):
    """A real picture popping in with a white border and a soft shadow, drifting
    slowly in (Ken Burns)."""
    at = shot.cue(spec.get("cue"), 0.0)
    if t < at:
        return
    a = clamp((t - at) / 0.35)
    gone = spec.get("out") is not None and t >= shot.cue(spec.get("out"), 1e9)
    if gone:
        return
    path = images.path_for(spec.get("image"))
    if path not in _PICS:
        img = None
        if path.exists():
            from PIL import Image
            from .gfx import pil_to_surface
            img = pil_to_surface(Image.open(path))
        _PICS[path] = img
    img = _PICS[path]
    cx, cy = float(spec.get("x", 0.5)) * W, float(spec.get("y", 0.4)) * H
    bw = float(spec.get("w", 0.8)) * W
    if img is not None:
        iw, ih = img.get_width(), img.get_height()
        bh = bw * float(spec.get("aspect", ih / iw))
    else:
        bh = bw * float(spec.get("aspect", 0.7))
    bh = min(bh, float(spec.get("max_h", 0.5)) * H)
    sc = back_out(a) * 0.15 + 0.85
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(math.radians(float(spec.get("tilt", (-2, 1.5, -1)[k % 3]))))
    ctx.scale(sc, sc)
    rounded_rect(ctx, -bw / 2 + 10, -bh / 2 + 14, bw, bh, 10)  # shadow
    ctx.set_source_rgba(0, 0, 0, 0.18 * a)
    ctx.fill()
    pad = 14
    rounded_rect(ctx, -bw / 2 - pad, -bh / 2 - pad, bw + 2 * pad, bh + 2 * pad, 10)
    ctx.set_source_rgba(1, 1, 1, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(0, 0, 0, 0.25 * a)
    ctx.set_line_width(2)
    ctx.stroke()
    ctx.rectangle(-bw / 2, -bh / 2, bw, bh)
    ctx.clip()
    if img is not None:
        iw, ih = img.get_width(), img.get_height()
        z = max(bw / iw, bh / ih) * (1.0 + 0.08 * ease_out((t - at) / max(shot.dur, 1)))  # slow push in
        ctx.scale(z, z)
        ctx.set_source_surface(img, -iw / 2, -ih / 2)
        ctx.paint_with_alpha(a)
    else:  # placeholder until the picture is fetched
        ctx.rectangle(-bw / 2, -bh / 2, bw, bh)
        ctx.set_source_rgba(0.85, 0.82, 0.74, a)
        ctx.fill()
        draw_surface(ctx, text("PICTURE", "title", 60, "#8a8270"), 0, 0, alpha=a)
    ctx.restore()
    if spec.get("label") and a > 0.5:
        draw_surface(ctx, text(str(spec["label"]).upper(), "comic", 40, "#1d4fa0"), cx, cy + bh / 2 * sc + 50,
                     alpha=clamp((a - 0.5) * 2))


@scene("whiteboard")
def whiteboard(cv, shot, t):
    """White page, the wizard, and `pictures: [{image: {search|file}, x, y, w, cue, out, label, tilt}]`.
    `wizard: {x, y, scale, pose: idle|point|cast|shrug, point, facing, pose_at: {cue: pose}, hide}`.
    `big: {text, cue, y, color}`: a big hand-lettered word (e.g. a year)."""
    ctx = cv.ctx
    o = shot.spec
    ctx.rectangle(-400, -400, W + 800, H + 800)
    set_color(ctx, "#fbfbf8")
    ctx.fill()
    for k, p in enumerate(o.get("pictures") or []):
        _picture(ctx, p, t, shot, k)
    big = o.get("big")
    if big and t >= shot.cue(big.get("cue"), 0.0):
        a = clamp((t - shot.cue(big.get("cue"), 0.0)) / 0.3)
        draw_surface(ctx, text(str(big.get("text", "")).upper(), "comic", int(big.get("size", 150)),
                               big.get("color", "#1d4fa0")), W / 2, float(big.get("y", 0.35)) * H,
                     back_out(a) * 0.2 + 0.8, a)
    wz = o.get("wizard", {})
    if wz.get("hide"):
        return
    pose = wz.get("pose", "idle")
    for cue, p in (wz.get("pose_at") or {}).items():
        if t >= shot.cue(cue, 1e9):
            pose = p
    draw_wizard(ctx, float(wz.get("x", 0.5)) * W, float(wz.get("y", 0.86)) * H, float(wz.get("scale", 1.25)),
                pose, shot.start + t, int(wz.get("facing", 1)), _talking(cv, shot, t),
                wz.get("robe", "#4a3a9a"), spell=bool(wz.get("spell")), point=float(wz.get("point", 0.35)))
