"""Big, word-by-word highlighted captions as an ASS subtitle file."""

from __future__ import annotations

from pathlib import Path

from .tts import Word


def _ass_color(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def _ts(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(word: str) -> str:
    return word.replace("\\", "").replace("{", "").replace("}", "").upper()


def chunk_words(words: list[Word], size: int) -> list[list[Word]]:
    """Group words into short caption lines, breaking early at sentence ends."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= size or w.text[-1:] in ".!?,;:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def write_ass(words: list[Word], path: Path, cfg: dict) -> None:
    c = cfg.get("captions", {})
    v = cfg.get("video", {})
    base = _ass_color(c.get("color", "#FFFFFF"))
    hi = _ass_color(c.get("highlight_color", "#FFE600"))
    size = c.get("font_size", 92)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {v.get('width', 1080)}",
        f"PlayResY: {v.get('height', 1920)}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{c.get('font', 'DejaVu Sans')},{size},{base},{base},&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,1,0,1,7,4,2,70,70,{c.get('position_from_bottom', 760)},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    chunks = chunk_words(words, c.get("words_per_caption", 3))
    for ci, chunk in enumerate(chunks):
        # Keep a line on screen until the next one starts, unless there's a long pause.
        next_start = chunks[ci + 1][0].start if ci + 1 < len(chunks) else chunk[-1].end + 0.4
        chunk_end = next_start if next_start - chunk[-1].end < 0.6 else chunk[-1].end + 0.3
        for wi, word in enumerate(chunk):
            start = word.start
            end = chunk[wi + 1].start if wi + 1 < len(chunk) else chunk_end
            if end <= start:
                continue
            parts = []
            for k, w in enumerate(chunk):
                color = hi if k == wi else base
                parts.append(f"{{\\c{color}}}{_clean(w.text)}")
            pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{pop}{' '.join(parts)}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
