import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from google.auth.exceptions import RefreshError

    from upload_plugg.constants import (
        YOUTUBE_READONLY_SCOPE,
        YOUTUBE_SCOPES,
        YOUTUBE_UPLOAD_SCOPE,
    )
    from upload_plugg.services.auth import (
        REAUTHORIZE_MESSAGE,
        AuthenticationError,
        OAuthManager,
        ReauthorizationRequired,
    )

    AUTH_DEPENDENCIES_AVAILABLE = True
except ImportError:
    AUTH_DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(
    AUTH_DEPENDENCIES_AVAILABLE,
    "Google OAuth dependencies are installed in the Windows build environment",
)
class OAuthConfigurationTests(unittest.TestCase):
    def test_required_scopes_include_upload_and_channel_read_access(self):
        self.assertEqual(
            YOUTUBE_SCOPES,
            [YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE],
        )

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

    def test_connect_forces_complete_consent_for_both_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            client = Path(directory) / "config" / "client_secret.json"
            client.parent.mkdir()
            client.write_text("{}", encoding="utf-8")
            manager = OAuthManager(client)
            credentials = MagicMock()
            credentials.to_json.return_value = '{"token":"new"}'
            flow = MagicMock()
            flow.run_local_server.return_value = credentials

            with (
                patch.object(manager, "disconnect") as disconnect,
                patch(
                    "upload_plugg.services.auth.InstalledAppFlow.from_client_secrets_file",
                    return_value=flow,
                ) as create_flow,
                patch("upload_plugg.services.auth.keyring.set_password") as save_token,
            ):
                result = manager.connect()

            self.assertIs(result, credentials)
            disconnect.assert_called_once_with()
            create_flow.assert_called_once_with(str(client), YOUTUBE_SCOPES)
            flow.run_local_server.assert_called_once_with(
                host="127.0.0.1",
                port=0,
                access_type="offline",
                prompt="consent select_account",
                authorization_prompt_message=(
                    "Your default browser will open for Google authorization."
                ),
                success_message=(
                    "UPLOAD PLUGG is connected. You may close this browser window."
                ),
                open_browser=True,
            )
            save_token.assert_called_once()

    def test_upload_only_legacy_token_is_deleted_and_requires_login(self):
        manager = OAuthManager(Path("C:/LocalAppData/UploadPlugg/config/client_secret.json"))
        raw = json.dumps({"scopes": [YOUTUBE_UPLOAD_SCOPE]})
        with (
            patch("upload_plugg.services.auth.keyring.get_password", return_value=raw),
            patch("upload_plugg.services.auth.keyring.delete_password") as delete_token,
            self.assertRaisesRegex(ReauthorizationRequired, "missing required permissions"),
        ):
            manager.credentials()
        delete_token.assert_called_once()

    def test_valid_saved_credentials_are_reused_after_restart(self):
        manager = OAuthManager(Path("C:/LocalAppData/UploadPlugg/config/client_secret.json"))
        raw = json.dumps({"scopes": YOUTUBE_SCOPES})
        credentials = MagicMock(expired=False, valid=True)
        with (
            patch("upload_plugg.services.auth.keyring.get_password", return_value=raw),
            patch(
                "upload_plugg.services.auth.Credentials.from_authorized_user_info",
                return_value=credentials,
            ) as restore,
        ):
            result = manager.credentials()
        self.assertIs(result, credentials)
        restore.assert_called_once_with(json.loads(raw), YOUTUBE_SCOPES)

    def test_invalid_refresh_token_is_removed_and_requests_new_login(self):
        manager = OAuthManager(Path("C:/LocalAppData/UploadPlugg/config/client_secret.json"))
        raw = json.dumps({"scopes": YOUTUBE_SCOPES})
        credentials = MagicMock(expired=True, refresh_token="refresh", valid=False)
        credentials.refresh.side_effect = RefreshError("invalid_grant")
        with (
            patch("upload_plugg.services.auth.keyring.get_password", return_value=raw),
            patch(
                "upload_plugg.services.auth.Credentials.from_authorized_user_info",
                return_value=credentials,
            ),
            patch("upload_plugg.services.auth.keyring.delete_password") as delete_token,
            self.assertRaisesRegex(
                ReauthorizationRequired,
                REAUTHORIZE_MESSAGE.split("\\n")[0],
            ),
        ):
            manager.credentials()
        delete_token.assert_called_once()

    def test_expired_access_token_is_refreshed_and_saved(self):
        manager = OAuthManager(Path("C:/LocalAppData/UploadPlugg/config/client_secret.json"))
        raw = json.dumps({"scopes": YOUTUBE_SCOPES})
        credentials = MagicMock(expired=True, refresh_token="refresh", valid=True)
        credentials.to_json.return_value = raw
        with (
            patch("upload_plugg.services.auth.keyring.get_password", return_value=raw),
            patch(
                "upload_plugg.services.auth.Credentials.from_authorized_user_info",
                return_value=credentials,
            ),
            patch("upload_plugg.services.auth.keyring.set_password") as save_token,
        ):
            result = manager.credentials()

        self.assertIs(result, credentials)
        credentials.refresh.assert_called_once()
        save_token.assert_called_once()

    def test_disconnect_removes_keyring_and_legacy_local_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = root / "config" / "client_secret.json"
            manager = OAuthManager(client)
            legacy_paths = manager._legacy_token_paths()
            for path in legacy_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("secret", encoding="utf-8")

            with patch("upload_plugg.services.auth.keyring.delete_password") as delete_token:
                manager.disconnect()

            delete_token.assert_called_once()
            self.assertTrue(all(not path.exists() for path in legacy_paths))


if __name__ == "__main__":
    unittest.main()
