from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from .design import COLORS


def line_icon(name: str, color: str = COLORS.secondary_text, size: int = 20) -> QIcon:
    """Return a small locally rendered line icon with no runtime asset dependency."""

    icon = QIcon()
    for mode, tone in (
        (QIcon.Normal, color),
        (QIcon.Active, COLORS.text),
        (QIcon.Selected, COLORS.crimson_hover),
        (QIcon.Disabled, COLORS.muted_text),
    ):
        icon.addPixmap(_draw(name, tone, size), mode)
    return icon


def _draw(name: str, color: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    scale = size / 24.0
    painter.scale(scale, scale)
    painter.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)

    if name == "dashboard":
        for box in (QRectF(3, 3, 7, 7), QRectF(14, 3, 7, 7), QRectF(3, 14, 7, 7), QRectF(14, 14, 7, 7)):
            painter.drawRoundedRect(box, 1.5, 1.5)
    elif name == "upload":
        painter.drawRoundedRect(QRectF(3, 13, 18, 8), 2, 2)
        painter.drawLine(QPointF(12, 16), QPointF(12, 3))
        painter.drawLine(QPointF(7.5, 7.5), QPointF(12, 3))
        painter.drawLine(QPointF(16.5, 7.5), QPointF(12, 3))
    elif name == "image":
        painter.drawRoundedRect(QRectF(3, 4, 18, 16), 2, 2)
        painter.drawEllipse(QPointF(8, 9), 1.6, 1.6)
        path = QPainterPath(QPointF(4.5, 17.5))
        path.lineTo(9.5, 12.5); path.lineTo(13, 16); path.lineTo(16, 13); path.lineTo(20, 17.5)
        painter.drawPath(path)
    elif name == "preset":
        painter.drawRoundedRect(QRectF(4, 3, 16, 18), 2, 2)
        painter.drawLine(QPointF(8, 8), QPointF(16, 8))
        painter.drawLine(QPointF(8, 12), QPointF(16, 12))
        painter.drawLine(QPointF(8, 16), QPointF(13, 16))
    elif name == "calendar":
        painter.drawRoundedRect(QRectF(3, 5, 18, 16), 2, 2)
        painter.drawLine(QPointF(3, 10), QPointF(21, 10))
        painter.drawLine(QPointF(8, 3), QPointF(8, 7))
        painter.drawLine(QPointF(16, 3), QPointF(16, 7))
        painter.drawPoint(QPointF(8, 14)); painter.drawPoint(QPointF(12, 14)); painter.drawPoint(QPointF(16, 14))
    elif name == "history":
        painter.drawEllipse(QRectF(4, 4, 16, 16))
        painter.drawLine(QPointF(12, 7), QPointF(12, 12)); painter.drawLine(QPointF(12, 12), QPointF(16, 14))
        painter.drawLine(QPointF(4, 4), QPointF(4, 9)); painter.drawLine(QPointF(4, 4), QPointF(9, 4))
    elif name == "logs":
        painter.drawRoundedRect(QRectF(3, 4, 18, 16), 2, 2)
        painter.drawLine(QPointF(7, 9), QPointF(10, 12)); painter.drawLine(QPointF(10, 12), QPointF(7, 15))
        painter.drawLine(QPointF(12, 15), QPointF(17, 15))
    elif name == "settings":
        painter.drawEllipse(QRectF(8, 8, 8, 8))
        for angle in range(0, 360, 45):
            painter.save(); painter.translate(12, 12); painter.rotate(angle)
            painter.drawLine(QPointF(0, -9), QPointF(0, -6)); painter.restore()
        painter.drawEllipse(QRectF(4, 4, 16, 16))
    elif name == "folder":
        path = QPainterPath(QPointF(3, 7)); path.lineTo(9, 7); path.lineTo(11, 9); path.lineTo(21, 9)
        path.lineTo(20, 20); path.lineTo(4, 20); path.closeSubpath(); painter.drawPath(path)
    elif name == "search":
        painter.drawEllipse(QRectF(4, 4, 12, 12)); painter.drawLine(QPointF(14.5, 14.5), QPointF(20, 20))
    elif name == "refresh":
        painter.drawArc(QRectF(4, 4, 16, 16), 35 * 16, 285 * 16)
        painter.drawLine(QPointF(18.5, 4.5), QPointF(20, 9)); painter.drawLine(QPointF(18.5, 4.5), QPointF(14, 5.5))
    elif name == "check":
        painter.drawEllipse(QRectF(3, 3, 18, 18)); painter.drawLine(QPointF(7, 12), QPointF(10.5, 15.5)); painter.drawLine(QPointF(10.5, 15.5), QPointF(17, 8))
    elif name == "warning":
        path = QPainterPath(QPointF(12, 3)); path.lineTo(21, 20); path.lineTo(3, 20); path.closeSubpath(); painter.drawPath(path)
        painter.drawLine(QPointF(12, 8), QPointF(12, 14)); painter.drawPoint(QPointF(12, 17))
    elif name == "stop":
        painter.drawRoundedRect(QRectF(5, 5, 14, 14), 2, 2)
    elif name == "link":
        painter.drawArc(QRectF(3, 7, 12, 10), 45 * 16, 270 * 16); painter.drawArc(QRectF(9, 7, 12, 10), 225 * 16, 270 * 16)
        painter.drawLine(QPointF(9, 12), QPointF(15, 12))
    elif name == "export":
        painter.drawRoundedRect(QRectF(4, 8, 16, 13), 2, 2); painter.drawLine(QPointF(12, 15), QPointF(12, 3)); painter.drawLine(QPointF(8, 7), QPointF(12, 3)); painter.drawLine(QPointF(16, 7), QPointF(12, 3))
    elif name == "trash":
        painter.drawRoundedRect(QRectF(6, 7, 12, 14), 1, 1); painter.drawLine(QPointF(4, 7), QPointF(20, 7)); painter.drawLine(QPointF(9, 4), QPointF(15, 4))
    elif name == "watermark":
        painter.drawEllipse(QRectF(4, 4, 16, 16)); painter.drawText(QRectF(4, 4, 16, 16), Qt.AlignCenter, "W")
    elif name == "color":
        painter.drawEllipse(QRectF(3, 3, 18, 18)); painter.drawArc(QRectF(7, 7, 10, 10), 0, 180 * 16)
    else:
        painter.drawEllipse(QRectF(5, 5, 14, 14))

    painter.end()
    return pixmap


NAV_ICONS = {
    "Dashboard": "dashboard",
    "Upload Generator": "upload",
    "Thumbnail Generator": "image",
    "Presets": "preset",
    "Upload Schedule": "calendar",
    "Upload History": "history",
    "Logs": "logs",
    "Settings": "settings",
}

