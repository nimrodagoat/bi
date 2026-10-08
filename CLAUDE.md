# YouTube Shorts autopilot

A GitHub Actions job (`.github/workflows/daily-short.yml`) runs daily, takes the
first entry of `content/queue.yaml`, renders a vertical Short and uploads it; then
it moves the entry to `content/posted.yaml` and commits. Everything is free: Edge
TTS (Piper fallback), ffmpeg, YouTube Data API.

Current format: **text-message storytimes**. Each queue entry has `contact:` and
`messages:` ([me, "..."] / [them, "..."]); `shorts/chat.py` draws an iMessage-style
panel (bundled Inter font in `assets/fonts/`) that fills up one message at a time
over the owner's Minecraft parkour clip (`assets/gameplay/minecraft-parkour.mp4`,
cropped to vertical so the creator's watermark is outside the frame; credit
"@rephyr2000 on TikTok" goes in the description via `visuals.gameplay_credits`).
Each message is read out: `me:` / `them:` pick voice presets from `chat.voices`
in `config.yaml` (male, female, young_male, young_female, old_male, deep_male).
No music under stories by default (`chat.music`). Stories: 20–28 short messages,
~90–150 words (≈45–60 s), lower-case texting style, a hook in the first message,
a twist or punchline at the end; mix suspense-with-a-twist, comedy and wholesome;
all original (never copy other channels' stories); no emoji inside messages (the
font can't draw them; titles may have one).

Older formats still work and are archived in `content/archive/`: cartoon duos
(Dave & Pip, Grug & Nova; `dialogue:` entries, art in `assets/characters/`,
regenerate with `tools/characters.mjs` → `tools/sticker.py` → `tools/design_sheet.py`),
and narrated `script:` videos. Music for those: `assets/music/` or Kevin MacLeod
CC BY tracks (credit added automatically); never copyrighted songs or
synthesised beats. Background fallback when no gameplay file exists: generated
Minecraft-style parkour (`shorts/parkour.py`). Never use footage downloaded
from others unless the owner confirms it's free to use.

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
  (`dave`/`pip` or `grug`/`nova`). Pattern: the naive one says/asks something,
  the smart one answers with the fact, reaction, lesson, the naive one ends with
  the call to action. Grug speaks caveman English ("Grug no understand paper").
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
