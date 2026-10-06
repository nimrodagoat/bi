"""Finish the character pictures made by tools/characters.mjs:

1. draw the rest of the body under the chest (shirt, belt, trousers, or a fur
   pelt for cavemen), in the same black line-art style;
2. give the whole figure a thick outline in the character's colour, like a
   sticker, so it stands out on busy gameplay.

    python tools/sticker.py

Per character in config.yaml (all optional):
    outfit: {pants: "#4a6fa5", belt: true}   or   outfit: {pelt: true}
"""

from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUTLINE = 22  # sticker outline, pixels on the 900px pictures
INK = (17, 17, 17, 255)
LINE = 7
SHIRT, BELT, PANTS = 190, 46, 430  # heights of the new body parts


def _rows(alpha: np.ndarray) -> np.ndarray:
    return np.where(alpha.max(axis=1) > 0)[0]


def _span(alpha_row: np.ndarray) -> tuple[int, int]:
    xs = np.where(alpha_row > 128)[0]
    return int(xs.min()), int(xs.max())


def _dark_runs(px: np.ndarray, alpha_row: np.ndarray) -> list[tuple[int, int]]:
    dark = np.where((alpha_row > 128) & (px[:, :3].mean(axis=1) < 90))[0]
    runs: list[list[int]] = []
    for x in dark:
        if runs and x - runs[-1][1] <= 2:
            runs[-1][1] = int(x)
        else:
            runs.append([int(x), int(x)])
    return [(a, b) for a, b in runs]


def _shade(hex_color: str) -> tuple[int, int, int, int]:
    """A darker version of a colour, for folds."""
    h = hex_color.lstrip("#")
    return tuple(int(int(h[i : i + 2], 16) * 0.72) for i in (0, 2, 4)) + (255,)


def _pelt(rng, size) -> Image.Image:
    """Tan fur with dark spots."""
    w, h = size
    fur = Image.new("RGBA", size, (176, 122, 58, 255))
    d = ImageDraw.Draw(fur)
    for _ in range(int(w * h / 5000)):
        x, y = rng.integers(0, w), rng.integers(0, h)
        r = rng.integers(10, 26)
        d.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=(92, 58, 26, 255))
    for _ in range(int(w * h / 900)):  # fur strokes
        x, y = rng.integers(0, w), rng.integers(0, h)
        d.line((x, y, x + rng.integers(-6, 7), y + 14), fill=(140, 94, 42, 255), width=3)
    return fur


