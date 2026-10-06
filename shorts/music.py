"""Original background beats, synthesised from scratch for every video.

Two styles that are popular under Shorts:
  phonk  fast, hard 808 bass, claps, rolling hi-hats and the signature cowbell melody
  lofi   slow, warm jazzy chords, soft drums and vinyl crackle

Every beat is generated here (tempo, key, chords and melody are picked at random
per video), so there is nothing anyone can copyright-claim.
"""

from __future__ import annotations

import random
import wave
from pathlib import Path

import numpy as np

SR = 44100


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _decay(n: int, seconds: float) -> np.ndarray:
    return np.exp(-np.arange(n) / (SR * seconds))


def _filter(x: np.ndarray, low: float | None = None, high: float | None = None) -> np.ndarray:
    """Keep frequencies between `low` and `high` Hz (gentle slopes, via FFT)."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    gain = np.ones_like(f)
    if low:
        gain *= 1 / (1 + (low / np.maximum(f, 1)) ** 4)
    if high:
        gain *= 1 / (1 + (f / high) ** 4)
    return np.fft.irfft(spec * gain, len(x))


def _add(track: np.ndarray, sound: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    if i >= len(track):
        return
    end = min(len(track), i + len(sound))
    track[i:end] += sound[: end - i] * gain


def _noise(rng: np.random.Generator, seconds: float) -> np.ndarray:
    return rng.uniform(-1, 1, int(SR * seconds))


# ── Instruments ────────────────────────────────────────────────────────────


def kick(punch: float = 1.0) -> np.ndarray:
    n = int(SR * 0.45)
    t = np.arange(n) / SR
    pitch = 45 + 110 * np.exp(-t * 28 * punch)
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    return np.sin(phase) * _decay(n, 0.16)


def bass808(midi: float, seconds: float, drive: float = 2.5) -> np.ndarray:
    n = int(SR * seconds)
    t = np.arange(n) / SR
    f = _freq(midi)
    pitch = f * (1 + 0.6 * np.exp(-t * 40))  # little pitch drop on the attack
    tone = np.sin(2 * np.pi * np.cumsum(pitch) / SR)
    env = np.minimum(1, t * 200) * _decay(n, seconds * 0.7)
    return np.tanh(tone * drive) / np.tanh(drive) * env


def clap(rng) -> np.ndarray:
    burst = _noise(rng, 0.25)
    env = _decay(len(burst), 0.06)
    for k in (0.0, 0.011, 0.022):  # a clap is a few quick slaps
        i = int(k * SR)
        env[i : i + 120] += 0.6
    return _filter(burst * env, 900, 6000)


def snare(rng) -> np.ndarray:
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 185 * t) * _decay(n, 0.05)
    return body * 0.6 + _filter(_noise(rng, 0.22), 1500, 8000) * _decay(n, 0.07)


def hat(rng, open_: bool = False) -> np.ndarray:
    return _filter(_noise(rng, 0.3), 7000, None) * _decay(int(SR * 0.3), 0.12 if open_ else 0.025)


def cowbell(midi: float) -> np.ndarray:
    """The phonk cowbell: two detuned square waves, band-passed, short decay."""
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f = _freq(midi)
    tone = np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.48 * t))
    return _filter(tone * _decay(n, 0.11), 350, 3500) * 0.5


def keys(midis: list[float], seconds: float) -> np.ndarray:
    """Soft electric-piano chord."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in midis:
        f = _freq(m)
        out += (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 3))
    env = np.minimum(1, t * 60) * _decay(n, seconds * 0.55)
    return out * env / max(len(midis), 1)


# ── Styles ─────────────────────────────────────────────────────────────────

MINOR_PENTA = [0, 3, 5, 7, 10]


