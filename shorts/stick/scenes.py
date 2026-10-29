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
    if shot.get("fog"):
        fog(cv.ctx, shot, t, shot.get("fog"))
    if shot.get("snow"):
        snow(cv.ctx, t, shot.get("snow"))


def snow(ctx, t, spec):
    """Falling snow; `{n, speed, wind}` or just true."""
    spec = spec if isinstance(spec, dict) else {}
    n = int(spec.get("n", 140))
    speed = float(spec.get("speed", 140))
    wind = float(spec.get("wind", 60))
    for k in range(n):
        depth = 0.5 + (k * 0.618) % 1
        x = (k * 197.3 + wind * depth * t + 30 * math.sin(t * 0.8 + k)) % (W + 200) - 100
        y = (k * 131.7 + speed * depth * t) % (H + 200) - 100
        ctx.arc(x, y, 1.6 + 2.4 * depth, 0, 2 * math.pi)
        ctx.set_source_rgba(0.95, 0.97, 1.0, 0.35 + 0.4 * (depth - 0.5))
        ctx.fill()


def fog(ctx, shot, t, spec):
    """Rolling fog from the bottom of the frame up to `top` (share of the height).
    `rise: [from, to]` moves the fog line during the shot."""
    spec = spec if isinstance(spec, dict) else {}
    top = float(spec.get("top", 0.6))
    if spec.get("rise"):
        a, b = spec["rise"]
        start = shot.cue(spec.get("cue"), 0.0)
        top = a + (b - a) * ease_in_out((t - start) / max(shot.dur - start, 0.1))
    dens = float(spec.get("density", 0.7))
    col = rgb(spec.get("color", "#9aa6b2"))
    y0 = top * H
    for k in range(4):
        y = y0 + k * 70 + 18 * math.sin(t * 0.5 + k * 1.7)
        g = cairo.LinearGradient(0, y - 160, 0, y + 140)
        g.add_color_stop_rgba(0, *col, 0)
        g.add_color_stop_rgba(1, *col, 0.22 * dens)
        ctx.set_source(g)
        ctx.rectangle(-400, y - 160, W + 800, H + 400 - y)
        ctx.fill()
    for k in range(9):  # drifting puffs along the fog line
        x = ((k * 263 + t * (30 + 12 * (k % 3))) % (W + 700)) - 350
        y = y0 + 40 + (k % 3) * 70
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(1, 0.4)
        r = 320 + 60 * (k % 4)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
        g.add_color_stop_rgba(0, *col, 0.28 * dens)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()


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
    f, d, r = shot.get("flicker"), shot.get("dies"), shot.get("relight")
    if r is not None and t >= shot.cue(r, 1e9):
        return 1.0
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
    if spec.get("cap") or (cv.item.get("cap") and spec.get("cap") is not False):
        draw_cap(cv.ctx, j.head, scale, facing)
    beam = None
    if has_light:
        tip = F.flashlight_tip(j, scale)
        beam = (tip[0], tip[1], j.hand_angle)
    return j, beam


