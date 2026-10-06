# YouTube Shorts autopilot

A GitHub Actions job (`.github/workflows/daily-short.yml`) runs daily, takes the
first entry of `content/queue.yaml`, renders a vertical Short and uploads it; then
it moves the entry to `content/posted.yaml` and commits. Everything is free: Edge
TTS (Piper fallback), ffmpeg, YouTube Data API.

Current format: two original cartoon characters, **Dave** (loud, clueless; Edge
voice en-US-AndrewMultilingualNeural) and **Pip** (smug know-it-all; Kokoro voice
bm_lewis), talk through a fact. Each has 5 expression pictures (face + hand
gesture, "Notionists" art, public domain) in `assets/characters/<name>/` that
rotate while they talk, a sticker outline and caption colour; all defined under
`characters:` in `config.yaml`. Regenerate art with `tools/characters.mjs`, then
`tools/sticker.py` (outline + torso extended to the frame bottom, so no gap under
the characters), then `tools/design_sheet.py`. Music: the owner's tracks in
`assets/music/`, else an original beat from `shorts/music.py` (phonk/lofi, never
copyrighted songs); the mix is loudness-normalised. Background: the owner's real gameplay (`assets/gameplay/`, also
pulled from the repo's `gameplay` release), else **generated Minecraft-style parkour**
(`shorts/parkour.py`, procedural textures, headless OpenGL), else Pixabay/Pexels
stock clips from `search_terms`, else a gradient. Never use real Minecraft/Subway
Surfers footage downloaded from others.

Don't imitate copyrighted characters or real people's voices (e.g. Family Guy):
the owner asked once and was steered to original characters; keep it that way.

The owner is not a programmer. They manage the channel by chatting. Keep replies
plain-language, and do the git work for them.

## Layout
- `config.yaml`: default niche, voice, caption style, privacy, uploads per run
- `content/queue.yaml`: upcoming videos (the "content calendar"); top = next
- `content/posted.yaml`: upload log (written by the job; don't hand-edit)
- `shorts/`: code (`tts.py`, `captions.py`, `visuals.py`, `render.py`, `upload.py`, `__main__.py`)
- `SETUP.md`: one-time account setup guide for the owner

## Common requests
- **"Change the niche to X"**: set `channel.niche` in `config.yaml`, then write a
  fresh batch of scripts for X (default 30) and **replace** the unposted entries
  in `content/queue.yaml` (ask first if they'd rather keep the existing ones).
  Update `search_terms`, `tags`, and the closing line of each script to fit.
- **"Make one video about Y" / "tomorrow's video should be Y"**: add a single entry
  at the **top** of the queue with `niche: Y`. Don't touch `config.yaml`.
- **"I need more videos" / queue is low**: append a new batch in the current niche;
  check `content/posted.yaml` and the queue so topics don't repeat.
- **"Post N times a day"**: set `schedule.uploads_per_run` (max ~6/day on the free
  API quota), or add more `cron` lines to the workflow.
- **Change voice / caption look / time of day**: `config.yaml`, or the cron line in
  the workflow (UTC).

## Writing scripts (queue entries)
- Default is `dialogue:` — a list of `[speaker, "line"]` using the character keys
  (`dave`, `pip`). Pattern: Dave says/asks something naive, Pip answers with the
  fact, Dave reacts, Pip lands the lesson, Dave ends with the call to action.
  8–11 short lines. `script:` (single narrator) still works for one-off videos.
- 85–140 words in total (≈30–55 s). Hook in the first line; no slow intros.
- Short sentences, spoken style, no emojis or symbols in `script` (the voice reads them).
  Spell numbers the way they should be spoken when it matters.
- End with a short call to action (e.g. "Follow for one strange fact every day.").
- `title` ≤ 100 chars, curiosity-driven, may include one emoji.
- `search_terms`: 4–6 concrete, filmable stock-footage queries (e.g. "octopus swimming",
  not "biology"), one per scene, in story order.
- `tags`: 4–6 relevant tags. `id`: short kebab-case, unique, never reused.
- Money niche: explain facts and maths, never tell viewers what to buy or invest in.
- Facts must be accurate; no medical/financial advice, no real people's likeness,
  no copyrighted text. Vary topics and structure; YouTube penalises
  repetitive mass-produced content.

## After editing
1. `python -m shorts status`: must print no `PROBLEM:` lines.
2. Optional local preview: `SHORTS_VOICES=espeak python -m shorts preview <id>`
   (Edge TTS needs a WebSocket connection that some sandboxes block; GitHub Actions is fine).
3. Commit and push to the repository's **default branch**. The scheduled job only
   runs there and reads the queue from there.
