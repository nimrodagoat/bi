"""Draw the channel's profile picture (1024x1024; YouTube shows it as a circle).

    python tools/profile_picture.py  ->  assets/branding/profile.png
"""

import math
import sys
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shorts.stick import figures as F  # noqa: E402
from shorts.stick.gfx import eyes, glow, rgb, set_color, stroke_line  # noqa: E402

S = 1024


def main(out: Path) -> None:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, S, S)
    c = cairo.Context(surf)
    # background: deep night blue, brighter in the middle
    g = cairo.RadialGradient(S * 0.5, S * 0.55, 50, S * 0.5, S * 0.5, S * 0.75)
    g.add_color_stop_rgb(0, *rgb("#1c2433"))
    g.add_color_stop_rgb(1, *rgb("#05070b"))
    c.set_source(g)
    c.paint()
    # floor line
    c.rectangle(0, S * 0.8, S, S * 0.2)
    set_color(c, "#0b0d12")
    c.fill()

    # where the hero and the beam will be (solve the pose first, draw later)
    hx, ground, sc = S * 0.3, S * 0.84, 1.75
    pose = F.flashlight(0.3, aim=-0.02)
    j = F.solve(pose, hx, ground, sc, 1)
    tip = F.flashlight_tip(j, sc)
    ang = j.hand_angle

    # darkness everywhere except the beam and a soft halo round the hero
    dark = cairo.ImageSurface(cairo.FORMAT_ARGB32, S, S)
    d = cairo.Context(dark)
    d.set_source_rgba(0.01, 0.01, 0.03, 0.85)
    d.paint()
    d.set_operator(cairo.OPERATOR_DEST_OUT)
    for spread, strength in ((0.44, 0.5), (0.32, 0.9), (0.18, 0.6)):
        rg = cairo.RadialGradient(tip[0], tip[1], 0, tip[0], tip[1], S * 0.9)
        rg.add_color_stop_rgba(0, 0, 0, 0, strength)
        rg.add_color_stop_rgba(1, 0, 0, 0, 0.1)
        d.set_source(rg)
        d.move_to(*tip)
        d.arc(tip[0], tip[1], S * 0.9, ang - spread, ang + spread)
        d.close_path()
        d.fill()
    c.set_source_surface(dark, 0, 0)
    c.paint()
    wg = cairo.RadialGradient(tip[0], tip[1], 0, tip[0], tip[1], S * 0.8)
    wg.add_color_stop_rgba(0, 1, 0.95, 0.78, 0.35)
    wg.add_color_stop_rgba(1, 1, 0.95, 0.78, 0.05)
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    c.set_source(wg)
    c.move_to(*tip)
    c.arc(tip[0], tip[1], S * 0.8, ang - 0.34, ang + 0.34)
    c.close_path()
    c.fill()
    c.restore()

    # something tall caught in the beam, shielding itself
    F.draw_creature(c, F.scared(0.2), S * 0.8, ground, 1.45, -1, eye_alpha=1.0)

    # the hero, bright on top of everything
    F.draw_shadow(c, hx, ground, sc, 0.5)
    F.draw_stickman(c, pose, hx, ground, sc, 1, prop="flashlight")
    glow(c, tip[0], tip[1], 80, "#fff6d6", 0.9)

    # more of them in the dark, outside the beam
    for x, y, s in ((S * 0.14, S * 0.26, 9), (S * 0.5, S * 0.12, 7), (S * 0.9, S * 0.3, 7)):
        eyes(c, x, y, s)

    # thin red ring, like the REC dot on the counter
    c.set_line_width(14)
    set_color(c, "#e0261b", 0.9)
    c.arc(S / 2, S / 2, S / 2 - 22, 0, 2 * math.pi)
    c.stroke()

    out.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(out))
    print(out)


if __name__ == "__main__":
    main(ROOT / "assets" / "branding" / "profile.png")
