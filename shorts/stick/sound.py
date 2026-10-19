"""Sound design for stickman stories: a low ambient drone and short effects
(whooshes, hits, radio static, knocks, heartbeats), all generated here so no
downloads or licences are needed. No music with a beat."""

from __future__ import annotations

import numpy as np

SR = 44100


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


def band(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Band-pass with soft edges (FFT based)."""
    if len(x) == 0:
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo > 0:
        m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi < SR / 2:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def env(n: int, attack: float, release: float) -> np.ndarray:
    e = np.ones(n)
    a = min(int(attack * SR), n)
    r = min(int(release * SR), n)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def norm(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = np.max(np.abs(x)) if len(x) else 0
    return x * (peak / m) if m > 0 else x


# ------------------------------------------------------------------ effects

def whoosh(dur: float = 0.55, seed: int = 1) -> np.ndarray:
    n = int(dur * SR)
    noise = _rng(seed).standard_normal(n)
    lo = band(noise, 300, 1200)
    hi = band(noise, 1500, 6000)
    k = np.linspace(0, 1, n)
    x = lo * (1 - k) + hi * k
    shape = np.sin(np.pi * k) ** 2
    return norm(x * shape, 0.7)


def boom(dur: float = 2.2, seed: int = 2) -> np.ndarray:
    t = _t(dur)
    f = 48 * np.exp(-t * 1.2) + 30
    phase = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(phase) * np.exp(-t * 2.2)
    noise = band(_rng(seed).standard_normal(len(t)), 20, 400) * np.exp(-t * 6)
    return norm(np.tanh((sub + noise * 0.6) * 2.2), 0.95)


def hit(seed: int = 3) -> np.ndarray:
    t = _t(1.2)
    body = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 5)
    metal = (np.sin(2 * np.pi * 183 * t) + 0.6 * np.sin(2 * np.pi * 431 * t)) * np.exp(-t * 7) * 0.4
    click = band(_rng(seed).standard_normal(len(t)), 800, 6000) * np.exp(-t * 40) * 0.6
    return norm(body + metal + click, 0.9)


def riser(dur: float = 1.2, seed: int = 4) -> np.ndarray:
    n = int(dur * SR)
    k = np.linspace(0, 1, n)
    noise = _rng(seed).standard_normal(n)
    x = band(noise, 400, 2000) * (1 - k) + band(noise, 2000, 9000) * k
    f = 180 + 520 * k ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    return norm((x * 0.6 + tone) * k ** 2.2, 0.6)


def tick(seed: int = 5) -> np.ndarray:
    t = _t(0.06)
    return norm(np.sin(2 * np.pi * 2100 * t) * np.exp(-t * 90), 0.5)


def click(seed: int = 6) -> np.ndarray:
    t = _t(0.08)
    x = band(_rng(seed).standard_normal(len(t)), 1000, 8000) * np.exp(-t * 120)
    return norm(x + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 80) * 0.5, 0.7)


def static(dur: float, seed: int = 7) -> np.ndarray:
    n = int(dur * SR)
    r = _rng(seed)
    hiss = band(r.standard_normal(n), 1200, 5000) * 0.35
    crackle = np.zeros(n)
    for p in r.integers(0, max(n - 400, 1), int(dur * 25)):
        crackle[p:p + 300] += r.standard_normal(300) * np.exp(-np.arange(300) / 40)
    wob = 0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * np.arange(n) / SR)
    return norm((hiss + band(crackle, 500, 7000) * 0.6) * wob * env(n, 0.05, 0.1), 0.6)


def knock(times: int = 3, gap: float = 0.32, seed: int = 8) -> np.ndarray:
    one_t = _t(0.25)
    one = (np.sin(2 * np.pi * 95 * one_t) * np.exp(-one_t * 28)
           + band(_rng(seed).standard_normal(len(one_t)), 100, 1500) * np.exp(-one_t * 60) * 0.7)
    out = np.zeros(int((gap * times + 0.3) * SR))
    for k in range(times):
        p = int(k * gap * SR)
        out[p:p + len(one)] += one
    return norm(out, 0.9)


def heartbeat(dur: float, bpm: float = 72, seed: int = 9) -> np.ndarray:
    n = int(dur * SR)
    out = np.zeros(n)
    beat_t = _t(0.18)
    thump = np.sin(2 * np.pi * 48 * beat_t) * np.exp(-beat_t * 25)
    period = 60 / bpm
    t = 0.0
    while t < dur:
        for off, g in ((0, 1.0), (0.22, 0.7)):
            p = int((t + off) * SR)
            if p + len(thump) < n:
                out[p:p + len(thump)] += thump * g
        t += period
    return norm(out, 0.9)


def buzz(dur: float, seed: int = 10) -> np.ndarray:
    """Electric flicker of a dying light."""
    t = _t(dur)
    sq = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.4 + np.sin(2 * np.pi * 240 * t) * 0.3
    r = _rng(seed)
    gate = np.repeat(r.random(int(dur * 18) + 1) > 0.45, SR // 18 + 1)[: len(t)]
    return norm(band(sq * gate, 80, 3000), 0.5)


def steps(dur: float, rate: float = 1.9, seed: int = 11) -> np.ndarray:
    n = int(dur * SR)
    out = np.zeros(n)
    st = _t(0.12)
    r = _rng(seed)
    t = 0.05
    while t < dur:
        one = band(r.standard_normal(len(st)), 80, 900) * np.exp(-st * 45)
        p = int(t * SR)
        if p + len(one) < n:
            out[p:p + len(one)] += one * (0.7 + 0.3 * r.random())
        t += 1 / rate
    return norm(out, 0.8)


def drone(dur: float, seed: int = 12) -> np.ndarray:
    """A dark, slowly breathing low pad that sits under the whole story."""
    t = _t(dur)
    lfo = 0.65 + 0.35 * np.sin(2 * np.pi * 0.07 * t)
    x = (np.sin(2 * np.pi * 55 * t) + 0.8 * np.sin(2 * np.pi * 55.35 * t)
         + 0.45 * np.sin(2 * np.pi * 82.4 * t + 1) + 0.3 * np.sin(2 * np.pi * 110.2 * t + 2)
         + 0.12 * np.sin(2 * np.pi * 164.8 * t * (1 + 0.002 * np.sin(2 * np.pi * 0.2 * t))))
    air = band(_rng(seed).standard_normal(len(t)), 60, 700) * 0.5
    out = (x * 0.6 + air) * lfo
    return norm(out * env(len(t), 2.5, 2.5), 0.5)


EFFECTS = {
    "whoosh": whoosh, "boom": boom, "hit": hit, "tick": tick, "click": click, "knock": knock,
}


def radio_voice(x: np.ndarray) -> np.ndarray:
    """Make a voice sound like it's coming out of a small radio."""
    y = band(x, 380, 3200)
    y = np.tanh(y * 3.0) / np.tanh(3.0)
    return norm(y, 0.85)


class Mixer:
    def __init__(self, dur: float):
        self.buf = np.zeros(int((dur + 1) * SR), np.float64)

    def add(self, at: float, x: np.ndarray, gain: float = 1.0) -> None:
        p = max(int(at * SR), 0)
        if p >= len(self.buf) or len(x) == 0:
            return
        end = min(p + len(x), len(self.buf))
        self.buf[p:end] += x[: end - p] * gain

    def finish(self, dur: float) -> np.ndarray:
        out = self.buf[: int(dur * SR)]
        out = out * env(len(out), 0.02, 0.6)
        peak = np.max(np.abs(out)) or 1
        return (out / peak * 0.95).astype(np.float32)
