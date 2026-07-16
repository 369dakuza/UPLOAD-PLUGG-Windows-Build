import tempfile
import unittest
from pathlib import Path

from PIL import Image

from upload_plugg.core.thumbnails import (
    ThumbnailOptions,
    compose_thumbnail,
    crop_box,
    generate_thumbnail,
    random_source_image,
    source_images,
)


class ThumbnailTests(unittest.TestCase):
    def test_crop_box_stays_in_bounds(self):
        left, top, right, bottom = crop_box((2000, 1000), 1.0, 0.9, 0.5)
        self.assertGreaterEqual(left, 0)
        self.assertLessEqual(right, 2000)
        self.assertEqual(right - left, bottom - top)

    def test_generate_exact_canvas_under_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "art.png"
            target = root / "thumb.jpg"
            Image.new("RGB", (900, 1200), (180, 20, 40)).save(source)
            result = generate_thumbnail(source, target, ThumbnailOptions())
            with Image.open(result) as image:
                self.assertEqual(image.size, (1920, 1080))
                self.assertEqual(image.mode, "RGB")
            self.assertLessEqual(result.stat().st_size, 2 * 1024 * 1024)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "art.png"
            target = root / "thumb.jpg"
            Image.new("RGB", (500, 500), "red").save(source)
            generate_thumbnail(source, target)
            second = generate_thumbnail(source, target)
            self.assertNotEqual(second, target)

    def test_crop_x_changes_wide_image_focus(self):
        source = Image.new("RGB", (2000, 1000), "red")
        source.paste(Image.new("RGB", (1000, 1000), "blue"), (1000, 0))
        left = compose_thumbnail(source, ThumbnailOptions(mode="crop_16_9", crop_x=0.0))
        right = compose_thumbnail(source, ThumbnailOptions(mode="crop_16_9", crop_x=1.0))
        self.assertNotEqual(left.getpixel((960, 540)), right.getpixel((960, 540)))

    def test_background_saturation_changes_preview_background(self):
        source = Image.new("RGB", (700, 1100), (190, 35, 20))
        gray = compose_thumbnail(
            source,
            ThumbnailOptions(mode="square_blur", blur=0, darkness=0, saturation=0),
        )
        saturated = compose_thumbnail(
            source,
            ThumbnailOptions(mode="square_blur", blur=0, darkness=0, saturation=1.6),
        )
        self.assertNotEqual(gray.getpixel((20, 20)), saturated.getpixel((20, 20)))

    def test_solid_background_uses_selected_color(self):
        source = Image.new("RGB", (900, 1200), "white")
        result = compose_thumbnail(
            source,
            ThumbnailOptions(
                mode="square_blur",
                background_mode="solid",
                solid_color=(22, 44, 88),
                center_size=640,
            ),
        )
        self.assertEqual(result.getpixel((10, 10)), (22, 44, 88))

    def test_source_folder_supports_random_image_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "one.jpg"
            second = root / "two.png"
            Image.new("RGB", (20, 20), "red").save(first)
            Image.new("RGB", (20, 20), "blue").save(second)
            (root / "ignore.txt").write_text("not an image", encoding="utf-8")

            candidates = source_images(root)

            self.assertEqual(candidates, [first, second])
            self.assertIn(random_source_image(root), candidates)


if __name__ == "__main__":
    unittest.main()
