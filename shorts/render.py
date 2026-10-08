"""Put voice, captions, background, characters and optional music together
into one vertical MP4."""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image

from . import captions, chat, tts, visuals
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
    lines = dialogue_lines(item) or chat.messages(item)
    if lines:
        return " ".join(text for _, text in lines)
    return " ".join(str(item.get("script", "")).split())


def expression_schedule(item: dict, turns: list, total: float, cfg: dict) -> dict:
    """Decide which face each character shows, and when.

    The speaking character stays on screen until the next one starts. Their face
    changes every `expression_seconds`: the first face fits the line (a question
    or an exclamation), then it rotates through the others.
    """
    schedule: dict[tuple[str, str], list[tuple[float, float]]] = {}
    characters = cfg.get("characters") or {}
    step = cfg.get("video", {}).get("expression_seconds", 1.6)
    rng = random.Random(item.get("id", ""))
    for i, turn in enumerate(turns):
        ch = characters.get(turn.speaker) or {}
        faces = list((ch.get("expressions") or {}).keys())
        if not faces:
            continue
        reactions = ch.get("reactions") or {}
        if "?" in turn.text and reactions.get("question") in faces:
            first = reactions["question"]
        elif "!" in turn.text and reactions.get("exclaim") in faces:
            first = reactions["exclaim"]
        else:
            first = rng.choice(faces)
        order = [first] + rng.sample([f for f in faces if f != first], len(faces) - 1)
        end = turns[i + 1].start if i + 1 < len(turns) else total
        t, k = turn.start, 0
        while t < end - 0.05:
            nxt = min(t + step, end)
            if end - nxt < step * 0.5:  # don't leave a tiny flash at the end
                nxt = end
            schedule.setdefault((turn.speaker, order[k % len(order)]), []).append((t, nxt))
            t, k = nxt, k + 1
    return schedule


def chat_voices(item: dict, cfg: dict) -> dict:
    """Voices for a text story: "me" and "them" each get a preset from
    config.yaml (chat.voices), chosen per story with `me:` / `them:`."""
    c = cfg.get("chat", {})
    presets = c.get("voices") or {}
    picks = {"me": item.get("me", c.get("me", "male")), "them": item.get("them", c.get("them", "female"))}
    chosen: dict[str, dict] = {}
    for who, name in picks.items():
        pool = presets.get(name) or [{}]
        pool = pool if isinstance(pool, list) else [pool]
        k = random.Random(f"voice-{item.get('id', '')}-{who}").randrange(len(pool))
        # never give both sides the same voice
        if who == "them" and len(pool) > 1 and pool[k] == chosen.get("me"):
            k = (k + 1) % len(pool)
        chosen[who] = pool[k]
    return chosen


def pick_music(item: dict, cfg: dict) -> Path | None:
    """Your own tracks in assets/music/ first; otherwise a free meme track.

    When a CC BY track is used, its credit is stored on the item so the uploader
    can put it in the description (the licence requires it).
    """
    own = sorted(f for f in MUSIC_DIR.glob("*") if f.suffix.lower() in (".mp3", ".wav", ".m4a")) if MUSIC_DIR.exists() else []
    if own:
        track = random.Random(item.get("id", "")).choice(own)
        print(f"  music: {track.name}")
        return track
    tracks = cfg.get("music", {}).get("tracks") or []
    if not tracks:
        return None
    from . import music

    found = music.pick(item.get("id", ""), tracks)
    if not found:
        print("  music: none available, video has voices only", file=sys.stderr)
        return None
    track, credit = found
    item["music_credit"] = credit
    print(f"  music: {track.stem}")
    return track


