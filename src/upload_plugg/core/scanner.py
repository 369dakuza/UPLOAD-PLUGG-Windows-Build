from __future__ import annotations

import hashlib
import os
import re
import threading
from pathlib import Path
from typing import Callable, Iterable

from ..models import UploadItem
from .filename_parser import parse_filename


NATURAL_TOKEN = re.compile(r"(\d+)")


def natural_key(value: str) -> tuple[object, ...]:
    return tuple(int(part) if part.isdigit() else part.casefold() for part in NATURAL_TOKEN.split(value))


def scan_videos(
    folder: str | Path,
    sorting: str = "natural",
    limit: int = 30,
    cancelled: threading.Event | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[UploadItem]:
    """Build a fresh queue snapshot from a folder.

    Files can disappear while Windows, a DAW or a synchronisation client is
    updating the folder. Those transient entries are skipped instead of taking
    down the whole application. Cancellation is cooperative and checked between
    every file operation.
    """
    directory = Path(folder)
    if not directory.is_dir():
        raise FileNotFoundError(f"Video folder does not exist: {directory}")
    files: list[Path] = []
    try:
        candidates = list(directory.iterdir())
    except OSError as exc:
        raise OSError(f"Video folder could not be read: {directory}") from exc
    for path in candidates:
        if cancelled is not None and cancelled.is_set():
            return []
        try:
            if path.is_file() and path.suffix.casefold() == ".mp4":
                files.append(path)
        except OSError:
            continue
    files = sort_paths(files, sorting)
    items: list[UploadItem] = []
    selected = files[: max(1, min(limit, 30))]
    total = len(selected)
    for index, path in enumerate(selected, start=1):
        if cancelled is not None and cancelled.is_set():
            return []
        try:
            parsed = parse_filename(path.name)
            stat = path.stat()
            resolved = path.resolve()
        except OSError:
            continue
        items.append(
            UploadItem(
                source_path=str(resolved),
                beat_name=parsed.beat_name,
                collaborator=parsed.collaborator,
                file_size=stat.st_size,
                modified_ns=stat.st_mtime_ns,
                validation_messages=list(parsed.warnings),
            )
        )
        if progress is not None:
            progress(index, total)
    return items


def sort_paths(paths: Iterable[Path], mode: str) -> list[Path]:
    values = list(paths)
    reverse = mode in {"name_desc", "created_newest", "modified_newest"}
    if mode in {"name", "name_desc"}:
        def key(path: Path) -> object:
            return path.name.casefold()
    elif mode in {"created_oldest", "created_newest"}:
        def key(path: Path) -> object:
            return _safe_stat_value(path, "st_ctime_ns")
    elif mode in {"modified_oldest", "modified_newest"}:
        def key(path: Path) -> object:
            return _safe_stat_value(path, "st_mtime_ns")
    elif mode == "manual":
        return values
    else:
        def key(path: Path) -> object:
            return natural_key(path.name)
    return sorted(values, key=key, reverse=reverse)


def _safe_stat_value(path: Path, attribute: str) -> int:
    try:
        return int(getattr(path.stat(), attribute))
    except (OSError, AttributeError):
        return 0


def reconcile_scan(
    existing: Iterable[UploadItem],
    scanned: Iterable[UploadItem],
) -> tuple[list[UploadItem], int, int, int]:
    """Replace stale queue entries while preserving edits for files still present."""
    previous = {_path_key(item.source_path): item for item in existing}
    result: list[UploadItem] = []
    added = updated = 0
    for fresh in scanned:
        old = previous.pop(_path_key(fresh.source_path), None)
        if old is None:
            result.append(fresh)
            added += 1
            continue
        file_changed = old.file_size != fresh.file_size or old.modified_ns != fresh.modified_ns
        old.source_path = fresh.source_path
        old.file_size = fresh.file_size
        old.modified_ns = fresh.modified_ns
        if not old.beat_name:
            old.beat_name = fresh.beat_name
        if not old.collaborator:
            old.collaborator = fresh.collaborator
        if file_changed:
            old.file_hash = ""
            old.validation_status = "Not checked"
            old.validation_messages = list(fresh.validation_messages)
            old.upload_status = "Ready"
            old.progress = 0
            old.youtube_id = ""
            old.youtube_url = ""
            updated += 1
        result.append(old)
    return result, added, updated, len(previous)


def _path_key(value: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(value)))


def sha256_file(
    path: str | Path,
    chunk_size: int = 1024 * 1024,
    cancelled: threading.Event | None = None,
) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(chunk_size):
            if cancelled is not None and cancelled.is_set():
                return ""
            digest.update(block)
    return digest.hexdigest()


def file_is_readable(path: str | Path) -> bool:
    source = Path(path)
    return source.is_file() and os.access(source, os.R_OK)
