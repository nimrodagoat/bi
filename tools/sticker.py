"""Give every character picture a thick outline in the character's colour, like a
sticker, so they stand out on busy gameplay. Run after tools/characters.mjs:

    python tools/sticker.py
"""

from pathlib import Path

import yaml
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUTLINE = 22  # pixels, on the 900px source pictures


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
    # Cut the bottom flat so the torso ends in a clean line instead of a rounded blob.
    box = border.getbbox()
    border.crop((0, 0, border.width, min(box[3], pad + img.height))).save(path)


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    for key, ch in (cfg.get("characters") or {}).items():
        for image in (ch.get("expressions") or {}).values():
            sticker(ROOT / image, ch.get("color", "#FFFFFF"))
            print(f"outlined {image}")


if __name__ == "__main__":
    main()
