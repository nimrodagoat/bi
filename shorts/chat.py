"""Text-message stories: an iMessage-style chat that fills up one message at a
time over gameplay.

Each moment of the conversation (after message 1, 2, 3, ...) is drawn as one
transparent picture; ffmpeg shows each picture for as long as that message is
being read out, so the chat "types itself" in sync with the voices.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

BLUE = (11, 132, 255, 255)
GREY = (233, 233, 235, 255)
HEADER = (246, 246, 246, 255)
LINE = (210, 210, 215, 255)
MUTED = (142, 142, 147, 255)


def messages(item: dict) -> list[tuple[str, str]]:
    """The story's messages as (sender, text), sender being "me" or "them"."""
    out = []
    for entry in item.get("messages") or []:
        if isinstance(entry, dict):
            (sender, text), = entry.items()
        else:
            sender, text = entry
        out.append((str(sender), " ".join(str(text).split())))
    return out


# Texting shorthand the voices would otherwise read letter by letter.
SPOKEN = {
    "u": "you", "ur": "your", "r": "are", "rn": "right now", "idk": "I don't know",
    "omg": "oh my god", "tbh": "to be honest", "brb": "be right back", "pls": "please",
    "plz": "please", "thx": "thanks", "ty": "thank you", "wyd": "what are you doing",
    "imo": "in my opinion", "nvm": "never mind", "ik": "I know", "bc": "because",
    "w": "with", "k": "okay", "ok": "okay", "ngl": "not gonna lie", "fr": "for real",
    "lmao": "lmao", "smh": "shaking my head", "btw": "by the way", "jk": "just kidding",
    "ily": "I love you", "wya": "where you at", "hbu": "how about you",
}


def speech(text: str) -> str:
    """How a message should be read out: expand shorthand, and read SHOUTED words
    as words (some voices spell out all-caps words letter by letter)."""
    def fix(m: re.Match) -> str:
        word = m.group(0)
        low = word.lower()
        if low in SPOKEN:
            return SPOKEN[low]
        return low if word.isupper() and len(word) > 1 else word
    return re.sub(r"[A-Za-z']+", fix, text)


