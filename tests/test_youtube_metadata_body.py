import json
import unittest

try:
    from upload_plugg.models import Preset, UploadItem
    from googleapiclient.errors import HttpError
    from httplib2 import Response

    from upload_plugg.services.youtube import (
        INSUFFICIENT_PERMISSIONS_MESSAGE,
        YouTubeService,
        _friendly_http_error,
    )

    YOUTUBE_DEPENDENCIES_AVAILABLE = True
except ImportError:
    YOUTUBE_DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(
    YOUTUBE_DEPENDENCIES_AVAILABLE,
    "Google YouTube dependencies are installed in the Windows build environment",
)
class YouTubeMetadataBodyTests(unittest.TestCase):
    def test_insufficient_scope_error_has_reconnect_instructions(self):
        response = Response({"status": "403", "reason": "Forbidden"})
        content = json.dumps(
            {
                "error": {
                    "message": "Request had insufficient authentication scopes.",
                    "errors": [{"reason": "insufficientPermissions"}],
                }
            }
        ).encode("utf-8")
        error = HttpError(response, content)

        self.assertEqual(_friendly_http_error(error), INSUFFICIENT_PERMISSIONS_MESSAGE)

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
