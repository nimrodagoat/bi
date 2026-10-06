"""Make a one-page design sheet of the characters (all expressions, colours,
voices) at assets/characters/design-sheet.png. Run after tools/sticker.py:

    python tools/design_sheet.py
"""

from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BLURBS = {
    "dave": "Loud, clueless and always confident. Asks the questions everyone is thinking.",
    "pip": "Calm, smug know-it-all. Has the fact, the receipts and the eye-roll.",
    "grug": "Caveman from 40,000 years ago. Baffled by coins, cards and receipts.",
    "nova": "Time traveller. Was there when money was invented, and loves to explain it.",
}

W, PAD, CARD = 2600, 70, 470


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    chars = cfg.get("characters") or {}
    big, mid, small, body = (ImageFont.truetype(FONT, s) for s in (96, 58, 32, 34))
    text = ImageFont.truetype(FONT_REGULAR, 34)
    row_h = 1000
    sheet = Image.new("RGB", (W, 260 + row_h * len(chars)), "#14161c")
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 60), "THE CAST", font=big, fill="white")
    d.text((PAD, 172), "Character design sheet", font=small, fill="#8a90a0")

    y = 260
    for key, ch in chars.items():
        color = ch.get("color", "#ffffff")
        d.rounded_rectangle((PAD - 20, y, W - PAD + 20, y + row_h - 40), 36, fill="#1d2029")
        d.text((PAD + 20, y + 30), ch.get("name", key).upper(), font=mid, fill=color)
        voice = ch.get("edge_voice") if (ch.get("engines") or ["edge"])[0] == "edge" else ch.get("kokoro_voice")
        d.text((PAD + 20, y + 110), BLURBS.get(key, ""), font=text, fill="#d6d9e0")
        d.text((PAD + 20, y + 160), f"Voice: {voice}   ·   Colour: {color.upper()}", font=text, fill="#8a90a0")
        x = PAD + 10
        for name, rel in (ch.get("expressions") or {}).items():
            pic = Image.open(ROOT / rel).convert("RGBA")
            pic.thumbnail((CARD - 20, 660))
            card = Image.new("RGBA", (CARD - 20, 680), "#2a2e3a")
            card.alpha_composite(pic, ((card.width - pic.width) // 2, card.height - pic.height))
            sheet.paste(card.convert("RGB"), (x, y + 220))
            label = name.upper()
            tw = d.textlength(label, font=body)
            d.text((x + (CARD - 20 - tw) / 2, y + 912), label, font=body, fill="white")
            x += CARD + 10
        y += row_h

    out = ROOT / "assets" / "characters" / "design-sheet.png"
    sheet.save(out)
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
