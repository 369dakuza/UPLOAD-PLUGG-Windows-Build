from __future__ import annotations

import csv
import json
from pathlib import Path

from ..models import UploadItem


def export_dry_run(items: list[UploadItem], target: Path, format_name: str) -> Path:
    selected = [item.to_dict() for item in items if item.selected]
    target.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "json":
        target.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    elif format_name == "csv":
        fields = ["source_path", "beat_name", "collaborator", "display_title", "description", "tags", "thumbnail_path", "publish_at", "validation_status", "validation_messages"]
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(selected)
    else:
        lines = ["UPLOAD PLUGG — DRY RUN REPORT", "No videos were uploaded.", ""]
        for index, item in enumerate(selected, start=1):
            lines.extend([
                f"{index}. {item['display_title']}",
                f"   File: {item['source_path']}",
                f"   Collaborator: {item['collaborator'] or 'None'}",
                f"   Publish: {item['publish_at'] or 'Not scheduled'}",
                f"   Thumbnail: {item['thumbnail_path'] or 'YouTube default'}",
                f"   Validation: {item['validation_status']}",
                "",
            ])
        target.write_text("\n".join(lines), encoding="utf-8")
    return target

