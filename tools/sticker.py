"""Give every character picture a thick outline in the character's colour, like a
sticker, so they stand out on busy gameplay, and continue the torso downwards so
the body reaches the bottom of the video. Run after tools/characters.mjs:

    python tools/sticker.py
"""

from pathlib import Path

import yaml
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUTLINE = 22  # pixels, on the 900px source pictures
EXTEND = 560  # how far the torso continues below the drawing, in pixels


def sticker(path: Path, color: str) -> None:
    img = Image.open(path).convert("RGBA")
    pad = OUTLINE * 2
    canvas = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    canvas.paste(img, (pad, pad), img)
    alpha = canvas.getchannel("A").point(lambda a: 255 if a > 20 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(OUTLINE * 2 + 1)).filter(ImageFilter.GaussianBlur(1.5))
    border = Image.new("RGBA", canvas.size, color)
    border.putalpha(grown)
    border.alpha_composite(canvas)
    # Cut the bottom flat, then repeat the last row of pixels downwards: the clothes,
    # their lines and the outline simply carry on to the bottom of the screen.
    box = border.getbbox()
    body = border.crop((0, 0, border.width, min(box[3], pad + img.height)))
    last = body.crop((0, body.height - 1, body.width, body.height))
    full = Image.new("RGBA", (body.width, body.height + EXTEND))
    full.paste(body, (0, 0))
    full.paste(last.resize((body.width, EXTEND)), (0, body.height))
    full.save(path)


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    for key, ch in (cfg.get("characters") or {}).items():
        for image in (ch.get("expressions") or {}).values():
            sticker(ROOT / image, ch.get("color", "#FFFFFF"))
            print(f"outlined {image}")


if __name__ == "__main__":
    main()
