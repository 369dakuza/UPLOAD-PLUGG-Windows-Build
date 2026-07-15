from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image, UnidentifiedImageError

from ..constants import (
    YOUTUBE_DESCRIPTION_LIMIT_BYTES,
    YOUTUBE_TAGS_LIMIT,
    YOUTUBE_THUMBNAIL_LIMIT_BYTES,
    YOUTUBE_TITLE_LIMIT,
)
from ..models import UploadItem
from .scanner import file_is_readable
from .templates import tag_length, unresolved_placeholders


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str
    fix: str


def validate_item(item: UploadItem, require_online: bool = False, connected: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    source = Path(item.source_path)
    if not source.exists():
        issues.append(ValidationIssue("error", "The source video was moved or deleted.", "Scan the folder again."))
    elif source.suffix.casefold() != ".mp4":
        issues.append(ValidationIssue("error", "The source file is not an MP4.", "Choose an MP4 video."))
    elif not file_is_readable(source):
        issues.append(ValidationIssue("error", "The video cannot be read.", "Check file permissions and close programs locking the file."))
    if not item.beat_name.strip():
        issues.append(ValidationIssue("error", "Beat Name is empty.", "Enter a beat name."))
    if not item.display_title.strip():
        issues.append(ValidationIssue("error", "The generated title is empty.", "Generate metadata or enter a title."))
    elif len(item.display_title) > YOUTUBE_TITLE_LIMIT:
        issues.append(ValidationIssue("error", f"The title exceeds {YOUTUBE_TITLE_LIMIT} characters.", "Shorten the title."))
    for placeholder in unresolved_placeholders(item.display_title):
        issues.append(ValidationIssue("error", f"Unresolved title placeholder: {placeholder}", "Edit the preset or provide the missing value."))
    if len(item.description.encode("utf-8")) > YOUTUBE_DESCRIPTION_LIMIT_BYTES:
        issues.append(ValidationIssue("error", f"The description exceeds {YOUTUBE_DESCRIPTION_LIMIT_BYTES} UTF-8 bytes.", "Shorten the description."))
    for placeholder in unresolved_placeholders(item.description):
        issues.append(ValidationIssue("error", f"Unresolved description placeholder: {placeholder}", "Edit the preset or provide the missing value."))
    if tag_length(item.tags) > YOUTUBE_TAGS_LIMIT:
        issues.append(ValidationIssue("error", "The combined tags exceed YouTube's 500-character calculation.", "Remove tags."))
    if item.thumbnail_path:
        issues.extend(_validate_thumbnail(Path(item.thumbnail_path)))
    if item.publish_at:
        try:
            scheduled = datetime.fromisoformat(item.publish_at)
            if scheduled.tzinfo is None:
                raise ValueError
            if scheduled <= datetime.now(scheduled.tzinfo):
                issues.append(ValidationIssue("error", "The publication time is in the past.", "Choose a future schedule slot."))
        except ValueError:
            issues.append(ValidationIssue("error", "The publication timestamp is invalid.", "Recalculate the schedule."))
    if require_online and not connected:
        issues.append(ValidationIssue("error", "No YouTube channel is connected.", "Connect and confirm a YouTube channel."))
    return issues


def validate_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except ZoneInfoNotFoundError:
        return False


def _validate_thumbnail(path: Path) -> list[ValidationIssue]:
    if not path.is_file():
        return [ValidationIssue("error", "The assigned thumbnail is unavailable.", "Assign another thumbnail.")]
    if path.suffix.casefold() not in {".jpg", ".jpeg", ".png"}:
        return [ValidationIssue("error", "The thumbnail format is unsupported.", "Use JPG or PNG.")]
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        return [ValidationIssue("error", "The thumbnail is damaged or unreadable.", "Assign a valid image.")]
    if path.stat().st_size > YOUTUBE_THUMBNAIL_LIMIT_BYTES:
        return [ValidationIssue("warning", "The thumbnail exceeds 2 MB and will be converted in the upload cache.", "No action is required unless conversion fails.")]
    return []

