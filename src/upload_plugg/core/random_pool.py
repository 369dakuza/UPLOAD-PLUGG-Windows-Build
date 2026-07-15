from __future__ import annotations

import random
from pathlib import Path


VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def image_pool(folder: str | Path) -> list[Path]:
    directory = Path(folder)
    if not directory.is_dir():
        return []
    return sorted(
        [p for p in directory.iterdir() if p.is_file() and p.suffix.casefold() in VALID_IMAGE_EXTENSIONS],
        key=lambda p: p.name.casefold(),
    )


def assign_without_repeats(
    item_ids: list[str], images: list[Path], seed: int | None = None
) -> dict[str, str]:
    if not images:
        return {}
    randomizer = random.Random(seed)
    result: dict[str, str] = {}
    cycle: list[Path] = []
    for item_id in item_ids:
        if not cycle:
            cycle = list(images)
            randomizer.shuffle(cycle)
        result[item_id] = str(cycle.pop())
    return result

