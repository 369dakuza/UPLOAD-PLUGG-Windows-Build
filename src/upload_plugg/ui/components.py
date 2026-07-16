from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .design import COLORS, SPACE_2, SPACE_3, SPACE_4
from .icons import line_icon


class ActionButton(QPushButton):
    def __init__(
        self,
        text: str,
        role: str = "secondary",
        icon_name: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(text, parent)
        self.setProperty("role", role)
        self.setCursor(Qt.PointingHandCursor)
        if icon_name:
            self.setIcon(line_icon(icon_name))
        self.setMinimumHeight(36)


class SectionCard(QFrame):
    def __init__(
        self,
        title: str = "",
        description: str = "",
        icon_name: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        self.outer.setSpacing(SPACE_3)
        if title:
            header = QHBoxLayout()
            header.setSpacing(SPACE_2)
            if icon_name:
                icon = QLabel()
                icon.setPixmap(line_icon(icon_name, COLORS.crimson_hover, 18).pixmap(18, 18))
                header.addWidget(icon, 0, Qt.AlignTop)
            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            heading = QLabel(title)
            heading.setObjectName("sectionTitle")
            text_box.addWidget(heading)
            if description:
                subtitle = QLabel(description)
                subtitle.setObjectName("muted")
                subtitle.setWordWrap(True)
                text_box.addWidget(subtitle)
            header.addLayout(text_box, 1)
            self.outer.addLayout(header)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(SPACE_3)
        self.outer.addLayout(self.body, 1)


class EmptyState(QWidget):
    def __init__(self, title: str, description: str = "", icon_name: str = "image"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACE_2)
        icon = QLabel()
        icon.setPixmap(line_icon(icon_name, COLORS.muted_text, 34).pixmap(34, 34))
        icon.setAlignment(Qt.AlignCenter)
        heading = QLabel(title)
        heading.setObjectName("emptyTitle")
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        layout.addWidget(heading)
        if description:
            detail = QLabel(description)
            detail.setObjectName("muted")
            detail.setAlignment(Qt.AlignCenter)
            detail.setWordWrap(True)
            layout.addWidget(detail)


class StatusBadge(QLabel):
    def __init__(self, text: str = "", status: str = "neutral"):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(status, text)

    def set_status(self, status: str, text: str | None = None) -> None:
        if text is not None:
            self.setText(text)
        self.setProperty("status", status.casefold().replace(" ", "_"))
        self.style().unpolish(self)
        self.style().polish(self)


class SparklineWidget(QWidget):
    def __init__(self, points: Iterable[float], color: str = COLORS.crimson_hover):
        super().__init__()
        self.points = list(points)
        self.color = QColor(color)
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_points(self, points: Iterable[float]) -> None:
        self.points = list(points) or [0]
        self.update()

    def paintEvent(self, _event: object) -> None:
        if len(self.points) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 3, -2, -3)
        low, high = min(self.points), max(self.points)
        span = max(high - low, 1)
        path = QPainterPath()
        for index, value in enumerate(self.points):
            x = rect.left() + index * rect.width() / (len(self.points) - 1)
            y = rect.bottom() - (value - low) * rect.height() / span
            point = QPointF(x, y)
            path.moveTo(point) if index == 0 else path.lineTo(point)
        painter.setPen(QPen(self.color, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)


class StatCard(QFrame):
    def __init__(self, label: str, icon_name: str, color: str, points: Iterable[float]):
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_3)
        layout.setSpacing(SPACE_2)
        top = QHBoxLayout()
        self.value = QLabel("0")
        self.value.setObjectName("statValue")
        self.value.setStyleSheet(f"color: {color};")
        icon = QLabel()
        icon.setPixmap(line_icon(icon_name, color, 25).pixmap(25, 25))
        top.addWidget(self.value)
        top.addStretch()
        top.addWidget(icon)
        layout.addLayout(top)
        caption = QLabel(label)
        caption.setObjectName("statLabel")
        layout.addWidget(caption)
        self.sparkline = SparklineWidget(points, color)
        layout.addWidget(self.sparkline)


class ProgressStrip(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("progressStrip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_4, 7, SPACE_4, 7)
        layout.setSpacing(SPACE_3)
        self.label = QLabel("Ready")
        self.label.setObjectName("progressLabel")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(7)
        self.bar.setRange(0, 100)
        self.percent = QLabel("")
        self.percent.setObjectName("progressPercent")
        layout.addWidget(self.label)
        layout.addWidget(self.bar, 1)
        layout.addWidget(self.percent)
        self.hide()

    def start(self, label: str, determinate: bool = False) -> None:
        self.setProperty("state", "running")
        self.style().unpolish(self)
        self.style().polish(self)
        self.label.setText(label)
        if determinate:
            self.bar.setRange(0, 100)
            self.bar.setValue(0)
            self.percent.setText("0%")
        else:
            self.bar.setRange(0, 0)
            self.percent.clear()
        self.show()

    def update_progress(self, current: int, total: int) -> None:
        if total <= 0:
            return
        value = round(current * 100 / total)
        self.bar.setRange(0, 100)
        self.bar.setValue(value)
        self.percent.setText(f"{value}%")

    def finish(self, label: str, success: bool = True) -> None:
        self.setProperty("state", "success" if success else "error")
        self.style().unpolish(self)
        self.style().polish(self)
        self.label.setText(label)
        self.bar.setRange(0, 100)
        self.bar.setValue(100 if success else 0)
        self.percent.setText("100%" if success else "")
