from __future__ import annotations

from dataclasses import dataclass

from ..models import Preset, UploadItem


@dataclass(frozen=True)
class MockChannelIdentity:
    id: str = "mock-channel"
    name: str = "UPLOAD PLUGG Test Channel"
    image_url: str = ""


class MockYouTubeService:
    """Offline deterministic test double. It never performs a network request."""

    def channel_identity(self) -> MockChannelIdentity:
        return MockChannelIdentity()

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

