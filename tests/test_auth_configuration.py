import json
import tempfile
import unittest
from pathlib import Path

try:
    from upload_plugg.services.auth import AuthenticationError, OAuthManager

    AUTH_DEPENDENCIES_AVAILABLE = True
except ImportError:
    AUTH_DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(
    AUTH_DEPENDENCIES_AVAILABLE,
    "Google OAuth dependencies are installed in the Windows build environment",
)
class OAuthConfigurationTests(unittest.TestCase):
    def test_desktop_client_json_is_validated_and_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "downloaded.json"
            destination = root / "config" / "client_secret.json"
            payload = {
                "installed": {
                    "client_id": "example.apps.googleusercontent.com",
                    "client_secret": "example-secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            source.write_text(json.dumps(payload), encoding="utf-8")

            result = OAuthManager(destination).install_client_secret(source)

            self.assertEqual(result, destination)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), payload)

    def test_web_client_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "web-client.json"
            source.write_text(json.dumps({"web": {"client_id": "wrong-kind"}}), encoding="utf-8")
            with self.assertRaises(AuthenticationError):
                OAuthManager(root / "client_secret.json").install_client_secret(source)


if __name__ == "__main__":
    unittest.main()
