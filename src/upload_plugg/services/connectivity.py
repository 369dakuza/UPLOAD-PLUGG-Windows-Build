from __future__ import annotations

import socket
import urllib.request


GOOGLE_ENDPOINTS = (
    "https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest",
    "https://accounts.google.com/.well-known/openid-configuration",
)


def _https_reachable(url: str, timeout: float) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "UPLOAD-PLUGG/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, ValueError):
        return False


def internet_available(timeout: float = 2.5) -> bool:
    for endpoint in GOOGLE_ENDPOINTS:
        if _https_reachable(endpoint, timeout):
            return True
    # Some security software blocks HTTP probes while the Google APIs remain
    # reachable by the application itself. Retain a low-level fallback.
    for host in ("www.googleapis.com", "accounts.google.com"):
        try:
            with socket.create_connection((host, 443), timeout=timeout):
                return True
        except OSError:
            continue
    return False
