"""How-it-works cut-aways: a slice through a back yard (sky, house, lawn, soil)
where parts of a build appear one at a time, with labels, measurements, big
numbers and stickman wizards who live in it. Used by `style: explainer` videos."""

from __future__ import annotations

import math

import cairo

from . import figures as F
from .gfx import (H, W, back_out, clamp, draw_surface, ease_in_out, ease_out, glow, pill, rgb,
                  rounded_rect, set_color, stroke_line, text, vgradient)
from .scenes import fill, scene, shade

GROUND = 820  # the lawn line, in scene pixels


def _px(v, size):
    return float(v) * size


def _appear(shot, t, part, default=0.0, dur=0.6):
    """0..1 progress of a part's entrance (`cue`, `anim`)."""
    at = shot.cue(part.get("cue"), default)
    if t < at:
        return -1.0
    return clamp((t - at) / float(part.get("dur", dur)))


# ------------------------------------------------------------------ the yard

def _sky(ctx, t, o):
    night = o.get("night")
    vgradient(ctx, -400, -400, W + 800, GROUND + 400, "#0b1430" if night else "#6fb3e8",
              "#1d2a4a" if night else "#cfe8f7")
    if not night:
        for k in range(5):  # clouds drifting
            cx = (k * 330 + t * (12 + k * 3)) % (W + 600) - 300
            cy = 120 + (k * 97) % 260
            for dx, dy, r in ((0, 0, 70), (60, -20, 60), (-60, -10, 55), (110, 10, 45), (-110, 12, 40)):
                ctx.arc(cx + dx, cy + dy, r, 0, 2 * math.pi)
            set_color(ctx, "#ffffff", 0.85)
            ctx.fill()


