from __future__ import annotations

import socket


def internet_available(timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(("www.googleapis.com", 443), timeout=timeout):
            return True
    except OSError:
        return False

