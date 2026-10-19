"""Turn a stickman-story queue entry into a finished vertical video.

An episode is a list of shots. Each shot has a scene (what we see), what the
narrator says over it, and options for the scene. The narrator is voiced
sentence by sentence, so captions stay in sync and pauses feel deliberate;
every shot lasts as long as its narration.

    - id: blackout-day-1
      format: stickman
      series: BLACKOUT
      day: 1
      place: APT 6B
      shots:
        - scene: hallway
          time: "9:00 PM"
          say: "At nine PM, every light in the city dies at once."
          lights: off
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import cairo
import numpy as np

from .. import tts
from ..media import run_ffmpeg
from . import gfx, overlay, scenes, sound
from .gfx import FPS, H, W

PAUSE_SENTENCE = 0.32
PAUSE_ELLIPSIS = 0.6
PAUSE_QUESTION = 0.45


@dataclass
class Word:
    text: str
    start: float
    end: float
    style: str = "narr"  # "radio" for words heard over the radio


@dataclass
class Shot:
    index: int
    spec: dict
    start: float = 0.0
    end: float = 0.0
    words: list[Word] = field(default_factory=list)
    clock: tuple[int, int] = (0, 0)  # minutes since midnight at start / end of shot
    voice_spans: list[tuple[float, float, str]] = field(default_factory=list)  # absolute

    @property
    def dur(self) -> float:
        return self.end - self.start

    @property
    def scene(self) -> str:
        return self.spec.get("scene", "room")

    def get(self, key, default=None):
        return self.spec.get(key, default)

    def cue(self, value, default: float | None = None) -> float:
        """Seconds into the shot for a cue: a number of seconds, "40%", "end-1.5",
        or a word the narrator says (its first occurrence in this shot)."""
        if value is None:
            return default if default is not None else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        v = str(value).strip().lower()
        if v.endswith("%"):
            return self.dur * float(v[:-1]) / 100
        if v.startswith("end"):
            return self.dur + (float(v[3:]) if len(v) > 3 else 0.0)
        if v == "start":
            return 0.0
        target = re.sub(r"[^\w']", "", v)
        for w in self.words:
            if re.sub(r"[^\w']", "", w.text.lower()).startswith(target):
                return w.start - self.start
        return default if default is not None else 0.0

    def sub(self, spec: dict) -> "Shot":
        """The same moment in time with a different scene (for overlays on a base scene)."""
        s = Shot(self.index, {**spec}, self.start, self.end, self.words, self.clock, self.voice_spans)
        return s

    def minutes_at(self, t: float) -> int:
        a, b = self.clock
        if b <= a or self.dur <= 0:
            return a
        return a + int((b - a) * gfx.clamp(t / self.dur) * 0.999)


def parse_time(s: str) -> int:
    m = re.match(r"\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])?", str(s))
    if not m:
        return 0
    h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").upper()
    if ap == "PM" and h != 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return h * 60 + mi


def format_time(minutes: int) -> tuple[str, str]:
    minutes %= 24 * 60
    h, m = divmod(minutes, 60)
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}", ap


# ------------------------------------------------------------------ narration

def _sentences(text: str) -> list[str]:
    text = " ".join(str(text).split())
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p for p in parts if p.strip()]


def _pause_after(sentence: str) -> float:
    s = sentence.rstrip()
    if s.endswith("...") or s.endswith("…"):
        return PAUSE_ELLIPSIS
    if s.endswith("?"):
        return PAUSE_QUESTION
    return PAUSE_SENTENCE


def _load_audio(path: Path) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sound.SR), "-"],
        check=True, capture_output=True,
    ).stdout
    x = np.frombuffer(out, np.float32).astype(np.float64)
    # trim leading/trailing silence so pauses are ours to decide
    thr = 0.01 * (np.max(np.abs(x)) or 1)
    idx = np.nonzero(np.abs(x) > thr)[0]
    if len(idx):
        a = max(idx[0] - int(0.02 * sound.SR), 0)
        b = min(idx[-1] + int(0.06 * sound.SR), len(x))
        x = x[a:b]
    return x


def _speak(text: str, work: Path, cfg: dict, voice: dict, name: str) -> tuple[np.ndarray, list[tts.Word]]:
    path, words = tts.synthesize(text, work, cfg, voice=voice, name=name)
    raw = _load_audio(path)
    full = len(raw) / sound.SR
    # word timings were measured on the untrimmed audio; rescale to the trimmed one
    if words:
        span = max(words[-1].end, 1e-3)
        k = full / span if span > full else 1.0
        words = [tts.Word(w.text, w.start * k, w.end * k) for w in words]
    rms = np.sqrt(np.mean(raw ** 2)) or 1
    return raw * (0.12 / rms), words


def narrator_voice(item: dict, cfg: dict) -> dict:
    st = cfg.get("stickman", {})
    voices = st.get("voices") or {}
    name = item.get("narrator", st.get("narrator", "narrator"))
    v = voices.get(name) or {}
    return {k: val for k, val in v.items() if k != "name"}


INHERIT = ("place", "light")


def make_shots(item: dict) -> list[Shot]:
    """Shots in order; the place and light level carry over until a shot changes them."""
    shots, carry = [], {}
    for i, spec in enumerate(item.get("shots") or []):
        spec = dict(spec)
        for key in INHERIT:
            if key in spec:
                val = spec[key]
                carry[key] = val[-1] if isinstance(val, (list, tuple)) else val
            elif key in carry and spec.get("scene") not in ("title",):
                spec[key] = carry[key]
        shots.append(Shot(i, spec))
    return shots


def build_timeline(item: dict, cfg: dict, work: Path) -> tuple[list[Shot], sound.Mixer, float]:
    shots = make_shots(item)
    voice = narrator_voice(item, cfg)
    pieces: list[tuple[float, np.ndarray]] = []
    t = 0.4  # a breath before the first line
    n = 0
    for shot in shots:
        shot.start = t
        lines = shot.get("say") or []
        if isinstance(lines, str):
            lines = [lines]
        for line in lines:
            style = "narr"
            if isinstance(line, dict):
                (style, line), = line.items()
                style = "radio" if style == "radio" else "narr"
            for sentence in _sentences(line):
                audio, words = _speak(sentence, work, cfg, voice, f"s{n:03d}")
                n += 1
                if style == "radio":
                    audio = sound.radio_voice(audio) * 0.4
                pieces.append((t, audio))
                for w in words:
                    shot.words.append(Word(w.text, t + w.start, t + w.end, style))
                dur = len(audio) / sound.SR
                shot.voice_spans.append((t, t + dur, style))
                t += dur + _pause_after(sentence)
        t += float(shot.get("hold", 0.15))
        t = max(t, shot.start + float(shot.get("min", 1.2)))
        shot.end = t

    # the clock in the corner: each shot can set the time; small jumps tick by
    prev = parse_time(item.get("start_time", "9:00 PM"))
    starts = []
    for shot in shots:
        if shot.get("time"):
            prev = parse_time(shot.get("time"))
        starts.append(prev)
    for i, shot in enumerate(shots):
        a = starts[i]
        b = starts[i + 1] if i + 1 < len(shots) else a
        if not (0 < b - a <= 15):
            b = a
        shot.clock = (a, b)

    total = shots[-1].end + 0.3 if shots else 3.0
    mix = sound.Mixer(total)
    for at, audio in pieces:
        mix.add(at, audio)
    return shots, mix, total


# ------------------------------------------------------------------ rendering

class Canvas:
    def __init__(self, item: dict, shots: list[Shot], total: float):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        self.ctx = cairo.Context(self.surface)
        self.prev = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)  # last shot's final picture
        self.last = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)  # this frame's picture, no text
        self.dark = gfx.Darkness()
        self.film = gfx.FilmLook(seed=len(item.get("id", "")))
        self.item = item
        self.shots = shots
        self.total = total
        self.frame = 0
        self.state: dict = {}  # per-shot scratch space for scenes

    def keep_picture(self) -> None:
        """Remember the frame before captions and counters go on top."""
        c = cairo.Context(self.last)
        c.set_source_surface(self.surface, 0, 0)
        c.set_operator(cairo.OPERATOR_SOURCE)
        c.paint()

    def snapshot(self) -> None:
        c = cairo.Context(self.prev)
        c.set_source_surface(self.last, 0, 0)
        c.set_operator(cairo.OPERATOR_SOURCE)
        c.paint()


SCENE_SHIFT = {"room": -140, "street": -170}


def camera(shot: Shot, t: float) -> cairo.Matrix:
    cam = shot.get("camera") or {}
    z0, z1 = cam.get("zoom", [1.0, 1.06])
    fx, fy = cam.get("focus", [0.5, 0.48])
    p = gfx.ease_in_out(t / max(shot.dur, 0.01))
    z = z0 + (z1 - z0) * p
    m = cairo.Matrix()
    sx = sy = 0.0
    for at in shot.get("shake_at", []) or []:
        k = t - shot.cue(at)
        if 0 <= k < 0.6:
            a = 18 * (1 - k / 0.6) ** 2
            sx += math.sin(k * 90) * a
            sy += math.cos(k * 77) * a
    shift = float(cam.get("shift", SCENE_SHIFT.get(shot.scene, 0)))
    m.translate(W * fx + sx, H * fy + sy + shift)
    m.scale(z, z)
    m.translate(-W * fx, -H * fy)
    return m


def render_frames(cv: Canvas, out_video: Path) -> None:
    frames = int(math.ceil(cv.total * FPS))
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
         str(out_video)],
        stdin=subprocess.PIPE,
    )
    shots = cv.shots
    k = 0
    ctx = cv.ctx
    for f in range(frames):
        now = f / FPS
        while k + 1 < len(shots) and now >= shots[k + 1].start:
            cv.snapshot()
            cv.state = {}
            k += 1
        shot = shots[k]
        t = now - shot.start if now >= shot.start else 0.0
        cv.frame = f
        ctx.identity_matrix()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_matrix(camera(shot, t))
        scenes.paint(cv, shot, t)
        ctx.identity_matrix()
        cv.film.apply(ctx, f)
        cv.keep_picture()
        overlay.paint(cv, shot, t, now)
        cv.surface.flush()
        proc.stdin.write(cv.surface.get_data())
        if f % (FPS * 10) == 0:
            print(f"  frame {f}/{frames}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed while encoding frames")


def add_effects(shots: list[Shot], mix: sound.Mixer, total: float) -> None:
    """Sound effects that follow from what's on screen."""
    sfx = sound
    for i, shot in enumerate(shots):
        s = shot.start
        if i > 0 and shot.get("cut", "whoosh") == "whoosh" and shot.scene not in ("choice",):
            mix.add(s - 0.25, sfx.whoosh(seed=i), 0.18)
        if shot.get("rule"):
            mix.add(s, sfx.hit(seed=i), 0.55)
        sc = shot.scene
        if sc == "title":
            mix.add(s - 1.0, sfx.riser(1.0, seed=i), 0.35)
            mix.add(s, sfx.boom(seed=i), 0.8)
        if sc == "inventory":
            for item in shot.get("items") or []:
                at = shot.cue(item.get("cue"), 0.3)
                for k in range(min(int(item.get("count", 1)), 14)):
                    mix.add(s + at + k * scenes.ICON_STAGGER, sfx.tick(seed=k), 0.12)
            if shot.get("total"):
                mix.add(s + shot.cue((shot.get("total") or {}).get("cue"), shot.dur * 0.8), sfx.hit(seed=99), 0.4)
        if sc == "radio":
            on = shot.cue(shot.get("on"), 0.7)
            mix.add(s + on - 0.05, sfx.click(seed=i), 0.5)
            mix.add(s + on, sfx.static(max(shot.dur - on, 0.5), seed=i), 0.045)
        if sc == "street":
            pace = shot.get("pace", "walk")
            mix.add(s, sfx.steps(shot.dur, 3.2 if pace == "run" else 1.8, seed=i), 0.16 if pace == "run" else 0.1)
        if shot.get("flicker"):
            at = shot.cue(shot.get("flicker"))
            dies = shot.cue(shot.get("dies"), at + 1.6)
            mix.add(s + at, sfx.buzz(max(dies - at, 0.3), seed=i), 0.22)
            mix.add(s + dies, sfx.click(seed=i + 1), 0.6)
        if shot.get("dies") and not shot.get("flicker"):
            mix.add(s + shot.cue(shot.get("dies")), sfx.click(seed=i + 1), 0.6)
        if shot.get("heartbeat"):
            at = shot.cue(shot.get("heartbeat"))
            mix.add(s + at, sfx.heartbeat(max(total - s - at, 1.0), 84, seed=i), 0.35)
        if sc == "endcard":
            mix.add(shot.end - 1.0, sfx.boom(seed=77), 0.7)
        for e in shot.get("sfx") or []:
            fn = sfx.EFFECTS.get(e.get("name"))
            if fn:
                mix.add(s + shot.cue(e.get("at")), fn(), float(e.get("gain", 0.6)))


