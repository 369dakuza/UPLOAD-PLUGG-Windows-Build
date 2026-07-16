from __future__ import annotations

import socket
import threading
import urllib.request


GOOGLE_ENDPOINTS = (
    "https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest",
    "https://accounts.google.com/.well-known/openid-configuration",
)


def _https_reachable(url: str, timeout: float) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "UPLOAD-PLUGG/1.1.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, ValueError):
        return False


def internet_available(
    timeout: float = 1.25,
    cancelled: threading.Event | None = None,
) -> bool:
    for endpoint in GOOGLE_ENDPOINTS:
        if cancelled is not None and cancelled.is_set():
            return False
        if _https_reachable(endpoint, timeout):
            return True
    # Some security software blocks HTTP probes while the Google APIs remain
    # reachable by the application itself. Retain a low-level fallback.
    for host in ("www.googleapis.com", "accounts.google.com"):
        if cancelled is not None and cancelled.is_set():
            return False
        try:
            with socket.create_connection((host, 443), timeout=timeout):
                return True
        except OSError:
            continue
    return False
