"""Objects: inventory icons, the radio, clocks, furniture pieces."""

from __future__ import annotations

import math

import cairo

from .gfx import glow, rgb, rounded_rect, set_color, stroke_line


# ------------------------------------------------------------------ inventory icons
# Each draws an icon of roughly `s` pixels tall, centred on (x, y).

def battery(ctx, x, y, s, alpha=1.0):
    w, h = s * 0.42, s * 0.9
    rounded_rect(ctx, x - w / 2, y - h / 2, w, h, w * 0.18)
    set_color(ctx, "#1d1d1f", alpha)
    ctx.fill()
    rounded_rect(ctx, x - w / 2, y - h / 2 + h * 0.42, w, h * 0.58, w * 0.18)
    set_color(ctx, "#e9b824", alpha)
    ctx.fill()
    ctx.rectangle(x - w * 0.18, y - h / 2 - s * 0.07, w * 0.36, s * 0.08)
    set_color(ctx, "#9a9aa0", alpha)
    ctx.fill()
    set_color(ctx, "#ffffff", alpha * 0.9)
    ctx.set_line_width(s * 0.05)
    ctx.move_to(x - w * 0.18, y - h * 0.22)
    ctx.line_to(x + w * 0.18, y - h * 0.22)
    ctx.move_to(x, y - h * 0.36)
    ctx.line_to(x, y - h * 0.08)
    ctx.stroke()


def candle(ctx, x, y, s, alpha=1.0, t=0.0):
    w, h = s * 0.32, s * 0.62
    top = y - h / 2 + s * 0.18
    rounded_rect(ctx, x - w / 2, top, w, h, w * 0.2)
    set_color(ctx, "#efe6d2", alpha)
    ctx.fill()
    ctx.set_line_width(s * 0.03)
    set_color(ctx, "#333333", alpha)
    ctx.move_to(x, top)
    ctx.line_to(x, top - s * 0.07)
    ctx.stroke()
    fl = 1 + 0.12 * math.sin(t * 17 + x)
    glow(ctx, x, top - s * 0.16, s * 0.45, "#ffb347", 0.35 * alpha)
    ctx.save()
    ctx.translate(x, top - s * 0.15)
    ctx.scale(1, fl)
    ctx.move_to(0, -s * 0.16)
    ctx.curve_to(s * 0.1, -s * 0.05, s * 0.08, s * 0.06, 0, s * 0.07)
    ctx.curve_to(-s * 0.08, s * 0.06, -s * 0.1, -s * 0.05, 0, -s * 0.16)
    set_color(ctx, "#ffd36a", alpha)
    ctx.fill()
    ctx.restore()


def matches(ctx, x, y, s, alpha=1.0):
    w, h = s * 0.8, s * 0.5
    rounded_rect(ctx, x - w / 2, y - h / 2, w, h, s * 0.05)
    set_color(ctx, "#c0392b", alpha)
    ctx.fill()
    rounded_rect(ctx, x - w / 2 + s * 0.08, y - h / 2 + s * 0.08, w - s * 0.16, h - s * 0.16, s * 0.04)
    set_color(ctx, "#f1e3c6", alpha)
    ctx.fill()
    for k in range(3):
        mx = x - s * 0.18 + k * s * 0.18
        stroke_line(ctx, [(mx, y + s * 0.08), (mx + s * 0.06, y - s * 0.12)], s * 0.05, "#c99a5b", alpha)
        set_color(ctx, "#8e1b10", alpha)
        ctx.arc(mx + s * 0.06, y - s * 0.13, s * 0.045, 0, 2 * math.pi)
        ctx.fill()


