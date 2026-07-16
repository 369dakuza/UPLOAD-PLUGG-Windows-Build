from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .models import LEGACY_AUTOMATIC_TAGS_TEMPLATE, Preset
from .paths import AppPaths


DEFAULT_SETTINGS: dict[str, Any] = {
    "version": 2,
    "window": {"width": 1500, "height": 900, "last_page": 0},
    "appearance": {"reduce_motion": False},
    "upload": {"keep_awake": True, "max_retries": 5, "chunk_size_mb": 8},
    "folders": {"videos": "", "thumbnails": "", "thumbnail_output": ""},
    "queue": [],
    "thumbnail_assignments": {},
    "channel": {"id": "", "name": "", "image_url": ""},
    "presets": [Preset().to_dict()],
    "active_preset": "Chief Keef Type Beat",
}


class SettingsStore:
    def __init__(self, paths: AppPaths):
        self.path = paths.config / "settings.json"
        self.data = deepcopy(DEFAULT_SETTINGS)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            self.save()
            return self.data
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            loaded, migrated = _migrate_settings(loaded)
            self.data = _deep_merge(deepcopy(DEFAULT_SETTINGS), loaded)
            if migrated:
                self.save()
        except (OSError, json.JSONDecodeError, TypeError):
            broken = self.path.with_suffix(".broken.json")
            try:
                self.path.replace(broken)
            except OSError:
                pass
            self.data = deepcopy(DEFAULT_SETTINGS)
            self.save()
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.path)

    def presets(self) -> list[Preset]:
        return [Preset.from_dict(item) for item in self.data.get("presets", [])]

    def upsert_preset(self, preset: Preset) -> None:
        raw = self.data.setdefault("presets", [])
        for index, item in enumerate(raw):
            if item.get("name", "").casefold() == preset.name.casefold():
                raw[index] = preset.to_dict()
                break
        else:
            raw.append(preset.to_dict())
        self.data["active_preset"] = preset.name
        self.save()

    def delete_preset(self, name: str) -> bool:
        raw = self.data.setdefault("presets", [])
        if len(raw) <= 1:
            return False
        remaining = [item for item in raw if item.get("name", "").casefold() != name.casefold()]
        if len(remaining) == len(raw):
            return False
        self.data["presets"] = remaining
        self.data["active_preset"] = remaining[0]["name"]
        self.save()
        return True


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _migrate_settings(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    try:
        version = int(data.get("version", 1))
    except (TypeError, ValueError):
        version = 1
    if version >= 2:
        return data, False
    for preset in data.get("presets", []):
        if not isinstance(preset, dict):
            continue
        if preset.get("tags_template", "").strip() == LEGACY_AUTOMATIC_TAGS_TEMPLATE:
            preset["tags_template"] = ""
        preset.setdefault("made_for_kids", False)
    data["version"] = 2
    return data, True