def render(item: dict, out_path: Path, work: Path, cfg: dict) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print("  voicing the narration…")
    shots, mix, total = build_timeline(item, cfg, work)
    add_effects(shots, mix, total)
    bed = sound.drone(total)
    mix.add(0, bed, float(cfg.get("stickman", {}).get("drone_volume", 0.09)))
    audio = mix.finish(total)
    raw = work / "mix.wav"
    with wave.open(str(raw), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sound.SR)
        f.writeframes((audio * 32767).astype("<i2").tobytes())
    print(f"  {len(shots)} shots, {total:.1f} s; drawing frames…")
    cv = Canvas(item, shots, total)
    video = work / "frames.mp4"
    render_frames(cv, video)
    run_ffmpeg([
        "-i", str(video), "-i", str(raw),
        "-filter_complex", "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(out_path),
    ])
    return out_path


def spoken_text(item: dict) -> str:
    out = []
    for shot in item.get("shots") or []:
        lines = shot.get("say") or []
        for line in [lines] if isinstance(lines, str) else lines:
            out.append(next(iter(line.values())) if isinstance(line, dict) else str(line))
    return " ".join(" ".join(out).split())


if __name__ == "__main__":  # quick local test: python -m shorts.stick.episode ID
    from .. import store
    q = {i["id"]: i for i in store.load_queue()}
    it = q[sys.argv[1]]
    render(it, Path("output") / f"{it['id']}.mp4", Path("output/work") / it["id"], store.load_config())


