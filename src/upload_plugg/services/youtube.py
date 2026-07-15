from __future__ import annotations

import json
import logging
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from ..constants import TRANSIENT_HTTP_STATUS
from ..models import Preset, UploadItem


ProgressCallback = Callable[[int, int, int, float, str], None]


@dataclass(frozen=True)
class ChannelIdentity:
    id: str
    name: str
    image_url: str


class UploadCancelled(RuntimeError):
    pass


class YouTubeService:
    def __init__(self, credentials: Credentials, logger: logging.Logger | None = None):
        self.credentials = credentials
        self.api = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        self.logger = logger or logging.getLogger("upload_plugg.youtube")

    def channel_identity(self) -> ChannelIdentity:
        response = self.api.channels().list(part="snippet", mine=True).execute()
        items = response.get("items", [])
        if not items:
            raise RuntimeError("No YouTube channel is available for the authorized account.")
        channel = items[0]
        thumbnails = channel.get("snippet", {}).get("thumbnails", {})
        image = thumbnails.get("default", {}).get("url", "")
        return ChannelIdentity(channel["id"], channel["snippet"]["title"], image)

    def upload_video(
        self,
        item: UploadItem,
        preset: Preset,
        thumbnail_path: str = "",
        max_retries: int = 5,
        chunk_size: int = 8 * 1024 * 1024,
        progress: ProgressCallback | None = None,
        cancelled: threading.Event | None = None,
        paused: threading.Event | None = None,
        session_callback: Callable[[str], None] | None = None,
    ) -> dict[str, str]:
        body = self._video_body(item, preset)
        media = MediaFileUpload(
            item.source_path, chunksize=chunk_size, resumable=True, mimetype="video/mp4"
        )
        request = self.api.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        retries = 0
        started = time.monotonic()
        last_bytes = 0
        last_time = started
        while response is None:
            if cancelled and cancelled.is_set():
                raise UploadCancelled("Upload cancelled by the user.")
            while paused and paused.is_set():
                if cancelled and cancelled.is_set():
                    raise UploadCancelled("Upload cancelled by the user.")
                time.sleep(0.25)
            try:
                status, response = request.next_chunk()
                if request.resumable_uri and session_callback:
                    session_callback(request.resumable_uri)
                    session_callback = None
                if status and progress:
                    uploaded = int(status.resumable_progress)
                    now = time.monotonic()
                    speed = (uploaded - last_bytes) / max(now - last_time, 0.001)
                    progress(int(status.progress() * 100), uploaded, item.file_size, speed, "Uploading")
                    last_bytes, last_time = uploaded, now
                retries = 0
            except HttpError as exc:
                if exc.resp.status not in TRANSIENT_HTTP_STATUS or retries >= max_retries:
                    raise RuntimeError(_friendly_http_error(exc)) from exc
                retries += 1
                delay = min(60.0, (2**retries) + random.random())
                self.logger.warning("Transient YouTube error status=%s retry=%s", exc.resp.status, retries)
                if progress:
                    progress(0, last_bytes, item.file_size, 0.0, f"Retrying in {delay:.1f}s")
                _interruptible_wait(delay, cancelled)
            except (OSError, httplib2.HttpLib2Error) as exc:
                if retries >= max_retries:
                    raise RuntimeError(f"Network upload failed after {max_retries} retries: {exc}") from exc
                retries += 1
                _interruptible_wait(min(60.0, (2**retries) + random.random()), cancelled)
        video_id = response["id"]
        if thumbnail_path:
            self.api.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            if progress:
                progress(100, item.file_size, item.file_size, 0.0, "Thumbnail Applied")
        return {
            "id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        }

    def recent_titles(self, limit: int = 50) -> list[dict[str, str]]:
        channels = self.api.channels().list(part="contentDetails", mine=True).execute()
        uploads = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        response = self.api.playlistItems().list(
            part="snippet", playlistId=uploads, maxResults=min(limit, 50)
        ).execute()
        return [
            {"video_id": row["snippet"]["resourceId"]["videoId"], "title": row["snippet"]["title"]}
            for row in response.get("items", [])
        ]

    @staticmethod
    def _video_body(item: UploadItem, preset: Preset) -> dict[str, object]:
        snippet: dict[str, object] = {
            "title": item.display_title,
            "description": item.description,
            "tags": item.tags,
            "categoryId": preset.category_id,
        }
        if preset.language:
            snippet["defaultLanguage"] = preset.language
        status: dict[str, object] = {
            "privacyStatus": "private" if item.publish_at else "private",
            "selfDeclaredMadeForKids": preset.made_for_kids,
            "containsSyntheticMedia": preset.contains_synthetic_media,
            "embeddable": preset.embeddable,
            "license": preset.license,
        }
        if item.publish_at:
            scheduled = datetime.fromisoformat(item.publish_at)
            status["publishAt"] = scheduled.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return {"snippet": snippet, "status": status}


class MockYouTubeService:
    """Deterministic service used by tests and the sample Dry Run."""

    def channel_identity(self) -> ChannelIdentity:
        return ChannelIdentity("mock-channel", "UPLOAD PLUGG Test Channel", "")

    def upload_video(self, item: UploadItem, preset: Preset, **kwargs: object) -> dict[str, str]:
        progress = kwargs.get("progress")
        if callable(progress):
            progress(100, item.file_size, item.file_size, 1_000_000.0, "Completed")
        video_id = "mock_" + item.id[:12]
        return {
            "id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        }


def _friendly_http_error(error: HttpError) -> str:
    try:
        payload = json.loads(error.content.decode("utf-8"))
        message = payload.get("error", {}).get("message", str(error))
        reason = payload.get("error", {}).get("errors", [{}])[0].get("reason", "")
        return f"YouTube API error {error.resp.status}: {message}" + (f" ({reason})" if reason else "")
    except Exception:
        return f"YouTube API error {error.resp.status}: {error}"


def _interruptible_wait(seconds: float, cancelled: threading.Event | None) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if cancelled and cancelled.is_set():
            raise UploadCancelled("Upload cancelled by the user.")
        time.sleep(min(0.25, deadline - time.monotonic()))
