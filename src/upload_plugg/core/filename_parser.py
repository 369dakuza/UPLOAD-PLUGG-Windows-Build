from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


FINAL_COLLABORATOR = re.compile(r"^(?P<beat>.+?)\s*\((?P<collab>[^()]+)\)\s*$", re.UNICODE)


@dataclass(frozen=True)
class ParsedFilename:
    beat_name: str
    collaborator: str
    warnings: tuple[str, ...] = ()


def parse_filename(filename: str) -> ParsedFilename:
    stem = Path(filename).stem.strip()
    warnings: list[str] = []
    if not stem:
        return ParsedFilename("", "", ("The filename has no usable beat name.",))
    match = FINAL_COLLABORATOR.fullmatch(stem)
    if match:
        beat = match.group("beat").strip()
        collaborator = match.group("collab").strip()
        if not beat or not collaborator:
            warnings.append("The final parenthetical collaborator group is incomplete.")
            return ParsedFilename(stem, "", tuple(warnings))
        return ParsedFilename(beat, collaborator, tuple(warnings))
    if "(" in stem or ")" in stem:
        warnings.append(
            "Parentheses were found but the final collaborator group is uncertain; review manually."
        )
    return ParsedFilename(stem, "", tuple(warnings))