class ChatPainter:
    def __init__(self, cfg: dict, contact: str):
        c = cfg.get("chat", {})
        v = cfg.get("video", {})
        self.frame_w = v.get("width", 1080)
        self.w = int(self.frame_w * c.get("width", 0.70))
        self.max_h = c.get("max_height", 900)
        self.contact = contact
        self.font = ImageFont.truetype(str(FONTS / "Inter-Regular.otf"), c.get("font_size", 33))
        self.bold = ImageFont.truetype(str(FONTS / "Inter-SemiBold.otf"), 34)
        self.small = ImageFont.truetype(str(FONTS / "Inter-Regular.otf"), 21)
        self.small_bold = ImageFont.truetype(str(FONTS / "Inter-SemiBold.otf"), 21)
        self.header_h = 92
        self.pad = 24  # space at the panel's sides
        self.bx, self.by = 26, 15  # space inside a bubble
        self.max_bubble = int(self.w * 0.72)
        self.time = c.get("time", "Today 3:42 PM")

    # ── layout ──
    def _wrap(self, text: str) -> list[str]:
        lines, cur = [], ""
        for word in text.split():
            test = f"{cur} {word}".strip()
            if self.font.getlength(test) <= self.max_bubble - 2 * self.bx or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        return lines + [cur] if cur else lines

    def _bubble(self, text: str) -> tuple[list[str], int, int]:
        lines = self._wrap(text)
        line_h = int(self.font.size * 1.28)
        w = int(max(self.font.getlength(l) for l in lines)) + 2 * self.bx
        h = line_h * len(lines) + 2 * self.by - (line_h - self.font.size) // 2
        return lines, w, h

    def _content(self, msgs: list[tuple[str, str]]) -> Image.Image:
        """All messages so far, top to bottom, on a tall white strip."""
        items, y = [], 18
        y += 62  # "iMessage / Today 3:42 PM" at the top of the thread
        for i, (sender, text) in enumerate(msgs):
            lines, w, h = self._bubble(text)
            if i and msgs[i - 1][0] != sender:
                y += 16
            last_of_group = i + 1 == len(msgs) or msgs[i + 1][0] != sender
            items.append((sender, lines, w, h, y, last_of_group))
            y += h + 7
        delivered = bool(msgs) and msgs[-1][0] == "me"
        height = y + (34 if delivered else 10)
        img = Image.new("RGBA", (self.w, height), (255, 255, 255, 255))
        d = ImageDraw.Draw(img)
        for k, label in enumerate(("iMessage", self.time)):
            font = self.small_bold if k == 0 else self.small
            tw = font.getlength(label)
            d.text(((self.w - tw) / 2, 16 + k * 26), label, font=font, fill=MUTED)
        line_h = int(self.font.size * 1.28)
        for sender, lines, w, h, top, tail in items:
            mine = sender == "me"
            x0 = self.w - self.pad - w if mine else self.pad
            color = BLUE if mine else GREY
            d.rounded_rectangle((x0, top, x0 + w, top + h), radius=min(h // 2, 38), fill=color)
            if tail:
                self._tail(d, x0, top, w, h, mine, color)
            for n, line in enumerate(lines):
                d.text((x0 + self.bx, top + self.by - 2 + n * line_h), line, font=self.font,
                       fill=(255, 255, 255, 255) if mine else (0, 0, 0, 255))
        if delivered:
            tw = self.small.getlength("Delivered")
            d.text((self.w - self.pad - tw - 4, y + 2), "Delivered", font=self.small, fill=MUTED)
        return img

    @staticmethod
    def _tail(d: ImageDraw.ImageDraw, x0: int, top: int, w: int, h: int, mine: bool, color) -> None:
        """The little curl at the bottom corner of the last bubble in a group."""
        bottom = top + h
        if mine:
            x = x0 + w
            d.ellipse((x - 26, bottom - 26, x + 6, bottom), fill=color)
            d.ellipse((x - 2, bottom - 34, x + 22, bottom - 4), fill=(255, 255, 255, 255))
        else:
            d.ellipse((x0 - 6, bottom - 26, x0 + 26, bottom), fill=color)
            d.ellipse((x0 - 22, bottom - 34, x0 + 2, bottom - 4), fill=(255, 255, 255, 255))

    def _header(self) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.header_h), HEADER)
        d = ImageDraw.Draw(img)
        cy = self.header_h // 2
        d.line([(44, cy - 18), (28, cy), (44, cy + 18)], fill=(0, 122, 255, 255), width=5, joint="curve")
        name_w = self.bold.getlength(self.contact)
        x = (self.w - name_w - 22) / 2
        d.text((x, cy - 21), self.contact, font=self.bold, fill=(0, 0, 0, 255))
        ax = x + name_w + 10
        d.line([(ax, cy - 9), (ax + 8, cy), (ax, cy + 9)], fill=MUTED, width=3)
        d.line([(0, self.header_h - 2), (self.w, self.header_h - 2)], fill=LINE, width=2)
        return img

    def paint(self, msgs: list[tuple[str, str]]) -> Image.Image:
        """The chat panel after these messages: header + the newest messages that
        fit (older ones scroll off the top, like a real phone)."""
        body = self._content(msgs)
        room = self.max_h - self.header_h
        if body.height > room:
            body = body.crop((0, body.height - room, self.w, body.height))
        panel = Image.new("RGBA", (self.w, self.max_h), (0, 0, 0, 0))
        panel.paste(self._header(), (0, 0))
        panel.paste(body, (0, self.header_h))
        return panel


def build_overlay(item: dict, turns: list, total: float, work_dir: Path, cfg: dict) -> Path:
    """Draw every state of the chat and write an ffmpeg concat list that shows
    state k from the moment message k starts being read."""
    painter = ChatPainter(cfg, item.get("contact", "Mom"))
    msgs = messages(item)
    frames = work_dir / "chat"
    frames.mkdir(exist_ok=True)
    entries = []
    for k, turn in enumerate(turns):
        path = frames / f"state{k:03d}.png"
        painter.paint(msgs[: k + 1]).save(path)
        start = 0.0 if k == 0 else turn.start  # the first message is there from the start
        end = turns[k + 1].start if k + 1 < len(turns) else total
        entries.append((path, max(end - start, 0.04)))
    listing = work_dir / "chat.txt"
    lines = []
    for path, duration in entries:
        lines += [f"file '{path.resolve()}'", f"duration {duration:.3f}"]
    lines.append(f"file '{entries[-1][0].resolve()}'")  # concat needs the last file twice
    listing.write_text("\n".join(lines) + "\n")
    return listing
