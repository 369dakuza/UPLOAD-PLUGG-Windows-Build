from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .constants import DEFAULT_CATEGORY_ID, DEFAULT_SCHEDULE_DAYS, DEFAULT_TIMEZONE


LEGACY_AUTOMATIC_TAGS_TEMPLATE = (
    "{ARTIST} type beat, {BEAT_NAME}, {PRODUCER}, {YEAR} type beat"
)
CHIEF_KEEF_DESCRIPTION_TEMPLATE = (
    "🎧 Free for non-profit use only – Must credit: [{PRODUCER_CREDITS}]\n\n"
    "💰 Need the exclusive rights or license?\n"
    "DM me on Instagram: www.instagram.com/369dakuza\n\n"
    "📩 Collabs / Questions:\n"
    "Email: 369dakuza@gmail.com\n"
    "IG: @369dakuza\n\n\n"
    "Tags (ignore):\n"
    "Chief Keef type beat, Chief Keef type beat {YEAR}, hard Chief Keef type beat, "
    "Shawn Ferrari type beat, Shawn Ferrari type beat {YEAR}, hard Shawn Ferrari type beat, "
    "Gucci Mane type beat, Gucci Mane type beat {YEAR}, hard Gucci Mane type beat, "
    "Mexiko Dro type beat, Mexiko Dro type beat {YEAR}, hard Mexiko Dro type beat, "
    "Bankroll Fresh type beat, Bankroll Fresh type beat {YEAR}, hard Bankroll Fresh type beat, "
    "D.Rich type beat, D.Rich type beat {YEAR}, hard D.Rich type beat, "
    "Shawty Redd type beat, Shawty Redd type beat {YEAR}, hard Shawty Redd type beat, "
    "Jeezy type beat, Jeezy type beat {YEAR}, hard Jeezy type beat, "
    "Zukeene type beat, Zukeene type beat {YEAR}, hard Zukeene type beat, "
    "Akachi type beat, Akachi type beat {YEAR}, hard Akachi type beat, "
    "Glo type beat, Glo type beat {YEAR}, hard Glo type beat, "
    "Karma2zz type beat, Karma2zz type beat {YEAR}, hard Karma2zz type beat, "
    "Tadoe type beat, Tadoe type beat {YEAR}, hard Tadoe type beat, "
    "Ballout type beat, Ballout type beat {YEAR}, hard Ballout type beat, "
    "Glo Gang type beat, Glo Gang type beat {YEAR}, hard Glo Gang type beat, "
    "Atlanta type beat, Atlanta type beat {YEAR}, hard Atlanta type beat, "
    "Chicago type beat, Chicago type beat {YEAR}, hard Chicago type beat"
)


@dataclass
class Preset:
    name: str = "Chief Keef Type Beat"
    producer: str = "Dakuza"
    artist: str = "Chief Keef"
    second_artist: str = ""
    title_template: str = '[FREE] {ARTIST} Type Beat - "{BEAT_NAME}"'
    description_template: str = CHIEF_KEEF_DESCRIPTION_TEMPLATE
    tags_template: str = ""
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
        values = {key: value for key, value in data.items() if key in allowed}
        if values.get("tags_template", "").strip() == LEGACY_AUTOMATIC_TAGS_TEMPLATE:
            values["tags_template"] = ""
        return cls(**values)


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
