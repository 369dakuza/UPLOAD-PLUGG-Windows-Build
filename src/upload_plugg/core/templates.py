from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Mapping

from ..models import Preset, UploadItem


PLACEHOLDER_PATTERN = re.compile(r"\{[A-Z][A-Z0-9_]*\}")


def producer_credits(producer: str, collaborator: str, separator: str = "&") -> str:
    producer = producer.strip()
    collaborator = collaborator.strip()
    base = f"Prod. {producer}" if producer else "Prod."
    return f"{base} {separator.strip() or '&'} {collaborator}" if collaborator else base


def render_template(template: str, values: Mapping[str, object]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key.upper() + "}", str(value or ""))
    rendered = re.sub(r"[ \t]+\n", "\n", rendered)
    return rendered.strip()


def unresolved_placeholders(text: str) -> list[str]:
    return sorted(set(PLACEHOLDER_PATTERN.findall(text)))


def split_tags(text: str) -> list[str]:
    tokens = re.split(r"[,\n]", text)
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        cleaned = token.strip()
        folded = cleaned.casefold()
        if cleaned and folded not in seen:
            result.append(cleaned)
            seen.add(folded)
    return result


def tag_length(tags: list[str]) -> int:
    return sum(len(tag) + (2 if " " in tag else 0) for tag in tags) + max(0, len(tags) - 1)


def hashtag_name(value: str) -> str:
    parts = re.findall(r"[^\W_]+", value, flags=re.UNICODE)
    return "".join(
        part[:1].upper() + part[1:] if part.islower() else part
        for part in parts
    )


def artist_for_hashtags(preset: Preset) -> str:
    if preset.artist.strip():
        return preset.artist.strip()
    return re.sub(
        r"(?i)\s*(?:[-–—]\s*)?type\s+beat(?:\s+preset)?\s*$",
        "",
        preset.name,
    ).strip()


def description_hashtags(preset: Preset, year: str | int) -> list[str]:
    artist = hashtag_name(artist_for_hashtags(preset))
    if not artist:
        return []
    return [
        f"#{artist}",
        f"#{artist}TypeBeat",
        f"#{artist}TypeBeat{year}",
    ]


def prepend_description_hashtags(description: str, hashtags: list[str]) -> str:
    if not hashtags:
        return description.strip()
    hashtag_line = " ".join(hashtags)
    if description.lstrip().casefold().startswith(hashtag_line.casefold()):
        return description.strip()
    return f"{hashtag_line}\n\n{description.strip()}" if description.strip() else hashtag_line


def values_for_item(
    item: UploadItem,
    preset: Preset,
    publish_at: datetime | None = None,
    bpm: str = "",
    key: str = "",
) -> dict[str, str]:
    now = datetime.now().astimezone()
    publication = publish_at or _parse_datetime(item.publish_at)
    return {
        "BEAT_NAME": item.beat_name,
        "COLLABORATOR": item.collaborator,
        "PRODUCER": preset.producer,
        "PRODUCER_CREDITS": producer_credits(
            preset.producer, item.collaborator, preset.credit_separator
        ),
        "YEAR": str((publication or now).year),
        "UPLOAD_DATE": now.strftime("%Y-%m-%d"),
        "PUBLISH_DATE": publication.strftime("%Y-%m-%d") if publication else "",
        "PUBLISH_TIME": publication.strftime("%H:%M") if publication else "",
        "VIDEO_FILENAME": Path(item.source_path).name,
        "BPM": bpm,
        "KEY": key,
        "ARTIST": preset.artist,
        "SECOND_ARTIST": preset.second_artist,
    }


def generate_metadata(item: UploadItem, preset: Preset) -> UploadItem:
    values = values_for_item(item, preset)
    item.display_title = render_template(preset.title_template, values)
    description = render_template(preset.description_template, values)
    item.description = prepend_description_hashtags(
        description,
        description_hashtags(preset, values["YEAR"]),
    )
    item.tags = split_tags(render_template(preset.tags_template, values))
    item.preset_name = preset.name
    return item


def migrate_credit_line(template: str, producer: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf"(?im)^(?P<prefix>\s*Must\s+credit\s*:\s*)Prod\.\s*{re.escape(producer)}\s*$"
    )
    updated, count = pattern.subn(r"\g<prefix>{PRODUCER_CREDITS}", template)
    return updated, bool(count)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
