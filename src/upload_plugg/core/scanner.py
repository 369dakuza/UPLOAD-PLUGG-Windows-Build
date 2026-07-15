from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Callable, Iterable

from ..models import UploadItem
from .filename_parser import parse_filename


NATURAL_TOKEN = re.compile(r"(\d+)")


def natural_key(value: str) -> tuple[object, ...]:
    return tuple(int(part) if part.isdigit() else part.casefold() for part in NATURAL_TOKEN.split(value))


def scan_videos(folder: str | Path, sorting: str = "natural", limit: int = 30) -> list[UploadItem]:
    directory = Path(folder)
    if not directory.is_dir():
        raise FileNotFoundError(f"Video folder does not exist: {directory}")
    files = [path for path in directory.iterdir() if path.is_file() and path.suffix.casefold() == ".mp4"]
    files = sort_paths(files, sorting)
    items: list[UploadItem] = []
    for path in files[: max(1, min(limit, 30))]:
        parsed = parse_filename(path.name)
        stat = path.stat()
        items.append(
            UploadItem(
                source_path=str(path.resolve()),
                beat_name=parsed.beat_name,
                collaborator=parsed.collaborator,
                file_size=stat.st_size,
                modified_ns=stat.st_mtime_ns,
                validation_messages=list(parsed.warnings),
            )
        )
    return items


def sort_paths(paths: Iterable[Path], mode: str) -> list[Path]:
    values = list(paths)
    reverse = mode in {"name_desc", "created_newest", "modified_newest"}
    if mode in {"name", "name_desc"}:
        key: Callable[[Path], object] = lambda p: p.name.casefold()
    elif mode in {"created_oldest", "created_newest"}:
        key = lambda p: p.stat().st_ctime_ns
    elif mode in {"modified_oldest", "modified_newest"}:
        key = lambda p: p.stat().st_mtime_ns
    elif mode == "manual":
        return values
    else:
        key = lambda p: natural_key(p.name)
    return sorted(values, key=key, reverse=reverse)


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()


def file_is_readable(path: str | Path) -> bool:
    source = Path(path)
    return source.is_file() and os.access(source, os.R_OK)