def torch_icon(ctx, x, y, s, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-0.6)
    rounded_rect(ctx, -s * 0.45, -s * 0.12, s * 0.62, s * 0.24, s * 0.05)
    set_color(ctx, "#2f343d", alpha)
    ctx.fill()
    rounded_rect(ctx, s * 0.15, -s * 0.2, s * 0.3, s * 0.4, s * 0.06)
    set_color(ctx, "#5a606b", alpha)
    ctx.fill()
    ctx.rectangle(s * 0.43, -s * 0.15, s * 0.05, s * 0.3)
    set_color(ctx, "#fff3c2", alpha)
    ctx.fill()
    ctx.rectangle(-s * 0.2, -s * 0.05, s * 0.12, s * 0.1)
    set_color(ctx, "#e9b824", alpha)
    ctx.fill()
    ctx.restore()


def can(ctx, x, y, s, alpha=1.0):
    w, h = s * 0.55, s * 0.7
    ctx.rectangle(x - w / 2, y - h / 2, w, h)
    set_color(ctx, "#b8bcc4", alpha)
    ctx.fill()
    ctx.rectangle(x - w / 2, y - h * 0.22, w, h * 0.44)
    set_color(ctx, "#d35400", alpha)
    ctx.fill()
    for yy in (y - h / 2, y + h / 2):
        ctx.save()
        ctx.translate(x, yy)
        ctx.scale(1, 0.25)
        ctx.arc(0, 0, w / 2, 0, 2 * math.pi)
        ctx.restore()
        set_color(ctx, "#8d929b", alpha)
        ctx.fill()


def bottle(ctx, x, y, s, alpha=1.0):
    w, h = s * 0.36, s * 0.7
    rounded_rect(ctx, x - w / 2, y - h / 2 + s * 0.1, w, h, w * 0.3)
    set_color(ctx, "#5dade2", alpha * 0.85)
    ctx.fill()
    ctx.rectangle(x - w * 0.22, y - h / 2 - s * 0.04, w * 0.44, s * 0.16)
    set_color(ctx, "#2e86c1", alpha)
    ctx.fill()
    ctx.rectangle(x - w / 2, y, w, s * 0.14)
    set_color(ctx, "#ffffff", alpha * 0.8)
    ctx.fill()


def key(ctx, x, y, s, alpha=1.0):
    set_color(ctx, "#d4ac0d", alpha)
    ctx.set_line_width(s * 0.09)
    ctx.arc(x - s * 0.2, y, s * 0.17, 0, 2 * math.pi)
    ctx.stroke()
    ctx.move_to(x - s * 0.03, y)
    ctx.line_to(x + s * 0.38, y)
    ctx.move_to(x + s * 0.28, y)
    ctx.line_to(x + s * 0.28, y + s * 0.13)
    ctx.move_to(x + s * 0.16, y)
    ctx.line_to(x + s * 0.16, y + s * 0.1)
    ctx.stroke()


ICONS = {
    "battery": battery, "candle": candle, "matches": matches, "flashlight": torch_icon,
    "can": can, "bottle": bottle, "water": bottle, "soup": can, "key": key,
}


def icon(ctx, name, x, y, s, alpha=1.0, t=0.0):
    fn = ICONS.get(name, battery)
    if fn is candle:
        fn(ctx, x, y, s, alpha, t)
    else:
        fn(ctx, x, y, s, alpha)


# ------------------------------------------------------------------ bigger things

