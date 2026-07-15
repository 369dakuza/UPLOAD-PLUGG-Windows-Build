import tempfile
import unittest
from pathlib import Path

from upload_plugg.core.scanner import natural_key, scan_videos, sha256_file


class ScannerTests(unittest.TestCase):
    def test_natural_sort(self):
        names = ["10 Beat.mp4", "2 Beat.mp4", "1 Beat.mp4"]
        self.assertEqual(sorted(names, key=natural_key), ["1 Beat.mp4", "2 Beat.mp4", "10 Beat.mp4"])

    def test_scan_ignores_non_mp4_and_respects_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("2 Beat.mp4", "1 Beat.mp4", "notes.txt"):
                (root / name).write_bytes(b"video")
            items = scan_videos(root, limit=1)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].filename, "1 Beat.mp4")

    def test_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp4"
            path.write_bytes(b"upload-plugg")
            self.assertEqual(len(sha256_file(path)), 64)


if __name__ == "__main__":
    unittest.main()