def phonk(rng: random.Random, nrng, duration: float) -> np.ndarray:
    bpm = rng.randint(128, 146)
    beat = 60 / bpm
    step = beat / 4
    key = rng.randint(29, 36)  # F1..C2 area for the 808
    prog = rng.choice([[0, 0, -4, -2], [0, -2, -4, -5], [0, 3, -4, -2], [0, 0, 5, 3]])
    bass_pattern = rng.choice([
        [(0, 6), (6, 4), (10, 6)],
        [(0, 3), (3, 3), (8, 6), (14, 2)],
        [(0, 8), (10, 2), (12, 4)],
    ])
    # A catchy cowbell motif: one bar, repeated, with a variation on bar 4.
    slots = sorted(rng.sample(range(16), rng.randint(6, 9)))
    motif = [(s, 60 + key % 12 + rng.choice(MINOR_PENTA) + rng.choice((0, 12))) for s in slots]
    variation = [(s, m + rng.choice((0, 0, 3, -2))) for s, m in motif]

    bar = 16 * step
    bars = int(duration / bar) + 2
    track = np.zeros(int(SR * (bars * bar + 1)))
    k, cl, oh = kick(), clap(nrng), hat(nrng, open_=True)
    for b in range(bars):
        root = key + prog[b % 4]
        t0 = b * bar
        for s, length in bass_pattern:
            _add(track, bass808(root, length * step * 0.95), t0 + s * step, 0.8)
            _add(track, k, t0 + s * step, 0.7)
        for s in (4, 12):
            _add(track, cl, t0 + s * step, 0.55)
        for s in range(0, 16, 2):
            _add(track, hat(nrng), t0 + s * step, 0.22 + 0.08 * (s % 4 == 0))
        if b % 2 == 1:  # hi-hat roll at the end of every other bar
            for r in range(6):
                _add(track, hat(nrng), t0 + 14 * step + r * step / 3, 0.16)
        else:
            _add(track, oh, t0 + 14 * step, 0.12)
        for s, m in (variation if b % 4 == 3 else motif):
            _add(track, cowbell(m), t0 + s * step, 0.42)
    return track


def lofi(rng: random.Random, nrng, duration: float) -> np.ndarray:
    bpm = rng.randint(74, 90)
    beat = 60 / bpm
    swing = beat / 2 * 0.12
    tonic = rng.randint(57, 64)
    # ii7 - V7 - Imaj7 - vi7, or a couple of other jazzy loops
    prog = rng.choice([
        [[2, 5, 9, 12], [7, 11, 14, 17], [0, 4, 7, 11], [9, 12, 16, 19]],
        [[0, 4, 7, 11], [9, 12, 16, 19], [5, 9, 12, 16], [7, 11, 14, 17]],
        [[9, 12, 16, 19], [5, 9, 12, 16], [0, 4, 7, 11], [7, 11, 14, 17]],
    ])
    bar = 4 * beat
    bars = int(duration / bar) + 2
    track = np.zeros(int(SR * (bars * bar + 1)))
    k, sn = kick(0.6), snare(nrng)
    for b in range(bars):
        t0 = b * bar
        chord = [tonic - 12 + n for n in prog[b % 4]]
        _add(track, keys(chord, bar * 1.05), t0, 0.5)
        _add(track, bass808(chord[0] - 12, beat * 1.6, drive=1.0), t0, 0.45)
        _add(track, bass808(chord[0] - 12, beat * 0.9, drive=1.0), t0 + 2.5 * beat, 0.35)
        if b == 0:
            continue  # first bar: just keys, then the drums come in
        for s in (0, 2.5):
            _add(track, k, t0 + s * beat, 0.6)
        for s in (1, 3):
            _add(track, sn, t0 + s * beat, 0.32)
        for e in range(8):
            _add(track, hat(nrng), t0 + e * beat / 2 + (swing if e % 2 else 0), 0.08 + 0.04 * (e % 2 == 0))
    track = _filter(track, 30, 4500)
    # vinyl: soft hiss plus random crackles
    hiss = _filter(nrng.normal(0, 0.012, len(track)), 2000, 7000)
    crackle = np.zeros(len(track))
    pops = nrng.integers(0, len(track), int(len(track) / SR * 6))
    crackle[pops] = nrng.uniform(-0.25, 0.25, len(pops))
    return track + hiss + _filter(crackle, 1500, None)


STYLES = {"phonk": phonk, "lofi": lofi}


def render(out: Path, duration: float, seed: str = "", styles: list[str] | None = None) -> tuple[Path, str]:
    """Write an original beat of `duration` seconds to `out` (WAV). Returns (path, style)."""
    rng = random.Random(f"music-{seed}")
    nrng = np.random.default_rng(rng.randrange(2**32))
    style = rng.choice([s for s in (styles or list(STYLES)) if s in STYLES] or ["phonk"])
    track = STYLES[style](rng, nrng, duration)[: int(SR * duration)]
    fade = np.ones(len(track))
    fi, fo = int(SR * 0.3), int(SR * 1.5)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    # Gentle glue: level the mix, soft-limit only the loudest peaks, then normalise.
    track = track * fade / max(np.percentile(np.abs(track), 99.5), 1e-6)
    track = np.tanh(track * 0.8) / np.tanh(0.8)
    track = track / max(np.max(np.abs(track)), 1e-6) * 0.89
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((track * 32767).astype("<i2").tobytes())
    return out, style