def add_body(img: Image.Image, outfit: dict, seed: int) -> Image.Image:
    px = np.array(img)
    alpha = px[..., 3]
    rows = _rows(alpha)
    top, bottom = int(rows.min()), int(rows.max())
    xl, xr = _span(alpha[bottom - 1])
    # The face is centred on the body; gestures stick out on one side, so the torso
    # is the part of the bottom edge that's symmetric around the face.
    hl, hr = _span(alpha[top + 140])
    centre = (hl + hr) / 2
    half = centre - xl
    tl, tr = int(centre - half), int(centre + half)
    # Continue only real clothing lines: ones that are also dark a little higher up
    # (patterns like stars or dots would otherwise turn into stripes).
    dark = (px[..., :3].mean(axis=2) < 90) & (alpha > 128)
    runs = [
        (a, b) for a, b in _dark_runs(px[bottom - 1], alpha[bottom - 1])
        if all(dark[bottom - k, max(a - 12, 0) : b + 13].any() for k in (25, 50, 80))
    ]

    rng = np.random.default_rng(seed)
    pelt = bool(outfit.get("pelt"))
    extra = SHIRT + (0 if pelt else BELT) + PANTS
    out = Image.new("RGBA", (img.width, bottom + 1 + extra))
    out.paste(img.crop((0, 0, img.width, bottom + 1)), (0, 0))
    d = ImageDraw.Draw(out)
    y0 = bottom

    if pelt:
        # One long fur tunic down to the bottom, with a jagged hem halfway.
        y1 = y0 + extra
        d.polygon([(xl, y0), (xr, y0), (xr - 14, y1), (xl + 14, y1)], fill=(255, 255, 255, 255))
        d.line([(xl, y0), (xl + 14, y1)], fill=INK, width=LINE)
        d.line([(xr, y0), (xr - 14, y1)], fill=INK, width=LINE)
        return out

    # 1. Shirt carries on down: sides lean in a little, the existing lines continue.
    y1 = y0 + SHIRT
    inset = 18
    d.polygon([(xl, y0), (xr, y0), (xr - inset, y1), (xl + inset, y1)], fill=(255, 255, 255, 255))
    for a, b in runs:
        if a <= xl + 2 or b >= xr - 2:
            continue  # the outer edges are drawn below
        lean = (inset if (a + b) / 2 < centre else -inset) * abs((a + b) / 2 - centre) / max(half, 1)
        d.line([((a + b) / 2, y0), ((a + b) / 2 + lean * 0.3, y1)], fill=INK, width=max(LINE - 1, b - a + 1))
    d.line([(xl, y0), (xl + inset, y1)], fill=INK, width=LINE)
    d.line([(xr, y0), (xr - inset, y1)], fill=INK, width=LINE)
    # untucked shirt hem: a gentle curve
    d.arc((xl + inset, y1 - 30, xr - inset, y1 + 30), 0, 180, fill=INK, width=LINE)

    # 2. Belt with a buckle, across the torso only.
    bl, br = tl + inset + 6, tr - inset - 6
    yb = y1 + 10
    d.rectangle((bl, yb, br, yb + BELT), fill=INK)
    d.rounded_rectangle((centre - 34, yb + 6, centre + 34, yb + BELT - 6), 6, outline=(210, 210, 210, 255), width=6)
    for x in range(int(bl + 70), int(br - 40), 120):  # belt loops
        d.rectangle((x, yb - 4, x + 14, yb + BELT + 4), fill=(60, 60, 60, 255))

    # 3. Trousers: two legs, pockets, slight flare.
    color = outfit.get("pants", "#4a6fa5")
    yp, y2 = yb + BELT, yb + BELT + PANTS
    d.polygon([(bl, yp), (br, yp), (br + 10, y2), (bl - 10, y2)], fill=color, outline=INK)
    d.line([(bl, yp), (bl - 10, y2)], fill=INK, width=LINE)
    d.line([(br, yp), (br + 10, y2)], fill=INK, width=LINE)
    d.line([(centre, yp + 60), (centre, y2)], fill=INK, width=LINE)  # leg split
    d.arc((centre - 60, yp - 20, centre + 4, yp + 70), 0, 90, fill=INK, width=LINE - 2)  # fly curve
    for side in (-1, 1):  # pockets
        px0 = centre + side * (half - inset - 20)
        d.arc((px0 - 90, yp - 70, px0 + 90, yp + 90), 0 if side < 0 else 90, 90 if side < 0 else 180, fill=INK, width=LINE - 2)
    # a couple of fold lines so it doesn't look flat
    for side in (-1, 1):
        fx = centre + side * half * 0.45
        d.line([(fx, yp + 160), (fx + side * 14, yp + 260)], fill=_shade(color), width=5)
    return out


def costume(img: Image.Image, outfit: dict, seed: int) -> Image.Image:
    """Paint the clothes with fur, for cavemen. The clothes are the white area joined
    to the new tunic at the bottom; hands and face are walled off by their outlines."""
    if not outfit.get("pelt"):
        return img
    px = np.array(img)
    rows = _rows(px[..., 3])
    top, bottom = int(rows.min()), int(rows.max())
    probe = img.copy()
    marker = (255, 0, 255, 255)
    ImageDraw.floodfill(probe, (img.width // 2, bottom - 40), marker, thresh=60)
    mask = np.all(np.array(probe) == marker, axis=2)
    mask[: top + int((bottom - top) * 0.3)] = False  # never above the chin
    fur = np.array(_pelt(np.random.default_rng(seed), img.size))
    px[mask] = fur[mask]
    return Image.fromarray(px)


def sticker(img: Image.Image, color: str) -> Image.Image:
    pad = OUTLINE * 2
    canvas = Image.new("RGBA", (img.width + pad * 2, img.height + pad), (0, 0, 0, 0))
    canvas.paste(img, (pad, pad), img)
    alpha = canvas.getchannel("A").point(lambda a: 255 if a > 20 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(OUTLINE * 2 + 1)).filter(ImageFilter.GaussianBlur(1.5))
    border = Image.new("RGBA", canvas.size, color)
    border.putalpha(grown)
    border.alpha_composite(canvas)
    return border


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    for key, ch in (cfg.get("characters") or {}).items():
        outfit = ch.get("outfit") or {}
        for n, image in enumerate((ch.get("expressions") or {}).values()):
            path = ROOT / image
            img = Image.open(path).convert("RGBA")
            img = costume(add_body(img, outfit, n), outfit, n)
            sticker(img, ch.get("color", "#FFFFFF")).save(path)
            print(f"finished {image}")


if __name__ == "__main__":
    main()
