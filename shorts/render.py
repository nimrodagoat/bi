"""Put voice, captions, background, characters and optional music together
into one vertical MP4."""

from __future__ import annotations

import random
from pathlib import Path

from . import captions, tts, visuals
from .media import probe_duration, run_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "assets" / "music"


def dialogue_lines(item: dict) -> list[tuple[str, str]]:
    """The item's dialogue as (speaker, text) pairs; empty for a narrated script."""
    lines = []
    for entry in item.get("dialogue") or []:
        if isinstance(entry, dict):  # {speaker: text}
            (speaker, text), = entry.items()
        else:  # [speaker, text]
            speaker, text = entry
        lines.append((str(speaker), " ".join(str(text).split())))
    return lines


def spoken_text(item: dict) -> str:
    lines = dialogue_lines(item)
    if lines:
        return " ".join(text for _, text in lines)
    return " ".join(str(item.get("script", "")).split())


def render(item: dict, out_path: Path, work_dir: Path, cfg: dict) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    v = cfg.get("video", {})
    w, h, fps = v.get("width", 1080), v.get("height", 1920), v.get("fps", 30)

    # 1. Voice
    lines = dialogue_lines(item)
    if lines:
        audio, words, turns = tts.synthesize_dialogue(lines, work_dir, cfg)
    else:
        audio, words = tts.synthesize(spoken_text(item), work_dir, cfg)
        turns = []
    total = probe_duration(audio) + v.get("tail_seconds", 0.6)
    captions.write_ass(words, work_dir / "captions.ass", cfg)

    # 2. Background: gameplay → stock clips → gradient
    inputs: list[str] = []
    filters: list[str] = []
    fill = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"
    gameplay = visuals.pick_gameplay(total, cfg)
    clips = [] if gameplay else visuals.fetch_clips(
        item.get("search_terms") or [item.get("niche") or cfg.get("channel", {}).get("niche", "")],
        total, work_dir, cfg,
    )
    if gameplay:
        path, start = gameplay
        inputs += ["-ss", f"{start:.2f}", "-t", f"{total + 0.5:.2f}", "-i", str(path.resolve())]
        filters.append(f"[0:v]{fill},setpts=PTS-STARTPTS[bg]")
        n = 1
    elif clips:
        seg = total / len(clips)
        for i, clip in enumerate(clips):
            inputs += ["-stream_loop", "-1", "-i", str(clip.resolve())]
            filters.append(f"[{i}:v]{fill},trim=duration={seg:.3f},setpts=PTS-STARTPTS[v{i}]")
        filters.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[bg]")
        n = len(clips)
    else:
        inputs += ["-f", "lavfi", "-i", visuals.gradient_source(total, cfg)]
        filters.append("[0:v]setsar=1[bg]")
        n = 1

    # Darken real footage a little so captions stay readable.
    vis = cfg.get("visuals", {})
    dim = vis.get("gameplay_dim", 0.15) if gameplay else (vis.get("dim", 0.35) if clips else 0)
    filters.append(f"[bg]drawbox=c=black@{dim}:t=fill[base]")
    current = "base"

    # 3. Characters: show whoever is talking, with a little talking bounce.
    # Each character stays on screen until the next one starts talking.
    shown = [
        (t.speaker, t.start, turns[i + 1].start if i + 1 < len(turns) else total)
        for i, t in enumerate(turns)
    ]
    for key, ch in (cfg.get("characters") or {}).items():
        spans = [(start, end) for speaker, start, end in shown if speaker == key]
        image = ROOT / ch.get("image", "") if ch.get("image") else None
        if not spans or not image or not image.exists():
            continue
        size = ch.get("size", 560)
        inputs += ["-loop", "1", "-i", str(image.resolve())]
        idx = n
        n += 1
        x = 40 if ch.get("side", "left") == "left" else w - size - 140
        y = h - size - ch.get("bottom", 420)
        enable = "+".join(f"between(t,{start:.2f},{end:.2f})" for start, end in spans)
        filters.append(f"[{idx}:v]scale={size}:-1,format=rgba[c{idx}]")
        filters.append(
            f"[{current}][c{idx}]overlay=x={x}:y='{y}-abs(14*sin(t*11))':"
            f"enable='{enable}':shortest=1[o{idx}]"
        )
        current = f"o{idx}"

    filters.append(f"[{current}]ass=captions.ass,format=yuv420p[vout]")

    # 4. Audio: voice (+ optional music)
    voice_idx = n
    inputs += ["-i", str(audio.resolve())]
    filters.append(f"[{voice_idx}:a]apad,atrim=0:{total:.3f}[voice]")
    music = sorted(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(random.choice(music).resolve())]
        vol = v.get("music_volume", 0.12)
        filters.append(
            f"[{voice_idx + 1}:a]volume={vol},atrim=0:{total:.3f},afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[music]"
        )
        filters.append("[voice][music]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        filters.append("[voice]anull[aout]")

    run_ffmpeg(
        [
            *inputs,
            "-filter_complex", ";".join(filters),
            "-map", "[vout]", "-map", "[aout]",
            "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(fps),
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-movflags", "+faststart",
            str(out_path.resolve()),
        ],
        cwd=work_dir,  # so the ass filter can use a plain relative filename
    )
    return out_path
