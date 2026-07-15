from __future__ import annotations

import ctypes
import sys


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


class KeepAwake:
    def __init__(self) -> None:
        self.active = False

    def enable(self) -> None:
        if sys.platform == "win32" and not self.active:
            result = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED
            )
            if not result:
                raise OSError("Windows refused the keep-awake request.")
        self.active = True

    def disable(self) -> None:
        if sys.platform == "win32" and self.active:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self.active = False

    def __enter__(self) -> "KeepAwake":
        self.enable()
        return self

    def __exit__(self, *_: object) -> None:
        self.disable()

