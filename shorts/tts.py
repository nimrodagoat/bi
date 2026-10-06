"""Text-to-speech with word timings, trying free engines in order."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .media import probe_duration

PIPER_DIR = Path(__file__).resolve().parent.parent / ".cache" / "piper"


@dataclass
class Word:
    text: str
    start: float  # seconds
    end: float


def synthesize(text: str, work_dir: Path, cfg: dict) -> tuple[Path, list[Word]]:
    """Speak `text`; return the audio file and when each word is said."""
    vcfg = cfg.get("voice", {})
    errors = []
    engines = vcfg.get("engines", ["edge", "piper"])
    if os.environ.get("SHORTS_VOICES"):  # e.g. SHORTS_VOICES=espeak for offline testing
        engines = os.environ["SHORTS_VOICES"].split(",")
    for engine in engines:
        try:
            fn = {"edge": _edge, "piper": _piper, "espeak": _espeak}[engine]
        except KeyError:
            errors.append(f"{engine}: unknown engine")
            continue
        try:
            audio, words = fn(text, work_dir, vcfg)
            print(f"  voice: {engine}")
            return audio, words
        except Exception as e:  # try the next engine
            errors.append(f"{engine}: {e}")
            print(f"  voice engine '{engine}' failed: {e}", file=sys.stderr)
    raise RuntimeError("every voice engine failed:\n  " + "\n  ".join(errors))


def _edge(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    import edge_tts

    out = work_dir / "voice.mp3"
    words: list[Word] = []

    async def run():
        comm = edge_tts.Communicate(
            text,
            vcfg.get("edge_voice", "en-US-AndrewNeural"),
            rate=vcfg.get("edge_rate", "+0%"),
            boundary="WordBoundary",
        )
        with out.open("wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 1e7
                    words.append(Word(chunk["text"], start, start + chunk["duration"] / 1e7))

    asyncio.run(run())
    if not words or out.stat().st_size == 0:
        raise RuntimeError("no audio returned")
    return out, _attach_punctuation(text, words)


def _piper(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    voice = vcfg.get("piper_voice", "en_US-ryan-high")
    model = PIPER_DIR / f"{voice}.onnx"
    if not model.exists():
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "piper.download_voices", "--download-dir", str(PIPER_DIR), voice],
            check=True,
        )
    out = work_dir / "voice.wav"
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", str(model), "-f", str(out)],
        input=text.encode(),
        check=True,
        capture_output=True,
    )
    return out, estimate_word_times(text, probe_duration(out))


def _espeak(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    out = work_dir / "voice.wav"
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", "165", "-w", str(out), text], check=True)
    return out, estimate_word_times(text, probe_duration(out))


def estimate_word_times(text: str, duration: float) -> list[Word]:
    """Spread words over the audio by length, with extra time at punctuation.

    Used for engines that don't report word timings themselves.
    """
    tokens = text.split()
    weights = []
    for t in tokens:
        w = len(re.sub(r"\W", "", t)) + 1
        if t[-1] in ".!?":
            w += 4
        elif t[-1] in ",;:":
            w += 2
        weights.append(w)
    scale = duration / max(sum(weights), 1)
    words, t = [], 0.0
    for token, w in zip(tokens, weights):
        span = w * scale
        words.append(Word(token, t, t + span * 0.85))
        t += span
    return words


def _attach_punctuation(text: str, words: list[Word]) -> list[Word]:
    """Edge reports bare words; put back the punctuation from the script so
    captions can break at sentence ends ("brain." instead of "brain")."""
    tokens = text.split()
    i = 0
    for w in words:
        for j in range(i, min(i + 4, len(tokens))):
            bare = re.sub(r"[^\w']", "", tokens[j]).lower()
            if bare and bare == re.sub(r"[^\w']", "", w.text).lower():
                w.text = tokens[j]
                i = j + 1
                break
    return words
