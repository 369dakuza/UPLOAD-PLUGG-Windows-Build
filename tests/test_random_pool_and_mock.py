import unittest
from pathlib import Path

from upload_plugg.core.random_pool import assign_without_repeats
from upload_plugg.models import Preset, UploadItem
from upload_plugg.services.mock_youtube import MockYouTubeService


class RandomPoolAndMockTests(unittest.TestCase):
    def test_no_repeats_before_pool_exhaustion(self):
        result = assign_without_repeats(["a", "b", "c", "d"], [Path("1.jpg"), Path("2.jpg"), Path("3.jpg")], seed=7)
        first_cycle = [result[key] for key in ("a", "b", "c")]
        self.assertEqual(len(set(first_cycle)), 3)

    def test_mock_upload_never_needs_credentials(self):
        item = UploadItem("sample.mp4", "Sample", file_size=10)
        result = MockYouTubeService().upload_video(item, Preset())
        self.assertTrue(result["id"].startswith("mock_"))


if __name__ == "__main__":
    unittest.main()

