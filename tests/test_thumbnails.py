import tempfile
import unittest
from pathlib import Path

from PIL import Image

from upload_plugg.core.thumbnails import ThumbnailOptions, crop_box, generate_thumbnail


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


if __name__ == "__main__":
    unittest.main()

