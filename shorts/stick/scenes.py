"""The places a story can cut to. Each scene paints one frame at time t
(seconds into the shot) using the shot's options."""

from __future__ import annotations

import math

import cairo

from . import figures as F
from . import props
from .gfx import (H, RED, TEAL, W, back_out, beam_tint, clamp, draw_surface, ease_in_out, ease_out, eyes,
                  flicker, glow, mix, noise, pill, ramp, rgb, rounded_rect, set_color, stroke_line, text,
                  vgradient)

ICON_STAGGER = 0.07
SCENES: dict = {}


def scene(name):
    def deco(fn):
        SCENES[name] = fn
        return fn
    return deco


def paint(cv, shot, t: float) -> None:
    SCENES.get(shot.scene, SCENES["room"])(cv, shot, t)


# ------------------------------------------------------------------ shared helpers

def shade(color, k: float):
    r, g, b = rgb(color)
    return (r * k, g * k, b * k)


def fill(ctx, pts, color, alpha=1.0):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    if isinstance(color, tuple):
        ctx.set_source_rgba(*color, alpha)
    else:
        set_color(ctx, color, alpha)
    ctx.fill()


def light_strength(shot, t: float) -> float:
    f, d = shot.get("flicker"), shot.get("dies")
    if f is None and d is None:
        return 1.0
    dt = shot.cue(d, 1e9) if d is not None else 1e9
    ft = shot.cue(f, dt) if f is not None else dt
    if t >= dt:
        return 0.0
    if t < ft:
        return 1.0
    return flicker(t, 1, 11)


def hero(cv, shot, t, spec, ground, scale=1.25, default_x=0.5):
    """Place and animate "you". Returns (joints, beam) where beam is
    (x, y, angle) of the flashlight or None."""
    spec = spec or {}
    x0 = float(spec.get("x", default_x)) * W
    action = spec.get("action", "idle")
    facing = int(spec.get("facing", 1))
    moving = False
    x = x0
    if spec.get("to") is not None:
        x1 = float(spec["to"]) * W
        go = shot.cue(spec.get("go"), 0.0)
        arrive = shot.cue(spec.get("arrive"), shot.dur)
        p = clamp((t - go) / max(arrive - go, 0.01))
        x = x0 + (x1 - x0) * p
        moving = t >= go and p < 1
        if "facing" not in spec:
            facing = 1 if x1 >= x0 else -1
        if moving:
            action = spec.get("move", "walk")
        elif p >= 1:
            action = spec.get("then", action)
    if spec.get("action_at"):  # switch action at a cue: {cue: action}
        for cue, act in spec["action_at"].items():
            if t >= shot.cue(cue, 1e9):
                action = act
    has_light = bool(spec.get("light"))
    if has_light and action in ("idle", "walk", "flashlight"):
        pose = F.flashlight(t, float(spec.get("aim", 0.0)), 1.0 if (moving or action == "walk") else 0.0)
    else:
        pose = F.pose_for(action, t, speed=float(spec.get("speed", 1.0)))
    F.draw_shadow(cv.ctx, x, ground, scale)
    j = F.draw_stickman(cv.ctx, pose, x, ground, scale, facing, prop="flashlight" if has_light else None)
    beam = None
    if has_light:
        tip = F.flashlight_tip(j, scale)
        beam = (tip[0], tip[1], j.hand_angle)
    return j, beam


def creature_eyes(ctx, j, scale, facing, alpha=1.0):
    eyes(ctx, j.head[0] + 5 * scale * facing, j.head[1] - 2 * scale, 4.2 * scale, alpha)


def draw_creatures(cv, shot, t, specs, ground, dark: bool, default_scale=1.25):
    out = []
    for k, c in enumerate(specs or []):
        appear = shot.cue(c.get("cue"), 0.0)
        if t < appear:
            continue
        a = clamp((t - appear) / 0.5)
        x = float(c.get("x", 0.2)) * W
        if c.get("to") is not None:
            p = clamp((t - appear) / max(shot.cue(c.get("arrive"), shot.dur) - appear, 0.01))
            x += (float(c["to"]) * W - x) * p
        sc = float(c.get("scale", default_scale))
        facing = int(c.get("facing", -1))
        pose = F.pose_for(c.get("action", "lurk"), t + k * 1.7, seed=k, speed=float(c.get("speed", 0.6)))
        g = float(c.get("ground", ground))
        j = F.draw_creature(cv.ctx, pose, x, g, sc, facing, alpha=a * (0.9 if dark else 1.0),
                            eye_alpha=0 if dark else a)
        out.append((j, sc, facing, a))
    return out


# ------------------------------------------------------------------ room

FLOOR_Y = 1205


