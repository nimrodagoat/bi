"""Text-to-speech with word timings, trying free engines in order."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

from .media import probe_duration, run_ffmpeg

CACHE = Path(__file__).resolve().parent.parent / ".cache"
PIPER_DIR = CACHE / "piper"
KOKORO_DIR = CACHE / "kokoro"
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")


@dataclass
class Word:
    text: str
    start: float  # seconds
    end: float
    speaker: str | None = None


@dataclass
class Turn:
    speaker: str
    start: float
    end: float
    text: str = ""


LINE_GAP = 0.18  # seconds of silence between two characters' lines


def synthesize(
    text: str, work_dir: Path, cfg: dict, voice: dict | None = None, name: str = "voice"
) -> tuple[Path, list[Word]]:
    """Speak `text`; return the audio file and when each word is said.

    `voice` overrides the voice settings from config.yaml (used for characters).
    """
    vcfg = {**cfg.get("voice", {}), **(voice or {}), "_name": name}
    errors = []
    engines = vcfg.get("engines", ["edge", "kokoro", "piper"])
    if os.environ.get("SHORTS_VOICES"):  # e.g. SHORTS_VOICES=espeak for offline testing
        engines = os.environ["SHORTS_VOICES"].split(",")
    for engine in engines:
        try:
            fn = {"edge": _edge, "kokoro": _kokoro, "piper": _piper, "espeak": _espeak}[engine]
        except KeyError:
            errors.append(f"{engine}: unknown engine")
            continue
        try:
            audio, words = fn(text, work_dir, vcfg)
            if name == "voice" or name.endswith("00"):
                print(f"  voice: {engine}")
            return audio, words
        except Exception as e:  # try the next engine
            errors.append(f"{engine}: {e}")
            print(f"  voice engine '{engine}' failed: {e}", file=sys.stderr)
    raise RuntimeError("every voice engine failed:\n  " + "\n  ".join(errors))


def _edge(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    import edge_tts

    out = work_dir / f"{vcfg['_name']}.mp3"
    words: list[Word] = []

    async def run():
        comm = edge_tts.Communicate(
            text,
            vcfg.get("edge_voice", "en-US-AndrewNeural"),
            rate=vcfg.get("edge_rate", "+0%"),
            pitch=vcfg.get("edge_pitch", "+0Hz"),
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


_kokoro_model = None


def _kokoro(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    """Kokoro: free open-source neural voice that runs on the machine itself."""
    global _kokoro_model
    if _kokoro_model is None:
        import requests
        from kokoro_onnx import Kokoro

        KOKORO_DIR.mkdir(parents=True, exist_ok=True)
        for name in KOKORO_FILES:
            target = KOKORO_DIR / name
            if not target.exists():
                print(f"  downloading voice model {name}…")
                with requests.get(KOKORO_URL + name, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    tmp = target.with_suffix(".part")
                    with tmp.open("wb") as f:
                        for block in r.iter_content(1 << 20):
                            f.write(block)
                    tmp.rename(target)
        _kokoro_model = Kokoro(str(KOKORO_DIR / KOKORO_FILES[0]), str(KOKORO_DIR / KOKORO_FILES[1]))

    voice = vcfg.get("kokoro_voice", "am_michael")
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, rate = _kokoro_model.create(text, voice=voice, speed=vcfg.get("kokoro_speed", 1.0), lang=lang)
    out = work_dir / f"{vcfg['_name']}.wav"
    pcm = (samples.clip(-1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(out), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return out, estimate_word_times(text, len(samples) / rate)


def _piper(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    voice = vcfg.get("piper_voice", "en_US-ryan-high")
    model = PIPER_DIR / f"{voice}.onnx"
    if not model.exists():
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "piper.download_voices", "--download-dir", str(PIPER_DIR), voice],
            check=True,
        )
    out = work_dir / f"{vcfg['_name']}.wav"
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", str(model), "-f", str(out)],
        input=text.encode(),
        check=True,
        capture_output=True,
    )
    return out, estimate_word_times(text, probe_duration(out))


def _espeak(text: str, work_dir: Path, vcfg: dict) -> tuple[Path, list[Word]]:
    out = work_dir / f"{vcfg['_name']}.wav"
    cmd = ["espeak-ng", "-v", vcfg.get("espeak_voice", "en-us"), "-s", "165"]
    cmd += ["-p", str(vcfg.get("espeak_pitch", 50)), "-w", str(out), text]
    subprocess.run(cmd, check=True)
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


def synthesize_dialogue(
    lines: list[tuple[str, str]], work_dir: Path, cfg: dict
) -> tuple[Path, list[Word], list[Turn]]:
    """Voice a conversation: each (speaker, text) line in that character's voice,
    joined into one audio track. Returns the audio, every word's timing (tagged
    with its speaker) and when each character is talking."""
    characters = cfg.get("characters", {})
    parts, words, turns = [], [], []
    t = 0.0
    for i, (speaker, text) in enumerate(lines):
        voice = {k: v for k, v in characters.get(speaker, {}).items() if k != "name"}
        audio, line_words = synthesize(text, work_dir, cfg, voice=voice, name=f"line{i:02d}")
        length = probe_duration(audio)
        for w in line_words:
            words.append(Word(w.text, w.start + t, w.end + t, speaker))
        turns.append(Turn(speaker, t, t + length, text))
        parts.append(audio)
        t += length + LINE_GAP

    out = work_dir / "dialogue.wav"
    args, filters = [], []
    for i, part in enumerate(parts):
        args += ["-i", str(part.resolve())]
        filters.append(
            f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
            f"apad=pad_dur={LINE_GAP}[a{i}]"
        )
    filters.append("".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[out]")
    run_ffmpeg([*args, "-filter_complex", ";".join(filters), "-map", "[out]", str(out.resolve())])
    return out, words, turns
