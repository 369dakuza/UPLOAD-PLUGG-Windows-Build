from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .constants import DEFAULT_CATEGORY_ID, DEFAULT_SCHEDULE_DAYS, DEFAULT_TIMEZONE


@dataclass
class Preset:
    name: str = "Chief Keef Type Beat"
    producer: str = "Dakuza"
    artist: str = "Chief Keef"
    second_artist: str = ""
    title_template: str = '[FREE] {ARTIST} Type Beat - "{BEAT_NAME}"'
    description_template: str = (
        "{BEAT_NAME}\n\nMust credit: {PRODUCER_CREDITS}\n\n"
        "Replace this example with your complete YouTube description."
    )
    tags_template: str = "{ARTIST} type beat, {BEAT_NAME}, {PRODUCER}, {YEAR} type beat"
    category_id: str = DEFAULT_CATEGORY_ID
    made_for_kids: bool = False
    contains_synthetic_media: bool = False
    embeddable: bool = True
    license: str = "youtube"
    language: str = "en"
    credit_separator: str = "&"
    default_batch_size: int = 10
    sorting_mode: str = "natural"
    timezone: str = DEFAULT_TIMEZONE
    schedule_days: list[int] = field(default_factory=lambda: list(DEFAULT_SCHEDULE_DAYS))
    schedule_time: str = "18:00"
    thumbnail_mode: str = "none"
    thumbnail_folder: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Preset":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class UploadItem:
    source_path: str
    beat_name: str
    collaborator: str = ""
    display_title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    preset_name: str = "Chief Keef Type Beat"
    thumbnail_path: str = ""
    publish_at: str = ""
    selected: bool = True
    validation_status: str = "Not checked"
    validation_messages: list[str] = field(default_factory=list)
    upload_status: str = "Ready"
    progress: int = 0
    youtube_id: str = ""
    youtube_url: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)
    file_size: int = 0
    modified_ns: int = 0
    file_hash: str = ""

    @property
    def filename(self) -> str:
        return Path(self.source_path).name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UploadItem":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class UploadResult:
    item_id: str
    status: str
    youtube_id: str = ""
    youtube_url: str = ""
    error: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    completed_at: str = ""
