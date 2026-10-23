"""Everything drawn on top of the scene: the day/clock counter, word-by-word
captions, rule cards, the end-of-episode question and the end card."""

from __future__ import annotations

import math
import re

from . import gfx
from .gfx import H, LIME, RED, TEAL, W, WHITE, back_out, draw_surface, ease_out, pill, ramp, set_color, text

STOP = set("""a an the and or but if of to in on at by for with from up as is are was were be been
it its this that these those you your i me my we our he she him her his they them their there here so than
then just not no do does did into out over all""".split())

CAPTION_Y = 1215
CAPTION_SIZE = 64


# ------------------------------------------------------------------ captions

def _clean(word: str) -> str:
    w = word.upper()
    keep = "..." if w.endswith("...") or w.endswith("…") else ("?" if w.endswith("?") else "")
    w = re.sub(r"[.,;:!?…\"“”]+$", "", w).strip("\"“”")
    return w + keep


def chunks(words, max_words: int = 3, max_chars: int = 18):
    """Group words into 1-3 word captions that break at punctuation."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or sum(len(x.text) + 1 for x in cur) + len(w.text) > max_chars
                    or w.style != cur[-1].style):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,;:…]$", w.text):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _highlight(chunk) -> int:
    best, best_len = -1, 0
    for i, w in enumerate(chunk):
        bare = re.sub(r"[^\w']", "", w.text.lower())
        if bare in STOP or not bare:
            continue
        if len(bare) >= best_len:
            best, best_len = i, len(bare)
    return best


def caption_plan(shots):
    plan = []
    words = [w for s in shots for w in s.words]
    groups = chunks(words)
    for i, g in enumerate(groups):
        start = g[0].start
        nxt = groups[i + 1][0].start if i + 1 < len(groups) else g[-1].end + 0.8
        end = min(nxt, g[-1].end + 1.1)
        plan.append((start, end, g, _highlight(g)))
    return plan


def draw_caption(ctx, chunk, hl: int, age: float, alpha: float = 1.0):
    radio = chunk[0].style == "radio"
    pieces = []
    for i, w in enumerate(chunk):
        word = _clean(w.text)
        if not word:
            continue
        col = (TEAL if radio else LIME) if i == hl else WHITE
        if radio and i != hl:
            col = "#dff7f2"
        s = text(word, "caption", CAPTION_SIZE, col, stroke=7, stroke_color="#101010", shadow=6)
        pieces.append(s)
    if not pieces:
        return
    space = 14
    widths = [p.get_width() - 2 * (7 + 12 + 4) for p in pieces]  # strip text padding
    total = sum(widths) + space * (len(pieces) - 1)
    scale = back_out(age / 0.16, 2.2) * 0.18 + 0.82 if age < 0.16 else 1.0
    scale = min(scale, 1.0 if total < W * 0.86 else W * 0.86 / total)
    a = alpha * gfx.clamp(age / 0.06)
    x = W / 2 - total * scale / 2
    y = CAPTION_Y + 14 * (1 - ease_out(age / 0.22))
    for p, w in zip(pieces, widths):
        draw_surface(ctx, p, x + w * scale / 2, y, scale, a)
        x += (w + space) * scale


# ------------------------------------------------------------------ HUD

def dl(cv) -> str:
    """What the counter counts: DAY (default) or e.g. NIGHT."""
    return str(cv.item.get("day_label", "DAY")).upper()


def draw_hud(cv, shot, t):
    from .episode import format_time
    item = cv.item
    ctx = cv.ctx
    day = shot.get("day", item.get("day", 1))
    x0, y0 = 62, 150
    blink = 0.55 + 0.45 * (math.sin(cv.frame / gfx.FPS * 4) > 0)
    gfx.glow(ctx, x0 + 8, y0, 18, RED, 0.35 * blink)
    set_color(ctx, RED, blink)
    ctx.arc(x0 + 8, y0, 7, 0, 2 * math.pi)
    ctx.fill()
    draw_surface(ctx, text(f"{dl(cv)} {day}", "mono", 24, "#d8d4cc", tracking=4), x0 + 26, y0, anchor="l")
    hm, ap = format_time(shot.minutes_at(t))
    big = text(hm, "mono", 66, "#f2efe8", shadow=3)
    draw_surface(ctx, big, x0 - 8, y0 + 62, anchor="l")
    tw = gfx.text_width(hm, "mono", 66)
    draw_surface(ctx, text(ap, "mono", 22, "#bdb8ae"), x0 + tw + 4, y0 + 74, anchor="l")
    place = shot.get("place") or cv.state.get("place") or item.get("place", "")
    if place:
        draw_surface(ctx, text(str(place).upper(), "mono_light", 21, "#a8a39a", tracking=3), x0 - 4, y0 + 118, anchor="l")
    set_color(ctx, "#ffffff", 0.25)
    ctx.rectangle(x0, y0 + 140, 300, 2)
    ctx.fill()
    light = shot.get("light")
    if light is not None:
        if isinstance(light, (list, tuple)):
            a, b = light
            p = gfx.clamp(t / max(shot.dur, 0.01))
            light = a + (b - a) * p
        level = gfx.clamp(float(light) / 100)
        col = "#39d353" if level > 0.5 else ("#ffd34d" if level > 0.2 else RED)
        if level <= 0.2 and math.sin(cv.frame / gfx.FPS * 9) < 0:
            col = "#5a1a16"
        label = str(shot.get("meter_label") or item.get("meter_label", "LIGHT")).upper()
        draw_surface(ctx, text(label, "mono", 20, "#a8a39a", tracking=3), x0 - 4, y0 + 170, anchor="l")
        bx = x0 + max(96, gfx.text_width(label, "mono", 20, 3) + 22)
        for k in range(5):
            on = level > k / 5 + 0.01
            set_color(ctx, col if on else "#3a3a3a")
            gfx.rounded_rect(ctx, bx + k * 30, y0 + 160, 24, 20, 3)
            ctx.fill()
        draw_surface(ctx, text(f"{round(level * 100)}%", "mono", 20, col), bx + 156, y0 + 170, anchor="l")


# ------------------------------------------------------------------ rule card

def draw_rule(cv, shot, t):
    rule = shot.get("rule")
    if not rule:
        return
    ctx = cv.ctx
    n, label = rule.get("n", 1), str(rule.get("text", "")).upper()
    at = shot.cue(rule.get("cue"), 0.0)
    k = t - at
    if k < 0:
        return
    big_for = float(rule.get("hold", 2.3))
    move = gfx.ease_in_out((k - big_for) / 0.45)
    pop = back_out(k / 0.28)
    # big (centre) -> small (top right)
    tag_y = 300 + (175 - 300) * move
    txt_y = 425 + (240 - 425) * move
    cx = W / 2 + (W * 0.63 - W / 2) * move
    size = 150 - (150 - 76) * move
    sc = pop
    pill(ctx, cx, tag_y, f"RULE #{n}", "caption", int(30 - 6 * move), WHITE, "#e0261b", 1.0,
         scale=sc, alpha=gfx.clamp(k / 0.1), pad_x=18, pad_y=8)
    full = gfx.text_width(label, "title", int(size))
    limit = W * (0.9 - 0.25 * move)
    if full > limit:
        size *= limit / full
        full = limit
    s = text(label, "title", int(size), "#f6f3ec", shadow=5)
    draw_surface(ctx, s, cx, txt_y, sc, gfx.clamp(k / 0.12))
    lw = full * ease_out((k - 0.15) / 0.5)
    set_color(ctx, "#e0261b")
    ctx.rectangle(cx - lw / 2, txt_y + size * 0.42, lw, max(4, size * 0.045))
    ctx.fill()


# ------------------------------------------------------------------ title / choice / end card

def draw_title(cv, shot, t):
    ctx = cv.ctx
    item = cv.item
    on = gfx.clamp(t / 0.12) * (1 if t > 0.5 else gfx.flicker(t, 3, 22))
    series = str(item.get("series", "")).upper()
    day = shot.get("day", item.get("day", 1))
    sc = 1.0 + 0.04 * gfx.ease_out(t / max(shot.dur, 0.1))
    draw_surface(ctx, text(series, "title", 190, "#f4f1ea", glow_color="#ffffff", glow_radius=10), W / 2, 800, sc, on)
    ap = gfx.clamp((t - 0.5) / 0.15) * (1 if t > 0.9 else gfx.flicker(t, 5, 25))
    draw_surface(ctx, text(f"{dl(cv)} {day}", "title", 140, "#ff4436", glow_color=RED, glow_radius=12), W / 2, 960, sc, ap)
    lw = 330 * ease_out((t - 0.6) / 0.4)
    set_color(ctx, RED, ap)
    ctx.rectangle(W / 2 - lw / 2, 1040, lw, 6)
    ctx.fill()


def draw_choice(cv, shot, t):
    ctx = cv.ctx
    q = str(shot.get("question", "")).upper()
    k = t - shot.cue(shot.get("question_cue"), 0.0)
    if q and k >= 0:
        size = min(128, int(128 * (W - 100) / max(gfx.text_width(q, "title", 128), 1)))  # long questions shrink to fit
        draw_surface(ctx, text(q, "title", size, "#f6f3ec", shadow=6), W / 2, 430, back_out(k / 0.3) * 0.15 + 0.85,
                     gfx.clamp(k / 0.15))
    opts = shot.get("options") or []
    colors = [("#1d6b2e", "#4cd964"), ("#7d1717", "#ff5a4f")]
    for i, o in enumerate(opts):
        label = str(o.get("text", "")).upper()
        k = t - shot.cue(o.get("cue"), 0.4 + i * 0.6)
        if k < 0:
            continue
        bg, border = colors[i % 2]
        x = W / 2 + (-170 if i == 0 else 170) * (1 if len(opts) > 1 else 0)
        pill(ctx, x, 560, label, "caption", 42, WHITE, bg, 0.95, border=border, scale=back_out(k / 0.25),
             alpha=gfx.clamp(k / 0.1), pad_x=40, pad_y=16)
    if opts:
        k = t - shot.cue(opts[-1].get("cue"), 1.0) - 0.4
        if k > 0:
            a = gfx.clamp(k / 0.3)
            draw_surface(ctx, text("COMMENT BELOW", "mono", 24, "#e8e4dc", tracking=4), W / 2, 645, alpha=a)
            y = 680 + 8 * math.sin(t * 5)
            set_color(ctx, "#e8e4dc", a)
            ctx.move_to(W / 2 - 12, y)
            ctx.line_to(W / 2 + 12, y)
            ctx.line_to(W / 2, y + 14)
            ctx.close_path()
            ctx.fill()


def draw_endcard(cv, shot, t):
    ctx = cv.ctx
    item = cv.item
    day = shot.get("day", item.get("day", 1))
    switch = shot.dur - 0.95
    a = gfx.clamp(t / 0.3)
    series = str(item.get("series", "")).upper()
    draw_surface(ctx, text(series, "title", 92, "#ece8e0", glow_color="#ffffff", glow_radius=5), W / 2, 560, alpha=a)
    from .episode import format_time
    hm, ap = format_time(shot.minutes_at(t))
    final = bool(shot.get("final"))
    if final:
        switch = 1e9
    if t < switch:
        draw_surface(ctx, text(f"{dl(cv)} {day}", "title", 230, "#f6f3ec", glow_color="#ffffff", glow_radius=10), W / 2, 720, alpha=a)
        if final:
            k = t - 0.9
            if k > 0:
                f = 1 if k > 0.35 else gfx.flicker(k, 4, 30)
                draw_surface(ctx, text("THE END?", "title", 120, "#ff4436", glow_color=RED, glow_radius=10), W / 2, 1040, 1, f)
    else:
        k = t - switch
        f = 1 if k > 0.35 else gfx.flicker(k, 9, 30)
        draw_surface(ctx, text(f"{dl(cv)} {day + 1}", "title", 230, "#ff4436", glow_color=RED, glow_radius=14),
                     W / 2, 720, 1 + 0.06 * (1 - ease_out(k / 0.3)), f)
    draw_surface(ctx, text(f"{hm} {ap}", "mono", 30, "#cfcac0", tracking=3), W / 2, 850, alpha=a)
    label = "FOLLOW FOR A NEW STORY" if final else f"FOLLOW FOR {dl(cv)} {day + 1}"
    pill(ctx, W / 2, 935, label, "caption", 26, WHITE, "#2a0d0b", 0.9, border="#c0392b",
         scale=back_out((t - 0.4) / 0.3), alpha=gfx.clamp((t - 0.4) / 0.15), pad_x=26, pad_y=12)


# ------------------------------------------------------------------ main entry

def paint(cv, shot, t: float, now: float) -> None:
    ctx = cv.ctx
    sc = shot.scene
    if sc not in ("title", "endcard") and not shot.get("no_hud"):
        draw_hud(cv, shot, t)
    if sc == "title":
        draw_title(cv, shot, t)
    elif sc == "choice":
        draw_choice(cv, shot, t)
    elif sc == "endcard":
        draw_endcard(cv, shot, t)
    draw_rule(cv, shot, t)
    if shot.get("recap"):
        a = gfx.clamp(t / 0.25) * gfx.clamp((shot.dur - t) / 0.25)
        pill(ctx, W / 2, 470, "PREVIOUSLY", "mono", 24, "#f2efe8", "#000000", 0.6, border="#8a8478",
             alpha=a, pad_x=18, pad_y=8, tracking=4)
    chip = shot.get("chip")
    if chip:
        k = t - shot.cue(chip.get("cue"), 0.5)
        if k >= 0:
            pill(ctx, W / 2, float(chip.get("y", 520)), str(chip.get("text", "")).upper(), "caption", 28, "#0b1e1b",
                 TEAL, 0.95, scale=back_out(k / 0.25), alpha=gfx.clamp(k / 0.1), pad_x=22, pad_y=10)
    # radio label while the radio speaks
    for a, b, style in shot.voice_spans:
        if style == "radio" and a - 0.2 <= now <= b + 0.3:
            label = str(shot.get("radio_label", "EMERGENCY BROADCAST · RADIO")).upper()
            pill(ctx, W / 2, CAPTION_Y - 78, label, "bold", 20, TEAL, "#06201c", 0.85,
                 border="#2a8f80", pad_x=16, pad_y=7, tracking=2)
            break
    if not hasattr(cv, "captions"):
        cv.captions = caption_plan(cv.shots)
    for start, end, chunk, hl in cv.captions:
        if start <= now < end:
            fade = gfx.clamp((end - now) / 0.12)
            draw_caption(ctx, chunk, hl, now - start, fade)
            break
