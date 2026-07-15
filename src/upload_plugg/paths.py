from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config: Path
    cache: Path
    logs: Path
    exports: Path
    database: Path
    oauth_client: Path

    @classmethod
    def discover(cls, override: Path | None = None) -> "AppPaths":
        if override is not None:
            root = Path(override)
        elif sys.platform == "win32":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "UploadPlugg"
        else:
            root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "UploadPlugg"
        return cls(
            root=root,
            config=root / "config",
            cache=root / "cache",
            logs=root / "logs",
            exports=root / "exports",
            database=root / "upload_plugg.sqlite3",
            oauth_client=root / "config" / "client_secret.json",
        )

    def ensure(self) -> "AppPaths":
        for directory in (self.root, self.config, self.cache, self.logs, self.exports):
            directory.mkdir(parents=True, exist_ok=True)
        return self

