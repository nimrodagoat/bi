# Shorts Autopilot

Posts a YouTube Short every day, automatically and for free.

**Script** (from `content/queue.yaml`) → **AI voice** (Edge TTS) → **word-by-word captions**
→ **stock footage** (Pexels) → **vertical 1080×1920 MP4** → **upload** (YouTube API),
run daily by GitHub Actions.

- First time? Follow **[SETUP.md](SETUP.md)**.
- Change the topic: edit `channel.niche` in [`config.yaml`](config.yaml), or just ask Claude:
  *"change the niche to cooking hacks"* or *"make tomorrow's video about black holes"*.
- See what's coming up: [`content/queue.yaml`](content/queue.yaml). What's been posted: [`content/posted.yaml`](content/posted.yaml).

Run locally (needs Python 3.10+ and ffmpeg):

```bash
pip install -r requirements.txt
python -m shorts status          # what's queued, and checks for mistakes
python -m shorts preview         # render the next video to output/
python -m shorts run --dry-run   # same as the daily job, without uploading
```
