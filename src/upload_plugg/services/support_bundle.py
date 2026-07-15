from __future__ import annotations

import json
import platform
import re
import zipfile
from pathlib import Path

from .. import APP_NAME, APP_VERSION
from ..paths import AppPaths


SECRET_PATTERN = re.compile(r"(?i)(access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|password)\s*[:=]\s*[^\s,]+")


def create_support_bundle(paths: AppPaths, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostic.json", json.dumps(report, indent=2))
        for log in paths.logs.glob("*.log*"):
            try:
                safe = SECRET_PATTERN.sub(r"\1=[REDACTED]", log.read_text(encoding="utf-8", errors="replace"))
                archive.writestr(f"logs/{log.name}", safe)
            except OSError:
                continue
    return target

