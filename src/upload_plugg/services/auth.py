from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..constants import YOUTUBE_UPLOAD_SCOPE


SERVICE_NAME = "UPLOAD_PLUGG"
TOKEN_ACCOUNT = "youtube_oauth_token"


class AuthenticationError(RuntimeError):
    pass


class OAuthManager:
    def __init__(self, client_secret_path: Path):
        self.client_secret_path = client_secret_path

    def connect(self) -> Credentials:
        if not self.client_secret_path.is_file():
            raise AuthenticationError(
                f"OAuth credentials are missing. Place client_secret.json in {self.client_secret_path.parent}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_path), [YOUTUBE_UPLOAD_SCOPE]
        )
        credentials = flow.run_local_server(
            host="localhost",
            port=0,
            authorization_prompt_message="Your default browser will open for Google authorization.",
            success_message="UPLOAD PLUGG is connected. You may close this browser window.",
            open_browser=True,
        )
        self._save(credentials)
        return credentials

    def credentials(self) -> Credentials | None:
        raw = keyring.get_password(SERVICE_NAME, TOKEN_ACCOUNT)
        if not raw:
            return None
        try:
            info: dict[str, Any] = json.loads(raw)
            credentials = Credentials.from_authorized_user_info(info, [YOUTUBE_UPLOAD_SCOPE])
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self._save(credentials)
            return credentials if credentials.valid else None
        except Exception as exc:
            raise AuthenticationError(f"Stored authorization could not be loaded: {exc}") from exc

    def disconnect(self) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, TOKEN_ACCOUNT)
        except keyring.errors.PasswordDeleteError:
            pass

    def _save(self, credentials: Credentials) -> None:
        keyring.set_password(SERVICE_NAME, TOKEN_ACCOUNT, credentials.to_json())