def radio(ctx, cx, cy, w, t=0.0, on=0.0, knob_turn=0.0, level=0.0):
    """A chunky orange emergency radio. `on` 0..1 lights the dial."""
    h = w * 0.62
    x, y = cx - w / 2, cy - h / 2
    # handle + antenna
    stroke_line(ctx, [(cx - w * 0.28, y + 6), (cx - w * 0.22, y - h * 0.22), (cx + w * 0.22, y - h * 0.22),
                      (cx + w * 0.28, y + 6)], w * 0.03, "#141414")
    stroke_line(ctx, [(cx + w * 0.36, y + 4), (cx + w * 0.52, y - h * 0.9)], w * 0.012, "#2a2a2a")
    glow(ctx, x + w / 2, y + h / 2, w * 0.75, "#ff8a1f", 0.12 + 0.12 * on)
    rounded_rect(ctx, x, y, w, h, w * 0.07)
    set_color(ctx, "#ff8a1f")
    ctx.fill()
    rounded_rect(ctx, x + w * 0.025, y + w * 0.025, w * 0.95, h - w * 0.05, w * 0.055)
    set_color(ctx, "#1c1c1e")
    ctx.fill()
    # speaker grille
    for r in range(6):
        for c in range(7):
            gx = x + w * 0.1 + c * w * 0.055
            gy = y + h * 0.2 + r * h * 0.115
            ctx.arc(gx, gy, w * 0.012, 0, 2 * math.pi)
            set_color(ctx, "#3a3a3e")
            ctx.fill()
    # dial window
    dx, dy, dw, dh = x + w * 0.56, y + h * 0.14, w * 0.34, h * 0.3
    rounded_rect(ctx, dx, dy, dw, dh, w * 0.02)
    lit = rgb("#ffd25a")
    off = rgb("#3b2f1f")
    ctx.set_source_rgb(*[o + (l - o) * on for o, l in zip(off, lit)])
    ctx.fill()
    if on > 0:
        glow(ctx, dx + dw / 2, dy + dh / 2, dw * 0.9, "#ffd25a", 0.35 * on)
    for k in range(9):
        lx = dx + dw * (0.1 + k * 0.1)
        ctx.move_to(lx, dy + dh * 0.15)
        ctx.line_to(lx, dy + dh * (0.4 if k % 2 else 0.55))
    set_color(ctx, "#6b4a1a")
    ctx.set_line_width(2)
    ctx.stroke()
    nx = dx + dw * (0.25 + 0.45 * on + 0.03 * math.sin(t * 3) * on)
    stroke_line(ctx, [(nx, dy + dh * 0.08), (nx, dy + dh * 0.92)], 4, "#d0021b")
    # knobs
    for k, kx in enumerate((dx + dw * 0.22, dx + dw * 0.72)):
        ky = y + h * 0.66
        set_color(ctx, "#4a4a4f")
        ctx.arc(kx, ky, w * 0.055, 0, 2 * math.pi)
        ctx.fill()
        a = -math.pi / 2 + (knob_turn * 2.2 if k == 1 else 0.6)
        stroke_line(ctx, [(kx, ky), (kx + math.cos(a) * w * 0.045, ky + math.sin(a) * w * 0.045)], 5, "#eeeeee")
        if k == 1:
            set_color(ctx, "#ff8a1f")
            ctx.arc(kx, ky, w * 0.018, 0, 2 * math.pi)
            ctx.fill()
    # signal bars
    for k in range(8):
        bx = x + w * 0.56 + k * w * 0.035
        by = y + h * 0.86
        on_bar = on > 0 and (k / 8) < level
        ctx.rectangle(bx, by - h * 0.045, w * 0.022, h * 0.045)
        set_color(ctx, "#39d353" if on_bar else "#2a3a2c")
        ctx.fill()


def wall_clock(ctx, x, y, r, hours: float, minutes: float, alpha=1.0, dark=False):
    set_color(ctx, "#2b2b2b", alpha)
    ctx.arc(x, y, r + r * 0.12, 0, 2 * math.pi)
    ctx.fill()
    set_color(ctx, "#d9d4c8" if not dark else "#8d897f", alpha)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    for k in range(12):
        a = k * math.pi / 6
        stroke_line(ctx, [(x + math.cos(a) * r * 0.78, y + math.sin(a) * r * 0.78),
                          (x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9)], r * 0.05, "#333333", alpha)
    ha = (hours % 12 + minutes / 60) / 12 * 2 * math.pi - math.pi / 2
    ma = minutes / 60 * 2 * math.pi - math.pi / 2
    stroke_line(ctx, [(x, y), (x + math.cos(ha) * r * 0.5, y + math.sin(ha) * r * 0.5)], r * 0.09, "#222222", alpha)
    stroke_line(ctx, [(x, y), (x + math.cos(ma) * r * 0.75, y + math.sin(ma) * r * 0.75)], r * 0.06, "#222222", alpha)
    set_color(ctx, "#c0392b", alpha)
    ctx.arc(x, y, r * 0.07, 0, 2 * math.pi)
    ctx.fill()


