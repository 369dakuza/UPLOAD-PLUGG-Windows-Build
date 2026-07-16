from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:
    background: str = "#07090C"
    sidebar: str = "#0A0D11"
    topbar: str = "#0B0E12"
    panel: str = "#10141A"
    elevated: str = "#141922"
    input: str = "#0C1015"
    hover: str = "#191E26"
    border: str = "#262D37"
    subtle_border: str = "#1C222B"
    crimson: str = "#E31837"
    crimson_hover: str = "#FF2347"
    crimson_pressed: str = "#B90F2C"
    crimson_soft: str = "#7A1425"
    text: str = "#F4F6F8"
    secondary_text: str = "#A3ADBA"
    muted_text: str = "#707C8B"
    success: str = "#32D583"
    warning: str = "#FFB020"
    error: str = "#FF3B5C"
    info: str = "#4EA1FF"


COLORS = Colors()

SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
CARD_RADIUS = 12
CONTROL_RADIUS = 8
SIDEBAR_WIDTH = 232

