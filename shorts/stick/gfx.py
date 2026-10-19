"""Drawing helpers for stickman stories: colours, easing, text, lights.

Shapes are drawn with cairo (smooth, anti-aliased vector graphics). Text is
rasterised with Pillow from the bundled fonts and cached as cairo surfaces.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets" / "fonts"

W, H, FPS = 1080, 1920, 30

FONT_FILES = {
    "title": "BebasNeue-Regular.ttf",
    "caption": "Montserrat-Black.ttf",
    "bold": "Montserrat-ExtraBold.ttf",
    "mono": "JetBrainsMono-Bold.ttf",
    "mono_light": "JetBrainsMono-Regular.ttf",
}

LIME = "#c8f135"
TEAL = "#5fe8cf"
RED = "#ff3b30"
WHITE = "#f4f1ea"
INK = "#161616"


# ---------------------------------------------------------------- basics

def rgb(color: str | tuple) -> tuple[float, float, float]:
    if isinstance(color, tuple):
        return tuple(c / 255 if c > 1 else c for c in color[:3])
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def set_color(ctx: cairo.Context, color, alpha: float = 1.0) -> None:
    r, g, b = rgb(color)
    ctx.set_source_rgba(r, g, b, alpha)


def mix(a, b, t: float) -> tuple[float, float, float]:
    a, b = rgb(a), rgb(b)
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def ease_out(x: float) -> float:
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def back_out(x: float, s: float = 1.7) -> float:
    """Overshoots a little, then settles: for things that pop in."""
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ramp(t: float, start: float, dur: float) -> float:
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def noise(t: float, seed: float = 0.0) -> float:
    """Smooth pseudo-random wobble in [-1, 1]."""
    return (math.sin(t * 1.7 + seed * 13.1) * 0.5 + math.sin(t * 3.9 + seed * 7.3) * 0.3
            + math.sin(t * 7.3 + seed * 3.7) * 0.2)


def flicker(t: float, seed: float = 0.0, rate: float = 14.0) -> float:
    """1 or a dim value, changing irregularly: a failing light."""
    k = math.floor(t * rate)
    h = math.sin(k * 12.9898 + seed * 78.233) * 43758.5453
    v = h - math.floor(h)
    return 1.0 if v > 0.45 else 0.15 + v


def rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def glow(ctx: cairo.Context, x: float, y: float, r: float, color, alpha: float = 1.0) -> None:
    """A soft round light."""
    if r <= 0 or alpha <= 0:
        return
    c = rgb(color)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *c, alpha)
    g.add_color_stop_rgba(0.35, *c, alpha * 0.45)
    g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def vgradient(ctx: cairo.Context, x, y, w, h, top, bottom) -> None:
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *rgb(top))
    g.add_color_stop_rgb(1, *rgb(bottom))
    ctx.set_source(g)
    ctx.rectangle(x, y, w, h)
    ctx.fill()


def stroke_line(ctx, pts, width, color, alpha=1.0, outline=None, outline_extra=6):
    """A thick round-capped line, optionally with a darker outline under it."""
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    passes = [(width + outline_extra, outline)] if outline else []
    passes.append((width, color))
    for w, col in passes:
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_line_width(w)
        set_color(ctx, col, alpha)
        ctx.stroke()


# ---------------------------------------------------------------- text

@lru_cache(maxsize=None)
def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / FONT_FILES[kind]), size)


def pil_to_surface(img: Image.Image) -> cairo.ImageSurface:
    a = np.asarray(img.convert("RGBA"), dtype=np.uint16)
    alpha = a[..., 3]
    pre = (a[..., :3] * alpha[..., None] + 127) // 255
    h, w = alpha.shape
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride), np.uint8)
    view = buf[:, : w * 4].reshape(h, w, 4)
    view[..., 0] = pre[..., 2]
    view[..., 1] = pre[..., 1]
    view[..., 2] = pre[..., 0]
    view[..., 3] = alpha
    surf = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, w, h, stride)
    _KEEP.append(buf)  # cairo doesn't own the memory
    return surf


_KEEP: list = []


@lru_cache(maxsize=4096)
def text(s: str, kind: str, size: int, color: str = WHITE, stroke: int = 0,
         stroke_color: str = "#000000", shadow: int = 0, glow_color: str | None = None,
         glow_radius: int = 0, tracking: int = 0) -> cairo.ImageSurface:
    """Render one line of text to a cached surface (centre it with draw_surface)."""
    f = font(kind, size)
    pad = stroke + max(shadow * 2, glow_radius * 3) + 4
    widths = [f.getlength(ch) for ch in s] if tracking else None
    width = (sum(widths) + tracking * max(len(s) - 1, 0)) if tracking else f.getlength(s)
    asc, desc = f.getmetrics()
    w = int(width + pad * 2 + 2)
    h = int(asc + desc + pad * 2 + 2)

    def draw_text(d: ImageDraw.ImageDraw, fill, sw=0, sf=None, dx=0, dy=0):
        if tracking:
            x = pad + dx
            for ch, cw in zip(s, widths):
                d.text((x, pad + dy), ch, font=f, fill=fill, stroke_width=sw, stroke_fill=sf)
                x += cw + tracking
        else:
            d.text((pad + dx, pad + dy), s, font=f, fill=fill, stroke_width=sw, stroke_fill=sf)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if glow_color and glow_radius:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_text(ImageDraw.Draw(g), glow_color, max(stroke, 2), glow_color)
        g = g.filter(ImageFilter.GaussianBlur(glow_radius))
        img = Image.alpha_composite(img, g)
        img = Image.alpha_composite(img, g.filter(ImageFilter.GaussianBlur(glow_radius * 2)))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_text(ImageDraw.Draw(sh), (0, 0, 0, 200), stroke, (0, 0, 0, 200), dy=shadow)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow * 0.8))
        img = Image.alpha_composite(img, sh)
    top = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_text(ImageDraw.Draw(top), color, stroke, stroke_color if stroke else None)
    img = Image.alpha_composite(img, top)
    return pil_to_surface(img)


def draw_surface(ctx: cairo.Context, surf: cairo.ImageSurface, x: float, y: float,
                 scale: float = 1.0, alpha: float = 1.0, anchor: str = "c") -> None:
    """Paint a surface with its centre (anchor c), left edge (l) or right edge (r) at x."""
    w, h = surf.get_width(), surf.get_height()
    if alpha <= 0 or scale <= 0:
        return
    ox = {"c": -w / 2, "l": 0, "r": -w}[anchor]
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    ctx.set_source_surface(surf, ox, -h / 2)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def text_width(s: str, kind: str, size: int, tracking: int = 0) -> float:
    f = font(kind, size)
    if tracking:
        return sum(f.getlength(ch) for ch in s) + tracking * max(len(s) - 1, 0)
    return f.getlength(s)


def pill(ctx, x, y, label, kind="bold", size=26, fg=WHITE, bg="#000000", bg_alpha=0.75,
         border=None, scale=1.0, alpha=1.0, pad_x=22, pad_y=10, tracking=0):
    """A rounded label centred at (x, y)."""
    if alpha <= 0:
        return
    s = text(label, kind, size, fg, tracking=tracking)
    tw = text_width(label, kind, size, tracking)
    w = tw + pad_x * 2
    h = size + pad_y * 2
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    rounded_rect(ctx, -w / 2, -h / 2, w, h, h / 2)
    set_color(ctx, bg, bg_alpha * alpha)
    ctx.fill_preserve()
    if border:
        set_color(ctx, border, alpha)
        ctx.set_line_width(3)
        ctx.stroke()
    else:
        ctx.new_path()
    draw_surface(ctx, s, 0, 1, alpha=alpha)
    ctx.restore()


# ---------------------------------------------------------------- lighting

class Darkness:
    """Darken the whole frame except where lights shine.

    Usage: d = Darkness(); d.begin(matrix, 0.9); d.radial(...); d.cone(...); d.apply(ctx)
    """

    SCALE = 0.5  # the mask is soft, so half resolution looks the same and is 4x faster

    def __init__(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(W * self.SCALE), int(H * self.SCALE))
        self.ctx = cairo.Context(self.surface)

    def begin(self, matrix: cairo.Matrix, alpha: float, color: str = "#020308") -> None:
        c = self.ctx
        c.identity_matrix()
        c.set_operator(cairo.OPERATOR_SOURCE)
        set_color(c, color, alpha)
        c.paint()
        c.set_operator(cairo.OPERATOR_DEST_OUT)
        c.set_matrix(matrix.multiply(cairo.Matrix(self.SCALE, 0, 0, self.SCALE, 0, 0)))

    def radial(self, x, y, r, strength=1.0, sx=1.0, sy=1.0) -> None:
        c = self.ctx
        c.save()
        c.translate(x, y)
        c.scale(sx, sy)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
        g.add_color_stop_rgba(0, 0, 0, 0, strength)
        g.add_color_stop_rgba(0.55, 0, 0, 0, strength * 0.6)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.set_source(g)
        c.arc(0, 0, r, 0, 2 * math.pi)
        c.fill()
        c.restore()

    def cone(self, x, y, angle, length, spread, strength=1.0) -> None:
        """A flashlight beam from (x, y) pointing at `angle` (radians, 0 = right)."""
        c = self.ctx
        for k, (sp, st) in enumerate(((spread * 1.35, 0.35), (spread, 0.75), (spread * 0.6, 0.5))):
            g = cairo.RadialGradient(x, y, 0, x, y, length)
            g.add_color_stop_rgba(0, 0, 0, 0, strength * st)
            g.add_color_stop_rgba(0.6, 0, 0, 0, strength * st * 0.7)
            g.add_color_stop_rgba(1, 0, 0, 0, 0)
            c.set_source(g)
            c.move_to(x, y)
            c.arc(x, y, length, angle - sp, angle + sp)
            c.close_path()
            c.fill()

    def apply(self, ctx: cairo.Context) -> None:
        ctx.save()
        ctx.identity_matrix()
        ctx.scale(1 / self.SCALE, 1 / self.SCALE)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
        ctx.paint()
        ctx.restore()


def beam_tint(ctx, x, y, angle, length, spread, alpha=0.10, color="#fff1c4") -> None:
    """Warm glow inside a flashlight beam (painted after the darkness)."""
    g = cairo.RadialGradient(x, y, 0, x, y, length)
    c = rgb(color)
    g.add_color_stop_rgba(0, *c, alpha)
    g.add_color_stop_rgba(1, *c, 0)
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    ctx.set_source(g)
    ctx.move_to(x, y)
    ctx.arc(x, y, length, angle - spread, angle + spread)
    ctx.close_path()
    ctx.fill()
    ctx.restore()


def eyes(ctx, x, y, size=6.0, alpha=1.0, color="#f2f6ff", gap=None) -> None:
    """Two glowing eyes in the dark."""
    if alpha <= 0:
        return
    gap = gap or size * 2.6
    for dx in (-gap / 2, gap / 2):
        glow(ctx, x + dx, y, size * 5, color, 0.25 * alpha)
        set_color(ctx, color, alpha)
        ctx.arc(x + dx, y, size, 0, 2 * math.pi)
        ctx.fill()


# ---------------------------------------------------------------- film look

class FilmLook:
    """Vignette and a little grain, painted over every frame (pre-mixed into a
    few full-frame images so it costs one paint per frame)."""

    def __init__(self, seed: int = 1):
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (H * 0.72)) ** 2 + ((yy - H * 0.45) / (H * 0.72)) ** 2)
        vig = np.clip((d - 0.35 * W / (H * 0.72)) / (1 - 0.35 * W / (H * 0.72)), 0, 1) * 0.45
        self.frames = []
        for _ in range(4):
            n = rng.random((H // 3, W // 3), dtype=np.float32)
            n = np.repeat(np.repeat(n, 3, 0), 3, 1)[:H, :W]
            grain = (n - 0.5) * 0.05
            g = np.abs(grain)
            # black vignette first, then faint white/black grain on top, as one layer
            alpha = 1 - (1 - vig) * (1 - g)
            col = np.where(grain > 0, g / np.maximum(alpha, 1e-6), 0.0) * 255
            img = np.dstack([col, col, col, alpha * 255]).astype(np.uint8)
            self.frames.append(pil_to_surface(Image.fromarray(img, "RGBA")))

    def apply(self, ctx: cairo.Context, frame: int) -> None:
        ctx.save()
        ctx.identity_matrix()
        ctx.set_source_surface(self.frames[(frame // 4) % len(self.frames)], 0, 0)
        ctx.paint()
        ctx.restore()