def _house(ctx, x, w=420):
    base = GROUND - 6
    h = w * 0.55
    ctx.rectangle(x, base - h, w, h)
    set_color(ctx, "#d9d2c3")
    ctx.fill()
    for k in range(int(h // 14)):  # siding
        ctx.rectangle(x, base - h + k * 14, w, 2)
    set_color(ctx, "#000000", 0.06)
    ctx.fill()
    fill(ctx, [(x - 30, base - h), (x + w / 2, base - h - w * 0.32), (x + w + 30, base - h)], "#c4553b")
    for r in range(2):
        for c in range(4):
            wx, wy = x + 30 + c * (w - 60) / 3.4, base - h + 30 + r * h * 0.45
            ctx.rectangle(wx, wy, 52, 62)
            set_color(ctx, "#2f5d8c")
            ctx.fill()
            for side in (-1, 1):
                ctx.rectangle(wx + (60 if side > 0 else -14), wy, 10, 62)
            set_color(ctx, "#1f3d6b")
            ctx.fill()
    ctx.rectangle(x + w * 0.45, base - 90, 46, 90)
    set_color(ctx, "#1f3d6b")
    ctx.fill()


def _ground(ctx, t, o):
    vgradient(ctx, -400, GROUND, W + 800, H + 600 - GROUND, "#7a5232", "#4a301c")
    for k in range(160):  # pebbles and grit
        x = (k * 157.3) % (W + 600) - 300
        y = GROUND + 60 + (k * 233.7) % (H - GROUND + 300)
        ctx.arc(x, y, 2 + (k % 3), 0, 2 * math.pi)
    set_color(ctx, "#2e1d10", 0.35)
    ctx.fill()
    ctx.rectangle(-400, GROUND - 4, W + 800, 34)
    set_color(ctx, "#4f9a34")
    ctx.fill()
    for k in range(-8, 20):  # mowing stripes
        ctx.rectangle(k * 90, GROUND - 4, 45, 34)
    set_color(ctx, "#ffffff", 0.06)
    ctx.fill()


# ------------------------------------------------------------------ parts

def _pipe(ctx, x, y, w, h, p, o):
    """A corrugated steel tube lying on its side, cut open so we see inside."""
    r = h / 2
    rounded_rect(ctx, x, y, w, h, r)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *rgb("#dfe4ea"))
    g.add_color_stop_rgb(0.5, *rgb("#9aa4ae"))
    g.add_color_stop_rgb(1, *rgb("#6c7680"))
    ctx.set_source(g)
    ctx.fill()
    inset = 18
    rounded_rect(ctx, x + inset, y + inset, w - 2 * inset, h - 2 * inset, r - inset)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *rgb("#8d97a1"))
    g.add_color_stop_rgb(1, *rgb("#55606a"))
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    rounded_rect(ctx, x + inset, y + inset, w - 2 * inset, h - 2 * inset, r - inset)
    ctx.clip()
    for k in range(int(w // 26)):  # ribs
        ctx.rectangle(x + k * 26, y, 6, h)
    set_color(ctx, "#ffffff", 0.08)
    ctx.fill()
    fy = y + h * 0.72  # wooden floor
    ctx.rectangle(x, fy, w, h)
    set_color(ctx, "#b07a45")
    ctx.fill()
    for k in range(int(w // 60) + 1):
        ctx.rectangle(x + k * 60, fy, 3, h)
    set_color(ctx, "#6e4524", 0.6)
    ctx.fill()
    if o.get("lamp", True):
        lx = x + w / 2
        stroke_line(ctx, [(lx, y + inset), (lx, y + inset + 40)], 3, "#333333")
        glow(ctx, lx, y + inset + 46, 160, "#ffe2a0", 0.35)
        set_color(ctx, "#fff1c4")
        ctx.arc(lx, y + inset + 46, 10, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()
    return fy


def _shaft(ctx, x, y, w, h, t, shot, part):
    ctx.rectangle(x, y, w, h)
    g = cairo.LinearGradient(x, 0, x + w, 0)
    g.add_color_stop_rgb(0, *rgb("#6c7680"))
    g.add_color_stop_rgb(0.5, *rgb("#b8c0c8"))
    g.add_color_stop_rgb(1, *rgb("#6c7680"))
    ctx.set_source(g)
    ctx.fill()
    ctx.rectangle(x + 12, y, w - 24, h)
    set_color(ctx, "#4a535c")
    ctx.fill()
    for k in range(int(h // 46)):  # ladder
        ctx.rectangle(x + w * 0.25, y + 20 + k * 46, w * 0.5, 6)
    for lx in (x + w * 0.25, x + w * 0.75 - 6):
        ctx.rectangle(lx, y, 6, h)
    set_color(ctx, "#c9ced6")
    ctx.fill()
    # the hatch on top: a lid that swings open at `open`
    ho = 0.0
    if part.get("open") is not None:
        ho = ease_out((t - shot.cue(part.get("open"))) / 0.7) if t >= shot.cue(part.get("open")) else 0.0
    ctx.save()
    ctx.translate(x - 10, y + 4)
    ctx.rotate(-1.9 * ho)
    rounded_rect(ctx, 0, -14, w + 20, 18, 6)
    set_color(ctx, "#2f3a48")
    ctx.fill()
    ctx.restore()


def _vent(ctx, x, y1, y2, t, shot, part):
    stroke_line(ctx, [(x, y2), (x, y1)], 22, "#8f99a3", 1.0, "#4b545c")
    fill(ctx, [(x - 40, y1), (x + 40, y1), (x + 26, y1 - 30), (x - 26, y1 - 30)], "#5c6670")  # rain cap
    if part.get("filter"):
        fy = y1 + (y2 - y1) * 0.62
        rounded_rect(ctx, x - 46, fy - 40, 92, 80, 10)
        set_color(ctx, "#e9e4d8")
        ctx.fill()
        for k in range(6):
            ctx.rectangle(x - 36, fy - 30 + k * 11, 72, 4)
        set_color(ctx, "#a59f90")
        ctx.fill()
    if part.get("fan"):
        ang = t * 9 if t >= shot.cue(part.get("spin"), 0.0) else 0.0
        fx, fy = x, y2 - 30
        set_color(ctx, "#2b3138")
        ctx.arc(fx, fy, 38, 0, 2 * math.pi)
        ctx.fill()
        for k in range(4):
            a = ang + k * math.pi / 2
            fill(ctx, [(fx, fy), (fx + math.cos(a) * 34, fy + math.sin(a) * 34),
                       (fx + math.cos(a + 0.6) * 30, fy + math.sin(a + 0.6) * 30)], "#c9ced6")
    if part.get("flow") is not None and t >= shot.cue(part.get("flow")):
        for k in range(6):  # fresh air moving down the pipe
            yy = y1 + ((t * 160 + k * (y2 - y1) / 6) % (y2 - y1))
            fill(ctx, [(x - 9, yy - 8), (x + 9, yy - 8), (x, yy + 6)], "#7fe0ff")


def _bunks(ctx, x, floor, n=2):
    for k in range(n):
        bx = x + k * 150
        for lvl in range(2):
            by = floor - 40 - lvl * 70
            rounded_rect(ctx, bx, by, 120, 18, 5)
            set_color(ctx, "#3b5b8c")
            ctx.fill()
            rounded_rect(ctx, bx + 4, by - 10, 30, 12, 4)
            set_color(ctx, "#f2efe8")
            ctx.fill()
        for px in (bx, bx + 116):
            ctx.rectangle(px, floor - 120, 5, 120)
        set_color(ctx, "#5a5f66")
        ctx.fill()


def _supplies(ctx, x, floor, n=6):
    cols = ["#c8963e", "#a8743a", "#6b8f3a", "#b5523b", "#3f6e9a"]
    for k in range(n):
        bx = x + (k % 3) * 52
        by = floor - 46 - (k // 3) * 46
        ctx.rectangle(bx, by, 48, 44)
        set_color(ctx, cols[k % len(cols)])
        ctx.fill()
        ctx.rectangle(bx, by + 18, 48, 4)
        set_color(ctx, "#000000", 0.2)
        ctx.fill()


def _dust(ctx, t, shot, part):
    """Fallout: specks drifting down from the sky and settling on the lawn."""
    at = shot.cue(part.get("cue"), 0.0)
    if t < at:
        return
    n = int(part.get("n", 70))
    col = part.get("color", "#d7ff5a")
    for k in range(n):
        start = at + (k * 0.618) % 1 * 2.5
        if t < start:
            continue
        x = (k * 97.31) % (W + 200) - 100
        y = min(-40 + (t - start) * (90 + (k % 5) * 25), GROUND - 4 + (k % 4))
        glow(ctx, x, y, 14, col, 0.35)
        set_color(ctx, col, 0.9)
        ctx.arc(x, y, 3.5, 0, 2 * math.pi)
        ctx.fill()


def _shield(ctx, t, shot, part):
    """Rays from the dust on the surface going down into the soil, getting
    weaker every layer: most never reach the bottom."""
    at = shot.cue(part.get("cue"), 0.0)
    if t < at:
        return
    x0, x1 = _px(part.get("x", 0.1), W), _px(part.get("x2", 0.9), W)
    y0, y1 = GROUND + 30, _px(part.get("bottom", 0.62), H)
    layers = int(part.get("layers", 6))
    for k in range(layers + 1):  # halving lines
        y = y0 + (y1 - y0) * k / layers
        ctx.rectangle(x0, y, x1 - x0, 2)
    set_color(ctx, "#ffd34d", 0.35 * clamp((t - at) / 0.5))
    ctx.fill()
    for k in range(40):
        x = x0 + (k * 0.618 % 1) * (x1 - x0)
        depth = ((t - at) * 220 + k * 37) % (y1 - y0 + 60)
        layer = depth / max((y1 - y0) / layers, 1)
        alive = 0.5 ** layer  # each layer of dirt lets half through
        if (k * 0.37) % 1 > alive * 1.6:
            continue
        stroke_line(ctx, [(x, y0 + depth - 26), (x, y0 + depth)], 4, "#d7ff5a", min(1.0, alive * 1.4))


def _measure(ctx, part, a):
    col = part.get("color", "#ffffff")
    if part.get("x") is not None:  # vertical
        x = _px(part["x"], W)
        ya, yb = _px(part["y1"], H), _px(part["y2"], H)
        stroke_line(ctx, [(x, ya), (x, ya + (yb - ya) * a)], 4, col)
        for yy in (ya, ya + (yb - ya) * a):
            stroke_line(ctx, [(x - 14, yy), (x + 14, yy)], 4, col)
        if a >= 1:
            pill(ctx, x + 20 + 60, (ya + yb) / 2, str(part.get("label", "")).upper(), "caption", 42, "#101010", col,
                 0.95, pad_x=14, pad_y=6)
    else:
        y = _px(part["y"], H)
        xa, xb = _px(part["x1"], W), _px(part["x2"], W)
        stroke_line(ctx, [(xa, y), (xa + (xb - xa) * a, y)], 4, col)
        for xx in (xa, xa + (xb - xa) * a):
            stroke_line(ctx, [(xx, y - 14), (xx, y + 14)], 4, col)
        if a >= 1:
            pill(ctx, (xa + xb) / 2, y - 40, str(part.get("label", "")).upper(), "caption", 42, "#101010", col, 0.95,
                 pad_x=14, pad_y=6)


def _label(ctx, part, a):
    x, y = _px(part["x"], W), _px(part["y"], H)
    if part.get("to"):
        tx, ty = _px(part["to"][0], W), _px(part["to"][1], H)
        stroke_line(ctx, [(x, y), (x + (tx - x) * a, y + (ty - y) * a)], 4, "#ffffff", 0.9, "#101010")
        set_color(ctx, "#ffffff", a)
        ctx.arc(tx, ty, 8 * a, 0, 2 * math.pi)
        ctx.fill()
    pill(ctx, x, y, str(part.get("text", "")).upper(), "caption", int(part.get("size", 40)), "#101010",
         part.get("color", "#ffd34d"), 0.96, scale=back_out(a), alpha=clamp(a * 3), pad_x=16, pad_y=8)


def _big(ctx, part, a):
    x, y = _px(part.get("x", 0.5), W), _px(part.get("y", 0.2), H)
    draw_surface(ctx, text(str(part.get("text", "")).upper(), "title", int(part.get("size", 170)),
                           part.get("color", "#ffd34d"), stroke=8, stroke_color="#101010", shadow=6),
                 x, y, back_out(a) * 0.2 + 0.8, clamp(a * 3))


# ------------------------------------------------------------------ wizards

def draw_wizard(ctx, t, spec, k=0):
    x = _px(spec.get("x", 0.5), W)
    y = _px(spec.get("y", 0.6), H)
    sc = float(spec.get("scale", 0.75))
    facing = int(spec.get("facing", 1))
    action = spec.get("action", "idle")
    robe = spec.get("robe", ["#5b3fa0", "#2f6e9a", "#8a2f4f", "#2f7a4f"][k % 4])
    if spec.get("to") is not None:
        p = clamp((t - float(spec.get("go", 0))) / max(float(spec.get("dur", 2.0)), 0.1))
        x += (_px(spec["to"], W) - x) * ease_in_out(p)
        if 0 < p < 1:
            action = "walk"
            facing = 1 if _px(spec["to"], W) > _px(spec.get("x", 0.5), W) else -1
    if action == "cast":
        pose = F.knock(t * 0.25 + k)
    else:
        pose = F.pose_for(action, t + k * 0.8, seed=k)
    j = F.solve(pose, x, y, sc, facing)
    # staff in the back hand, glowing tip
    hx, hy = j.hand_b
    top = (hx + 8 * facing * sc, hy - 120 * sc)
    stroke_line(ctx, [(hx, hy + 40 * sc), top], 7 * sc, "#7a5232", 1.0, "#3a2414")
    glow(ctx, top[0], top[1], 40 * sc, spec.get("glow", "#8fd3ff"), 0.6)
    set_color(ctx, spec.get("glow", "#8fd3ff"))
    ctx.arc(top[0], top[1], 8 * sc, 0, 2 * math.pi)
    ctx.fill()
    F.draw_stickman(ctx, pose, x, y, sc, facing)
    # robe over the body
    nx, ny = j.neck
    fill(ctx, [(nx - 18 * sc, ny + 6 * sc), (nx + 18 * sc, ny + 6 * sc), (j.hip[0] + 46 * sc, y - 6 * sc),
               (j.hip[0] - 46 * sc, y - 6 * sc)], robe)
    for i in range(3):  # little stars on the robe
        sx = j.hip[0] + (-20 + i * 20) * sc
        sy = j.hip[1] + (-10 + (i % 2) * 30) * sc
        set_color(ctx, "#ffd34d", 0.9)
        ctx.arc(sx, sy, 3.5 * sc, 0, 2 * math.pi)
        ctx.fill()
    hx0, hy0 = j.head
    r = F.HEAD * sc
    fill(ctx, [(hx0 - r * 0.7, hy0 + r * 0.4), (hx0 + r * 0.7, hy0 + r * 0.4), (hx0 + 4 * facing * sc, hy0 + r * 2.4)],
         "#f4f1ea")  # beard
    ctx.save()  # pointy hat with a floppy tip
    ctx.translate(hx0, hy0 - r * 0.55)
    fill(ctx, [(-r * 1.6, 0), (r * 1.6, 0), (r * 0.5 * facing, -r * 2.6), (r * 1.2 * facing, -r * 3.0),
               (r * 0.1 * facing, -r * 2.5), (-r * 0.6, -r * 0.4)], robe)
    ctx.rectangle(-r * 1.7, -4 * sc, r * 3.4, 9 * sc)
    set_color(ctx, shade(robe, 0.6))
    ctx.fill()
    set_color(ctx, "#ffd34d")
    ctx.arc(r * 0.1, -r * 1.3, 4 * sc, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()
    cast = spec.get("spell")
    if cast is not None and t >= float(cast):
        for i in range(8):  # sparkles from the staff
            a = t * 3 + i * 0.8
            d = 20 + ((t * 60 + i * 13) % 70)
            set_color(ctx, "#fff3a0", 0.9)
            ctx.arc(top[0] + math.cos(a) * d * sc, top[1] + math.sin(a) * d * sc, 4 * sc, 0, 2 * math.pi)
            ctx.fill()


# ------------------------------------------------------------------ the scene

@scene("cutaway")
def cutaway(cv, shot, t):
    """A slice through a back yard. `parts`: [{type, cue, ...}] drawn in order:
    hole, pipe, shaft, vent, backfill, bunks, supplies, dust, shield, measure,
    label, big. `wizards`: [{x, y, action, facing, to, go, dur, spell, robe}]."""
    ctx = cv.ctx
    o = shot.spec
    _sky(ctx, t, o)
    if o.get("house", True):
        _house(ctx, float(o.get("house_x", 0.52)) * W)
    _ground(ctx, t, o)
    later = []
    for part in o.get("parts") or []:
        kind = part.get("type")
        a = _appear(shot, t, part)
        if a < 0:
            continue
        anim = part.get("anim", "drop" if kind in ("pipe", "shaft") else "fade")
        x, y = _px(part.get("x", 0.1), W), _px(part.get("y", 0.5), H)
        w, h = _px(part.get("w", 0.3), W), _px(part.get("h", 0.1), H)
        ctx.save()
        if anim == "drop":
            ctx.translate(0, -(1 - ease_out(a)) * (y + h + 200))
        if kind == "hole":  # dug out, top to bottom
            ctx.rectangle(x, GROUND - 4, w, (y + h - GROUND + 4) * (ease_out(a) if anim == "dig" else 1))
            set_color(ctx, "#2e1d10")
            ctx.fill()
        elif kind == "pipe":
            _pipe(ctx, x, y, w, h, a, part)
        elif kind == "shaft":
            _shaft(ctx, x, y, w, h, t, shot, part)
        elif kind == "vent":
            _vent(ctx, x, _px(part.get("top", 0.38), H), _px(part.get("bottom", 0.6), H), t, shot, part)
        elif kind == "backfill":  # dirt poured back over, rising from the bottom of the hole
            top = y + h - (h * ease_out(a) if anim != "fade" else h)
            ctx.rectangle(x, top, w, y + h - top)
            g = cairo.LinearGradient(0, y, 0, y + h)
            g.add_color_stop_rgb(0, *rgb("#8a5e3a"))
            g.add_color_stop_rgb(1, *rgb("#6a4428"))
            ctx.set_source(g)
            ctx.fill()
        elif kind == "bunks":
            _bunks(ctx, x, y, int(part.get("n", 2)))
        elif kind == "supplies":
            _supplies(ctx, x, y, int(part.get("n", 6)))
        elif kind in ("dust", "shield", "measure", "label", "big"):
            later.append((kind, part, a))
        ctx.restore()
    for k, wz in enumerate(o.get("wizards") or []):
        if t >= shot.cue(wz.get("cue"), 0.0):
            draw_wizard(ctx, t, wz, k)
    for kind, part, a in later:  # on top of everything
        if kind == "dust":
            _dust(ctx, t, shot, part)
        elif kind == "shield":
            _shield(ctx, t, shot, part)
        elif kind == "measure":
            _measure(ctx, part, ease_out(a))
        elif kind == "label":
            _label(ctx, part, ease_out(a))
        elif kind == "big":
            _big(ctx, part, a)


# ------------------------------------------------------------------ pre-rendered footage (e.g. Blender)

_FRAMES: dict = {}


@scene("footage")
def footage(cv, shot, t):
    """Plays an image sequence (`frames`: a folder of PNGs, `fps`) as the picture,
    holding the last frame once it runs out. Used for 3D renders."""
    from pathlib import Path
    folder = Path(shot.get("frames"))
    if folder not in _FRAMES:
        _FRAMES[folder] = sorted(folder.glob("*.png"))
    files = _FRAMES[folder]
    if not files:
        return
    k = min(int((t + float(shot.get("offset", 0))) * float(shot.get("fps", 30))), len(files) - 1)
    img = cairo.ImageSurface.create_from_png(str(files[k]))
    ctx = cv.ctx
    ctx.save()
    ctx.scale(W / img.get_width(), H / img.get_height())
    ctx.set_source_surface(img, 0, 0)
    ctx.paint()
    ctx.restore()