def _room_back(ctx, o, t, cv, shot):
    wall = o.get("wall", "#8a7868")
    vgradient(ctx, -300, -300, W + 600, 645, "#100e0c", "#272019")
    vgradient(ctx, -300, 340, W + 600, 870, mix(wall, "#ffffff", 0.06), mix(wall, "#000000", 0.25))
    ctx.rectangle(-300, 1010, W + 600, 180)
    ctx.set_source_rgba(*shade(wall, 0.72), 1)
    ctx.fill()
    ctx.rectangle(-300, 1004, W + 600, 10)
    ctx.set_source_rgba(*shade(wall, 0.5), 1)
    ctx.fill()
    ctx.rectangle(-300, 1186, W + 600, 22)
    set_color(ctx, "#2d2018")
    ctx.fill()
    g = cairo.LinearGradient(0, FLOOR_Y, 0, H + 200)
    g.add_color_stop_rgb(0, *rgb("#4a2f1e"))
    g.add_color_stop_rgb(1, *rgb("#5e3c27"))
    ctx.set_source(g)
    ctx.rectangle(-300, FLOOR_Y, W + 600, H)
    ctx.fill()
    ctx.set_line_width(3)
    for i in range(-16, 17):
        ctx.move_to(W / 2 + i * 70, FLOOR_Y)
        ctx.line_to(W / 2 + i * 300, H + 300)
    ctx.set_source_rgba(0, 0, 0, 0.28)
    ctx.stroke()
    for y in (1240, 1300, 1390, 1520, 1700, 1950):
        ctx.rectangle(-300, y, W + 600, 2)
    ctx.set_source_rgba(0, 0, 0, 0.12)
    ctx.fill()


