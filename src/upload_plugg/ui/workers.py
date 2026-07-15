from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..core.scanner import sha256_file
from ..core.thumbnails import ensure_upload_thumbnail
from ..database import Database
from ..models import Preset, UploadItem, UploadResult
from ..paths import AppPaths
from ..services.keep_awake import KeepAwake
from ..services.youtube import UploadCancelled, YouTubeService


class FunctionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self.function(*self.args, **self.kwargs))
        except Exception as exc:
            self.failed.emit(str(exc))


class UploadQueueWorker(QObject):
    item_progress = Signal(str, int, str)
    item_finished = Signal(str, str, str)
    queue_finished = Signal(int, int)
    failed = Signal(str)

    def __init__(
        self,
        credentials,
        items: list[UploadItem],
        preset: Preset,
        database: Database,
        paths: AppPaths,
        channel_id: str,
        channel_name: str,
        max_retries: int,
        chunk_size: int,
        keep_awake: bool,
        logger: logging.Logger,
    ):
        super().__init__()
        self.credentials = credentials
        self.items = items
        self.preset = preset
        self.database = database
        self.paths = paths
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.should_keep_awake = keep_awake
        self.logger = logger
        self.cancelled = threading.Event()
        self.paused = threading.Event()

    @Slot()
    def run(self) -> None:
        completed = 0
        failed = 0
        keep_awake = KeepAwake()
        try:
            if self.should_keep_awake:
                keep_awake.enable()
            service = YouTubeService(self.credentials, self.logger)
            for item in self.items:
                if self.cancelled.is_set():
                    item.upload_status = "Cancelled"
                    break
                result = UploadResult(item.id, "Failed")
                try:
                    item.upload_status = "Uploading"
                    if not item.file_hash:
                        self.item_progress.emit(item.id, 0, "Hashing")
                        item.file_hash = sha256_file(item.source_path)
                    thumbnail = ""
                    if item.thumbnail_path:
                        self.item_progress.emit(item.id, 0, "Preparing Thumbnail")
                        thumbnail = str(ensure_upload_thumbnail(item.thumbnail_path, self.paths.cache))

                    def update(percent: int, uploaded: int, total: int, speed: float, stage: str) -> None:
                        speed_mb = speed / (1024 * 1024)
                        label = f"{stage} · {uploaded / 1048576:.1f}/{total / 1048576:.1f} MB · {speed_mb:.1f} MB/s"
                        self.item_progress.emit(item.id, percent, label)

                    remote = service.upload_video(
                        item,
                        self.preset,
                        thumbnail_path=thumbnail,
                        max_retries=self.max_retries,
                        chunk_size=self.chunk_size,
                        progress=update,
                        cancelled=self.cancelled,
                        paused=self.paused,
                    )
                    result = UploadResult(
                        item.id,
                        "Completed",
                        youtube_id=remote["id"],
                        youtube_url=remote["url"],
                        completed_at=datetime.now().astimezone().isoformat(),
                    )
                    item.youtube_id = result.youtube_id
                    item.youtube_url = result.youtube_url
                    item.upload_status = "Completed"
                    item.progress = 100
                    completed += 1
                    self.item_finished.emit(item.id, "Completed", result.youtube_url)
                except UploadCancelled as exc:
                    result.error = str(exc)
                    result.status = "Cancelled"
                    item.upload_status = "Cancelled"
                    self.item_finished.emit(item.id, "Cancelled", str(exc))
                    self.database.add_upload(item, result, self.channel_id, self.channel_name)
                    break
                except Exception as exc:
                    failed += 1
                    result.error = str(exc)
                    result.completed_at = datetime.now().astimezone().isoformat()
                    item.upload_status = "Failed"
                    self.logger.exception("Upload failed item=%s", item.id)
                    self.item_finished.emit(item.id, "Failed", str(exc))
                self.database.add_upload(item, result, self.channel_id, self.channel_name)
                self.database.save_queue(self.items)
        except Exception as exc:
            self.logger.exception("Upload queue failed")
            self.failed.emit(str(exc))
        finally:
            keep_awake.disable()
            self.queue_finished.emit(completed, failed)

    @Slot()
    def pause(self) -> None:
        self.paused.set()

    @Slot()
    def resume(self) -> None:
        self.paused.clear()

    @Slot()
    def cancel(self) -> None:
        self.cancelled.set()