def stills(item: dict, out_dir: Path, per_shot: int = 3) -> list[Path]:
    """Draw a few frames of every shot without voicing anything (for checking
    the look quickly). Word times are estimated from the text."""
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = make_shots(item)
    t = 0.4
    for shot in shots:
        shot.start = t
        lines = shot.get("say") or []
        for line in [lines] if isinstance(lines, str) else lines:
            style = "narr"
            if isinstance(line, dict):
                (style, line), = line.items()
            for sentence in _sentences(line):
                dur = len(sentence.split()) / 2.5 + 0.2
                for w in tts.estimate_word_times(sentence, dur):
                    shot.words.append(Word(w.text, t + w.start, t + w.end, "radio" if style == "radio" else "narr"))
                shot.voice_spans.append((t, t + dur, "radio" if style == "radio" else "narr"))
                t += dur + _pause_after(sentence)
        t = max(t + float(shot.get("hold", 0.15)), shot.start + float(shot.get("min", 1.2)))
        shot.end = t
    prev = parse_time(item.get("start_time", "9:00 PM"))
    for i, shot in enumerate(shots):
        if shot.get("time"):
            prev = parse_time(shot.get("time"))
        shot.clock = (prev, prev)
    cv = Canvas(item, shots, t)
    paths = []
    for k, shot in enumerate(shots):
        if k > 0:
            # draw the previous shot's last frame first, for scenes that reuse it
            _draw(cv, shots[k - 1], shots[k - 1].dur - 0.01, shots[k - 1].end - 0.01)
            cv.snapshot()
        cv.state = {}
        for n in range(per_shot):
            tt = shot.dur * (n + 0.5) / per_shot
            _draw(cv, shot, tt, shot.start + tt)
            p = out_dir / f"shot{k:02d}_{n}.png"
            cv.surface.write_to_png(str(p))
            paths.append(p)
    return paths


def _draw(cv: Canvas, shot: Shot, t: float, now: float) -> None:
    ctx = cv.ctx
    ctx.identity_matrix()
    ctx.set_operator(cairo.OPERATOR_SOURCE)
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.set_matrix(camera(shot, t))
    scenes.paint(cv, shot, t)
    ctx.identity_matrix()
    cv.film.apply(ctx, cv.frame)
    cv.keep_picture()
    overlay.paint(cv, shot, t, now)
