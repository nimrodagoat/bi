"""Put voice, captions, footage and optional music together into one vertical MP4."""

from __future__ import annotations

import random
from pathlib import Path

from . import captions, tts, visuals
from .media import probe_duration, run_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "assets" / "music"


def render(item: dict, out_path: Path, work_dir: Path, cfg: dict) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    v = cfg.get("video", {})
    w, h, fps = v.get("width", 1080), v.get("height", 1920), v.get("fps", 30)

    script = " ".join(str(item["script"]).split())
    audio, words = tts.synthesize(script, work_dir, cfg)
    total = probe_duration(audio) + v.get("tail_seconds", 0.6)
    captions.write_ass(words, work_dir / "captions.ass", cfg)

    niche = item.get("niche") or cfg.get("channel", {}).get("niche", "")
    clips = visuals.fetch_clips(item.get("search_terms") or [niche], total, work_dir, cfg)

    inputs: list[str] = []
    filters: list[str] = []
    if clips:
        seg = total / len(clips)
        for i, clip in enumerate(clips):
            inputs += ["-stream_loop", "-1", "-i", str(clip.resolve())]
            filters.append(
                f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                f"setsar=1,fps={fps},trim=duration={seg:.3f},setpts=PTS-STARTPTS[v{i}]"
            )
        filters.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[bg]")
        n = len(clips)
    else:
        inputs += ["-f", "lavfi", "-i", visuals.gradient_source(total, cfg)]
        filters.append("[0:v]setsar=1[bg]")
        n = 1

    # Darken stock footage so captions stay readable; gradients are dark already.
    dim = cfg.get("visuals", {}).get("dim", 0.35) if clips else 0
    filters.append(f"[bg]drawbox=c=black@{dim}:t=fill,ass=captions.ass,format=yuv420p[vout]")

    voice_idx = n
    inputs += ["-i", str(audio.resolve())]
    filters.append(f"[{voice_idx}:a]apad,atrim=0:{total:.3f}[voice]")

    music = sorted(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(random.choice(music).resolve())]
        vol = cfg.get("video", {}).get("music_volume", 0.12)
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