def alarm_clock(ctx, x, y, r, hours, minutes, t=0.0, ringing=0.0):
    shake = math.sin(t * 60) * 0.06 * ringing
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(shake)
    for sx in (-1, 1):
        set_color(ctx, "#e74c3c")
        ctx.arc(sx * r * 0.62, -r * 0.88, r * 0.32, math.pi, 2 * math.pi)
        ctx.fill()
    stroke_line(ctx, [(-r * 0.6, r * 0.85), (-r * 0.8, r * 1.15)], r * 0.1, "#333333")
    stroke_line(ctx, [(r * 0.6, r * 0.85), (r * 0.8, r * 1.15)], r * 0.1, "#333333")
    set_color(ctx, "#e74c3c")
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()
    wall_clock(ctx, x, y, r * 0.8, hours, minutes)


def phone(ctx, x, y, s, t=0.0, screen="NO SIGNAL", lit=1.0):
    w, h = s * 0.5, s
    rounded_rect(ctx, x - w / 2, y - h / 2, w, h, w * 0.14)
    set_color(ctx, "#121212")
    ctx.fill()
    rounded_rect(ctx, x - w / 2 + 8, y - h / 2 + 8, w - 16, h - 16, w * 0.1)
    c = rgb("#1f3a5f")
    ctx.set_source_rgb(*(v * (0.3 + 0.7 * lit) for v in c))
    ctx.fill()
    if lit > 0:
        glow(ctx, x, y, s * 0.8, "#4a90e2", 0.18 * lit)


# ------------------------------------------------------------------ furniture

def bookshelf(ctx, x, y, w, h, alpha=1.0, seed=0):
    ctx.rectangle(x, y, w, h)
    set_color(ctx, "#4a2f1d", alpha)
    ctx.fill()
    shelves = 4
    colors = ["#8e3b2f", "#2f5d62", "#c49b3d", "#5b4a7a", "#3d6b3d", "#a0522d", "#2c3e50"]
    for s in range(shelves):
        sy = y + h * (s + 1) / (shelves + 0.3)
        ctx.rectangle(x, sy, w, h * 0.03)
        set_color(ctx, "#2e1c11", alpha)
        ctx.fill()
        bx = x + w * 0.06
        k = s * 7 + seed
        while bx < x + w * 0.9:
            bw = w * (0.05 + 0.04 * ((k * 37) % 5) / 4)
            bh = h / (shelves + 0.3) * (0.55 + 0.35 * ((k * 53) % 7) / 6)
            ctx.rectangle(bx, sy - bh, bw, bh)
            set_color(ctx, colors[k % len(colors)], alpha)
            ctx.fill()
            bx += bw + w * 0.01
            k += 1


def couch(ctx, x, y, w, h, alpha=1.0, color="#2d4a5a"):
    rounded_rect(ctx, x, y + h * 0.15, w, h * 0.85, h * 0.18)
    set_color(ctx, color, alpha)
    ctx.fill()
    rounded_rect(ctx, x + w * 0.08, y, w * 0.84, h * 0.55, h * 0.15)
    set_color(ctx, color, alpha)
    ctx.fill()
    ctx.set_source_rgba(0, 0, 0, 0.18 * alpha)
    rounded_rect(ctx, x + w * 0.08, y + h * 0.48, w * 0.84, h * 0.12, 6)
    ctx.fill()
    for ax in (x, x + w - w * 0.1):
        rounded_rect(ctx, ax, y + h * 0.25, w * 0.1, h * 0.75, h * 0.1)
        ctx.set_source_rgba(*rgb(color), alpha)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.15 * alpha)
        rounded_rect(ctx, ax, y + h * 0.25, w * 0.1, h * 0.75, h * 0.1)
        ctx.fill()
    rounded_rect(ctx, x + w * 0.55, y + h * 0.18, w * 0.16, h * 0.3, 10)
    set_color(ctx, "#d9822b", alpha)
    ctx.fill()


