from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

from ..constants import YOUTUBE_THUMBNAIL_LIMIT_BYTES


CANVAS_SIZE = (1920, 1080)
VALID_SOURCE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass(frozen=True)
class ThumbnailOptions:
    mode: str = "square_blur"
    crop_x: float = 0.5
    crop_y: float = 0.5
    zoom: float = 1.0
    blur: float = 28.0
    darkness: float = 0.45
    saturation: float = 0.75
    center_size: int = 1080
    quality: int = 92
    max_bytes: int = YOUTUBE_THUMBNAIL_LIMIT_BYTES
    solid_color: tuple[int, int, int] = (18, 18, 20)


def crop_box(source_size: tuple[int, int], target_ratio: float, x: float, y: float, zoom: float = 1.0) -> tuple[int, int, int, int]:
    width, height = source_size
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_height = height / max(zoom, 0.1)
        crop_width = crop_height * target_ratio
    else:
        crop_width = width / max(zoom, 0.1)
        crop_height = crop_width / target_ratio
    center_x = width * min(1.0, max(0.0, x))
    center_y = height * min(1.0, max(0.0, y))
    left = min(max(0.0, center_x - crop_width / 2), width - crop_width)
    top = min(max(0.0, center_y - crop_height / 2), height - crop_height)
    return round(left), round(top), round(left + crop_width), round(top + crop_height)


def compose_thumbnail(source: Image.Image, options: ThumbnailOptions) -> Image.Image:
    source = ImageOps.exif_transpose(source).convert("RGB")
    if options.mode == "crop_16_9":
        box = crop_box(source.size, 16 / 9, options.crop_x, options.crop_y, options.zoom)
        return source.crop(box).resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    if options.mode == "fit_background":
        background = _background(source, options)
        foreground = ImageOps.contain(source, CANVAS_SIZE, Image.Resampling.LANCZOS)
        background.paste(foreground, ((1920 - foreground.width) // 2, (1080 - foreground.height) // 2))
        return background

    size = max(320, min(1080, options.center_size))
    square = source.crop(crop_box(source.size, 1.0, options.crop_x, options.crop_y, options.zoom))
    square = square.resize((size, size), Image.Resampling.LANCZOS)
    if options.mode == "square_solid":
        canvas = Image.new("RGB", CANVAS_SIZE, options.solid_color)
    else:
        canvas = _background(source, options)
    canvas.paste(square, ((1920 - size) // 2, (1080 - size) // 2))
    return canvas


def generate_thumbnail(
    source_path: str | Path,
    output_path: str | Path,
    options: ThumbnailOptions | None = None,
    overwrite: bool = False,
) -> Path:
    options = options or ThumbnailOptions()
    source = Path(source_path)
    target = Path(output_path)
    if source.suffix.casefold() not in VALID_SOURCE_EXTENSIONS:
        raise ValueError(f"Unsupported source image: {source.name}")
    if target.exists() and not overwrite:
        target = unique_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source) as image:
            composed = compose_thumbnail(image, options)
            _save_under_limit(composed, target, options.quality, options.max_bytes)
    except UnidentifiedImageError as exc:
        raise ValueError(f"Image is damaged or unsupported: {source.name}") from exc
    return target


def generate_batch(
    sources: list[Path],
    output_folder: Path,
    options: ThumbnailOptions,
    suffix: str = "_thumbnail",
    progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    results: list[Path] = []
    valid = [p for p in sources if p.suffix.casefold() in VALID_SOURCE_EXTENSIONS]
    for index, source in enumerate(valid, start=1):
        results.append(generate_thumbnail(source, output_folder / f"{source.stem}{suffix}.jpg", options))
        if progress:
            progress(index, len(valid))
    return results


def ensure_upload_thumbnail(source: str | Path, cache_folder: Path) -> Path:
    path = Path(source)
    with Image.open(path) as image:
        converted = ImageOps.exif_transpose(image).convert("RGB")
        converted.thumbnail(CANVAS_SIZE, Image.Resampling.LANCZOS)
        target = cache_folder / f"upload_{path.stem}.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        _save_under_limit(converted, target, 92, YOUTUBE_THUMBNAIL_LIMIT_BYTES)
        return target


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    number = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{number}{path.suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def _background(source: Image.Image, options: ThumbnailOptions) -> Image.Image:
    box = crop_box(source.size, 16 / 9, options.crop_x, options.crop_y, 1.0)
    background = source.crop(box).resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    background = ImageEnhance.Color(background).enhance(max(0.0, options.saturation))
    background = ImageEnhance.Brightness(background).enhance(max(0.0, 1.0 - options.darkness))
    return background.filter(ImageFilter.GaussianBlur(max(0.0, options.blur)))


def _save_under_limit(image: Image.Image, target: Path, quality: int, max_bytes: int) -> None:
    quality = max(45, min(95, quality))
    for current_quality in range(quality, 44, -3):
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=current_quality, optimize=True, progressive=True)
        if buffer.tell() <= max_bytes:
            target.write_bytes(buffer.getvalue())
            return
    reduced = image.copy()
    while reduced.width > 1280:
        reduced = reduced.resize((int(reduced.width * 0.9), int(reduced.height * 0.9)), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        reduced.save(buffer, "JPEG", quality=72, optimize=True, progressive=True)
        if buffer.tell() <= max_bytes:
            target.write_bytes(buffer.getvalue())
            return
    raise ValueError(f"Could not create a thumbnail below {max_bytes} bytes.")

