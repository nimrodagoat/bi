"""Upload a finished video to YouTube with the official Data API."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from .render import spoken_text

SCOPE = "https://www.googleapis.com/auth/youtube.upload"
SECRETS = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")


class QuotaExceeded(RuntimeError):
    pass


def missing_secrets() -> list[str]:
    return [name for name in SECRETS if not os.environ.get(name)]


def _clean(text: str, limit: int) -> str:
    # YouTube rejects < and > in titles and descriptions.
    return re.sub(r"[<>]", "", text).strip()[:limit]


def build_metadata(item: dict, cfg: dict) -> dict:
    title = _clean(str(item["title"]), 100)
    tags = [str(t).lstrip("#") for t in (item.get("tags") or [])]
    tags += [t for t in cfg.get("upload", {}).get("extra_tags", []) if t not in tags]
    # The API caps tags at ~500 characters in total.
    kept, size = [], 0
    for t in tags:
        size += len(t) + 3
        if size > 480:
            break
        kept.append(t)

    description = item.get("description")
    if not description and item.get("dialogue"):
        description = title  # a dialogue's first line reads oddly out of context
    if not description:
        sentences = re.split(r"(?<=[.!?])\s+", spoken_text(item))
        description = " ".join(sentences[:2])
    hashtags = " ".join(f"#{t.replace(' ', '')}" for t in kept[:3])
    if "#shorts" not in description.lower():
        hashtags = (hashtags + " #shorts").strip()
    credit = f"\n\nMusic: {item['music_credit']}" if item.get("music_credit") else ""
    description = _clean(f"{description}\n\n{hashtags}{credit}", 5000)

    up = cfg.get("upload", {})
    lang = cfg.get("channel", {}).get("language", "en")
    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": kept,
            "categoryId": str(up.get("category_id", "27")),
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": {
            "privacyStatus": up.get("privacy", "public"),
            "selfDeclaredMadeForKids": bool(up.get("made_for_kids", False)),
        },
    }


def upload(video: Path, item: dict, cfg: dict) -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[SCOPE],
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body=build_metadata(item, cfg),
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", chunksize=-1, resumable=True),
    )
    try:
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  uploading… {int(status.progress() * 100)}%")
    except HttpError as e:
        reason = str(e)
        if "quotaExceeded" in reason or "uploadLimitExceeded" in reason:
            raise QuotaExceeded(
                "YouTube's daily upload limit was reached; the video stays in the queue for tomorrow."
            ) from e
        raise
    video_id = response["id"]
    privacy = response.get("status", {}).get("privacyStatus")
    wanted = cfg.get("upload", {}).get("privacy", "public")
    if privacy and privacy != wanted:
        print(
            f"  note: YouTube set this video to '{privacy}' (you asked for '{wanted}'). "
            "Unaudited API projects can only upload private videos; see SETUP.md step 6.",
            file=sys.stderr,
        )
    return video_id