def floor_lamp(ctx, x, top, bottom, on=0.0, alpha=1.0):
    stroke_line(ctx, [(x, top + 40), (x, bottom)], 7, "#222222", alpha)
    ctx.rectangle(x - 34, bottom - 8, 68, 8)
    set_color(ctx, "#222222", alpha)
    ctx.fill()
    ctx.move_to(x - 42, top + 60)
    ctx.line_to(x + 42, top + 60)
    ctx.line_to(x + 26, top)
    ctx.line_to(x - 26, top)
    ctx.close_path()
    set_color(ctx, "#e8dcc0" if on else "#8a8070", alpha)
    ctx.fill()
    if on:
        glow(ctx, x, top + 50, 260, "#ffd89a", 0.35 * on)


def door(ctx, x, y, w, h, alpha=1.0, color="#6b3f22", open_amount=0.0, dark=False):
    ctx.rectangle(x - 10, y - 10, w + 20, h + 10)
    set_color(ctx, "#3b2414", alpha)
    ctx.fill()
    if open_amount > 0:
        ctx.rectangle(x, y, w, h)
        set_color(ctx, "#050505", alpha)
        ctx.fill()
    dw = w * (1 - open_amount * 0.8)
    ctx.rectangle(x, y, dw, h)
    set_color(ctx, color, alpha)
    ctx.fill()
    for py in (0.08, 0.55):
        ctx.rectangle(x + dw * 0.14, y + h * py, dw * 0.72, h * 0.36)
        ctx.set_source_rgba(0, 0, 0, 0.16 * alpha)
        ctx.fill()
    set_color(ctx, "#d4ac0d", alpha)
    ctx.arc(x + dw * 0.85, y + h * 0.52, w * 0.045, 0, 2 * math.pi)
    ctx.fill()
    set_color(ctx, "#111111", alpha)
    ctx.arc(x + dw * 0.5, y + h * 0.3, w * 0.025, 0, 2 * math.pi)
    ctx.fill()


def window(ctx, x, y, w, h, t=0.0, moon=True, alpha=1.0, city_lights=0.0):
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *rgb("#0b1530"))
    g.add_color_stop_rgb(1, *rgb("#1c2440"))
    ctx.set_source(g)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    if moon:
        glow(ctx, x + w * 0.72, y + h * 0.25, w * 0.35, "#dfe7ff", 0.25)
        set_color(ctx, "#e8ecf5")
        ctx.arc(x + w * 0.72, y + h * 0.25, w * 0.07, 0, 2 * math.pi)
        ctx.fill()
    bx = x
    k = 0
    while bx < x + w:
        bw = w * (0.12 + 0.08 * ((k * 31) % 4) / 3)
        bh = h * (0.3 + 0.4 * ((k * 17) % 5) / 4)
        ctx.rectangle(bx, y + h - bh, bw, bh)
        set_color(ctx, "#070a14")
        ctx.fill()
        if city_lights > 0:
            for r in range(4):
                for c in range(2):
                    if (k + r * 3 + c) % 3 == 0:
                        ctx.rectangle(bx + bw * (0.2 + c * 0.4), y + h - bh + bh * (0.15 + r * 0.2), bw * 0.18, bh * 0.08)
                        set_color(ctx, "#ffd36a", city_lights)
                        ctx.fill()
        bx += bw + 3
        k += 1
    # frame + cross bars
    set_color(ctx, "#e9e2d0", alpha)
    ctx.set_line_width(14)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    ctx.set_line_width(8)
    ctx.move_to(x + w / 2, y)
    ctx.line_to(x + w / 2, y + h)
    ctx.move_to(x, y + h / 2)
    ctx.line_to(x + w, y + h / 2)
    ctx.stroke()