@scene("room")
def room(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    _room_back(ctx, o, t, cv, shot)
    dark = float(o.get("dark", 0))
    barricade = o.get("barricade")
    bp = 0.0
    if barricade:
        if isinstance(barricade, dict):
            a = shot.cue(barricade.get("start"), 0.0)
            b = shot.cue(barricade.get("end"), shot.dur * 0.7)
            bp = clamp((t - a) / max(b - a, 0.01))
            if barricade.get("remove"):
                bp = 1 - bp
        else:
            bp = 1.0
    if o.get("window", True):
        props.window(ctx, 400, 470, 300, 330, t, moon=True, city_lights=float(o.get("city_lights", 0)))
    minutes = shot.minutes_at(t)
    props.wall_clock(ctx, 170, 630, 48, minutes // 60, minutes % 60, dark=dark > 0.5)
    if o.get("picture", True):
        ctx.rectangle(745, 540, 70, 90)
        set_color(ctx, "#e7e1d2")
        ctx.fill()
        ctx.rectangle(755, 552, 50, 66)
        set_color(ctx, "#3e6b8a")
        ctx.fill()
        set_color(ctx, "#d9822b")
        ctx.arc(780, 590, 14, 0, 2 * math.pi)
        ctx.fill()
    props.door(ctx, 840, 760, 200, 445, open_amount=float(o.get("door_open", 0)))
    props.floor_lamp(ctx, 770, 860, FLOOR_Y, on=1.0 if o.get("lamp") else 0.0)
    # barricade: the couch slides to the door and the shelf tips against it
    cx = 330 + (690 - 330) * bp
    props.couch(ctx, cx, 1015 + 20 * bp, 380, 190)
    ctx.save()
    ctx.translate(300 + (1000 - 300) * bp, FLOOR_Y)
    ctx.rotate(-0.32 * ease_in_out(bp))
    props.bookshelf(ctx, -260, -505, 260, 505)
    ctx.restore()
    for box in o.get("boxes", []) or []:
        bx, bw = float(box[0]) * W, float(box[1]) * W
        ctx.rectangle(bx, FLOOR_Y + 30 - bw * 0.7, bw, bw * 0.7)
        set_color(ctx, "#a07444")
        ctx.fill()
    ground = float(o.get("ground", 1430))
    crs = draw_creatures(cv, shot, t, o.get("creatures"), ground, dark > 0)
    j, beam = hero(cv, shot, t, o.get("you"), ground)
    if dark > 0:
        _apply_dark(cv, shot, t, dark, beam, j, extra=[("radial", 550, 640, 520, 0.45), ("radial", 540, 1000, 900, 0.25)] if o.get("window", True) else [])
        for cj, sc, fc, a in crs:
            creature_eyes(ctx, cj, sc, fc, a)
    if o.get("lamp"):
        glow(ctx, 770, 900, 300, "#ffd89a", 0.12)


def _apply_dark(cv, shot, t, dark, beam, hero_joints=None, extra=(), beam_len=950, spread=0.3):
    ctx = cv.ctx
    d = cv.dark
    d.begin(ctx.get_matrix(), dark)
    s = light_strength(shot, t)
    if beam and s > 0:
        d.cone(beam[0], beam[1], beam[2], beam_len, spread, s)
    if hero_joints is not None:
        d.radial(hero_joints.hip[0], hero_joints.hip[1] - 60, 400, 0.45 + 0.25 * s)
    for kind, *args in extra:
        if kind == "radial":
            d.radial(*args)
        elif kind == "cone":
            d.cone(*args)
    d.apply(ctx)
    if beam and s > 0:
        beam_tint(ctx, beam[0], beam[1], beam[2], beam_len, spread, 0.09 * s)


# ------------------------------------------------------------------ hallway

CX, CY, FOC = W / 2, 860, 520
Z0, ZF = 0.55, 9.0


def proj(x, y, z):
    return (CX + FOC * x / z, CY - FOC * y / z)


@scene("hallway")
def hallway(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    lights = o.get("lights", "on")
    wall, floor, carpet, ceil = o.get("wall", "#33554e"), "#2a2420", "#742424", "#222a28"
    zs = [Z0 * (ZF / Z0) ** (k / 16) for k in range(17)]
    for za, zb in zip(zs[:-1], zs[1:]):
        k = 1 / (1 + 0.17 * (za - Z0))
        fill(ctx, [proj(-1, -1, za), proj(1, -1, za), proj(1, -1, zb), proj(-1, -1, zb)], shade(floor, k))
        fill(ctx, [proj(-0.55, -1, za), proj(0.55, -1, za), proj(0.55, -1, zb), proj(-0.55, -1, zb)], shade(carpet, k))
        fill(ctx, [proj(-1, 1.25, za), proj(1, 1.25, za), proj(1, 1.25, zb), proj(-1, 1.25, zb)], shade(ceil, k))
        for sx in (-1, 1):
            fill(ctx, [proj(sx, -1, za), proj(sx, 1.25, za), proj(sx, 1.25, zb), proj(sx, -1, zb)], shade(wall, k))
            fill(ctx, [proj(sx, -1, za), proj(sx, -0.25, za), proj(sx, -0.25, zb), proj(sx, -1, zb)], shade(wall, k * 0.72))
    # carpet borders
    for x in (-0.5, 0.5):
        a, b = proj(x, -1, Z0), proj(x, -1, ZF)
        stroke_line(ctx, [a, b], 3, "#c9a24a", 0.35)
    # end wall + exit sign
    tl, br = proj(-1, 1.25, ZF), proj(1, -1, ZF)
    ctx.rectangle(tl[0], tl[1], br[0] - tl[0], br[1] - tl[1])
    ctx.set_source_rgba(*shade(wall, 0.35), 1)
    ctx.fill()
    ex, ey = proj(0, 0.85, ZF)
    glow(ctx, ex, ey, 60, "#ff2a1a", 0.6)
    ctx.rectangle(ex - 16, ey - 7, 32, 14)
    set_color(ctx, "#ff4a3a")
    ctx.fill()
    # doors
    open_doors = o.get("open_doors") or []
    for k, (sx, z) in enumerate([(-1, 1.5), (1, 2.3), (-1, 3.5), (1, 4.5), (-1, 5.7), (1, 6.9), (-1, 8.0)]):
        sh = 1 / (1 + 0.17 * (z - Z0))
        pts = [proj(sx, -1, z), proj(sx, 0.75, z), proj(sx, 0.75, z + 0.5), proj(sx, -1, z + 0.5)]
        fill(ctx, pts, shade("#2a1a10", sh))
        inner = [proj(sx, -1, z + 0.04), proj(sx, 0.7, z + 0.04), proj(sx, 0.7, z + 0.46), proj(sx, -1, z + 0.46)]
        if k in open_doors:
            fill(ctx, inner, (0.01, 0.01, 0.01))
            hinge = z + 0.04
            fill(ctx, [proj(sx, -1, hinge), proj(sx, 0.7, hinge), proj(sx * 0.6, 0.7, hinge - 0.05),
                       proj(sx * 0.6, -1, hinge - 0.05)], shade("#5a3520", sh * 1.1))
        else:
            fill(ctx, inner, shade("#5a3520", sh))
            kx, ky = proj(sx, -0.1, z + 0.4)
            set_color(ctx, "#d4ac0d", 0.8)
            ctx.arc(kx, ky, max(2, 12 * sh), 0, 2 * math.pi)
            ctx.fill()
    # drag marks on the carpet
    if o.get("marks"):
        mk = o["marks"]
        z_end = float(mk.get("to", 3.6)) if isinstance(mk, dict) else 3.6
        for k in range(28):
            z = Z0 + 0.4 + (z_end - Z0 - 0.4) * k / 27
            x = -0.05 + 0.04 * math.sin(k * 1.7)
            px, py = proj(x, -1, z)
            ctx.save()
            ctx.translate(px, py)
            ctx.scale(1, 0.35)
            set_color(ctx, "#3a0d0d", 0.75)
            ctx.arc(0, 0, 70 / z, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()
    # ceiling lights
    light_pts = []
    for k, z in enumerate((1.3, 2.9, 4.5, 6.1, 7.7)):
        if lights == "on":
            b = 1.0
        elif lights == "flicker":
            b = flicker(t, k, 9)
        else:
            b = 0.0
        if lights == "dying":
            b = 1.0 if t < shot.cue(o.get("off"), 0.8) - k * 0.15 else 0.0
        fx, fy = proj(0, 1.25, z)
        ctx.rectangle(fx - 70 / z, fy - 6 / z, 140 / z, 14 / z)
        set_color(ctx, "#fff4d8" if b > 0.5 else "#444444")
        ctx.fill()
        if b > 0:
            glow(ctx, fx, fy + 10, 320 / z, "#fff1cf", 0.55 * b)
            px, py = proj(0, -1, z)
            ctx.save()
            ctx.translate(px, py)
            ctx.scale(1, 0.32)
            glow(ctx, 0, 0, 700 / z, "#ffe7b0", 0.22 * b)
            ctx.restore()
            light_pts.append((fx, fy + 30, 520 / z, b))
    # rolling flashlight
    beam = None
    roll = o.get("rolling")
    if roll:
        r0, r1 = float(roll.get("from", 1.3)), float(roll.get("to", 4.2))
        p = ease_out(t / max(shot.dur * 0.9, 0.1))
        z = r0 + (r1 - r0) * p
        x = 0.12 * math.sin(p * 4)
        px, py = proj(x, -0.97, z)
        spin = (1 - p) * 9 * t + p * 3 + float(roll.get("angle", 0))
        s = 2.2 / z
        props.torch_icon(ctx, px, py, 90 * s)
        beam = (px, py, -0.15 + 0.6 * math.sin(spin))
    figures = []
    for k, f in enumerate(o.get("figures") or []):
        if t < shot.cue(f.get("cue"), 0.0):
            continue
        z = float(f.get("z", 4.0))
        if f.get("to_z") is not None:
            p = clamp((t - shot.cue(f.get("cue"), 0.0)) / max(shot.dur * 0.9, 0.1))
            z = z + (float(f["to_z"]) - z) * p
        fx, gy = proj(float(f.get("x", 0)), -1, z)
        sc = 3.0 / z
        who = f.get("who", "creature")
        pose = F.pose_for(f.get("action", "lurk" if who == "creature" else "idle"), t + k, seed=k,
                          speed=float(f.get("speed", 0.6)))
        facing = int(f.get("facing", -1))
        if who == "creature":
            j = F.draw_creature(ctx, pose, fx, gy, sc, facing, eye_alpha=0 if lights != "on" else 1)
            figures.append((j, sc, facing))
        else:
            F.draw_stickman(ctx, pose, fx, gy, sc, facing)
    if lights != "on":
        d = cv.dark
        d.begin(ctx.get_matrix(), float(o.get("dark", 0.8)))
        d.radial(CX, CY + 200, 900, 0.3)
        if beam:
            d.cone(beam[0], beam[1], beam[2], 520, 0.32, 1.0)
            d.radial(beam[0], beam[1], 90, 0.8)
        for lx, ly, lr, b in light_pts:
            d.radial(lx, ly + lr * 0.6, lr * 1.3, b * 0.9, 1.0, 1.0)
        d.radial(ex, ey, 140, 0.5)
        d.apply(ctx)
        if beam:
            beam_tint(ctx, beam[0], beam[1], beam[2], 520, 0.32, 0.12)
        glow(ctx, ex, ey, 70, "#ff2a1a", 0.45)
        for j, sc, facing in figures:
            creature_eyes(ctx, j, sc, facing)


# ------------------------------------------------------------------ peephole

@scene("peephole")
def peephole(cv, shot, t):
    ctx = cv.ctx
    cx, cy, r = W / 2, 840, 470
    ctx.save()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.clip()
    ctx.translate(cx, cy)
    ctx.scale(1.3, 1.3)
    ctx.translate(-cx, -cy - 20)
    hallway(cv, shot.sub({**shot.spec, **(shot.get("view") or {}), "scene": "hallway"}), t)
    ctx.restore()
    g = cairo.RadialGradient(cx, cy, r * 0.55, cx, cy, r)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(0.75, 0, 0, 0, 0.45)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.95)
    ctx.set_source(g)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.rectangle(-400, -400, W + 800, H + 800)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    set_color(ctx, "#020202")
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    ctx.set_line_width(6)
    set_color(ctx, "#ffffff", 0.06)
    ctx.arc(cx, cy, r - 3, 0, 2 * math.pi)
    ctx.stroke()


# ------------------------------------------------------------------ inventory board

@scene("inventory")
def inventory(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    vgradient(ctx, -300, -300, W + 600, H + 600, "#24170f", "#140c08")
    for k in range(-4, 16):
        ctx.rectangle(k * 90, -300, 3, H + 600)
    ctx.set_source_rgba(0, 0, 0, 0.25)
    ctx.fill()
    x, y, w, h = 70, 390, 940, 760
    glow(ctx, W / 2, y + h / 2, 700, "#ff6b3d", 0.08)
    rounded_rect(ctx, x, y, w, h, 26)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *rgb("#80301f"))
    g.add_color_stop_rgb(1, *rgb("#5a1d13"))
    ctx.set_source(g)
    ctx.fill()
    rounded_rect(ctx, x + 22, y + 22, w - 44, h - 44, 16)
    set_color(ctx, "#c2614a", 0.55)
    ctx.set_line_width(3)
    ctx.stroke()
    items = o.get("items") or []
    size, step, per_max = 78, 96, 8
    need = sum(math.ceil(int(i.get("count", 1)) / per_max) * step + 112 for i in items)
    room_for = h - (200 if o.get("total") else 70)
    fit = min(1.0, room_for / max(need, 1))
    size, step = size * fit, step * fit
    cy = y + 30 + step / 2
    for item in items:
        n = int(item.get("count", 1))
        at = shot.cue(item.get("cue"), 0.3)
        per_row = min(per_max, n)
        rows = math.ceil(n / per_row)
        row_w = per_row * step
        shown = 0
        for k in range(n):
            k_t = t - at - k * ICON_STAGGER
            if k_t < 0:
                continue
            shown += 1
            r, c = divmod(k, per_row)
            ix = W / 2 - row_w / 2 + step / 2 + c * step
            iy = cy + r * step
            sc = back_out(k_t / 0.2)
            ctx.save()
            ctx.translate(ix, iy)
            ctx.scale(sc, sc)
            props.icon(ctx, item.get("icon", "battery"), 0, 0, size, 1.0, t)
            ctx.restore()
        ly = cy + (rows - 1) * step + step * 0.66
        if shown:
            label = f"{str(item.get('label', '')).upper()} ×{shown}"
            pill(ctx, W / 2, ly, label, "mono", 28, "#f3efe6", "#1a0b07", 0.85, border="#c2614a",
                 pad_x=18, pad_y=8, tracking=2)
        cy = ly + 112 * fit - 50 * fit + step / 2
    total = o.get("total")
    if total:
        k = t - shot.cue(total.get("cue"), shot.dur * 0.8)
        if k >= 0:
            s = text(str(total.get("text", "")).upper(), "title", 110, "#ffd34d", shadow=4,
                     glow_color="#ff9d00", glow_radius=6)
            draw_surface(ctx, s, W / 2, y + h - 90, back_out(k / 0.3), clamp(k / 0.1))


# ------------------------------------------------------------------ radio

@scene("radio")
def radio(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    vgradient(ctx, -300, -300, W + 600, H + 600, "#1d150f", "#0c0907")
    for k, (bx, by, br, col) in enumerate([(160, 380, 160, "#ffb347"), (920, 300, 120, "#ff6b3d"),
                                           (820, 1500, 200, "#ffb347"), (120, 1300, 140, "#7a5c3d")]):
        glow(ctx, bx + 20 * math.sin(t * 0.3 + k), by, br, col, 0.12)
    ctx.rectangle(-300, 1050, W + 600, H)
    set_color(ctx, "#2b1c12")
    ctx.fill()
    ctx.rectangle(-300, 1050, W + 600, 8)
    set_color(ctx, "#3d2a1b")
    ctx.fill()
    on_t = shot.cue(o.get("on"), 0.7)
    on = clamp((t - on_t) / 0.4)
    talking = any(a <= shot.start + t <= b for a, b, s in shot.voice_spans if s == "radio")
    level = (0.35 + 0.55 * abs(noise(t * 6, 2))) if talking else 0.12 * on
    props.radio(ctx, W / 2, 800, 640, t, on, clamp((t - on_t + 0.5) / 0.5), level)
    # the hand reaching for the knob
    knob = (W / 2 + 640 * 0.04 + 640 * 0.34 * 0.72 - 6, 800 - 640 * 0.31 + 640 * 0.62 * 0.66)
    reach = ease_out(t / 0.5) * (1 - ease_in_out((t - on_t - 0.4) / 0.5))
    if reach > 0.01:
        start = (W + 160, 1650)
        hand = (start[0] + (knob[0] + 26 - start[0]) * reach, start[1] + (knob[1] + 30 - start[1]) * reach)
        stroke_line(ctx, [start, hand], 34, "#f2f2f2", 1.0, "#1b1b1b", 8)
        set_color(ctx, "#1b1b1b")
        ctx.arc(hand[0], hand[1], 25, 0, 2 * math.pi)
        ctx.fill()
        set_color(ctx, "#f2f2f2")
        ctx.arc(hand[0], hand[1], 21, 0, 2 * math.pi)
        ctx.fill()


# ------------------------------------------------------------------ map (blueprint)

@scene("map")
def city_map(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    vgradient(ctx, -300, -300, W + 600, H + 600, "#0b1d38", "#071225")
    ctx.set_line_width(1)
    for gx in range(-300, W + 300, 36):
        ctx.move_to(gx, -300)
        ctx.line_to(gx, H + 300)
    for gy in range(-300, H + 300, 36):
        ctx.move_to(-300, gy)
        ctx.line_to(W + 300, gy)
    set_color(ctx, "#6fa8ff", 0.07)
    ctx.stroke()
    ctx.set_line_width(2)
    for gx in range(-288, W + 300, 180):
        ctx.move_to(gx, -300)
        ctx.line_to(gx, H + 300)
    for gy in range(-264, H + 300, 180):
        ctx.move_to(-300, gy)
        ctx.line_to(W + 300, gy)
    set_color(ctx, "#6fa8ff", 0.12)
    ctx.stroke()
    mx, my, mw, mh = 110, 330, 860, 790
    cols, rows = 4, 5
    bw, bh = mw / cols, mh / rows
    for r in range(rows):
        for c in range(cols):
            rounded_rect(ctx, mx + c * bw + 18, my + r * bh + 18, bw - 36, bh - 36, 8)
            set_color(ctx, "#6fa8ff", 0.05)
            ctx.fill_preserve()
            set_color(ctx, "#6fa8ff", 0.45)
            ctx.set_line_width(2)
            ctx.stroke()

    def P(pt):
        return (mx + float(pt[0]) * mw, my + float(pt[1]) * mh)

    route = [P(p) for p in (o.get("route") or [[0.08, 0.95], [0.08, 0.5], [0.5, 0.5], [0.5, 0.05]])]
    # dead street lights along the route
    lamps = o.get("lamps")
    if lamps:
        dead_at = shot.cue(lamps.get("cue") if isinstance(lamps, dict) else None, shot.dur * 0.5)
        pts = []
        for a, b in zip(route[:-1], route[1:]):
            n = max(int(math.dist(a, b) / 90), 1)
            pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
        for k, (lx, ly) in enumerate(pts[1:], 1):
            off = t > dead_at + k * 0.05
            col = "#3a3f4a" if off else "#ffd34d"
            if not off:
                glow(ctx, lx + 22, ly, 28, "#ffd34d", 0.4)
            set_color(ctx, col)
            ctx.arc(lx + 22, ly, 7, 0, 2 * math.pi)
            ctx.fill()
    # danger zones
    for k, z in enumerate(o.get("danger") or []):
        at = shot.cue(z.get("cue"), 0.0)
        if t < at:
            continue
        a = clamp((t - at) / 0.4)
        zx, zy = P((z.get("x", 0.5), z.get("y", 0.5)))
        zr = float(z.get("r", 0.12)) * mw
        glow(ctx, zx, zy, zr * 1.3, RED, 0.2 * a)
        for d in range(int(z.get("n", 18))):
            ang = d * 2.39996 + k
            rr = zr * math.sqrt((d + 0.5) / int(z.get("n", 18)))
            px = zx + math.cos(ang) * rr + 4 * math.sin(t * 3 + d)
            py = zy + math.sin(ang) * rr + 4 * math.cos(t * 2.6 + d)
            set_color(ctx, "#ff4b3e", a * 0.9)
            ctx.arc(px, py, 6, 0, 2 * math.pi)
            ctx.fill()
    # route, drawn progressively
    r0 = shot.cue(o.get("route_cue"), 0.3)
    r1 = shot.cue(o.get("route_end"), shot.dur * 0.7)
    p = ease_in_out((t - r0) / max(r1 - r0, 0.1))
    total_len = sum(math.dist(a, b) for a, b in zip(route[:-1], route[1:]))
    left = total_len * p
    ctx.set_dash([18, 12], -t * 40)
    ctx.set_line_width(7)
    set_color(ctx, "#ffd34d")
    ctx.move_to(*route[0])
    for a, b in zip(route[:-1], route[1:]):
        seg = math.dist(a, b)
        if left <= 0:
            break
        f = min(left / seg, 1.0)
        ctx.line_to(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        left -= seg
    ctx.stroke()
    ctx.set_dash([])
    for xm in o.get("x_marks") or []:
        at = shot.cue(xm.get("cue"), 0.0)
        if t >= at:
            px, py = P((xm["x"], xm["y"]))
            s = 26 * back_out((t - at) / 0.25)
            stroke_line(ctx, [(px - s, py - s), (px + s, py + s)], 9, "#ff3b30")
            stroke_line(ctx, [(px + s, py - s), (px - s, py + s)], 9, "#ff3b30")
    # you
    yx, yy = route[0]
    pulse = 1 + 0.25 * math.sin(t * 5)
    glow(ctx, yx, yy, 50 * pulse, "#ffd34d", 0.45)
    set_color(ctx, "#ffd34d")
    ctx.arc(yx, yy, 13, 0, 2 * math.pi)
    ctx.fill()
    pill(ctx, yx + 85, yy, "YOU", "caption", 22, "#1a1400", "#ffd34d", 0.95, pad_x=14, pad_y=6)
    # target
    tg = o.get("target")
    if tg:
        at = shot.cue(tg.get("cue"), 0.0)
        if t >= at:
            k = back_out((t - at) / 0.3)
            tx, ty = route[-1]
            glow(ctx, tx, ty, 120, "#5fe8cf", 0.35)
            ctx.save()
            ctx.translate(tx, ty)
            ctx.scale(k, k * 0.62)
            ctx.set_line_width(10)
            set_color(ctx, TEAL)
            ctx.arc(0, 0, 70, 0, 2 * math.pi)
            ctx.stroke()
            ctx.arc(0, 0, 38, 0, 2 * math.pi)
            ctx.stroke()
            ctx.restore()
            for sx in (-1, 1):  # floodlight towers
                stroke_line(ctx, [(tx + sx * 80, ty), (tx + sx * 80, ty - 90 * k)], 5, TEAL)
                glow(ctx, tx + sx * 80, ty - 90 * k, 40, "#ffffff", 0.6)
            pill(ctx, tx, ty + 85, str(tg.get("label", "")).upper(), "caption", 22, "#062019", TEAL, 0.95,
                 scale=k, pad_x=14, pad_y=6)
    br = o.get("bracket")
    if br:
        at = shot.cue(br.get("cue"), 0.0)
        if t >= at:
            a = clamp((t - at) / 0.3)
            x = mx - 50
            y0, y1 = route[-1][1], route[0][1]
            set_color(ctx, "#cfe3ff", a)
            ctx.set_line_width(3)
            ctx.move_to(x + 16, y0)
            ctx.line_to(x, y0)
            ctx.line_to(x, y1)
            ctx.line_to(x + 16, y1)
            ctx.stroke()
            ctx.save()
            ctx.translate(x - 26, (y0 + y1) / 2)
            ctx.rotate(-math.pi / 2)
            draw_surface(ctx, text(str(br.get("label", "")).upper(), "mono", 26, "#cfe3ff", tracking=3), 0, 0, alpha=a)
            ctx.restore()


# ------------------------------------------------------------------ street (side-scrolling)

def _buildings(ctx, offset, base, color, seed, min_h, max_h, windows=None):
    k0 = int(math.floor((offset - 400) / 260))
    for k in range(k0, k0 + 9):
        h = min_h + (max_h - min_h) * (((k * 73 + seed * 31) % 11) / 10)
        w = 220 + 60 * (((k * 37 + seed) % 5) / 4)
        x = k * 260 - offset
        ctx.rectangle(x, base - h, w, h)
        set_color(ctx, color)
        ctx.fill()
        if windows:
            for r in range(int(h // 90)):
                for c in range(3):
                    wx = x + 30 + c * (w - 60) / 3
                    wy = base - h + 40 + r * 90
                    ctx.rectangle(wx, wy, 34, 46)
                    lit = windows if ((k * 5 + r * 3 + c) % 4 == 0) else 0
                    set_color(ctx, "#ffd36a" if lit else "#0a0c11", 0.9 if lit else 1)
                    ctx.fill()


@scene("street")
def street(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    pace = o.get("pace", "walk")
    speed = float(o.get("speed", 160 if pace == "walk" else 430))
    if o.get("stop"):
        st = shot.cue(o.get("stop"))
        scroll = speed * min(t, st) + speed * 0.4 * ease_out((t - st) / 0.4) * (t > st)
        moving = t < st
    else:
        scroll = speed * t
        moving = True
    scroll += float(o.get("offset", 0))
    base = 1340
    vgradient(ctx, -300, -300, W + 600, base + 300, "#03050a", "#101624")
    glow(ctx, 830, 380, 260, "#cfdcff", 0.12)
    set_color(ctx, "#dfe6f5")
    ctx.arc(830, 380, 34, 0, 2 * math.pi)
    ctx.fill()
    _buildings(ctx, scroll * 0.15, base - 120, "#111725", 1, 380, 820)
    _buildings(ctx, scroll * 0.45, base, "#1b2131", 2, 300, 620, windows=float(o.get("windows", 0)))
    # big counters (block numbers) passing by
    for c in o.get("counter") or []:
        tc = shot.cue(c.get("cue"), 0.0)
        wx = speed * tc + W * 0.6 - scroll + float(o.get("offset", 0)) * 0
        if -400 < wx < W + 400:
            draw_surface(ctx, text(str(c.get("text", "")), "title", 330, "#e9e4da"), wx, 860, alpha=0.16)
            draw_surface(ctx, text(str(c.get("label", "")).upper(), "mono", 26, "#e9e4da", tracking=4), wx, 1010, alpha=0.3)
    # lamp posts (dead)
    k0 = int(math.floor(scroll / 560)) - 1
    for k in range(k0, k0 + 4):
        lx = k * 560 + 200 - scroll
        stroke_line(ctx, [(lx, base + 10), (lx, 780), (lx + 70, 760)], 12, "#2c3038")
        ctx.rectangle(lx + 50, 752, 60, 20)
        set_color(ctx, "#3a3f4a")
        ctx.fill()
    ctx.rectangle(-300, base, W + 600, 40)
    set_color(ctx, "#262a31")
    ctx.fill()
    ctx.rectangle(-300, base + 40, W + 600, H)
    set_color(ctx, "#121418")
    ctx.fill()
    ctx.set_line_width(10)
    set_color(ctx, "#3b3f46")
    k0 = int(math.floor(scroll * 1.15 / 260)) - 1
    for k in range(k0, k0 + 7):
        x = k * 260 - scroll * 1.15
        ctx.move_to(x, base + 300)
        ctx.line_to(x + 120, base + 300)
    ctx.stroke()
    hx = float(o.get("hero_x", 0.4)) * W
    dark = float(o.get("dark", 0.82))
    # lurkers stand in the dark ahead, and back off from the beam
    s_light = light_strength(shot, t)
    lurkers = []
    for k in range(int(o.get("lurkers", 0))):
        wx = 650 + k * 520 + 140 * math.sin(k * 2.1)
        sx = wx - scroll * (1.0 if moving else 1.0)
        dist = sx - hx
        back = 0.0
        if s_light > 0.5 and 0 < dist < 700:
            back = (700 - dist) * 0.5
        approach = 0.0
        if s_light < 0.3 and o.get("dies"):
            approach = min((t - shot.cue(o.get("dies"))) * 120, max(dist - 180, 0)) if dist > 0 else 0
        sx += back - approach
        if -200 < sx < W + 200:
            act = "creep" if approach > 0 else ("lurk" if back < 30 else "scared")
            pose = F.pose_for(act, t + k, seed=k, speed=0.5)
            j = F.draw_creature(ctx, pose, sx, base + 8, 1.05, -1, eye_alpha=0)
            lurkers.append((j, 1.05, -1))
    chasers = []
    ch = o.get("chasers")
    if ch:
        at = shot.cue(ch.get("cue"), 0.0) if isinstance(ch, dict) else 0.0
        n = int(ch.get("n", 3)) if isinstance(ch, dict) else int(ch)
        for k in range(n):
            if t < at:
                break
            gap = 260 + k * 190 - 60 * ease_out((t - at) / 3)
            sx = hx - gap - 30 * math.sin(t * 2 + k)
            pose = F.pose_for("reach" if k % 2 else "creep", t * 1.6 + k, seed=k, speed=1.4)
            j = F.draw_creature(ctx, pose, sx, base + 8 + 6 * k, 1.1, 1, eye_alpha=0)
            chasers.append((j, 1.1, 1))
    you = dict(o.get("you") or {})
    you.setdefault("x", hx / W)
    you.setdefault("light", True)
    if moving:
        you.setdefault("action", "run" if pace == "run" else "walk")
        you["speed"] = 1.0
    if pace == "run" and moving:
        you["light"] = False if not you.get("light_running") else True
    j, beam = hero(cv, shot, t, you, base + 6, 1.15)
    if pace == "run" and moving and you.get("light_running", True) is not False:
        hand = j.hand_f
        beam = (hand[0] + 30, hand[1], -0.05 + 0.1 * math.sin(t * 9))
    if dark > 0:
        _apply_dark(cv, shot, t, dark, beam, j, extra=[("radial", 830, 380, 700, 0.35), ("radial", W / 2, base - 300, 1100, 0.22)], beam_len=820, spread=0.27)
        for cj, sc, fc in lurkers + chasers:
            creature_eyes(ctx, cj, sc, fc)
    ey = o.get("eyes")
    if ey:
        at = shot.cue(ey.get("cue") if isinstance(ey, dict) else ey, 0.0)
        n = int(ey.get("n", 26)) if isinstance(ey, dict) else 26
        for k in range(n):
            delay = (k * 0.618) % 1 * 1.6
            a = clamp((t - at - delay) / 0.4)
            if a <= 0:
                continue
            ex = (k * 211 + 70) % (W + 100) - 50
            eyy = 420 + (k * 137) % 900
            blink = 0.0 if math.sin(t * 1.3 + k * 2.7) > 0.985 else 1.0
            eyes(ctx, ex + 6 * math.sin(t + k), eyy, 4 + (k % 3), a * blink)


# ------------------------------------------------------------------ close-ups

@scene("closeup")
def closeup(cv, shot, t):
    ctx = cv.ctx
    o = shot.spec
    obj = o.get("object", "flashlight")
    vgradient(ctx, -300, -300, W + 600, H + 600, "#100d0b", "#050404")
    if obj == "flashlight":
        s = light_strength(shot, t)
        y = 900
        stroke_line(ctx, [(-200, 1600), (300, 960)], 64, "#f2f2f2", 1, "#1b1b1b", 10)
        rounded_rect(ctx, 120, y - 62, 470, 124, 22)
        set_color(ctx, "#2b2f37")
        ctx.fill()
        for k in range(6):
            ctx.rectangle(170 + k * 50, y - 62, 18, 124)
        set_color(ctx, "#22252c")
        ctx.fill()
        rounded_rect(ctx, 560, y - 95, 150, 190, 26)
        set_color(ctx, "#4a505b")
        ctx.fill()
        ctx.rectangle(700, y - 78, 18, 156)
        set_color(ctx, "#fff6d6" if s > 0.3 else "#5c5a52")
        ctx.fill()
        set_color(ctx, "#1b1b1b")
        ctx.arc(300, 960, 44, 0, 2 * math.pi)
        ctx.fill()
        set_color(ctx, "#f2f2f2")
        ctx.arc(300, 960, 38, 0, 2 * math.pi)
        ctx.fill()
        cv.dark.begin(ctx.get_matrix(), float(o.get("dark", 0.9)))
        if s > 0:
            cv.dark.cone(712, y, 0.0, 1100, 0.3, s)
            cv.dark.radial(650, y, 300, 0.7 * s)
        cv.dark.radial(330, 1000, 420, 0.35)
        cv.dark.apply(ctx)
        if s > 0:
            beam_tint(ctx, 712, y, 0.0, 1100, 0.3, 0.14 * s)
            glow(ctx, 712, y, 90, "#fff6d6", 0.5 * s)
        for k in range(int(o.get("eyes", 0))):
            a = clamp((t - shot.cue(o.get("eyes_cue"), 0.0) - k * 0.25) / 0.4)
            eyes(ctx, 760 + (k * 97) % 280, 520 + (k * 173) % 760, 5, a * (1 - s))
    elif obj == "phone":
        props.phone(ctx, W / 2, 860, 640, t, lit=1.0)
        draw_surface(ctx, text(str(o.get("screen", "NO SIGNAL")).upper(), "bold", 40, "#f2f2f2"), W / 2, 820)
        draw_surface(ctx, text(str(o.get("sub", "")).upper(), "mono", 24, "#9fb6d6"), W / 2, 880)
    elif obj == "alarm":
        m = shot.minutes_at(t)
        props.alarm_clock(ctx, W / 2, 860, 260, m // 60, m % 60, t, clamp((t - shot.cue(o.get("ring"), 1e9)) * 3))


# ------------------------------------------------------------------ title / choice / end card backdrops

def _frozen(cv, alpha_dark, zoom=1.0, t=0.0):
    ctx = cv.ctx
    ctx.save()
    ctx.identity_matrix()
    ctx.translate(W / 2, H / 2)
    ctx.scale(zoom, zoom)
    ctx.translate(-W / 2, -H / 2)
    ctx.set_source_surface(cv.prev, 0, 0)
    ctx.paint()
    ctx.restore()
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_rgba(0, 0, 0, alpha_dark)
    ctx.paint()
    ctx.restore()


@scene("title")
def title(cv, shot, t):
    _frozen(cv, 0.78, 1.0 + 0.03 * t / max(shot.dur, 0.1))


def _base(cv, shot, t):
    base = shot.get("base")
    if base:
        extra = {k: shot.get(k) for k in ("flicker", "dies") if shot.get(k) is not None}
        paint(cv, shot.sub({**base, **extra}), t)
    else:
        _frozen(cv, 0.0)


@scene("choice")
def choice(cv, shot, t):
    _base(cv, shot, t)
    ctx = cv.ctx
    ctx.save()
    ctx.identity_matrix()
    g = cairo.LinearGradient(0, 0, 0, 900)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.75)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g)
    ctx.rectangle(0, 0, W, 900)
    ctx.fill()
    ctx.restore()


@scene("endcard")
def endcard(cv, shot, t):
    _base(cv, shot, t)
    ctx = cv.ctx
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_rgba(0, 0, 0, 0.6 * clamp(t / 0.4))
    ctx.paint()
    ctx.restore()
