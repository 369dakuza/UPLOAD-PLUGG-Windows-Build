from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import keyring
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..constants import YOUTUBE_SCOPES


SERVICE_NAME = "UPLOAD_PLUGG"
TOKEN_ACCOUNT = "youtube_oauth_token"
REAUTHORIZE_MESSAGE = (
    "Your saved YouTube authorization is missing required permissions or is no longer valid.\n"
    "Please connect the YouTube channel again."
)


class AuthenticationError(RuntimeError):
    pass


class ReauthorizationRequired(AuthenticationError):
    pass


class OAuthManager:
    def __init__(self, client_secret_path: Path):
        self.client_secret_path = client_secret_path

    def client_configured(self) -> bool:
        return self.client_secret_path.is_file()

    def install_client_secret(self, source: Path) -> Path:
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AuthenticationError(f"Could not read the JSON file: {exc}") from exc
        installed = payload.get("installed") if isinstance(payload, dict) else None
        required = ("client_id", "client_secret", "auth_uri", "token_uri")
        if not isinstance(installed, dict) or any(not installed.get(key) for key in required):
            raise AuthenticationError(
                "Choose an OAuth Client ID JSON created for a Google Desktop app."
            )
        self.client_secret_path.parent.mkdir(parents=True, exist_ok=True)
        self.client_secret_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        try:
            self.client_secret_path.chmod(0o600)
        except OSError:
            pass
        return self.client_secret_path

    def connect(self) -> Credentials:
        if not self.client_secret_path.is_file():
            raise AuthenticationError(
                "Google OAuth credentials are missing. Click Connect YouTube Channel and "
                "select the Desktop Client JSON downloaded from Google Cloud."
            )
        # A reconnect is always a complete authorization. Google cannot extend an
        # already-issued desktop token with additional scopes after the fact.
        self.disconnect()
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_path), YOUTUBE_SCOPES
        )
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            access_type="offline",
            prompt="consent select_account",
            authorization_prompt_message="Your default browser will open for Google authorization.",
            success_message="UPLOAD PLUGG is connected. You may close this browser window.",
            open_browser=True,
        )
        self._save(credentials)
        return credentials

    def credentials(self) -> Credentials | None:
        try:
            raw = keyring.get_password(SERVICE_NAME, TOKEN_ACCOUNT)
        except keyring.errors.KeyringError as exc:
            raise AuthenticationError(
                f"Windows Credential Locker could not be opened: {exc}"
            ) from exc
        if not raw:
            return None
        try:
            info: dict[str, Any] = json.loads(raw)
            if not _stored_scopes(info).issuperset(YOUTUBE_SCOPES):
                self.disconnect()
                raise ReauthorizationRequired(REAUTHORIZE_MESSAGE)
            credentials = Credentials.from_authorized_user_info(info, YOUTUBE_SCOPES)
            if credentials.expired:
                if not credentials.refresh_token:
                    self.disconnect()
                    raise ReauthorizationRequired(REAUTHORIZE_MESSAGE)
                try:
                    credentials.refresh(Request())
                except RefreshError as exc:
                    self.disconnect()
                    raise ReauthorizationRequired(REAUTHORIZE_MESSAGE) from exc
                except Exception as exc:
                    raise AuthenticationError(
                        "The saved YouTube authorization could not be refreshed. "
                        "Check the internet connection and try again."
                    ) from exc
                self._save(credentials)
            if not credentials.valid:
                self.disconnect()
                raise ReauthorizationRequired(REAUTHORIZE_MESSAGE)
            return credentials
        except ReauthorizationRequired:
            raise
        except AuthenticationError:
            raise
        except Exception as exc:
            self.disconnect()
            raise ReauthorizationRequired(REAUTHORIZE_MESSAGE) from exc

    def disconnect(self) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, TOKEN_ACCOUNT)
        except keyring.errors.KeyringError:
            pass
        for path in self._legacy_token_paths():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def _save(self, credentials: Credentials) -> None:
        try:
            keyring.set_password(SERVICE_NAME, TOKEN_ACCOUNT, credentials.to_json())
        except keyring.errors.KeyringError as exc:
            raise AuthenticationError(
                f"YouTube authorization could not be saved in Windows Credential Locker: {exc}"
            ) from exc

    def _legacy_token_paths(self) -> tuple[Path, ...]:
        config = self.client_secret_path.parent
        root = config.parent
        return (
            config / "token.json",
            config / "youtube_token.json",
            root / "token.json",
            root / "auth" / "token.json",
        )


def _stored_scopes(info: dict[str, Any]) -> set[str]:
    stored: set[str] = set()
    for key in ("scopes", "scope", "granted_scopes"):
        raw = info.get(key, [])
        if isinstance(raw, str):
            stored.update(raw.replace(",", " ").split())
        elif isinstance(raw, (list, tuple, set)):
            stored.update(str(scope) for scope in raw)
    return stored