def draw_cap(ctx, head, scale, facing, alpha=1.0):
    """A security guard's cap."""
    ctx.save()
    ctx.translate(head[0], head[1] - 20 * scale)
    ctx.move_to(-28 * scale, 6 * scale)
    ctx.curve_to(-26 * scale, -22 * scale, 26 * scale, -22 * scale, 28 * scale, 6 * scale)
    ctx.close_path()
    set_color(ctx, "#1f2a44", alpha)
    ctx.fill()
    ctx.rectangle(-28 * scale if facing < 0 else 0, 2 * scale, 50 * scale, 7 * scale)
    ctx.fill()
    set_color(ctx, "#d4ac0d", alpha)
    ctx.arc(0, -6 * scale, 5 * scale, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


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
    dark = float(_cue_list(shot, t, o.get("dark", 0)) or 0)  # or [[value, cue], ...]
    lamp = _cue_list(shot, t, o.get("lamp"))  # true/false/flicker, or [[state, cue], ...]
    lamp_on = flicker(t, 4, 10) if lamp == "flicker" else (1.0 if lamp else 0.0)
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
    if o.get("monitors"):  # a security office: a wall of camera screens
        ctx.rectangle(380, 450, 340, 360)
        set_color(ctx, "#1a1a1d")
        ctx.fill()
        for r in range(2):
            for c in range(2):
                mx_, my_ = 395 + c * 165, 465 + r * 170
                ctx.rectangle(mx_, my_, 150, 155)
                on = o.get("monitors") != "off"
                lit = 0.75 + 0.25 * flicker(t, r * 2 + c, 6) if on else 0.1
                ctx.set_source_rgba(0.16 * lit, 0.26 * lit, 0.28 * lit, 1)
                ctx.fill()
                if on:  # each screen shows a little corridor
                    cxm, cym = mx_ + 75, my_ + 70
                    ctx.set_line_width(2)
                    ctx.set_source_rgba(0.6, 0.85, 0.85, 0.55 * lit)
                    for ex, ey in ((mx_, my_ + 155), (mx_ + 150, my_ + 155), (mx_, my_ + 10), (mx_ + 150, my_ + 10)):
                        ctx.move_to(cxm + (ex - cxm) * 0.15, cym + (ey - cym) * 0.15)
                        ctx.line_to(ex, ey)
                    ctx.rectangle(cxm - 11, cym - 9, 22, 18)
                    ctx.stroke()
                    draw_surface(ctx, text(f"CAM 0{r * 2 + c + 1}", "mono", 14, "#cfe9e6"), mx_ + 8, my_ + 14, anchor="l")
                for y in range(my_, my_ + 155, 6):
                    ctx.rectangle(mx_, y, 150, 2)
                ctx.set_source_rgba(0, 0, 0, 0.18)
                ctx.fill()
        glow(ctx, 550, 630, 420, "#7fb6c4", 0.18)
    elif o.get("window", True):
        props.window(ctx, 400, 470, 300, 330, t, moon=True, city_lights=float(o.get("city_lights", 0)),
                     forest=o.get("window_view") == "forest", cinema=o.get("window_view") == "cinema")
        ctx.save()  # lights out in the night beyond the glass: [{x, y, color, cue, n, drift}]
        ctx.rectangle(407, 477, 286, 316)
        ctx.clip()
        for k, wl in enumerate(o.get("window_lights") or []):
            at = shot.cue(wl.get("cue"), 0.0)
            if t < at:
                continue
            a = clamp((t - at) / 0.6)
            for m in range(int(wl.get("n", 1))):
                lx = 400 + 300 * float(wl.get("x", 0.5)) + m * 26 + float(wl.get("drift", 0)) * (t - at) + 3 * math.sin(t * 2 + m)
                ly = 470 + 330 * float(wl.get("y", 0.7)) + 6 * math.sin(t * 1.3 + m * 2)
                b = a * (0.7 + 0.3 * flicker(t, k * 5 + m, 6))
                glow(ctx, lx, ly, 30, wl.get("color", "#ff9a2a"), 0.6 * b)
                set_color(ctx, wl.get("color", "#ff9a2a"), b)
                ctx.arc(lx, ly, 4, 0, 2 * math.pi)
                ctx.fill()
        ctx.restore()
        wf = float(o.get("window_fog", 0))
        if wf > 0:
            for k in range(3):
                y = 470 + 330 * (0.35 + 0.18 * k) + 8 * math.sin(t * 0.6 + k)
                g = cairo.LinearGradient(0, y - 60, 0, y + 60)
                g.add_color_stop_rgba(0, 0.62, 0.66, 0.7, 0)
                g.add_color_stop_rgba(1, 0.62, 0.66, 0.7, 0.45 * wf)
                ctx.set_source(g)
                ctx.rectangle(407, y - 60, 286, 800 - y + 60 - 7)
                ctx.fill()
    furniture = o.get("furniture", True)
    minutes = shot.minutes_at(t)
    if furniture or o.get("clock"):
        props.wall_clock(ctx, 170, 630, 48, minutes // 60, minutes % 60, dark=dark > 0.5)
    if furniture and o.get("picture", True):
        ctx.rectangle(745, 540, 70, 90)
        set_color(ctx, "#e7e1d2")
        ctx.fill()
        ctx.rectangle(755, 552, 50, 66)
        set_color(ctx, "#3e6b8a")
        ctx.fill()
        set_color(ctx, "#d9822b")
        ctx.arc(780, 590, 14, 0, 2 * math.pi)
        ctx.fill()
    if o.get("door", True):
        props.door(ctx, 840, 760, 200, 445, open_amount=float(_cue_list(shot, t, o.get("door_open", 0)) or 0))
    air = _cue_list(shot, t, o.get("on_air"))  # a radio studio's ON AIR sign: on|off|flicker
    if air:
        b = {"on": 1.0, "flicker": flicker(t, 3, 8), True: 1.0}.get(air, 0.0)
        rounded_rect(ctx, 850, 690, 180, 50, 10)
        set_color(ctx, mix("#3a1414", "#ff2d2d", b))
        ctx.fill()
        if b > 0.5:
            glow(ctx, 940, 715, 160, "#ff2d2d", 0.35 * b)
        draw_surface(ctx, text("ON AIR", "title", 40, "#ffe9e9" if b > 0.5 else "#7a4a4a", tracking=3), 940, 716)
    if furniture:
        props.floor_lamp(ctx, 770, 860, FLOOR_Y, on=lamp_on)
        # barricade: the couch slides to the door and the shelf tips against it
        cx = 330 + (690 - 330) * bp
        props.couch(ctx, cx, 1015 + 20 * bp, 380, 190)
        ctx.save()
        ctx.translate(300 + (1000 - 300) * bp, FLOOR_Y)
        ctx.rotate(-0.32 * ease_in_out(bp))
        props.bookshelf(ctx, -260, -505, 260, 505)
        ctx.restore()
    if o.get("desk"):  # a guard's desk with a mug and a radio
        ctx.rectangle(330, 1040, 420, 30)
        set_color(ctx, "#3b2b20")
        ctx.fill()
        for lx in (350, 715):
            ctx.rectangle(lx, 1070, 18, 150)
            ctx.fill()
        ctx.rectangle(400, 1000, 44, 40)
        set_color(ctx, "#d9d4c8")
        ctx.fill()
        props.radio(ctx, 620, 1000, 120, t, 0.6, 0, 0.2)
    # mannequins: pale figures that turn to face you when nobody is looking
    for k, mq in enumerate(o.get("mannequins") or []):
        mx_ = float(mq.get("x", 0.3)) * W
        facing = int(mq.get("facing", -1))
        if mq.get("turn") is not None and t >= shot.cue(mq.get("turn"), 1e9):
            facing = -facing
        mpose = F.Pose(lean=0.0, sh_f=0.25, el_f=0.35, sh_b=-0.15, el_b=0.3, hip_f=0.06, hip_b=-0.06,
                       head=0.25 if mq.get("turn") is not None and t >= shot.cue(mq.get("turn"), 1e9) else 0.0)
        gy = float(mq.get("ground", FLOOR_Y + 60))
        F.draw_shadow(ctx, mx_, gy, 1.1, 0.25)
        F.draw_stickman(ctx, mpose, mx_, gy, float(mq.get("scale", 1.1)), facing, color="#d8c7ad", outline="#6d5d47")
    stares = []
    for k, pp in enumerate(o.get("people") or []):  # other people: [{x, action, facing, color, cue, fade, stare, scale}]
        if t < shot.cue(pp.get("cue"), 0.0):
            continue
        a = 1.0 - clamp((t - shot.cue(pp.get("fade"), 1e9)) / 0.6)
        if a <= 0:
            continue
        sc = float(pp.get("scale", 1.2))
        pg = float(pp.get("ground", 1430))
        px = float(pp.get("x", 0.6)) * W
        if pp.get("to") is not None:
            pr = clamp((t - shot.cue(pp.get("go"), 0.0)) / max(shot.cue(pp.get("arrive"), shot.dur) - shot.cue(pp.get("go"), 0.0), 0.01))
            px += (float(pp["to"]) * W - px) * pr
        act = pp.get("action", "idle")
        if pp.get("action_at"):
            for cue, act2 in pp["action_at"].items():
                if t >= shot.cue(cue, 1e9):
                    act = act2
        F.draw_shadow(ctx, px, pg, sc, 0.3 * a)
        pj = F.draw_stickman(ctx, F.pose_for(act, t + k * 0.9, seed=k), px, pg, sc, int(pp.get("facing", -1)),
                             color=pp.get("color", "#e6d3b3"), alpha=a)
        if pp.get("stare"):
            stares.append((pj, sc, int(pp.get("facing", -1))))
    for box in o.get("boxes", []) or []:
        bx, bw = float(box[0]) * W, float(box[1]) * W
        ctx.rectangle(bx, FLOOR_Y + 30 - bw * 0.7, bw, bw * 0.7)
        set_color(ctx, "#a07444")
        ctx.fill()
    ground = float(o.get("ground", 1430))
    crs = draw_creatures(cv, shot, t, o.get("creatures"), ground, dark > 0)
    j, beam = hero(cv, shot, t, o.get("you"), ground)
    if dark > 0:
        lit = o.get("window", True) or o.get("monitors")
        extra = [("radial", 550, 640, 520, 0.45), ("radial", 540, 1000, 900, 0.25)] if lit else []
        if lamp_on > 0 and furniture:
            extra.append(("radial", 770, 900, 520, 0.7 * lamp_on))
        _apply_dark(cv, shot, t, dark, beam, j, extra=extra)
        for cj, sc, fc, a in crs:
            creature_eyes(ctx, cj, sc, fc, a)
    if lamp_on > 0:
        glow(ctx, 770, 900, 300, "#ffd89a", 0.12 * lamp_on)
    for sj, sc, fc in stares:
        eyes(ctx, sj.head[0] + 4 * sc * fc, sj.head[1] - 2 * sc, 3.2 * sc, 0.9, gap=11 * sc)


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
    wall, floor = o.get("wall", "#33554e"), o.get("floor", "#2a2420")
    carpet, ceil = o.get("carpet", "#742424"), o.get("ceiling", "#222a28")
    exit_col = o.get("exit_color", "#ff2a1a")
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
    glow(ctx, ex, ey, 60, exit_col, 0.6)
    ctx.rectangle(ex - 16, ey - 7, 32, 14)
    set_color(ctx, exit_col)
    ctx.fill()
    # doors
    open_doors = o.get("open_doors") or []
    for k, (sx, z) in enumerate([(-1, 1.5), (1, 2.3), (-1, 3.5), (1, 4.5), (-1, 5.7), (1, 6.9), (-1, 8.0)]):
        sh = 1 / (1 + 0.17 * (z - Z0))
        pts = [proj(sx, -1, z), proj(sx, 0.75, z), proj(sx, 0.75, z + 0.5), proj(sx, -1, z + 0.5)]
        fill(ctx, pts, shade("#2a1a10", sh))
        inner = [proj(sx, -1, z + 0.04), proj(sx, 0.7, z + 0.04), proj(sx, 0.7, z + 0.46), proj(sx, -1, z + 0.46)]
        if o.get("shelves"):  # a library: tall bookcases instead of doors
            case = [proj(sx, -1, z - 0.3), proj(sx, 0.95, z - 0.3), proj(sx, 0.95, z + 0.8), proj(sx, -1, z + 0.8)]
            fill(ctx, case, shade("#3a2414", sh))
            spines = ["#8e3b2f", "#2f5d7a", "#6b7a3a", "#a07a2c", "#5a3a6b", "#7a2f3f"]
            for row in range(5):
                y0, y1 = -0.95 + row * 0.38, -0.95 + row * 0.38 + 0.3
                for b in range(7):
                    za, zb = z - 0.27 + b * 0.15, z - 0.27 + b * 0.15 + 0.11
                    top = y1 - 0.06 * ((b * 3 + row) % 3)
                    fill(ctx, [proj(sx, y0, za), proj(sx, top, za), proj(sx, top, zb), proj(sx, y0, zb)],
                         shade(spines[(b + row * 2 + k) % len(spines)], sh * 0.9))
                fill(ctx, [proj(sx, y0 - 0.04, z - 0.3), proj(sx, y0, z - 0.3), proj(sx, y0, z + 0.8),
                           proj(sx, y0 - 0.04, z + 0.8)], shade("#22150c", sh))
            continue
        if o.get("shops"):  # a mall: wide dark shop windows with a sign strip above
            shop = [proj(sx, -1, z - 0.25), proj(sx, 0.55, z - 0.25), proj(sx, 0.55, z + 0.75), proj(sx, -1, z + 0.75)]
            fill(ctx, shop, shade("#1b2a33", sh))
            gl = [proj(sx, -0.9, z - 0.2), proj(sx, 0.45, z - 0.2), proj(sx, 0.45, z + 0.7), proj(sx, -0.9, z + 0.7)]
            fill(ctx, gl, shade("#2c4552", sh * 0.9), 0.85)
            sign_cols = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#d35400", "#16a085", "#7f8c8d"]
            signs = o.get("signs_lit", True)
            sg = [proj(sx, 0.62, z - 0.2), proj(sx, 0.85, z - 0.2), proj(sx, 0.85, z + 0.7), proj(sx, 0.62, z + 0.7)]
            fill(ctx, sg, shade(sign_cols[k % len(sign_cols)], sh * (1.0 if signs else 0.35)))
            continue
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
    figures, stares = [], []
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
        elif who == "mannequin":
            mp = F.Pose(sh_f=0.25, el_f=0.35, sh_b=-0.15, el_b=0.3, hip_f=0.06, hip_b=-0.06)
            F.draw_stickman(ctx, mp, fx, gy, sc, facing, color="#d8c7ad", outline="#6d5d47")
        else:
            col = f.get("color", "#f2f2f2")
            pj = F.draw_stickman(ctx, pose, fx, gy, sc, facing, color=col)
            if f.get("cap"):
                draw_cap(ctx, pj.head, sc, facing)
            if f.get("stare"):
                stares.append((pj, sc, facing))
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
        glow(ctx, ex, ey, 70, exit_col, 0.45)
        for j, sc, facing in figures:
            creature_eyes(ctx, j, sc, facing)
    for j, sc, facing in stares:  # a person whose eyes shine like theirs
        eyes(ctx, j.head[0] + 4 * sc * facing, j.head[1] - 2 * sc, 3.2 * sc, 0.9, gap=11 * sc)


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
        zc = z.get("color", RED)  # e.g. orange for a fire, blue for strange lights
        glow(ctx, zx, zy, zr * 1.3, zc, 0.2 * a)
        for d in range(int(z.get("n", 18))):
            ang = d * 2.39996 + k
            rr = zr * math.sqrt((d + 0.5) / int(z.get("n", 18)))
            px = zx + math.cos(ang) * rr + 4 * math.sin(t * 3 + d)
            py = zy + math.sin(ang) * rr + 4 * math.cos(t * 2.6 + d)
            set_color(ctx, z.get("color", "#ff4b3e"), a * 0.9)
            ctx.arc(px, py, 6, 0, 2 * math.pi)
            ctx.fill()
    fz = o.get("fog_zone")
    if fz:  # fog covering the map from the bottom (harbour side) up
        a0, a1 = fz.get("level", [0.3, 0.6]) if isinstance(fz.get("level"), list) else (fz.get("level", 0.4),) * 2
        at = shot.cue(fz.get("cue"), 0.0)
        lv = a0 + (a1 - a0) * ease_in_out((t - at) / max(shot.dur - at, 0.1))
        fy = my + mh * (1 - lv)
        g = cairo.LinearGradient(0, fy - 60, 0, fy + 80)
        g.add_color_stop_rgba(0, 0.75, 0.8, 0.86, 0)
        g.add_color_stop_rgba(1, 0.75, 0.8, 0.86, 0.5)
        ctx.set_source(g)
        ctx.rectangle(mx - 40, fy - 60, mw + 80, my + mh + 40 - fy + 60)
        ctx.fill()
        stroke_line(ctx, [(mx - 40, fy), (mx + mw + 40, fy)], 3, "#dfe7f2", 0.6)
        pill(ctx, mx + mw - 90, fy - 30, str(fz.get("label", "FOG LINE")).upper(), "mono", 20, "#0b1d38", "#dfe7f2",
             0.9, pad_x=12, pad_y=5, tracking=2)
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
    for k, sp in enumerate(o.get("stops") or []):  # named stations along a train line
        at = shot.cue(sp.get("cue"), 0.0) + k * 0.06
        if t < at:
            continue
        a = clamp((t - at) / 0.25)
        px, py = P((sp["x"], sp["y"]))
        ghost = sp.get("ghost")
        col = "#ff3b30" if ghost else "#ffffff"
        if ghost:
            glow(ctx, px, py, 70, RED, 0.35 * a)
        set_color(ctx, "#0b1d38", a)
        ctx.arc(px, py, 17, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_line_width(6)
        set_color(ctx, col, a)
        ctx.arc(px, py, 14, 0, 2 * math.pi)
        ctx.stroke()
        side = -1 if sp.get("left") else 1
        draw_surface(ctx, text(str(sp.get("label", "")).upper(), "mono", 26, col, shadow=2, tracking=2),
                     px + side * 34, py, anchor="l" if side > 0 else "r", alpha=a)
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
        if t >= at and tg.get("icon") == "pin":
            set_color(ctx, TEAL)
            ctx.arc(tx, ty - 34 * k, 22 * k, 0, 2 * math.pi)
            ctx.fill()
            ctx.move_to(tx - 18 * k, ty - 26 * k)
            ctx.line_to(tx, ty)
            ctx.line_to(tx + 18 * k, ty - 26 * k)
            ctx.fill()
            pill(ctx, tx, ty + 50, str(tg.get("label", "")).upper(), "caption", 22, "#062019", TEAL, 0.95,
                 scale=k, pad_x=14, pad_y=6)
        elif t >= at:
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
    if o.get("dawn"):
        vgradient(ctx, -300, -300, W + 600, base + 300, "#2b3a5c", "#e9a26b")
        glow(ctx, 300, base - 80, 520, "#ffd28a", 0.55)
    else:
        vgradient(ctx, -300, -300, W + 600, base + 300, "#03050a", "#101624")
        glow(ctx, 830, 380, 260, "#cfdcff", 0.12)
        set_color(ctx, "#dfe6f5")
        ctx.arc(830, 380, 34, 0, 2 * math.pi)
        ctx.fill()
    roof = bool(o.get("rooftop"))
    sea = bool(o.get("sea"))
    if sea:  # open water to the horizon (a causeway, a pier)
        vgradient(ctx, -300, base - 420, W + 600, 420, "#0b1626", "#16304a")
        for k in range(26):  # moonlight glinting on the waves
            wy = base - 400 + (k * 37) % 390
            wx = 830 + 90 * math.sin(k * 2.3) - ((scroll * 0.2 + k * 40) % 60)
            ctx.rectangle(wx - 30 - k % 4 * 10, wy, 60 + k % 4 * 20, 3)
        ctx.set_source_rgba(0.8, 0.86, 1.0, 0.18)
        ctx.fill()
    elif roof:  # up on a roof: the town is below, only a few tops stick out
        _buildings(ctx, scroll * 0.1, base + 260, "#111725", 1, 300, 560)
    else:
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
    for k in range(k0, k0 + (0 if roof or sea else 4)):
        lx = k * 560 + 200 - scroll
        stroke_line(ctx, [(lx, base + 10), (lx, 780), (lx + 70, 760)], 12, "#2c3038")
        ctx.rectangle(lx + 50, 752, 60, 20)
        set_color(ctx, "#3a3f4a")
        ctx.fill()
    if roof:
        ctx.rectangle(110, base - 330, 210, 250)  # water tank
        set_color(ctx, "#1d2028")
        ctx.fill()
        for lx in (130, 300):
            stroke_line(ctx, [(lx, base - 80), (lx, base)], 10, "#1d2028")
        ctx.save()
        ctx.translate(215, base - 330)
        ctx.scale(1, 0.25)
        ctx.arc(0, 0, 105, math.pi, 2 * math.pi)
        ctx.restore()
        set_color(ctx, "#1d2028")
        ctx.fill()
        ctx.rectangle(-300, base, W + 600, H)
        set_color(ctx, "#25272d")
        ctx.fill()
        ctx.rectangle(W - 60, base - 60, 400, 60)  # the ledge
        set_color(ctx, "#33363d")
        ctx.fill()
    else:
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
    for k, p in enumerate(o.get("people") or []):  # other people out on the street
        at = shot.cue(p.get("cue"), 0.0)
        if t < at:
            continue
        a = 1.0 - clamp((t - shot.cue(p.get("fade"), 1e9)) / 0.9)
        if a <= 0:
            continue
        px = float(p.get("x", 0.75)) * W + float(p.get("drift", 0)) * (t - at)
        act = p.get("action", "walk" if moving else "idle")
        F.draw_stickman(ctx, F.pose_for(act, t + k * 0.4, speed=0.9), px, base + 6, 1.05,
                        int(p.get("facing", 1)), color="#d9d9d9", alpha=a)
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
    wants_light = you.get("light", True)
    you.setdefault("x", hx / W)
    you.setdefault("light", True)
    if moving:
        you.setdefault("action", "run" if pace == "run" else "walk")
        you["speed"] = 1.0
    if pace == "run" and moving:
        you["light"] = False if not you.get("light_running") else True
    j, beam = hero(cv, shot, t, you, base + 6, 1.15)
    if pace == "run" and moving and wants_light and you.get("light_running", True) is not False:
        hand = j.hand_f
        beam = (hand[0] + 30, hand[1], -0.05 + 0.1 * math.sin(t * 9))
    fl = o.get("floodlights")
    flood = 0.0
    if fl is not None:
        flood = ease_out((t - shot.cue(fl, 0.0)) / 1.2)
    extra = [("radial", 830, 380, 700, 0.35), ("radial", W / 2, base - 300, 1100, 0.22)]
    if flood > 0:
        extra.append(("radial", W + 120, base - 380, 1150, 0.95 * flood))
    if dark > 0:
        _apply_dark(cv, shot, t, dark, beam, j, extra=extra, beam_len=820, spread=0.27)
        for cj, sc, fc in lurkers + chasers:
            creature_eyes(ctx, cj, sc, fc)
    if flood > 0:
        for k in range(3):  # floodlight towers over the wall
            fx = W - 40 + k * 90
            stroke_line(ctx, [(fx, base - 120), (fx - 30, 420)], 8, "#3a3f4a", flood)
            glow(ctx, fx - 30, 420, 260, "#ffffff", 0.55 * flood)
            set_color(ctx, "#ffffff", flood)
            ctx.arc(fx - 30, 420, 16, 0, 2 * math.pi)
            ctx.fill()
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
            eyes(ctx, ex + 6 * math.sin(t + k), eyy, 4 + (k % 3), a * blink * (1 - 0.85 * s_light))


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
        ring = t >= shot.cue(o.get("ring"), 1e9)
        buzz = math.sin(t * 70) * 6 if ring and (t * 2) % 1 < 0.5 else 0
        ctx.save()
        ctx.translate(buzz, 0)
        props.phone(ctx, W / 2, 860, 640, t, lit=1.0)
        draw_surface(ctx, text(str(o.get("screen", "NO SIGNAL")).upper(), "bold", 54, "#f2f2f2"), W / 2, 780)
        draw_surface(ctx, text(str(o.get("sub", "")).upper(), "mono", 26, "#9fb6d6"), W / 2, 850)
        if o.get("message"):
            k = t - shot.cue(o.get("message_cue"), 0.0)
            if k >= 0:
                y = 950
                for line in str(o["message"]).split("\n"):
                    draw_surface(ctx, text(line, "bold", 30, "#f2f2f2"), W / 2, y, alpha=clamp(k / 0.3))
                    y += 44
        ctx.restore()
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


# ------------------------------------------------------------------ security camera

@scene("cctv")
def cctv(cv, shot, t):
    """A security-camera feed on a monitor: any scene (`view`), tinted, with
    scanlines, CAM label, REC light and timestamp."""
    ctx = cv.ctx
    o = shot.spec
    vgradient(ctx, -300, -300, W + 600, H + 600, "#0d0f12", "#050607")
    mx, my, mw, mh = 70, 400, 940, 760
    rounded_rect(ctx, mx - 26, my - 26, mw + 52, mh + 52, 28)
    set_color(ctx, "#1d2025")
    ctx.fill()
    glow(ctx, W / 2, my + mh / 2, 760, "#8fc3cf", 0.12)
    view = {**(o.get("view") or {"scene": "hallway", "lights": "on"})}
    for k in ("flicker", "dies", "relight"):
        if o.get(k) is not None and k not in view:
            view[k] = o[k]
    ctx.save()
    ctx.rectangle(mx, my, mw, mh)
    ctx.clip()
    src_y = float(o.get("src_y", 470))
    s = mw / W * float(o.get("zoom", 1.0))
    ctx.translate(mx + mw / 2, my)
    ctx.scale(s, s)
    ctx.translate(-W / 2, -src_y)
    paint(cv, shot.sub({**view, "scene": view.get("scene", "hallway")}), t)
    ctx.restore()
    ctx.save()
    ctx.rectangle(mx, my, mw, mh)
    ctx.clip()
    ctx.set_source_rgba(0.35, 0.55, 0.5, 0.18)  # cheap camera colour
    ctx.paint()
    for y in range(int(my), int(my + mh), 5):
        ctx.rectangle(mx, y, mw, 2)
    ctx.set_source_rgba(0, 0, 0, 0.16)
    ctx.fill()
    band = my + (t * 220) % (mh + 200) - 100
    g = cairo.LinearGradient(0, band - 40, 0, band + 40)
    g.add_color_stop_rgba(0, 1, 1, 1, 0)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.06)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g)
    ctx.rectangle(mx, band - 40, mw, 80)
    ctx.fill()
    if o.get("glitch") is not None and t >= shot.cue(o.get("glitch"), 1e9) and flicker(t, 5, 18) < 0.9:
        ctx.set_source_rgba(1, 1, 1, 0.12)
        ctx.paint()
    ctx.restore()
    from .episode import format_time
    draw_surface(ctx, text(str(o.get("cam", "CAM 01")).upper(), "mono", 30, "#e8f1ee", shadow=2), mx + 30, my + 45, anchor="l")
    if math.sin(t * 5) > -0.2:
        set_color(ctx, RED)
        ctx.arc(mx + mw - 120, my + 45, 11, 0, 2 * math.pi)
        ctx.fill()
    draw_surface(ctx, text("REC", "mono", 28, "#e8f1ee", shadow=2), mx + mw - 100, my + 45, anchor="l")
    hm, ap = format_time(shot.minutes_at(t))
    draw_surface(ctx, text(f"{hm}:{int(t * 7) % 60:02d} {ap}", "mono", 26, "#e8f1ee", shadow=2),
                 mx + 30, my + mh - 40, anchor="l")


# ------------------------------------------------------------------ subway car

def _travel(shot, t, speed):
    """Distance the train has covered at t, braking to a stop at `stop` and
    pulling away at `start` (each over about two seconds). `parked: true`
    means it stands still until `start`."""
    brake = 2.2
    if shot.get("parked"):
        d, moving = 0.0, False
    else:
        st = shot.cue(shot.get("stop"), 1e9) if shot.get("stop") is not None else 1e9
        d = speed * min(t, st)
        if t > st:
            tau = min(t - st, brake)
            d += speed * (tau - tau * tau / (2 * brake))
        moving = t < st + brake
    go = shot.cue(shot.get("start"), 1e9) if shot.get("start") is not None else 1e9
    if t > go:
        tau = t - go
        d += speed * (tau * tau / 4.0 if tau < 2.0 else 1.0 + (tau - 2.0))
        moving = True
    return d, moving


def _until_stop(shot, t, speed):
    """How far the train still has to go before it stops (0 once stopped,
    negative after it pulls away again)."""
    d = _travel(shot, t, speed)[0]
    if shot.get("stop") is not None:
        end = _travel(shot, shot.cue(shot.get("stop")) + 5, speed)[0] if shot.get("start") is None else \
            _travel(shot, shot.cue(shot.get("start")), speed)[0]
        return end - d
    if shot.get("start") is not None:
        return _travel(shot, shot.cue(shot.get("start")), speed)[0] - d
    return 0.0


def _waiting(ctx, shot, t, people, ground, scale):
    """People standing still (on a platform); `turn: cue` makes them face you."""
    out = []
    for k, p in enumerate(people or []):
        if t < shot.cue(p.get("cue"), 0.0):
            continue
        facing = int(p.get("facing", 1))
        turned = p.get("turn") is not None and t >= shot.cue(p.get("turn"), 1e9)
        if turned:
            facing = int(p.get("to_facing", -facing))
        x = float(p.get("x", 0.5)) * W
        pose = F.Pose(lean=0.0, sh_f=0.1, el_f=0.12, sh_b=-0.1, el_b=0.12, head=0.2 if turned else 0.0)
        col = p.get("color", "#cfd3d8")
        j = F.draw_stickman(ctx, pose, x, ground, scale, facing, color=col, outline="#1b1b1b")
        if p.get("coat"):
            _coat(ctx, j, scale, p["coat"] if isinstance(p["coat"], str) else "#6e737b", facing)
        if p.get("stare", turned):
            out.append((j, scale, facing))
    return out


def _coat(ctx, j, scale, color, facing):
    """A long coat over the torso (the man in the grey coat)."""
    w = 22 * scale
    nx, ny = j.neck
    hx, hy = j.hip
    fill(ctx, [(nx - w, ny + 4), (nx + w, ny + 4), (hx + w * 1.35, hy + 46 * scale), (hx - w * 1.35, hy + 46 * scale)],
         color)
    ctx.move_to(nx + 4 * facing, ny + 10)
    ctx.line_to(hx + 6 * facing, hy + 40 * scale)
    ctx.set_line_width(3)
    ctx.set_source_rgba(0, 0, 0, 0.35)
    ctx.stroke()


def _led(ctx, x, y, w, msg, alpha=1.0):
    rounded_rect(ctx, x - w / 2, y - 30, w, 60, 8)
    set_color(ctx, "#0b0b0c")
    ctx.fill()
    draw_surface(ctx, text(str(msg).upper(), "mono", 30, "#ff9a2a", glow_color="#ff7a00", glow_radius=6,
                           tracking=2), x, y, alpha=alpha)


def _cue_list(shot, t, value):
    """A value or a list of [value, cue] pairs: the latest one whose cue has passed."""
    if not isinstance(value, list):
        return value
    cur = None
    for v, cue in value:
        if t >= shot.cue(cue, 0.0):
            cur = v
    return cur


@scene("train")
def train(cv, shot, t):
    """Inside a subway car, seen from the side: windows onto the tunnel (or a
    station), benches, poles, a sliding door in the middle."""
    ctx = cv.ctx
    o = shot.spec
    speed = float(o.get("speed", 1700))
    dist, moving = _travel(shot, t, speed)
    sway = 3 * math.sin(t * 7.3) * (1 if moving else 0)
    lights = _cue_list(shot, t, o.get("lights", "on"))  # or [[off, 0], [on, cue]]
    top, wall_bot, floor_y = 300, 1205, 1205
    win_y0, win_y1 = 520, 860
    station = o.get("station")
    door_open = 0.0
    if o.get("doors") is not None:
        d = o.get("doors")
        a = shot.cue(d.get("open") if isinstance(d, dict) else d, 0.0)
        door_open = ease_out((t - a) / 0.8) if t >= a else 0.0
        if isinstance(d, dict) and d.get("close") is not None:
            door_open *= 1 - ease_out((t - shot.cue(d["close"])) / 0.6) if t >= shot.cue(d["close"]) else 1
    # outside: the tunnel rushing past, or a station platform
    ctx.save()
    ctx.translate(0, sway)
    vgradient(ctx, -300, top, W + 600, wall_bot - top, "#06070a", "#0d0f13")
    stares = []
    if station:
        st = station if isinstance(station, dict) else {"name": station}
        x_off = _until_stop(shot, t, speed)  # the platform slides in as the train brakes
        if x_off < 3000:
            ctx.save()
            ctx.translate(x_off, 0)
            tile = st.get("color", "#cfc6a8")
            vgradient(ctx, -1400, top, W + 2800, 700, shade(tile, 0.75), shade(tile, 0.55))
            for gx in range(-1400, W + 1400, 60):
                ctx.rectangle(gx, top, 2, 700)
            for gy in range(top, top + 700, 40):
                ctx.rectangle(-1400, gy, W + 2800, 2)
            ctx.set_source_rgba(0, 0, 0, 0.12)
            ctx.fill()
            ctx.rectangle(-1400, 980, W + 2800, 260)
            set_color(ctx, "#3a3a3e")
            ctx.fill()
            ctx.rectangle(-1400, 975, W + 2800, 14)
            set_color(ctx, "#e5c01e")
            ctx.fill()
            for k, sx in enumerate((-900, 200, 1300, 2400)):  # name signs along the wall
                rounded_rect(ctx, sx - 170, 600, 340, 80, 10)
                set_color(ctx, st.get("sign", "#1d3d6b"))
                ctx.fill()
                draw_surface(ctx, text(str(st.get("name", "STATION")).upper(), "title", 58, "#f4f1e8", tracking=3),
                             sx, 641)
            for k, lx in enumerate(range(-1300, W + 1400, 420)):
                b = flicker(t, k, 7) if st.get("flicker") else 1.0
                glow(ctx, lx, 380, 260, "#fff2c8", 0.45 * b)
            stares += _waiting(ctx, shot, t, st.get("people"), 980, 1.0)
            ctx.restore()
    if not station or abs(x_off) > 0:  # tunnel wall with lamps and cables streaming by
        ctx.save()
        if station:  # only where the platform isn't
            if x_off > 0:
                ctx.rectangle(-300, top, max(x_off - 1100, 0), wall_bot - top)
            else:
                ctx.rectangle(x_off + W + 1400, top, W + 600, wall_bot - top)
            ctx.clip()
        for k in range(3):
            y = 640 + k * 26
            ctx.rectangle(-300, y, W + 600, 5)
        ctx.set_source_rgba(0.25, 0.26, 0.28, 1)
        ctx.fill()
        gap = 700
        for k in range(4):
            lx = (k * gap - dist) % (gap * 4) - 400
            glow(ctx, lx, 760, 110, "#ffb35c", 0.6)
            ctx.rectangle(lx - 18, 752, 36, 16)
            set_color(ctx, "#ffd9a0")
            ctx.fill()
        if moving:  # streaks of the tunnel wall rushing by
            for k in range(14):
                sy = 540 + (k * 97) % 300
                sx = (k * 523 - dist * 1.3) % (W + 900) - 450
                ctx.rectangle(sx, sy, 160 + (k * 37) % 220, 3)
            ctx.set_source_rgba(0.6, 0.62, 0.66, 0.18)
            ctx.fill()
        for k in range(int(o.get("tunnel_eyes", 0))):  # eyes in the tunnel, keeping pace
            ex = 150 + k * 330 + 30 * math.sin(t + k)
            if t >= shot.cue(o.get("eyes_cue"), 0.0):
                eyes(ctx, ex, 700 + 50 * math.sin(k * 2.3), 5, 0.9)
        ctx.restore()
    ctx.restore()
    # the car: wall with window holes (and the door gap when it opens)
    ctx.save()
    ctx.translate(0, sway)
    body = o.get("wall", "#c9ccd1")
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.rectangle(-300, top, W + 600, wall_bot - top)
    wins = [(-260, 330), (750, 1340)]
    for wx0, wx1 in wins:
        rounded_rect(ctx, wx0 + 40, win_y0, wx1 - wx0 - 80, win_y1 - win_y0, 26)
    dx0, dx1 = 400, 680
    gapw = (dx1 - dx0) * 0.5 * door_open
    if gapw > 1:
        ctx.rectangle(540 - gapw, 440, gapw * 2, wall_bot - 440)
    g = cairo.LinearGradient(0, top, 0, wall_bot)
    g.add_color_stop_rgb(0, *shade(body, 0.8))
    g.add_color_stop_rgb(0.3, *rgb(body))
    g.add_color_stop_rgb(1, *shade(body, 0.7))
    ctx.set_source(g)
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    for wx0, wx1 in wins:  # window frames + a faint reflection
        rounded_rect(ctx, wx0 + 40, win_y0, wx1 - wx0 - 80, win_y1 - win_y0, 26)
        ctx.set_line_width(10)
        set_color(ctx, "#7d838c")
        ctx.stroke()
        ctx.move_to(wx0 + 120, win_y0 + 20)
        ctx.line_to(wx0 + 60, win_y0 + 110)
        ctx.set_line_width(14)
        ctx.set_source_rgba(1, 1, 1, 0.05)
        ctx.stroke()
    # sliding door leaves
    for side in (-1, 1):
        lw = (dx1 - dx0) / 2
        x0 = (540 - lw if side < 0 else 540) + side * gapw
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.rectangle(x0, 440, lw, wall_bot - 440)
        rounded_rect(ctx, x0 + 22, 520, lw - 44, 300, 14)
        set_color(ctx, shade(body, 0.86))
        ctx.fill()
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
        ctx.rectangle(x0, 440, lw, wall_bot - 440)
        ctx.set_line_width(4)
        set_color(ctx, "#6b7079")
        ctx.stroke()
    ctx.rectangle(dx0 - 14, 430, 14, wall_bot - 430)
    ctx.rectangle(dx1, 430, 14, wall_bot - 430)
    set_color(ctx, "#8e949c")
    ctx.fill()
    # ceiling, light strip, the next-stop sign over the door, ad panels
    vgradient(ctx, -300, top - 400, W + 600, 520, "#15161a", shade(body, 0.55))
    strip = []
    for k, lx in enumerate(range(-200, W + 300, 260)):
        if lights == "on":
            b = 1.0
        elif lights == "flicker":
            b = flicker(t, k, 9)
        elif lights == "dying":
            b = 1.0 if t < shot.cue(o.get("off"), 0.8) - k * 0.12 else 0.0
        else:
            b = 0.0
        rounded_rect(ctx, lx - 100, 330, 200, 26, 12)
        set_color(ctx, "#fffaf0" if b > 0.5 else "#4a4c50")
        ctx.fill()
        if b > 0:
            glow(ctx, lx, 360, 220, "#fff6e0", 0.35 * b)
            strip.append((lx, 380, 480, b))
    nxt = _cue_list(shot, t, o.get("next"))
    if nxt:
        _led(ctx, 540, 395, 470, nxt)
    for ax in (100, 870):
        ctx.rectangle(ax - 90, 395, 180, 90)
        set_color(ctx, "#e9e4d8")
        ctx.fill()
        ctx.rectangle(ax - 80, 405, 70, 70)
        set_color(ctx, "#4f7aa8" if ax < 500 else "#b5523b")
        ctx.fill()
    # benches and the floor
    for bx0, bx1 in ((-300, 380), (700, W + 300)):
        rounded_rect(ctx, bx0, 1110, bx1 - bx0, 60, 14)
        set_color(ctx, o.get("seats", "#2f5d8c"))
        ctx.fill()
        ctx.rectangle(bx0, 1170, bx1 - bx0, 35)
        set_color(ctx, "#53575e")
        ctx.fill()
    ctx.restore()
    g = cairo.LinearGradient(0, floor_y, 0, H + 200)
    g.add_color_stop_rgb(0, *rgb("#4b4e55"))
    g.add_color_stop_rgb(1, *rgb("#2e3036"))
    ctx.set_source(g)
    ctx.rectangle(-300, floor_y, W + 600, H)
    ctx.fill()
    for k in range(-6, 7):
        ctx.arc(540 + k * 160 + (sway * 0.5), 1300 + 40 * (k % 2), 3, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.06)
    ctx.fill()
    if gapw > 1:  # platform edge through the open door
        ctx.rectangle(540 - gapw, floor_y, gapw * 2, 8)
        set_color(ctx, "#e5c01e" if station else "#111111")
        ctx.fill()
    # poles and the grab rail
    for px in [float(x) * W for x in o.get("poles", [0.3, 0.74])]:
        stroke_line(ctx, [(px, top + 20 + sway), (px, floor_y + 160)], 14, "#c9ced6", 1.0, "#5e636b")
    stroke_line(ctx, [(-300, 470 + sway), (W + 300, 470 + sway)], 10, "#b9bec6", 1.0, "#5e636b")
    # passengers on the benches (or standing), then creatures, then you
    seat_ground = 1262
    for k, p in enumerate(o.get("passengers") or []):
        if t < shot.cue(p.get("cue"), 0.0):
            continue
        a = 1.0 - clamp((t - shot.cue(p.get("fade"), 1e9)) / 0.6)
        if a <= 0:
            continue
        sitting = p.get("sit", True)
        facing = int(p.get("facing", 1))
        if p.get("turn") is not None and t >= shot.cue(p.get("turn"), 1e9):
            facing = -facing
        sc = float(p.get("scale", 1.0 if sitting else 1.15))
        g_y = seat_ground + sway if sitting else float(o.get("ground", 1430))
        pose = F.pose_for("sit" if sitting else p.get("action", "idle"), t + k * 0.7, seed=k)
        if p.get("asleep"):
            pose.head = 0.55
        col = p.get("color", "#d9d9d9")
        j = F.draw_stickman(ctx, pose, float(p.get("x", 0.2)) * W, g_y, sc, facing, color=col, alpha=a)
        if p.get("coat"):
            _coat(ctx, j, sc, p.get("coat") if isinstance(p.get("coat"), str) else "#6e737b", facing)
            ctx.arc(j.head[0], j.head[1], (F.HEAD + 3) * sc, 0, 2 * math.pi)
            set_color(ctx, "#1b1b1b", a)
            ctx.fill()
            ctx.arc(j.head[0], j.head[1], F.HEAD * sc, 0, 2 * math.pi)
            set_color(ctx, col, a)
            ctx.fill()
        if p.get("stare") is not None and t >= shot.cue(p.get("stare"), 0.0) if not isinstance(p.get("stare"), bool) \
                else p.get("stare"):
            stares.append((j, sc, facing))
    dark = float(o.get("dark", 0 if lights in ("on", "flicker") else 0.85))
    ground = float(o.get("ground", 1430))
    crs = draw_creatures(cv, shot, t, o.get("creatures"), ground, dark > 0)
    j, beam = hero(cv, shot, t, o.get("you"), ground if (o.get("you") or {}).get("action") != "sit" else seat_ground,
                   1.0 if (o.get("you") or {}).get("action") == "sit" else 1.25)
    if dark > 0:
        extra = [("radial", lx, ly, r * 1.2, b * 0.9) for lx, ly, r, b in strip]
        if station:
            extra += [("radial", 160, 690, 420, 0.6), ("radial", 920, 690, 420, 0.6)] if abs(x_off) < 200 else []
        _apply_dark(cv, shot, t, dark, beam, j, extra=extra)
        for cj, sc, fc, a in crs:
            creature_eyes(ctx, cj, sc, fc, a)
    for sj, sc, fc in stares:
        eyes(ctx, sj.head[0] + 4 * sc * fc, sj.head[1] - 2 * sc, 3.2 * sc, 0.9, gap=11 * sc)


# ------------------------------------------------------------------ the driver's view

@scene("tunnel")
def tunnel(cv, shot, t):
    """From the driver's cab: the tunnel ahead in the headlights, rails, signals,
    a station platform sliding up on the right, figures on the tracks."""
    ctx = cv.ctx
    o = shot.spec
    speed = float(o.get("speed", 3.2))  # depth units per second
    dist, moving = _travel(shot, t, speed)
    vgradient(ctx, -300, -300, W + 600, H + 600, "#020203", "#07080a")
    rw, rh = 1.35, 1.5
    gap = 1.1
    # rings of the tunnel lining
    k0 = int(dist // gap)
    for k in range(k0 + 30, k0 - 1, -1):
        z = k * gap - dist + Z0
        if z < Z0 or z > 16:
            continue
        sh = 1 / (1 + 0.22 * (z - Z0))
        pts = [proj(-rw, -1, z), proj(-rw, rh * 0.55, z)] + \
              [proj(-rw * math.cos(a), rh * 0.55 + rh * 0.45 * math.sin(a), z) for a in [i * math.pi / 12 for i in range(13)]] + \
              [proj(rw, -1, z)]
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_line_width(max(1.0, 9 * sh))
        ctx.set_source_rgba(*shade("#5d6066", sh), 1)
        ctx.stroke()
        if k % 3 == 0:  # a work lamp on the left wall
            lx, ly = proj(-rw + 0.02, 0.35, z)
            glow(ctx, lx, ly, 120 * sh, "#ffb35c", 0.7 * sh)
    # track bed, sleepers and rails
    fill(ctx, [proj(-rw, -1, Z0), proj(rw, -1, Z0), proj(rw, -1, 16), proj(-rw, -1, 16)], (0.08, 0.075, 0.07))
    for k in range(int(dist // 0.45), int(dist // 0.45) + 40):
        z = k * 0.45 - dist + Z0
        if Z0 <= z <= 16:
            a, b = proj(-0.6, -1, z), proj(0.6, -1, z)
            stroke_line(ctx, [a, b], max(1, 16 / z), "#2b2620")
    for x in (-0.36, 0.36):
        stroke_line(ctx, [proj(x, -1, Z0), proj(x, -1, 16)], 5, "#9ea3aa")
    # a station platform on the right
    station = o.get("station")
    lit = []
    if station:
        st = station if isinstance(station, dict) else {"name": station}
        zf = float(st.get("park", 1.2)) + _until_stop(shot, t, speed)
        if zf < 30:
            zb = zf + 9
            tile = st.get("color", "#cfc6a8")
            px0, ptop = 0.95, -0.35
            fill(ctx, [proj(px0, ptop, zf), proj(3.5, ptop, zf), proj(3.5, ptop, zb), proj(px0, ptop, zb)], shade("#55565a", 0.9))
            fill(ctx, [proj(px0, -1, zf), proj(px0, ptop, zf), proj(px0, ptop, zb), proj(px0, -1, zb)], shade("#2a2a2c", 1))
            stroke_line(ctx, [proj(px0 + 0.05, ptop, zf), proj(px0 + 0.05, ptop, zb)], 6, "#e5c01e")
            fill(ctx, [proj(2.4, ptop, zf), proj(2.4, 1.6, zf), proj(2.4, 1.6, zb), proj(2.4, ptop, zb)], shade(tile, 0.8))
            sx, sy = proj(2.38, 0.75, zf + 2.0)
            draw_surface(ctx, text(str(st.get("name", "")).upper(), "title", max(12, int(150 / (zf + 2.0))), "#f4f1e8",
                                   tracking=2), sx, sy)
            for k in range(4):
                lz = zf + 0.5 + k * 2.2
                lx, ly = proj(1.6, 1.45, lz)
                b = flicker(t, k, 7) if st.get("flicker") else 1.0
                glow(ctx, lx, ly, 260 / lz, "#fff2c8", 0.6 * b)
                lit.append((lx, ly + 200 / lz, 700 / lz, 0.8 * b))
            for k, p in enumerate(st.get("people") or []):
                pz = zf + float(p.get("dz", 1 + k))
                fx, gy = proj(float(p.get("x", 1.6)), ptop, pz)
                facing = int(p.get("facing", -1))
                turned = p.get("turn") is not None and t >= shot.cue(p.get("turn"), 1e9)
                pose = F.Pose(sh_f=0.1, el_f=0.12, sh_b=-0.1, el_b=0.12, head=0.2 if turned else 0.0)
                pj = F.draw_stickman(ctx, pose, fx, gy, 3.0 / pz, -1 if turned else facing, color=p.get("color", "#cfd3d8"))
                if p.get("coat"):
                    _coat(ctx, pj, 3.0 / pz, p["coat"] if isinstance(p["coat"], str) else "#6e737b", facing)
                if turned or p.get("stare"):
                    eyes(ctx, pj.head[0] - 4 * 3.0 / pz, pj.head[1] - 6 / pz, 9.6 / pz, 0.9, gap=33 / pz)
    # a signal ahead
    sig = _cue_list(shot, t, o.get("signal"))
    if sig:
        sx, sy = proj(-0.95, 0.4, 6.0)
        rounded_rect(ctx, sx - 16, sy - 30, 32, 60, 8)
        set_color(ctx, "#111111")
        ctx.fill()
        col = {"red": "#ff3b30", "green": "#34e07a", "yellow": "#ffcc00"}.get(sig, "#ff3b30")
        glow(ctx, sx, sy - 10, 90, col, 0.8)
        set_color(ctx, col)
        ctx.arc(sx, sy - 10, 9, 0, 2 * math.pi)
        ctx.fill()
        lit.append((sx, sy, 120, 0.4))
    # figures on (or beside) the tracks, like the hallway's
    figs = []
    for k, f in enumerate(o.get("figures") or []):
        if t < shot.cue(f.get("cue"), 0.0):
            continue
        z = float(f.get("z", 6.0))
        if f.get("fixed", True):  # stands still in the tunnel, so it comes closer as we move
            z -= dist - _travel(shot, shot.cue(f.get("cue"), 0.0), speed)[0]
        if z < 0.7:
            continue
        fx, gy = proj(float(f.get("x", 0)), -1, z)
        sc = 3.0 / z
        who = f.get("who", "creature")
        pose = F.pose_for(f.get("action", "lurk" if who == "creature" else "idle"), t + k, seed=k)
        facing = int(f.get("facing", -1))
        if who == "creature":
            figs.append((F.draw_creature(ctx, pose, fx, gy, sc, facing, eye_alpha=0), sc, facing))
        else:
            pj = F.draw_stickman(ctx, pose, fx, gy, sc, facing, color=f.get("color", "#cfd3d8"))
            if f.get("coat"):
                _coat(ctx, pj, sc, f.get("coat") if isinstance(f.get("coat"), str) else "#6e737b", facing)
    # headlights
    s = light_strength(shot, t) if o.get("headlights", True) else 0.0
    d = cv.dark
    d.begin(ctx.get_matrix(), float(o.get("dark", 0.9)))
    if s > 0:
        d.radial(CX, CY + 360, 900, 0.75 * s, 1.0, 0.55)
        d.radial(CX, CY, 520, 0.5 * s)
    for lx, ly, r, b in lit:
        d.radial(lx, ly, r, b)
    d.apply(ctx)
    for j, sc, facing in figs:
        creature_eyes(ctx, j, sc, facing)
    if o.get("cab", True):  # windscreen frame and the dashboard
        ctx.save()
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.rectangle(-400, -400, W + 800, H + 800)
        rounded_rect(ctx, 40, 330, W - 80, 900, 40)
        set_color(ctx, "#121317")
        ctx.fill()
        ctx.restore()
        rounded_rect(ctx, 40, 330, W - 80, 900, 40)
        ctx.set_line_width(14)
        set_color(ctx, "#26282e")
        ctx.stroke()
        stroke_line(ctx, [(W / 2, 330), (W / 2, 1230)], 16, "#1a1b20")
        vgradient(ctx, -300, 1240, W + 600, 700, "#202227", "#0d0e11")
        for k, (bx, col) in enumerate(((180, "#34e07a"), (250, "#ffcc00"), (320, "#ff3b30"))):
            on = 0.35 + 0.65 * (math.sin(t * 2 + k) > 0)
            glow(ctx, bx, 1330, 40, col, 0.4 * on)
            set_color(ctx, col, on)
            ctx.arc(bx, 1330, 12, 0, 2 * math.pi)
            ctx.fill()
        nxt = _cue_list(shot, t, o.get("next"))
        if nxt:
            _led(ctx, 740, 1330, 520, nxt)
        # speed gauge
        v = (_travel(shot, t + 0.05, speed)[0] - _travel(shot, t, speed)[0]) / 0.05 / max(speed, 0.01)
        gx, gy, gr = W / 2, 1640, 150
        ctx.set_line_width(16)
        set_color(ctx, "#2c2f36")
        ctx.arc(gx, gy, gr, math.pi * 0.8, math.pi * 2.2)
        ctx.stroke()
        set_color(ctx, "#ff9a2a", 0.85)
        ctx.arc(gx, gy, gr, math.pi * 0.8, math.pi * (0.8 + 1.4 * 0.75 * clamp(v)))
        ctx.stroke()
        ang = math.pi * (0.8 + 1.4 * 0.75 * clamp(v)) + 0.01 * math.sin(t * 13) * (v > 0.05)
        stroke_line(ctx, [(gx, gy), (gx + math.cos(ang) * (gr - 30), gy + math.sin(ang) * (gr - 30))], 8, "#f4f1e8")
        draw_surface(ctx, text(f"{int(round(60 * clamp(v)))}", "title", 70, "#f4f1e8"), gx, gy + 70)
        draw_surface(ctx, text("KM/H", "mono", 22, "#8a8f98", tracking=3), gx, gy + 120)


# ------------------------------------------------------------------ cinema hall

@scene("cinema")
def cinema(cv, shot, t):
    """An old cinema seen from the back row: the lit screen, red curtains, rows of
    seats with an audience (`audience`: share of seats taken) whose heads turn
    round at `turn` (glowing eyes). `screen` puts big text on the screen;
    `screen_off: cue` blacks it out."""
    ctx = cv.ctx
    o = shot.spec
    vgradient(ctx, -300, -300, W + 600, H + 600, "#0a090c", "#050407")
    off = o.get("screen_off") is not None and t >= shot.cue(o.get("screen_off"), 1e9)
    sx, sy, sw, sh = 120, 360, 840, 470
    lum = 0.0 if off else (0.85 + 0.1 * flicker(t, 2, 6) if o.get("flicker") else 0.95)
    if lum > 0:
        glow(ctx, W / 2, sy + sh / 2, 900, "#cfd8ff", 0.22 * lum)
    ctx.rectangle(sx, sy, sw, sh)
    set_color(ctx, mix("#0c0c10", "#e6ecff", lum))
    ctx.fill()
    msg = _cue_list(shot, t, o.get("screen"))
    if msg and lum > 0:
        draw_surface(ctx, text(str(msg).upper(), "title", int(o.get("screen_size", 120)), "#1a1d26", tracking=4),
                     W / 2, sy + sh / 2, alpha=lum)
    for side in (-1, 1):  # curtains
        cx = sx - 60 if side < 0 else sx + sw + 60
        g = cairo.LinearGradient(cx - 110, 0, cx + 110, 0)
        g.add_color_stop_rgb(0, *rgb("#4a0d12"))
        g.add_color_stop_rgb(0.5, *rgb("#7a1820"))
        g.add_color_stop_rgb(1, *rgb("#4a0d12"))
        ctx.set_source(g)
        ctx.rectangle(cx - 120, sy - 140, 240, sh + 260)
        ctx.fill()
    ctx.rectangle(-300, sy - 160, W + 600, 70)
    set_color(ctx, "#5e1118")
    ctx.fill()
    # rows of seats, back of the hall nearest the camera
    share = float(o.get("audience", 0.0))
    turned = o.get("turn") is not None and t >= shot.cue(o.get("turn"), 1e9)
    heads = []
    for r in range(6):
        k = 0.55 + r * 0.11
        y = 960 + r * (70 + r * 18)
        n = 11 - r
        gap = (W + 160) / n
        for c in range(n):
            x = -80 + gap * (c + 0.5) + (r % 2) * gap * 0.3
            rounded_rect(ctx, x - 40 * k, y, 80 * k, 70 * k, 14 * k)
            set_color(ctx, shade("#5a1219", 0.45 + 0.08 * r))
            ctx.fill()
            if ((c * 7 + r * 3) % 10) / 10 < share:
                hy = y - 22 * k + 2 * math.sin(t * 0.7 + c + r)
                ctx.arc(x, hy, 30 * k, 0, 2 * math.pi)
                set_color(ctx, "#2a2a32" if turned else "#121217")
                ctx.fill()
                heads.append((x, hy, k))
    if lum > 0:  # the projector beam over the heads
        g = cairo.LinearGradient(0, H, 0, sy)
        g.add_color_stop_rgba(0, 0.85, 0.9, 1.0, 0.0)
        g.add_color_stop_rgba(1, 0.85, 0.9, 1.0, 0.07 * lum)
        ctx.set_source(g)
        ctx.move_to(W / 2 - 30, H + 100)
        ctx.line_to(sx, sy)
        ctx.line_to(sx + sw, sy)
        ctx.line_to(W / 2 + 30, H + 100)
        ctx.close_path()
        ctx.fill()
    if o.get("you"):
        hero(cv, shot, t, o.get("you"), float(o.get("ground", 1820)), 1.3)
    if turned:
        for x, hy, k in heads:
            eyes(ctx, x, hy - 2 * k, 5 * k, 0.95, gap=20 * k)
