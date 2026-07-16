import unittest

try:
    from upload_plugg.models import Preset, UploadItem
    from upload_plugg.services.youtube import YouTubeService

    YOUTUBE_DEPENDENCIES_AVAILABLE = True
except ImportError:
    YOUTUBE_DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(
    YOUTUBE_DEPENDENCIES_AVAILABLE,
    "Google YouTube dependencies are installed in the Windows build environment",
)
class YouTubeMetadataBodyTests(unittest.TestCase):
    def test_made_for_kids_setting_is_sent_exactly_as_selected(self):
        item = UploadItem(
            "C:/Beats/Hellcat.mp4",
            "Hellcat",
            display_title="Title",
            description="Description",
            tags=["Chief Keef", "Glo Gang"],
        )

        not_for_kids = YouTubeService._video_body(item, Preset(made_for_kids=False))
        for_kids = YouTubeService._video_body(item, Preset(made_for_kids=True))

        self.assertFalse(not_for_kids["status"]["selfDeclaredMadeForKids"])
        self.assertTrue(for_kids["status"]["selfDeclaredMadeForKids"])
        self.assertEqual(not_for_kids["snippet"]["tags"], item.tags)


if __name__ == "__main__":
    unittest.main()