def render(item: dict, out_path: Path, work_dir: Path, cfg: dict) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    v = cfg.get("video", {})
    w, h, fps = v.get("width", 1080), v.get("height", 1920), v.get("fps", 30)

    # 1. Voice
    lines = dialogue_lines(item)
    texts = chat.messages(item)
    if texts:  # text story: every message is read out as it appears
        spoken = [(sender, chat.speech(text)) for sender, text in texts]
        gap = cfg.get("chat", {}).get("gap_seconds", 0.3)
        audio, words, turns = tts.synthesize_dialogue(spoken, work_dir, cfg, voices=chat_voices(item, cfg), gap=gap)
    elif lines:
        audio, words, turns = tts.synthesize_dialogue(lines, work_dir, cfg)
    else:
        audio, words = tts.synthesize(spoken_text(item), work_dir, cfg)
        turns = []
    total = probe_duration(audio) + v.get("tail_seconds", 0.6) + (1.0 if texts else 0)
    if not texts:  # the chat itself is the text; no captions needed
        captions.write_ass(words, work_dir / "captions.ass", cfg)

    # 2. Background: gameplay → stock clips → gradient
    inputs: list[str] = []
    filters: list[str] = []
    fill = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"
    gameplay = visuals.pick_gameplay(total, cfg, work_dir, item.get("id", ""))
    clips = [] if gameplay else visuals.fetch_clips(
        item.get("search_terms") or [item.get("niche") or cfg.get("channel", {}).get("niche", "")],
        total, work_dir, cfg,
    )
    if gameplay:
        path, start = gameplay
        credit = (cfg.get("visuals", {}).get("gameplay_credits") or {}).get(path.name)
        if credit:
            item["gameplay_credit"] = credit
        inputs += ["-stream_loop", "-1", "-ss", f"{start:.2f}", "-t", f"{total + 0.5:.2f}", "-i", str(path.resolve())]
        # Mirror every other video's gameplay, so reused footage looks like a new run.
        mirror = ",hflip" if random.Random(f"mirror-{item.get('id', '')}").random() < 0.5 else ""
        filters.append(f"[0:v]{fill}{mirror},setpts=PTS-STARTPTS[bg]")
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
    if texts:
        dim = 0  # the chat panel is opaque; keep the gameplay bright
    filters.append(f"[bg]drawbox=c=black@{dim}:t=fill[base]")
    current = "base"

    # 3. Characters: show whoever is talking, switching between their expressions.
    for (key, expression), spans in expression_schedule(item, turns, total, cfg).items():
        ch = cfg["characters"][key]
        image = ROOT / ch["expressions"][expression]
        if not image.exists():
            continue
        size = ch.get("size", 760)
        scaled = work_dir / f"face-{key}-{expression}.png"
        run_ffmpeg(["-i", str(image.resolve()), "-vf", f"scale={size}:-1", str(scaled.resolve())])
        inputs += ["-framerate", str(fps), "-loop", "1", "-i", str(scaled.resolve())]
        idx = n
        n += 1
        x = -30 if ch.get("side", "left") == "left" else w - size + 30
        # The pictures' torsos run off the bottom of the frame (no gap below them);
        # "bottom" nudges a character up (positive) or further down (negative).
        with Image.open(image) as pic:
            height = round(pic.height * size / pic.width)
        y = h - height - ch.get("bottom", -60)
        enable = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in spans)
        filters.append(f"[{idx}:v]format=rgba[c{idx}]")
        filters.append(f"[{current}][c{idx}]overlay=x={x}:y={y}:enable='{enable}':shortest=1[o{idx}]")
        current = f"o{idx}"

    # 3b. Text story: the chat panel, filling up message by message.
    if texts:
        listing = chat.build_overlay(item, turns, total, work_dir, cfg)
        inputs += ["-f", "concat", "-safe", "0", "-i", str(listing.resolve())]
        c = cfg.get("chat", {})
        x = (w - int(w * c.get("width", 0.70))) // 2
        filters.append(f"[{n}:v]fps={fps},format=rgba[chat]")
        filters.append(f"[{current}][chat]overlay=x={x}:y={c.get('top', 470)}:eof_action=repeat[withchat]")
        current = "withchat"
        n += 1
        filters.append(f"[{current}]format=yuv420p[vout]")
    else:
        filters.append(f"[{current}]ass=captions.ass,format=yuv420p[vout]")

    # 4. Audio: voice (+ optional music)
    voice_idx = n
    inputs += ["-i", str(audio.resolve())]
    filters.append(f"[{voice_idx}:a]apad,atrim=0:{total:.3f}[voice]")
    track = None if texts and not cfg.get("chat", {}).get("music", False) else pick_music(item, cfg)
    if track:
        inputs += ["-stream_loop", "-1", "-i", str(track.resolve())]
        vol = cfg.get("music", {}).get("volume", v.get("music_volume", 0.14))
        filters.append(
            f"[{voice_idx + 1}:a]volume={vol},atrim=0:{total:.3f},afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[music]"
        )
        filters.append("[voice][music]amix=inputs=2:duration=first:normalize=0[mix]")
    else:
        filters.append("[voice]anull[mix]")
    # Shorts-standard loudness, so videos aren't quieter than everything around them.
    filters.append("[mix]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[aout]")

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
