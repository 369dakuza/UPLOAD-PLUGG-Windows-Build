import tempfile
import threading
import unittest
from pathlib import Path

from upload_plugg.core.scanner import natural_key, reconcile_scan, scan_videos, sha256_file
from upload_plugg.models import UploadItem


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

    def test_cancelled_scan_does_not_return_partial_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Beat.mp4").write_bytes(b"video")
            cancelled = threading.Event()
            cancelled.set()
            self.assertEqual(scan_videos(root, cancelled=cancelled), [])

    def test_reconcile_removes_missing_and_preserves_manual_metadata(self):
        existing = UploadItem(
            source_path=str(Path("C:/beats/kept.mp4")),
            beat_name="Manual Beat",
            display_title="My manual title",
            file_size=5,
            modified_ns=10,
            manual_metadata_fields=["title"],
        )
        stale = UploadItem(source_path=str(Path("C:/beats/removed.mp4")), beat_name="Old")
        fresh = UploadItem(
            source_path=str(Path("C:/beats/kept.mp4")),
            beat_name="Parsed Beat",
            file_size=5,
            modified_ns=10,
        )
        added_item = UploadItem(source_path=str(Path("C:/beats/new.mp4")), beat_name="New")

        result, added, updated, removed = reconcile_scan(
            [existing, stale], [fresh, added_item]
        )

        self.assertEqual((added, updated, removed), (1, 0, 1))
        self.assertIs(result[0], existing)
        self.assertEqual(result[0].display_title, "My manual title")
        self.assertEqual([item.beat_name for item in result], ["Manual Beat", "New"])

    def test_reconcile_resets_hash_when_file_changed(self):
        old = UploadItem(
            source_path="beat.mp4",
            beat_name="Beat",
            file_size=5,
            modified_ns=10,
            file_hash="abc",
            upload_status="Completed",
            progress=100,
        )
        fresh = UploadItem(
            source_path="beat.mp4",
            beat_name="Beat",
            file_size=7,
            modified_ns=11,
        )
        result, added, updated, removed = reconcile_scan([old], [fresh])
        self.assertEqual((added, updated, removed), (0, 1, 0))
        self.assertEqual(result[0].file_hash, "")
        self.assertEqual(result[0].upload_status, "Ready")
        self.assertEqual(result[0].progress, 0)


if __name__ == "__main__":
    unittest.main()
