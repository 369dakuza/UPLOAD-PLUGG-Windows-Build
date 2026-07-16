from __future__ import annotations

import json
import os
import re
import threading
import webbrowser
from datetime import date, datetime, time, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QSize, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QIcon,
    QPalette,
    QPainter,
    QPen,
    QPixmap,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION, CREATOR_CREDIT
from ..constants import MAX_BATCH_SIZE, YOUTUBE_TAGS_LIMIT
from ..core.dry_run import export_dry_run
from ..core.filename_parser import parse_filename
from ..core.random_pool import assign_without_repeats, image_pool
from ..core.scanner import scan_videos, sha256_file
from ..core.scheduling import ScheduleError, calculate_schedule
from ..core.templates import (
    description_hashtags,
    generate_metadata,
    migrate_credit_line,
    producer_credits,
    preset_metadata_signature,
    split_tags,
    synchronize_metadata,
    tag_length,
)
from ..core.thumbnails import (
    ThumbnailOptions,
    generate_batch,
    generate_thumbnail,
    random_source_image,
    source_images,
)
from ..core.validation import validate_item
from ..database import Database
from ..models import Preset, UploadItem
from ..paths import AppPaths
from ..settings import SettingsStore
from .components import ActionButton, EmptyState, SectionCard, StatCard, StatusBadge
from .design import COLORS, SPACE_2, SPACE_3, SPACE_4
from .icons import line_icon


def page_header(title: str, subtitle: str) -> tuple[QVBoxLayout, QLabel]:
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    layout.addWidget(heading)
    muted = QLabel(subtitle)
    muted.setObjectName("muted")
    muted.setWordWrap(True)
    layout.addWidget(muted)
    return layout, heading


def panel() -> QFrame:
    frame = QFrame()
    frame.setObjectName("panel")
    return frame


class DarkComboBox(QComboBox):
    """Use a Qt-owned list popup so Windows cannot replace it with a white native menu."""

    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        popup = QListView()
        popup.setObjectName("darkComboPopup")
        popup.setUniformItemSizes(True)
        popup.setAutoFillBackground(True)
        popup.setStyleSheet(
            "QListView { background-color: #080a0d; color: #ffffff; "
            "border: 1px solid #343740; outline: 0; padding: 4px; }"
            "QListView::item { color: #ffffff; min-height: 28px; padding: 5px 9px; }"
            "QListView::item:selected { background-color: #291018; color: #ffffff; "
            "border-left: 3px solid #E31837; }"
            "QListView::item:hover { background-color: #191E26; color: #ffffff; }"
        )
        palette = popup.palette()
        palette.setColor(QPalette.Base, QColor("#080a0d"))
        palette.setColor(QPalette.Window, QColor("#080a0d"))
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        palette.setColor(QPalette.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.Highlight, QColor("#291018"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        popup.setPalette(palette)
        self.setView(popup)

    def showPopup(self) -> None:
        super().showPopup()
        popup_window = self.view().window()
        popup_window.setAutoFillBackground(True)
        popup_window.setPalette(self.view().palette())


class AspectPreviewLabel(QLabel):
    """Display the complete 16:9 preview without clipping it to the widget."""

    def __init__(self, text: str = ""):
        super().__init__(text)
        self._source_pixmap = QPixmap()
        self._show_center_guide = True

    def set_preview_pixmap(self, pixmap: QPixmap) -> None:
        self._source_pixmap = pixmap
        self.setText("")
        self._fit_pixmap()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._fit_pixmap()

    def set_center_guide(self, visible: bool) -> None:
        self._show_center_guide = visible
        self.update()

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)
        pixmap = self.pixmap()
        if not self._show_center_guide or pixmap is None or pixmap.isNull():
            return
        width, height = pixmap.width(), pixmap.height()
        if width <= height:
            return
        x = (self.width() - width) / 2 + (width - height) / 2
        y = (self.height() - height) / 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(227, 24, 55, 185), 1.5, Qt.DashLine))
        painter.drawRect(int(x), int(y), max(0, height - 1), max(0, height - 1))
        painter.setPen(QColor(255, 107, 128))
        painter.drawText(int(x + 10), int(y + height - 12), "CENTER COVER · 1080 × 1080")

    def _fit_pixmap(self) -> None:
        if self._source_pixmap.isNull():
            return
        available = self.contentsRect().size()
        if available.width() <= 0 or available.height() <= 0:
            return
        fitted = self._source_pixmap.scaled(
            available,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        super().setPixmap(fitted)


def hash_upload_items(items: list[UploadItem]) -> list[UploadItem]:
    for item in items:
        source = Path(item.source_path)
        stat = source.stat()
        item.file_size = stat.st_size
        item.modified_ns = stat.st_mtime_ns
        item.file_hash = sha256_file(source)
    return items


class QueueTableWidget(QTableWidget):
    rows_reordered = Signal(int, int)

    def dropEvent(self, event) -> None:
        source = self.currentRow()
        target = self.indexAt(event.position().toPoint()).row()
        if target < 0:
            target = self.rowCount() - 1
        if source >= 0 and target >= 0 and source != target:
            self.rows_reordered.emit(source, target)
            event.accept()
        else:
            event.ignore()


class DashboardPage(QWidget):
    quick_upload = Signal()
    quick_thumbnails = Signal()
    quick_schedule = Signal()
    quick_connect = Signal()

    def __init__(self, database: Database, settings: SettingsStore | None = None):
        super().__init__()
        self.database = database
        self.settings = settings
        root, _ = page_header("Dashboard", "Creator workflow overview and quick actions")
        cards = QGridLayout()
        cards.setSpacing(SPACE_3)
        self.stat_cards: dict[str, StatCard] = {}
        definitions = [
            ("waiting", "Videos Waiting", "history", COLORS.crimson_hover),
            ("completed", "Completed Uploads", "check", COLORS.success),
            ("failed", "Failed Uploads", "warning", COLORS.error),
            ("thumbs", "Generated Thumbnails", "image", "#FF3B78"),
        ]
        for index, (key, label, icon_name, color) in enumerate(definitions):
            card = StatCard(label, icon_name, color, [0])
            cards.addWidget(card, 0, index)
            self.stat_cards[key] = card
        root.addLayout(cards)

        actions = SectionCard("Quick Actions", "Jump directly into the creator workflow", "upload")
        action_layout = QHBoxLayout()
        for text, detail, icon_name, signal in [
            ("Create Upload Batch", "Prepare a new video batch", "upload", self.quick_upload),
            ("Generate Thumbnails", "Create artwork from a source", "image", self.quick_thumbnails),
            ("Open Schedule", "Preview publishing slots", "calendar", self.quick_schedule),
            ("Connect Channel", "Manage YouTube access", "link", self.quick_connect),
        ]:
            button = ActionButton(f"{text}\n{detail}", "secondary", icon_name)
            button.setMinimumHeight(58)
            button.clicked.connect(signal.emit)
            action_layout.addWidget(button)
        actions.body.addLayout(action_layout)
        root.addWidget(actions)

        lower = QHBoxLayout()
        lower.setSpacing(SPACE_3)
        activity = SectionCard("Recent Activity", "Real actions recorded by UPLOAD PLUGG", "history")
        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(SPACE_2)
        activity.body.addLayout(self.activity_layout)
        overview = SectionCard("System Overview", "Current local workflow state", "dashboard")
        self.overview_labels: dict[str, QLabel] = {}
        for key, label in (
            ("preset", "Active Preset"),
            ("output", "Output Folder"),
            ("timezone", "Timezone"),
            ("next", "Next Upload"),
        ):
            row = QHBoxLayout()
            caption = QLabel(label)
            caption.setObjectName("muted")
            value = QLabel("—")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value.setWordWrap(True)
            row.addWidget(caption)
            row.addWidget(value, 1)
            overview.body.addLayout(row)
            self.overview_labels[key] = value
        self.overall_label = QLabel("Overall progress · 0%")
        self.overall_label.setObjectName("muted")
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setFixedHeight(8)
        overview.body.addWidget(self.overall_label)
        overview.body.addWidget(self.overall_progress)
        lower.addWidget(activity, 3)
        lower.addWidget(overview, 2)
        root.addLayout(lower, 1)
        root.addStretch()
        self.setLayout(root)

    def refresh(self, queue: list[UploadItem], generated_count: int = 0) -> None:
        rows = self.database.list_uploads()
        activities = self.database.list_activities(1000)
        thumbnail_total = sum(
            int(row.get("detail", "0").split()[0])
            for row in activities
            if row.get("kind") == "thumbnail" and row.get("detail", "").split()[:1]
            and row.get("detail", "").split()[0].isdigit()
        )
        values = {
            "waiting": sum(item.selected for item in queue),
            "completed": sum(r["status"] == "Completed" for r in rows),
            "failed": sum(r["status"] == "Failed" for r in rows),
            "thumbs": max(generated_count, thumbnail_total),
        }
        for key, value in values.items():
            self.stat_cards[key].value.setText(str(value))
        self.stat_cards["waiting"].sparkline.set_points([item.progress for item in queue] or [0])
        self.stat_cards["completed"].sparkline.set_points(self._history_points(rows, "Completed"))
        self.stat_cards["failed"].sparkline.set_points(self._history_points(rows, "Failed"))
        self.stat_cards["thumbs"].sparkline.set_points(
            [int(row["detail"].split()[0]) for row in reversed(activities)
             if row.get("kind") == "thumbnail" and row.get("detail", "").split()[:1]
             and row["detail"].split()[0].isdigit()] or [0]
        )
        self._refresh_activity(activities[:6])
        active = self.settings.data.get("active_preset", "—") if self.settings else "—"
        presets = self.settings.presets() if self.settings else []
        preset = next((entry for entry in presets if entry.name == active), presets[0] if presets else None)
        self.overview_labels["preset"].setText(active or "—")
        self.overview_labels["output"].setText(
            self.settings.data.get("folders", {}).get("thumbnail_output", "") or "Not selected"
            if self.settings else "Not selected"
        )
        self.overview_labels["timezone"].setText(preset.timezone if preset else "Europe/Berlin")
        now = datetime.now().astimezone()
        upcoming = sorted(
            item.publish_at
            for item in queue
            if item.selected
            and item.publish_at
            and (parsed := self._parse_queue_time(item.publish_at)) is not None
            and parsed > now
        )
        self.overview_labels["next"].setText(upcoming[0].replace("T", " ")[:16] if upcoming else "Not scheduled")
        selected = [item for item in queue if item.selected]
        progress = round(sum(item.progress for item in selected) / len(selected)) if selected else 0
        self.overall_progress.setValue(progress)
        self.overall_label.setText(f"Overall progress · {progress}%")

    @staticmethod
    def _parse_queue_time(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
        except ValueError:
            return None

    @staticmethod
    def _history_points(rows: list[dict[str, object]], status: str) -> list[int]:
        buckets: dict[str, int] = {}
        for row in rows:
            if row.get("status") == status:
                day = str(row.get("created_at", ""))[:10]
                buckets[day] = buckets.get(day, 0) + 1
        return list(reversed(list(buckets.values())[:10])) or [0]

    def _refresh_activity(self, rows: list[dict[str, object]]) -> None:
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        if not rows:
            self.activity_layout.addWidget(
                EmptyState("No activity yet", "Actions appear here after you use the workflow.", "history")
            )
            return
        for entry in rows:
            row = QFrame()
            row.setObjectName("activityRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(4, 5, 4, 5)
            status = str(entry.get("status", "info"))
            icon = QLabel()
            icon.setPixmap(line_icon(
                "warning" if status == "error" else "check",
                COLORS.error if status == "error" else COLORS.success,
                17,
            ).pixmap(17, 17))
            texts = QVBoxLayout()
            texts.setSpacing(1)
            title = QLabel(str(entry.get("message", "Activity")))
            detail = QLabel(str(entry.get("detail", "")))
            detail.setObjectName("caption")
            texts.addWidget(title)
            if detail.text():
                texts.addWidget(detail)
            when = QLabel(str(entry.get("created_at", ""))[:16])
            when.setObjectName("caption")
            layout.addWidget(icon)
            layout.addLayout(texts, 1)
            layout.addWidget(when)
            self.activity_layout.addWidget(row)


class UploadGeneratorPage(QWidget):
    request_task = Signal(object, object, object)
    request_upload = Signal(object, object)
    request_cancel = Signal()
    queue_changed = Signal()

    COLUMNS = [
        "Use", "#", "Thumbnail", "Source Filename", "Beat Name", "Collaborator", "Generated Title",
        "Preset", "Scheduled Date", "Scheduled Time", "Validation", "Upload Status", "Progress", "YouTube Result",
    ]

    def __init__(self, settings: SettingsStore, database: Database, paths: AppPaths):
        super().__init__()
        self.settings = settings
        self.database = database
        self.paths = paths
        self.items: list[UploadItem] = database.load_queue()
        self._populating = False
        self._initializing = True
        root, _ = page_header("Upload Generator", "Prepare, validate and upload up to 30 finished MP4 videos")

        configuration_row = QHBoxLayout()
        configuration_row.setSpacing(SPACE_3)
        workflow = SectionCard(
            "Source Configuration",
            "Select the finished MP4 files and metadata preset",
            "folder",
        )
        controls = QGridLayout()
        controls.setHorizontalSpacing(SPACE_2)
        controls.setVerticalSpacing(SPACE_2)
        self.folder = QLineEdit(settings.data["folders"].get("videos", ""))
        browse = ActionButton("Select Folder", "secondary", "folder")
        browse.clicked.connect(self.choose_folder)
        self.batch = QSpinBox()
        self.batch.setRange(1, MAX_BATCH_SIZE)
        self.batch.setValue(10)
        self.sorting = DarkComboBox()
        self.sorting.addItems([
            "Natural numeric order", "Name, A–Z", "Name, Z–A", "Date created, oldest first",
            "Date created, newest first", "Date modified, oldest first", "Date modified, newest first",
            "Manual order",
        ])
        self.preset = DarkComboBox()
        self.refresh_presets()
        controls.addWidget(QLabel("Video folder"), 0, 0)
        controls.addWidget(self.folder, 1, 0, 1, 6)
        controls.addWidget(browse, 1, 6)
        controls.addWidget(QLabel("Batch size"), 2, 0)
        controls.addWidget(self.batch, 3, 0)
        controls.addWidget(QLabel("Sorting"), 2, 1)
        controls.addWidget(self.sorting, 3, 1, 1, 3)
        controls.addWidget(QLabel("Preset"), 2, 4)
        controls.addWidget(self.preset, 3, 4, 1, 3)
        workflow.body.addLayout(controls)
        configuration_row.addWidget(workflow, 5)

        actions = SectionCard("Batch Actions", "Prepare and verify the selected videos", "preset")
        action_grid = QGridLayout()
        action_grid.setSpacing(SPACE_2)
        scan = ActionButton("Scan Folder", "secondary", "search")
        scan.clicked.connect(self.scan)
        metadata = ActionButton("Generate Metadata", "secondary", "preset")
        metadata.clicked.connect(self.generate_all)
        random_button = ActionButton("Random Thumbnails", "secondary", "image")
        random_button.clicked.connect(self.random_thumbnails)
        schedule_button = ActionButton("Calculate Schedule", "secondary", "calendar")
        schedule_button.clicked.connect(self.schedule)
        validate_button = ActionButton("Validate Batch", "secondary", "check")
        validate_button.clicked.connect(self.validate)
        dry_button = ActionButton("Run Dry Test", "secondary", "logs")
        dry_button.clicked.connect(self.dry_run)
        for index, button in enumerate((scan, metadata, random_button, validate_button, schedule_button, dry_button)):
            action_grid.addWidget(button, index // 2, index % 2)
        actions.body.addLayout(action_grid)
        configuration_row.addWidget(actions, 3)

        upload_control = SectionCard("Upload Control", "YouTube queue and cancellation", "upload")
        self.upload_button = ActionButton("Start Uploads", "primary", "upload")
        self.upload_button.setMinimumHeight(48)
        self.upload_button.clicked.connect(self.start_uploads)
        self.cancel_upload_button = ActionButton("Stop Uploads", "danger", "stop")
        self.cancel_upload_button.setEnabled(False)
        self.cancel_upload_button.clicked.connect(self.request_cancel.emit)
        self.upload_control_status = StatusBadge("Ready", "ready")
        upload_control.body.addWidget(self.upload_button)
        upload_control.body.addWidget(self.cancel_upload_button)
        upload_control.body.addWidget(self.upload_control_status)
        configuration_row.addWidget(upload_control, 2)
        root.addLayout(configuration_row)

        schedule_box = SectionCard("Schedule", "Choose the local publication cadence", "calendar")
        schedule_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.schedule_time = QTimeEdit(QTime(18, 0))
        self.timezone = QLineEdit("Europe/Berlin")
        self.day_checks: list[QCheckBox] = []
        for index, day in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            check = QCheckBox(day)
            check.setProperty("chip", True)
            check.setChecked(index in {1, 3, 4, 6})
            self.day_checks.append(check)
            schedule_layout.addWidget(check)
        schedule_layout.addWidget(QLabel("Start"))
        schedule_layout.addWidget(self.start_date)
        schedule_layout.addWidget(QLabel("Time"))
        schedule_layout.addWidget(self.schedule_time)
        schedule_layout.addWidget(QLabel("Timezone"))
        schedule_layout.addWidget(self.timezone)
        schedule_box.body.addLayout(schedule_layout)
        root.addWidget(schedule_box)
        self.preset.currentTextChanged.connect(self.apply_preset_defaults)

        self.summary = QLabel("Ready to scan a folder.")
        self.summary.setObjectName("muted")
        root.addWidget(self.summary)
        self.queue_empty = EmptyState(
            "No upload batch loaded",
            "Select a video folder and scan it to build the queue.",
            "upload",
        )
        root.addWidget(self.queue_empty, 1)
        self.table = QueueTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setDragDropMode(QAbstractItemView.InternalMove)
        self.table.setDefaultDropAction(Qt.MoveAction)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setIconSize(QSize(64, 36))
        self.table.setMinimumHeight(270)
        self.table.cellChanged.connect(self.cell_changed)
        self.table.currentCellChanged.connect(self.show_details)
        self.table.rows_reordered.connect(self.reorder_rows)
        self.table.hide()
        root.addWidget(self.table, 1)

        details = SectionCard(
            "Selected Video Inspector",
            "Review the exact metadata and artwork that will be sent to YouTube",
            "preset",
        )
        details_layout = QGridLayout()
        details_layout.setHorizontalSpacing(SPACE_4)
        details_layout.setVerticalSpacing(SPACE_2)
        self.detail_description = QPlainTextEdit()
        self.detail_description.setPlaceholderText("Full generated description")
        self.detail_description.setMinimumHeight(145)
        self.detail_description.textChanged.connect(self.description_changed)
        self.detail_tags = QLineEdit()
        self.detail_tags.textEdited.connect(self.tags_changed)
        self.detail_credit = QLabel("Producer credits")
        self.detail_path = QLabel("Source path")
        self.detail_path.setWordWrap(True)
        self.detail_title = QLabel("No video selected")
        self.detail_title.setObjectName("sectionTitle")
        self.detail_preset = QLabel("Preset · —")
        self.detail_schedule = QLabel("Schedule · Not scheduled")
        self.detail_validation = StatusBadge("Not checked", "not_checked")
        self.detail_upload = StatusBadge("Ready", "ready")
        self.detail_thumbnail = QLabel("No custom thumbnail assigned")
        self.detail_thumbnail.setAlignment(Qt.AlignCenter)
        self.detail_thumbnail.setMinimumSize(300, 169)
        self.detail_thumbnail.setStyleSheet(
            "background:#080B0F;border:1px solid #262D37;border-radius:10px;color:#707C8B"
        )
        details_layout.addWidget(self.detail_thumbnail, 0, 0, 6, 1)
        details_layout.addWidget(self.detail_title, 0, 1, 1, 2)
        details_layout.addWidget(self.detail_validation, 0, 3)
        details_layout.addWidget(self.detail_upload, 0, 4)
        details_layout.addWidget(QLabel("Description"), 1, 1)
        details_layout.addWidget(self.detail_description, 2, 1, 4, 2)
        details_layout.addWidget(QLabel("YouTube Tags"), 1, 3, 1, 2)
        details_layout.addWidget(self.detail_tags, 2, 3, 1, 2)
        details_layout.addWidget(self.detail_credit, 3, 3, 1, 2)
        details_layout.addWidget(self.detail_preset, 4, 3, 1, 2)
        details_layout.addWidget(self.detail_schedule, 5, 3, 1, 2)
        details_layout.addWidget(self.detail_path, 6, 0, 1, 5)
        details.body.addLayout(details_layout)
        root.addWidget(details)
        self.setLayout(root)
        self.apply_preset_defaults(self.preset.currentText())
        self._initializing = False
        self.synchronize_queue_metadata()
        self.populate()
        if self.items:
            self.show_details(0, 0)

    def refresh_presets(self, prefer_active: bool = False) -> None:
        selected = self.preset.currentText() if hasattr(self, "preset") else ""
        if hasattr(self, "preset"):
            self.preset.blockSignals(True)
            self.preset.clear()
            self.preset.addItems([preset.name for preset in self.settings.presets()])
            target = self.settings.data.get("active_preset", "") if prefer_active else selected
            index = self.preset.findText(target or self.settings.data.get("active_preset", ""))
            self.preset.setCurrentIndex(max(0, index))
            self.preset.blockSignals(False)

    def presets_updated(self) -> None:
        self.refresh_presets(prefer_active=True)
        self.apply_preset_defaults(self.preset.currentText())
        self.synchronize_queue_metadata()
        self.populate()

    def synchronize_queue_metadata(self, force: bool = False) -> int:
        if not self.items:
            return 0
        preset = self.current_preset()
        signature = preset_metadata_signature(preset)
        changed = 0
        for item in self.items:
            if force or item.metadata_signature != signature or item.preset_name != preset.name:
                synchronize_metadata(item, preset, preserve_manual=not force)
                changed += 1
        if changed:
            self.persist()
            self.summary.setText(
                f"Metadata synchronized with preset '{preset.name}' for {changed} video(s)."
            )
        return changed

    def choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select MP4 Video Folder", self.folder.text())
        if selected:
            self.folder.setText(selected)
            self.settings.data["folders"]["videos"] = selected
            self.settings.save()

    def scan(self) -> None:
        modes = ["natural", "name", "name_desc", "created_oldest", "created_newest", "modified_oldest", "modified_newest", "manual"]
        self.summary.setText("Scanning MP4 files…")
        self.request_task.emit(
            scan_videos,
            (self.folder.text(), modes[self.sorting.currentIndex()], self.batch.value()),
            {"done": self.scan_done, "failed": self.task_failed, "label": "Scanning folder"},
        )

    def scan_done(self, items: list[UploadItem]) -> None:
        self.items = items
        if items:
            self.generate_all()
            self.database.add_activity(
                "scan", "Folder scanned", f"{len(items)} video(s) found", "success"
            )
        self.summary.setText(f"{len(items)} of {self.batch.value()} requested videos found")
        if not items:
            QMessageBox.information(self, APP_NAME, "No supported MP4 files were found in this folder.")

    def generate_all(self) -> None:
        if not self.items:
            QMessageBox.information(self, APP_NAME, "Scan a video folder before generating metadata.")
            return
        preset = self.current_preset()
        for item in self.items:
            generate_metadata(item, preset)
        self.persist()
        self.populate()
        self.database.add_activity(
            "metadata", "Metadata generated", f"{len(self.items)} video(s) · {preset.name}", "success"
        )

    def random_thumbnails(self) -> None:
        if not any(item.selected for item in self.items):
            QMessageBox.information(self, APP_NAME, "Scan and select at least one video first.")
            return
        initial = self.settings.data["folders"].get("thumbnails", "")
        selected = QFileDialog.getExistingDirectory(self, "Select Thumbnail Pool", initial)
        if not selected:
            return
        images = image_pool(selected)
        if not images:
            QMessageBox.warning(self, APP_NAME, "No valid JPG, JPEG or PNG thumbnails were found.")
            return
        assignments = assign_without_repeats([item.id for item in self.items if item.selected], images)
        for item in self.items:
            if item.id in assignments:
                item.thumbnail_path = assignments[item.id]
        self.settings.data["folders"]["thumbnails"] = selected
        self.settings.data["thumbnail_assignments"] = assignments
        self.settings.save()
        self.persist()
        self.populate()
        self.database.add_activity(
            "thumbnail_assignment",
            "Random thumbnails assigned",
            f"{len(assignments)} assignment(s)",
            "success",
        )

    def schedule(self) -> None:
        if not any(item.selected for item in self.items):
            QMessageBox.information(self, APP_NAME, "Scan and select at least one video first.")
            return
        try:
            slots = calculate_schedule(
                sum(item.selected for item in self.items),
                date(self.start_date.date().year(), self.start_date.date().month(), self.start_date.date().day()),
                [i for i, box in enumerate(self.day_checks) if box.isChecked()],
                time(self.schedule_time.time().hour(), self.schedule_time.time().minute()),
                self.timezone.text().strip(),
            )
        except ScheduleError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        for item, slot in zip((i for i in self.items if i.selected), slots):
            item.publish_at = slot.isoformat()
            synchronize_metadata(item, self.current_preset(), preserve_manual=True)
        self.persist()
        self.populate()
        self.database.add_activity(
            "schedule", "Schedule calculated", f"{len(slots)} publication slot(s)", "success"
        )

    def validate(self, online: bool = False, connected: bool = False) -> tuple[int, int]:
        self.synchronize_queue_metadata()
        errors = warnings = 0
        for item in self.items:
            if not item.selected:
                continue
            issues = validate_item(item, online, connected)
            item.validation_messages = [f"{issue.severity.upper()}: {issue.message} Fix: {issue.fix}" for issue in issues]
            item.validation_status = "Error" if any(i.severity == "error" for i in issues) else "Warning" if issues else "Ready"
            errors += sum(i.severity == "error" for i in issues)
            warnings += sum(i.severity == "warning" for i in issues)
        self.persist()
        self.populate()
        self.summary.setText(f"Validation complete · {errors} errors · {warnings} warnings")
        self.database.add_activity(
            "validation",
            "Batch validated",
            f"{errors} error(s) · {warnings} warning(s)",
            "error" if errors else "success",
        )
        return errors, warnings

    def dry_run(self) -> None:
        self.validate()
        target, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Dry Run", str(self.paths.exports / "upload_plugg_dry_run.json"),
            "JSON (*.json);;CSV (*.csv);;Text report (*.txt)",
        )
        if not target:
            return
        format_name = "csv" if "CSV" in selected_filter else "text" if "Text" in selected_filter else "json"
        export_dry_run(self.items, Path(target), format_name)
        QMessageBox.information(self, APP_NAME, f"DRY RUN complete. No videos were uploaded.\n\nReport: {target}")

    def start_uploads(self) -> None:
        selected = [item for item in self.items if item.selected]
        if not selected:
            QMessageBox.warning(self, APP_NAME, "Select at least one video.")
            return
        errors, warnings = self.validate(online=True, connected=True)
        if errors:
            QMessageBox.critical(self, APP_NAME, f"Uploads cannot start while {errors} blocking validation errors remain.")
            return
        if any(not item.file_hash for item in selected):
            self.summary.setText("Calculating SHA-256 fingerprints for duplicate protection…")
            self.request_task.emit(
                hash_upload_items,
                (selected,),
                {
                    "done": lambda result: self.finish_start_uploads(result, warnings),
                    "failed": self.task_failed,
                    "label": "Preparing upload fingerprints",
                },
            )
            return
        self.finish_start_uploads(selected, warnings)

    def finish_start_uploads(self, selected: list[UploadItem], warnings: int) -> None:
        self.persist()
        duplicates = []
        for item in selected:
            for row in self.database.find_duplicates(item):
                if item.file_hash and row.get("sha256") == item.file_hash:
                    reason = "exact SHA-256 file match"
                elif row.get("original_filename") == item.filename and row.get("file_size") == item.file_size:
                    reason = "same filename and file size"
                else:
                    reason = "same generated title"
                duplicates.append((item, row, reason))
        total_size = sum(item.file_size for item in selected) / (1024**3)
        first = min((i.publish_at for i in selected if i.publish_at), default="Not scheduled")
        last = max((i.publish_at for i in selected if i.publish_at), default="Not scheduled")
        duplicate_detail = ""
        if duplicates:
            duplicate_detail = "\nPossible duplicates:\n" + "\n".join(
                f"• {item.filename}: {reason} (previous status: {row.get('status', '')})"
                for item, row, reason in duplicates[:5]
            )
        message = (
            f"Videos: {len(selected)}\nTotal data: {total_size:.2f} GB\n"
            f"First publication: {first}\nLast publication: {last}\n"
            f"Custom thumbnails: {sum(bool(i.thumbnail_path) for i in selected)}\n"
            f"Duplicate warnings: {len(duplicates)}\nValidation warnings: {warnings}\n\n"
            "End screens cannot be applied by the official API and remain a post-upload task."
            + duplicate_detail
        )
        answer = QMessageBox.question(self, "Confirm Uploads", message + "\n\nStart uploads now?")
        if answer == QMessageBox.Yes:
            self.request_upload.emit(selected, self.current_preset())

    def current_preset(self) -> Preset:
        for preset in self.settings.presets():
            if preset.name == self.preset.currentText():
                return preset
        return self.settings.presets()[0]

    def apply_preset_defaults(self, _name: str) -> None:
        preset = self.current_preset()
        self.batch.setValue(max(1, min(30, preset.default_batch_size)))
        self.timezone.setText(preset.timezone)
        try:
            hour, minute = (int(value) for value in preset.schedule_time.split(":", 1))
            self.schedule_time.setTime(QTime(hour, minute))
        except (ValueError, TypeError):
            self.schedule_time.setTime(QTime(18, 0))
        for index, box in enumerate(self.day_checks):
            box.setChecked(index in preset.schedule_days)
        if not self._initializing:
            self.settings.data["active_preset"] = preset.name
            self.settings.save()
            self.synchronize_queue_metadata()
            self.populate()

    def populate(self) -> None:
        selected_id = ""
        if 0 <= self.table.currentRow() < len(self.items):
            selected_id = self.items[self.table.currentRow()].id
        self._populating = True
        self.queue_empty.setVisible(not self.items)
        self.table.setVisible(bool(self.items))
        self.table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            use = QTableWidgetItem()
            use.setFlags(use.flags() | Qt.ItemIsUserCheckable)
            use.setCheckState(Qt.Checked if item.selected else Qt.Unchecked)
            thumbnail_item = QTableWidgetItem(Path(item.thumbnail_path).name if item.thumbnail_path else "Default")
            if item.thumbnail_path and Path(item.thumbnail_path).is_file():
                thumbnail_item.setIcon(QIcon(QPixmap(item.thumbnail_path).scaled(96, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            scheduled_date = item.publish_at[:10] if item.publish_at else "Not scheduled"
            scheduled_time = item.publish_at[11:16] if item.publish_at else ""
            values = [
                use, QTableWidgetItem(str(row + 1)), thumbnail_item,
                QTableWidgetItem(item.filename), QTableWidgetItem(item.beat_name), QTableWidgetItem(item.collaborator),
                QTableWidgetItem(item.display_title), QTableWidgetItem(item.preset_name),
                QTableWidgetItem(scheduled_date), QTableWidgetItem(scheduled_time),
                QTableWidgetItem(item.validation_status), QTableWidgetItem(item.upload_status),
                QTableWidgetItem(f"{item.progress}%"), QTableWidgetItem(item.youtube_url),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, value)
            validation = StatusBadge(item.validation_status, self._status_role(item.validation_status))
            upload = StatusBadge(item.upload_status, self._status_role(item.upload_status))
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(item.progress)
            progress.setFormat(f"{item.progress}%")
            progress.setMinimumWidth(82)
            self.table.setCellWidget(row, 10, validation)
            self.table.setCellWidget(row, 11, upload)
            self.table.setCellWidget(row, 12, progress)
            for column in (1, 2, 3, 7, 8, 9, 10, 11, 12, 13):
                self.table.item(row, column).setFlags(self.table.item(row, column).flags() & ~Qt.ItemIsEditable)
        self._populating = False
        if selected_id:
            selected_row = next((index for index, item in enumerate(self.items) if item.id == selected_id), -1)
            if selected_row >= 0:
                self.table.selectRow(selected_row)
        elif self.items:
            self.table.selectRow(0)
        self.queue_changed.emit()

    @staticmethod
    def _status_role(value: str) -> str:
        folded = value.casefold()
        if any(token in folded for token in ("complete", "ready", "applied")):
            return "ready"
        if any(token in folded for token in ("fail", "error", "cancel")):
            return "error"
        if any(token in folded for token in ("upload", "validat", "hash", "preparing")):
            return "uploading"
        if "schedul" in folded:
            return "scheduled"
        if any(token in folded for token in ("wait", "warning", "retry")):
            return "waiting"
        return "neutral"

    def cell_changed(self, row: int, column: int) -> None:
        if self._populating or row >= len(self.items):
            return
        item = self.items[row]
        if column == 0:
            item.selected = self.table.item(row, 0).checkState() == Qt.Checked
        elif column == 4:
            item.beat_name = self.table.item(row, column).text().strip()
            synchronize_metadata(item, self.current_preset(), preserve_manual=True)
        elif column == 5:
            item.collaborator = self.table.item(row, column).text().strip()
            synchronize_metadata(item, self.current_preset(), preserve_manual=True)
        elif column == 6:
            item.display_title = self.table.item(row, column).text().strip()
            if "title" not in item.manual_metadata_fields:
                item.manual_metadata_fields.append("title")
        self.persist()

    def reorder_rows(self, source: int, target: int) -> None:
        item = self.items.pop(source)
        self.items.insert(target, item)
        self.persist()
        self.populate()
        self.table.selectRow(target)

    def show_details(self, row: int, _column: int, *_: int) -> None:
        if row < 0 or row >= len(self.items):
            return
        item = self.items[row]
        self.detail_description.blockSignals(True)
        self.detail_description.setPlainText(item.description)
        self.detail_description.blockSignals(False)
        self.detail_tags.blockSignals(True)
        self.detail_tags.setText(", ".join(item.tags))
        self.detail_tags.blockSignals(False)
        preset = self.current_preset()
        self.detail_title.setText(item.display_title or item.filename)
        self.detail_credit.setText(producer_credits(preset.producer, item.collaborator, preset.credit_separator))
        self.detail_preset.setText(f"Preset · {item.preset_name or preset.name}")
        self.detail_schedule.setText(
            f"Schedule · {item.publish_at.replace('T', ' ')[:16]}" if item.publish_at
            else "Schedule · Not scheduled"
        )
        self.detail_validation.set_status(
            self._status_role(item.validation_status), item.validation_status
        )
        self.detail_upload.set_status(self._status_role(item.upload_status), item.upload_status)
        self.detail_path.setText(item.source_path)
        if item.thumbnail_path and Path(item.thumbnail_path).is_file():
            preview = QPixmap(item.thumbnail_path).scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.detail_thumbnail.setPixmap(preview)
        else:
            self.detail_thumbnail.clear()
            self.detail_thumbnail.setText("▧\nNo custom thumbnail assigned")

    def description_changed(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.items):
            self.items[row].description = self.detail_description.toPlainText()
            if "description" not in self.items[row].manual_metadata_fields:
                self.items[row].manual_metadata_fields.append("description")
            self.persist()

    def tags_changed(self, text: str) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.items):
            self.items[row].tags = [value.strip() for value in text.split(",") if value.strip()]
            if "tags" not in self.items[row].manual_metadata_fields:
                self.items[row].manual_metadata_fields.append("tags")
            self.persist()

    def update_progress(self, item_id: str, percent: int, stage: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.progress = percent
                item.upload_status = stage
                break
        self.upload_control_status.set_status(self._status_role(stage), stage)
        self.populate()

    def update_result(self, item_id: str, status: str, value: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.upload_status = status
                if status == "Completed":
                    item.youtube_url = value
                    item.progress = 100
                else:
                    item.validation_messages.append(value)
                break
        self.upload_control_status.set_status(self._status_role(status), status)
        self.persist()
        self.populate()

    def persist(self) -> None:
        self.database.save_queue(self.items)
        self.queue_changed.emit()

    def task_failed(self, message: str) -> None:
        self.summary.setText(message)
        QMessageBox.critical(self, APP_NAME, message)


class ThumbnailGeneratorPage(QWidget):
    request_task = Signal(object, object, object)
    generated = Signal(int)

    def __init__(
        self,
        settings: SettingsStore,
        paths: AppPaths,
        database: Database | None = None,
    ):
        super().__init__()
        self.settings = settings
        self.paths = paths
        self.database = database
        self.preview_source: Path | None = None
        self.preview_revision = 0
        self.batch_cancel_event: threading.Event | None = None
        self.solid_color = (18, 18, 20)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300)
        self.preview_timer.timeout.connect(self.refresh_live_preview)
        root, _ = page_header("Thumbnail Generator", "Offline 1920 × 1080 JPG processing from existing artwork")
        self.source = QLineEdit()
        self.output = QLineEdit(settings.data["folders"].get("thumbnail_output", ""))
        source_file = QPushButton("Source Image")
        source_file.clicked.connect(self.select_source)
        source_folder = QPushButton("Source Folder")
        source_folder.clicked.connect(self.select_source_folder)
        output_button = QPushButton("Output Folder")
        output_button.clicked.connect(self.select_output)
        self.mode = DarkComboBox()
        self.mode.addItem("Square Center + Blurred Sides", "square_blur")
        self.mode.addItem("Crop to Full 16:9", "crop_16_9")
        self.mode.addItem("Fit Entire Image + Background Fill", "fit_background")
        self.background_mode = DarkComboBox()
        self.background_mode.addItem("Artwork · Blur / Darken", "artwork")
        self.background_mode.addItem("Solid Color", "solid")
        self.color_button = QPushButton("Choose Background Color")
        self.color_button.clicked.connect(self.choose_background_color)
        self.filter_mode = DarkComboBox()
        self.filter_mode.addItem("Original Colors", "original")
        self.filter_mode.addItem("Monochrome", "monochrome")
        self.filter_mode.addItem("Red Tones", "red")
        self.filter_mode.addItem("Blue Tones", "blue")
        self.filter_mode.addItem("Change Color…", "custom")
        self.filter_color = (190, 25, 45)
        self.filter_color_button = QPushButton("Change Filter Color")
        self.filter_color_button.clicked.connect(self.choose_filter_color)
        self.filter_strength = QSlider(Qt.Horizontal)
        self.filter_strength.setRange(0, 100)
        self.filter_strength.setValue(100)
        self.watermark = QLineEdit()
        self.watermark.setPlaceholderText("Optional transparent PNG or JPG logo")
        watermark_button = QPushButton("Watermark / Logo")
        watermark_button.clicked.connect(self.select_watermark)
        clear_watermark = QPushButton("Clear Watermark")
        clear_watermark.clicked.connect(self.clear_watermark)
        self.watermark_position = DarkComboBox()
        self.watermark_position.addItem("Bottom Right", "bottom_right")
        self.watermark_position.addItem("Bottom Left", "bottom_left")
        self.watermark_size = QSlider(Qt.Horizontal)
        self.watermark_size.setRange(10, 100)
        self.watermark_size.setValue(55)
        self.watermark_margin = QSpinBox()
        self.watermark_margin.setRange(16, 180)
        self.watermark_margin.setValue(48)
        self.watermark_margin.setSuffix(" px")
        self.blur = QSlider(Qt.Horizontal)
        self.blur.setRange(0, 60)
        self.blur.setValue(28)
        self.darkness = QSlider(Qt.Horizontal)
        self.darkness.setRange(0, 90)
        self.darkness.setValue(45)
        self.quality = QSpinBox()
        self.quality.setRange(45, 95)
        self.quality.setValue(92)
        self.crop_x = QSlider(Qt.Horizontal); self.crop_x.setRange(0, 100); self.crop_x.setValue(50)
        self.crop_y = QSlider(Qt.Horizontal); self.crop_y.setRange(0, 100); self.crop_y.setValue(50)
        self.zoom = QDoubleSpinBox(); self.zoom.setRange(1.0, 3.0); self.zoom.setDecimals(2); self.zoom.setSingleStep(0.05); self.zoom.setValue(1.15)
        self.saturation = QSlider(Qt.Horizontal); self.saturation.setRange(0, 160); self.saturation.setValue(75)
        self.center_size = QSpinBox(); self.center_size.setRange(640, 1080); self.center_size.setValue(1080); self.center_size.setSuffix(" px")
        self.suffix = QLineEdit("_thumbnail")
        self.crop_x_label = QLabel("Crop X · 50%")
        self.crop_y_label = QLabel("Crop Y · 50%")
        self.blur_label = QLabel("Blur · 28 px")
        self.darkness_label = QLabel("Darkness · 45%")
        self.saturation_label = QLabel("Background saturation · 75%")
        self.filter_strength_label = QLabel("Filter strength · 100%")
        self.watermark_size_label = QLabel("Watermark size · 55%")
        self.crop_x.setToolTip("Move the crop focus left or right. The preview updates automatically.")
        self.crop_y.setToolTip("Move the crop focus up or down. The preview updates automatically.")
        self.zoom.setToolTip("Zoom creates room for Crop X and Crop Y to reposition square artwork.")
        self.saturation.setToolTip("Change only the artwork used behind the centered cover.")
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setMinimumWidth(390)
        left_scroll.setMaximumWidth(550)
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, SPACE_2, 0)
        left.setSpacing(SPACE_3)

        source_card = SectionCard("Source & Output", "Choose artwork, folders and export location", "folder")
        source_form = QGridLayout()
        source_form.setSpacing(SPACE_2)
        source_form.addWidget(QLabel("Source"), 0, 0, 1, 2)
        source_form.addWidget(self.source, 1, 0, 1, 2)
        source_form.addWidget(source_file, 2, 0)
        source_form.addWidget(source_folder, 2, 1)
        source_form.addWidget(QLabel("Output"), 3, 0, 1, 2)
        source_form.addWidget(self.output, 4, 0, 1, 2)
        source_form.addWidget(output_button, 5, 0, 1, 2)
        source_card.body.addLayout(source_form)
        left.addWidget(source_card)

        background_card = SectionCard("Layout & Background", "Control the 16:9 side areas", "image")
        background_form = QGridLayout()
        background_form.setSpacing(SPACE_2)
        background_form.addWidget(QLabel("Layout"), 0, 0)
        background_form.addWidget(self.mode, 0, 1)
        background_form.addWidget(QLabel("Background"), 1, 0)
        background_form.addWidget(self.background_mode, 1, 1)
        background_form.addWidget(self.color_button, 2, 0, 1, 2)
        background_form.addWidget(self.blur_label, 3, 0)
        background_form.addWidget(self.blur, 3, 1)
        background_form.addWidget(self.darkness_label, 4, 0)
        background_form.addWidget(self.darkness, 4, 1)
        background_form.addWidget(self.saturation_label, 5, 0)
        background_form.addWidget(self.saturation, 5, 1)
        background_card.body.addLayout(background_form)
        left.addWidget(background_card)

        cover_card = SectionCard("Cover Position & Scale", "Move and zoom the centered square cover", "image")
        cover_form = QGridLayout()
        cover_form.setSpacing(SPACE_2)
        cover_form.addWidget(self.crop_x_label, 0, 0)
        cover_form.addWidget(self.crop_x, 0, 1)
        cover_form.addWidget(self.crop_y_label, 1, 0)
        cover_form.addWidget(self.crop_y, 1, 1)
        cover_form.addWidget(QLabel("Zoom"), 2, 0)
        cover_form.addWidget(self.zoom, 2, 1)
        cover_form.addWidget(QLabel("Center size"), 3, 0)
        cover_form.addWidget(self.center_size, 3, 1)
        cover_card.body.addLayout(cover_form)
        left.addWidget(cover_card)

        filter_card = SectionCard("Color & Filter", "Apply tonal remapping without flattening the artwork", "color")
        filter_form = QGridLayout()
        filter_form.setSpacing(SPACE_2)
        filter_form.addWidget(QLabel("Color filter"), 0, 0)
        filter_form.addWidget(self.filter_mode, 0, 1)
        filter_form.addWidget(self.filter_strength_label, 1, 0)
        filter_form.addWidget(self.filter_strength, 1, 1)
        filter_form.addWidget(self.filter_color_button, 2, 0, 1, 2)
        filter_card.body.addLayout(filter_form)
        left.addWidget(filter_card)

        watermark_card = SectionCard("Watermark", "Place a transparent logo in either side area", "watermark")
        watermark_form = QGridLayout()
        watermark_form.setSpacing(SPACE_2)
        watermark_form.addWidget(self.watermark, 0, 0, 1, 2)
        watermark_form.addWidget(watermark_button, 1, 0)
        watermark_form.addWidget(clear_watermark, 1, 1)
        watermark_form.addWidget(QLabel("Placement"), 2, 0)
        watermark_form.addWidget(self.watermark_position, 2, 1)
        watermark_form.addWidget(self.watermark_size_label, 3, 0)
        watermark_form.addWidget(self.watermark_size, 3, 1)
        watermark_form.addWidget(QLabel("Edge margin"), 4, 0)
        watermark_form.addWidget(self.watermark_margin, 4, 1)
        watermark_card.body.addLayout(watermark_form)
        left.addWidget(watermark_card)

        export_card = SectionCard("Export Settings", "JPG quality and filename", "export")
        export_form = QGridLayout()
        export_form.setSpacing(SPACE_2)
        export_form.addWidget(QLabel("Quality"), 0, 0)
        export_form.addWidget(self.quality, 0, 1)
        export_form.addWidget(QLabel("Filename suffix"), 1, 0)
        export_form.addWidget(self.suffix, 1, 1)
        export_card.body.addLayout(export_form)
        left.addWidget(export_card)

        buttons = QGridLayout()
        buttons.setSpacing(SPACE_2)
        preview = ActionButton("Generate Preview", "secondary", "image")
        preview.clicked.connect(self.preview)
        random_preview = ActionButton("New Random Preview", "secondary", "refresh")
        random_preview.clicked.connect(self.new_random_preview)
        self.generate_random_button = ActionButton("Generate Random Thumbnail", "secondary", "image")
        self.generate_random_button.clicked.connect(self.generate_random)
        self.generate_button = ActionButton("Generate Thumbnail(s)", "primary", "upload")
        self.generate_button.clicked.connect(self.generate)
        self.stop_button = ActionButton("Stop Generation", "danger", "stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_generation)
        buttons.addWidget(preview, 0, 0)
        buttons.addWidget(random_preview, 0, 1)
        buttons.addWidget(self.generate_random_button, 1, 0, 1, 2)
        buttons.addWidget(self.generate_button, 2, 0, 1, 2)
        buttons.addWidget(self.stop_button, 3, 0, 1, 2)
        left.addLayout(buttons)
        left.addStretch()
        left_scroll.setWidget(left_widget)
        split.addWidget(left_scroll)

        preview_card = SectionCard(
            "Live Preview · 1920 × 1080",
            "The complete 16:9 output with a centered square cover and visible side areas",
            "image",
        )
        self.preview_source_label = QLabel("Preview source: none")
        self.preview_source_label.setObjectName("muted")
        preview_card.body.addWidget(self.preview_source_label)
        self.preview_label = AspectPreviewLabel("Preview appears here")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(560, 315)
        self.preview_label.setStyleSheet(
            "background:#05070A;border:1px solid #323B48;border-radius:12px;color:#707C8B"
        )
        preview_card.body.addWidget(self.preview_label, 1)
        dimensions = QLabel("Output canvas 1920 × 1080 · Center cover up to 1080 × 1080 · 16:9")
        dimensions.setObjectName("caption")
        dimensions.setAlignment(Qt.AlignCenter)
        preview_card.body.addWidget(dimensions)
        self.progress = QProgressBar()
        preview_card.body.addWidget(self.progress)
        split.addWidget(preview_card)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([470, 1050])
        root.addWidget(split, 1)
        self.setLayout(root)
        self.source.textChanged.connect(self.source_changed)
        self.mode.currentIndexChanged.connect(self.option_changed)
        self.background_mode.currentIndexChanged.connect(self.background_changed)
        self.filter_mode.currentIndexChanged.connect(self.filter_changed)
        self.watermark.textChanged.connect(self.option_changed)
        for control in (
            self.blur, self.darkness, self.quality, self.crop_x, self.crop_y,
            self.zoom, self.saturation, self.center_size, self.filter_strength,
            self.watermark_size, self.watermark_margin,
        ):
            control.valueChanged.connect(self.option_changed)
        self.watermark_position.currentIndexChanged.connect(self.option_changed)
        self.update_control_labels()
        self.update_background_controls()
        self.update_color_button()
        self.update_filter_controls()

    def select_source(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Select Artwork", "", "Images (*.png *.jpg *.jpeg)")
        if selected:
            self.source.setText(selected)

    def select_source_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Artwork Folder")
        if selected:
            self.source.setText(selected)

    def select_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Thumbnail Output Folder", self.output.text())
        if selected:
            self.output.setText(selected)
            self.settings.data["folders"]["thumbnail_output"] = selected
            self.settings.save()

    def select_watermark(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Watermark or Logo",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if selected:
            self.watermark.setText(selected)

    def clear_watermark(self) -> None:
        self.watermark.clear()

    def source_changed(self, _text: str) -> None:
        self.preview_source = None
        self.preview_source_label.setText("Preview source: none")
        self.schedule_live_preview()

    def option_changed(self, *_: object) -> None:
        self.update_control_labels()
        self.preview_label.set_center_guide(self.mode.currentData() == "square_blur")
        self.schedule_live_preview()

    def background_changed(self, *_: object) -> None:
        self.update_background_controls()
        self.schedule_live_preview()

    def filter_changed(self, *_: object) -> None:
        self.update_filter_controls()
        self.schedule_live_preview()

    def update_control_labels(self) -> None:
        self.blur_label.setText(f"Blur · {self.blur.value()} px")
        self.darkness_label.setText(f"Darkness · {self.darkness.value()}%")
        self.crop_x_label.setText(f"Crop X · {self.crop_x.value()}%")
        self.crop_y_label.setText(f"Crop Y · {self.crop_y.value()}%")
        self.saturation_label.setText(f"Background saturation · {self.saturation.value()}%")
        self.filter_strength_label.setText(
            f"Filter strength · {self.filter_strength.value()}%"
        )
        self.watermark_size_label.setText(
            f"Watermark size · {self.watermark_size.value()}%"
        )

    def update_background_controls(self) -> None:
        artwork = self.background_mode.currentData() == "artwork"
        for control in (self.blur, self.darkness, self.saturation):
            control.setEnabled(artwork)
        self.color_button.setEnabled(not artwork)

    def choose_background_color(self) -> None:
        initial = QColor(*self.solid_color)
        color = QColorDialog.getColor(initial, self, "Choose Thumbnail Background Color")
        if not color.isValid():
            return
        self.solid_color = (color.red(), color.green(), color.blue())
        self.update_color_button()
        self.schedule_live_preview()

    def choose_filter_color(self) -> None:
        initial = QColor(*self.filter_color)
        color = QColorDialog.getColor(initial, self, "Choose Thumbnail Filter Color")
        if not color.isValid():
            return
        self.filter_color = (color.red(), color.green(), color.blue())
        self.update_filter_color_button()
        self.schedule_live_preview()

    def update_color_button(self) -> None:
        red, green, blue = self.solid_color
        brightness = (red * 299 + green * 587 + blue * 114) / 1000
        text = "#111111" if brightness > 150 else "white"
        self.color_button.setText(f"Color · #{red:02X}{green:02X}{blue:02X}")
        self.color_button.setStyleSheet(
            f"background: rgb({red}, {green}, {blue}); color: {text}; font-weight: 700;"
        )

    def update_filter_controls(self) -> None:
        mode = self.filter_mode.currentData()
        self.filter_strength.setEnabled(mode != "original")
        self.filter_color_button.setEnabled(mode == "custom")
        self.update_filter_color_button()

    def update_filter_color_button(self) -> None:
        red, green, blue = self.filter_color
        brightness = (red * 299 + green * 587 + blue * 114) / 1000
        text = "#111111" if brightness > 150 else "white"
        self.filter_color_button.setText(
            f"Change Color · #{red:02X}{green:02X}{blue:02X}"
        )
        self.filter_color_button.setStyleSheet(
            f"background: rgb({red}, {green}, {blue}); color: {text}; font-weight: 700;"
        )

    def schedule_live_preview(self) -> None:
        if source_images(self.source.text()):
            self.preview_timer.start()

    def options(self) -> ThumbnailOptions:
        return ThumbnailOptions(
            mode=self.mode.currentData(), background_mode=self.background_mode.currentData(),
            blur=float(self.blur.value()),
            darkness=self.darkness.value() / 100, quality=self.quality.value(),
            crop_x=self.crop_x.value() / 100, crop_y=self.crop_y.value() / 100,
            zoom=self.zoom.value(), saturation=self.saturation.value() / 100,
            center_size=self.center_size.value(), solid_color=self.solid_color,
            color_filter=self.filter_mode.currentData(),
            filter_color=self.filter_color,
            filter_strength=self.filter_strength.value() / 100,
            watermark_path=self.watermark.text().strip(),
            watermark_position=self.watermark_position.currentData(),
            watermark_scale=self.watermark_size.value() / 100,
            watermark_margin=self.watermark_margin.value(),
        )

    def resolve_preview_source(self, force_random: bool = False) -> Path:
        root = Path(self.source.text())
        candidates = source_images(root)
        if not candidates:
            raise ValueError("Select a source image or a folder containing JPG, JPEG or PNG images.")
        if root.is_file():
            return root
        if not force_random and self.preview_source in candidates:
            return self.preview_source
        return random_source_image(root)

    def preview(self) -> None:
        self.request_preview(force_random=False, show_errors=True)

    def new_random_preview(self) -> None:
        self.request_preview(force_random=True, show_errors=True)

    def refresh_live_preview(self) -> None:
        self.request_preview(force_random=False, show_errors=False)

    def request_preview(self, force_random: bool, show_errors: bool) -> None:
        try:
            source = self.resolve_preview_source(force_random)
        except ValueError as exc:
            if show_errors:
                QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.preview_source = source
        self.preview_revision += 1
        revision = self.preview_revision
        target = self.paths.cache / f"thumbnail_preview_{revision}.jpg"
        self.preview_source_label.setText(f"Preview source: {source.name}")
        self.request_task.emit(
            generate_thumbnail,
            (source, target, self.options(), True),
            {
                "done": lambda path, current=revision: self.preview_done(path, current),
                "failed": lambda message, current=revision, visible=show_errors: self.preview_failed(message, current, visible),
                "label": "Generating preview" if show_errors else "",
            },
        )

    def preview_done(self, path: Path, revision: int) -> None:
        if revision != self.preview_revision:
            return
        self.preview_label.set_preview_pixmap(QPixmap(str(path)))

    def preview_failed(self, message: str, revision: int, show_error: bool) -> None:
        if revision != self.preview_revision:
            return
        self.preview_source_label.setText(f"Preview failed: {message}")
        if show_error:
            self.failed(message)

    def generate_random(self) -> None:
        output = Path(self.output.text())
        if not output.is_dir():
            QMessageBox.warning(self, APP_NAME, "Select a writable output folder first.")
            return
        try:
            source = random_source_image(self.source.text())
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        target = output / f"{source.stem}{self.suffix.text()}.jpg"
        self.progress.setValue(0)
        self.request_task.emit(
            generate_thumbnail,
            (source, target, self.options()),
            {
                "done": self.generated_done,
                "failed": self.generation_failed,
                "label": "Generating thumbnail",
            },
        )

    def generate(self) -> None:
        if self.batch_cancel_event is not None:
            QMessageBox.information(
                self,
                APP_NAME,
                "Thumbnail generation is already running. Use Stop Generation first.",
            )
            return
        source = Path(self.source.text())
        output = Path(self.output.text())
        if not source.exists() or not output.is_dir():
            QMessageBox.warning(self, APP_NAME, "Select a valid source and writable output folder.")
            return
        if source.is_dir():
            sources = source_images(source)
            if not sources:
                QMessageBox.warning(self, APP_NAME, "No valid JPG, JPEG or PNG images were found in the source folder.")
                return
            self.batch_cancel_event = threading.Event()
            self.generate_button.setEnabled(False)
            self.generate_random_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.stop_button.setText("Stop Generation")
            function, args = generate_batch, (
                sources,
                output,
                self.options(),
                self.suffix.text(),
                self.batch_cancel_event,
            )
            callbacks = {
                "done": self.generated_done,
                "failed": self.generation_failed,
                "progress": self.generation_progress,
                "label": "Generating thumbnails",
            }
        else:
            function, args = generate_thumbnail, (source, output / f"{source.stem}{self.suffix.text()}.jpg", self.options())
            callbacks = {
                "done": self.generated_done,
                "failed": self.generation_failed,
                "label": "Generating thumbnail",
            }
        self.progress.setValue(0)
        self.request_task.emit(function, args, callbacks)

    def generated_done(self, result: object) -> None:
        count = len(result) if isinstance(result, list) else 1
        was_stopped = bool(self.batch_cancel_event and self.batch_cancel_event.is_set())
        self._finish_batch_state()
        if not was_stopped:
            self.progress.setValue(100)
        self.generated.emit(count)
        if self.database is not None:
            self.database.add_activity(
                "thumbnail",
                "Thumbnail generation stopped" if was_stopped else "Thumbnail generation completed",
                f"{count} thumbnail(s)",
                "warning" if was_stopped else "success",
            )
        if was_stopped:
            QMessageBox.information(
                self,
                APP_NAME,
                f"Thumbnail generation stopped after {count} thumbnail(s). "
                "Original files were not changed.",
            )
        else:
            QMessageBox.information(
                self,
                APP_NAME,
                f"Generated {count} thumbnail(s). Original files were not changed.",
            )

    def generation_progress(self, current: int, total: int) -> None:
        self.progress.setValue(round(current * 100 / max(total, 1)))

    def stop_generation(self) -> None:
        if self.batch_cancel_event is None:
            return
        self.batch_cancel_event.set()
        self.stop_button.setEnabled(False)
        self.stop_button.setText("Stopping…")
        self.preview_source_label.setText(
            "Stopping thumbnail generation after the current image…"
        )

    def _finish_batch_state(self) -> None:
        self.batch_cancel_event = None
        self.generate_button.setEnabled(True)
        self.generate_random_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setText("Stop Generation")

    def generation_failed(self, message: str) -> None:
        self._finish_batch_state()
        self.failed(message)

    def failed(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)


class PresetsPage(QWidget):
    presets_changed = Signal()

    def __init__(self, settings: SettingsStore):
        super().__init__()
        self.settings = settings
        root, _ = page_header("Presets", "Reusable metadata, credits, tags and schedule defaults")
        toolbar = SectionCard("Preset Library", "Create, copy, import and manage reusable presets", "preset")
        chooser = QHBoxLayout()
        self.selector = DarkComboBox()
        self.selector.currentTextChanged.connect(self.load_selected)
        chooser.addWidget(QLabel("Preset"))
        chooser.addWidget(self.selector, 1)
        new_button = ActionButton("New", "secondary", "preset")
        new_button.clicked.connect(self.new_preset)
        duplicate = ActionButton("Save As / Duplicate", "secondary", "preset")
        duplicate.clicked.connect(self.duplicate)
        import_button = ActionButton("Import", "ghost", "folder")
        import_button.clicked.connect(self.import_preset)
        export_button = ActionButton("Export", "ghost", "export")
        export_button.clicked.connect(self.export_preset)
        reset_button = ActionButton("Reset", "warning", "refresh")
        reset_button.clicked.connect(self.reset_preset)
        delete = ActionButton("Delete", "danger", "trash")
        delete.clicked.connect(self.delete)
        chooser.addWidget(new_button)
        chooser.addWidget(duplicate)
        chooser.addWidget(import_button)
        chooser.addWidget(export_button)
        chooser.addWidget(reset_button)
        chooser.addWidget(delete)
        toolbar.body.addLayout(chooser)
        root.addWidget(toolbar)
        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)
        meta = SectionCard("Metadata", "Titles, tags, audience and schedule defaults", "preset")
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setVerticalSpacing(SPACE_2)
        self.name = QLineEdit()
        self.producer = QLineEdit()
        self.artist = QLineEdit()
        self.second_artist = QLineEdit()
        self.title_template = QLineEdit()
        self.tags = QPlainTextEdit()
        self.tags.setMaximumHeight(90)
        self.tags.setPlaceholderText(
            "Paste your own comma-separated YouTube tags here. Nothing is added automatically."
        )
        self.tags.textChanged.connect(self.update_tag_counter)
        self.tag_counter = QLabel()
        self.tag_counter.setObjectName("muted")
        tags_box = QWidget()
        tags_layout = QVBoxLayout(tags_box)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(4)
        tags_layout.addWidget(self.tags)
        tags_layout.addWidget(self.tag_counter)
        self.separator = DarkComboBox()
        self.separator.addItems(["&", "x"])
        self.made_for_kids = QCheckBox("Made for kids")
        self.made_for_kids.toggled.connect(self.update_audience_status)
        self.audience_status = QLabel()
        audience_box = QWidget()
        audience_layout = QVBoxLayout(audience_box)
        audience_layout.setContentsMargins(0, 0, 0, 0)
        audience_layout.setSpacing(3)
        audience_layout.addWidget(self.made_for_kids)
        audience_layout.addWidget(self.audience_status)
        self.synthetic_media = QCheckBox("Contains realistic altered or synthetic media")
        self.preset_timezone = QLineEdit("Europe/Berlin")
        self.preset_time = QLineEdit("18:00")
        self.preset_days = QLineEdit("Tue, Thu, Fri, Sun")
        self.preset_batch = QSpinBox(); self.preset_batch.setRange(1, 30)
        for label, widget in [("Name", self.name), ("Producer", self.producer), ("Artist", self.artist), ("Second artist", self.second_artist), ("Title template", self.title_template), ("Custom YouTube tags", tags_box), ("Credit separator", self.separator), ("Audience", audience_box), ("Schedule days", self.preset_days), ("Schedule time", self.preset_time), ("Timezone", self.preset_timezone), ("Default batch", self.preset_batch), ("YouTube disclosure", self.synthetic_media)]:
            form.addRow(label, widget)
        meta.body.addLayout(form)
        body.addWidget(meta)
        description_box = SectionCard(
            "Description Template",
            "The exact description rendered for every queue item",
            "logs",
        )
        description_layout = QVBoxLayout()
        hint = QLabel(
            "Use Must credit: {PRODUCER_CREDITS} so collaborator names are added safely. "
            "The three ranking hashtags below are inserted automatically at the top."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        self.hashtag_preview = QLabel()
        self.hashtag_preview.setObjectName("statusGood")
        self.description = QPlainTextEdit()
        migrate = ActionButton("Offer Credit Placeholder Migration", "secondary", "refresh")
        migrate.clicked.connect(self.migrate)
        description_layout.addWidget(hint)
        description_layout.addWidget(self.hashtag_preview)
        description_layout.addWidget(self.description, 1)
        description_layout.addWidget(migrate)
        description_box.body.addLayout(description_layout)
        body.addWidget(description_box)
        body.setStretchFactor(0, 2)
        body.setStretchFactor(1, 3)
        root.addWidget(body, 1)
        save = ActionButton("Save Preset", "primary", "check")
        save.setMinimumHeight(42)
        save.clicked.connect(self.save)
        root.addWidget(save)
        self.setLayout(root)
        self.artist.textChanged.connect(self.update_hashtag_preview)
        self.name.textChanged.connect(self.update_hashtag_preview)
        self.update_audience_status(False)
        self.refresh()

    def refresh(self) -> None:
        current = self.selector.currentText()
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItems([preset.name for preset in self.settings.presets()])
        self.selector.blockSignals(False)
        index = self.selector.findText(current or self.settings.data.get("active_preset", ""))
        self.selector.setCurrentIndex(max(index, 0))
        self.load_selected(self.selector.currentText())

    def load_selected(self, name: str) -> None:
        for preset in self.settings.presets():
            if preset.name == name:
                self.name.setText(preset.name)
                self.producer.setText(preset.producer)
                self.artist.setText(preset.artist)
                self.second_artist.setText(preset.second_artist)
                self.title_template.setText(preset.title_template)
                self.description.setPlainText(preset.description_template)
                self.tags.setPlainText(preset.tags_template)
                self.separator.setCurrentText(preset.credit_separator)
                self.made_for_kids.setChecked(preset.made_for_kids)
                self.synthetic_media.setChecked(preset.contains_synthetic_media)
                self.preset_timezone.setText(preset.timezone)
                self.preset_time.setText(preset.schedule_time)
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                self.preset_days.setText(", ".join(day_names[day] for day in preset.schedule_days))
                self.preset_batch.setValue(preset.default_batch_size)
                self.update_tag_counter()
                self.update_hashtag_preview()
                return

    def value(self) -> Preset:
        base = next((p for p in self.settings.presets() if p.name == self.selector.currentText()), Preset())
        base.name = self.name.text().strip() or "Untitled Preset"
        base.producer = self.producer.text().strip()
        base.artist = self.artist.text().strip()
        base.second_artist = self.second_artist.text().strip()
        base.title_template = self.title_template.text()
        base.description_template = self.description.toPlainText()
        base.tags_template = self.tags.toPlainText()
        base.credit_separator = self.separator.currentText()
        base.made_for_kids = self.made_for_kids.isChecked()
        base.contains_synthetic_media = self.synthetic_media.isChecked()
        base.timezone = self.preset_timezone.text().strip() or "Europe/Berlin"
        base.schedule_time = self.preset_time.text().strip() or "18:00"
        day_map = {"mon": 0, "monday": 0, "tue": 1, "tuesday": 1, "wed": 2, "wednesday": 2, "thu": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5, "sun": 6, "sunday": 6}
        parsed_days = [day_map[token.strip().casefold()] for token in self.preset_days.text().split(",") if token.strip().casefold() in day_map]
        base.schedule_days = sorted(set(parsed_days)) or [1, 3, 4, 6]
        base.default_batch_size = self.preset_batch.value()
        return base

    def save(self) -> None:
        if not self.tags_are_valid():
            return
        self.settings.upsert_preset(self.value())
        self.refresh()
        self.presets_changed.emit()

    def duplicate(self) -> None:
        if not self.tags_are_valid():
            return
        preset = self.value()
        preset.name = preset.name + " Copy"
        self.settings.upsert_preset(preset)
        self.refresh()
        self.presets_changed.emit()

    def new_preset(self) -> None:
        number = len(self.settings.presets()) + 1
        preset = Preset(name=f"New Preset {number}", artist="", description_template="Must credit: {PRODUCER_CREDITS}", tags_template="")
        self.settings.upsert_preset(preset)
        self.refresh()
        self.presets_changed.emit()

    def import_preset(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Import Preset", "", "UPLOAD PLUGG Preset (*.json)")
        if not source:
            return
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
            preset = Preset.from_dict(payload)
            if not preset.name.strip():
                raise ValueError("The preset name is empty.")
            self.settings.upsert_preset(preset)
            self.refresh()
            self.presets_changed.emit()
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Preset import failed: {exc}")

    def export_preset(self) -> None:
        target, _ = QFileDialog.getSaveFileName(self, "Export Preset", f"{self.value().name}.preset.json", "UPLOAD PLUGG Preset (*.json)")
        if target:
            Path(target).write_text(json.dumps(self.value().to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def reset_preset(self) -> None:
        if QMessageBox.question(self, APP_NAME, "Reset the editor to the initial Chief Keef Type Beat defaults?") != QMessageBox.Yes:
            return
        self.settings.upsert_preset(Preset())
        self.refresh()
        self.presets_changed.emit()

    def delete(self) -> None:
        if QMessageBox.question(self, APP_NAME, f"Delete preset '{self.selector.currentText()}'?") == QMessageBox.Yes:
            if not self.settings.delete_preset(self.selector.currentText()):
                QMessageBox.warning(self, APP_NAME, "At least one preset must remain.")
            self.refresh()
            self.presets_changed.emit()

    def migrate(self) -> None:
        updated, found = migrate_credit_line(self.description.toPlainText(), self.producer.text())
        if not found:
            QMessageBox.information(self, APP_NAME, "No exact legacy credit line was found.")
            return
        if QMessageBox.question(self, APP_NAME, "Replace the fixed producer credit with {PRODUCER_CREDITS}?") == QMessageBox.Yes:
            self.description.setPlainText(updated)

    def update_tag_counter(self) -> None:
        used = tag_length(split_tags(self.tags.toPlainText()))
        self.tag_counter.setText(f"YouTube tag usage · {used} / {YOUTUBE_TAGS_LIMIT}")
        color = "#ff7183" if used > YOUTUBE_TAGS_LIMIT else "#858a95"
        self.tag_counter.setStyleSheet(f"color: {color};")

    def tags_are_valid(self) -> bool:
        used = tag_length(split_tags(self.tags.toPlainText()))
        if used <= YOUTUBE_TAGS_LIMIT:
            return True
        QMessageBox.warning(
            self,
            APP_NAME,
            f"Your custom YouTube tags use {used} of {YOUTUBE_TAGS_LIMIT} allowed characters. "
            "Shorten the tag list before saving this preset.",
        )
        return False

    def update_hashtag_preview(self) -> None:
        preset = Preset(name=self.name.text(), artist=self.artist.text())
        hashtags = description_hashtags(preset, datetime.now().astimezone().year)
        self.hashtag_preview.setText(
            "Automatic description hashtags · " + (" ".join(hashtags) or "Enter an artist")
        )

    def update_audience_status(self, made_for_kids: bool) -> None:
        if made_for_kids:
            self.audience_status.setText("ON · YouTube comments will be disabled")
            self.audience_status.setStyleSheet("color: #f0b84b;")
        else:
            self.audience_status.setText("OFF · Not made for kids · comments stay enabled")
            self.audience_status.setStyleSheet("color: #59c98b;")


class SchedulePage(QWidget):
    def __init__(self):
        super().__init__()
        root, _ = page_header("Upload Schedule", "Preview chronological publication slots with Europe/Berlin daylight-saving support")
        form_box = SectionCard(
            "Schedule Configuration",
            "Select active weekdays and calculate exact local and UTC timestamps",
            "calendar",
        )
        form = QHBoxLayout()
        self.count = QSpinBox(); self.count.setRange(1, 30); self.count.setValue(10)
        self.start = QDateEdit(QDate.currentDate()); self.start.setCalendarPopup(True)
        self.time = QTimeEdit(QTime(18, 0))
        self.zone = QLineEdit("Europe/Berlin")
        self.days: list[QCheckBox] = []
        for index, text in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")):
            box = QCheckBox(text)
            box.setProperty("chip", True)
            box.setChecked(index in {1, 3, 4, 6})
            self.days.append(box)
            form.addWidget(box)
        form.addWidget(QLabel("Videos")); form.addWidget(self.count)
        form.addWidget(self.start); form.addWidget(self.time); form.addWidget(self.zone)
        form_box.body.addLayout(form)
        root.addWidget(form_box)
        button = ActionButton("Preview Schedule", "primary", "calendar"); button.clicked.connect(self.preview)
        button.setMinimumHeight(40)
        root.addWidget(button)
        self.empty = EmptyState(
            "No schedule preview yet",
            "Choose the weekdays and click Preview Schedule.",
            "calendar",
        )
        root.addWidget(self.empty, 1)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Weekday", "Local Time", "UTC Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.hide()
        root.addWidget(self.table, 1)
        self.setLayout(root)

    def preview(self) -> None:
        try:
            slots = calculate_schedule(
                self.count.value(), date(self.start.date().year(), self.start.date().month(), self.start.date().day()),
                [i for i, box in enumerate(self.days) if box.isChecked()],
                time(self.time.time().hour(), self.time.time().minute()), self.zone.text(),
            )
        except ScheduleError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc)); return
        self.empty.hide()
        self.table.show()
        self.table.setRowCount(len(slots))
        for row, slot in enumerate(slots):
            values = (
                str(row + 1),
                slot.strftime("%A"),
                slot.strftime("%Y-%m-%d %H:%M %Z"),
                slot.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            for column, value in enumerate(values): self.table.setItem(row, column, QTableWidgetItem(value))


class HistoryPage(QWidget):
    def __init__(self, database: Database, paths: AppPaths):
        super().__init__()
        self.database = database; self.paths = paths
        root, _ = page_header("Upload History", "Local records, results, links and post-upload tasks")
        toolbar = SectionCard("History Tools", "Search records and continue post-upload work", "history")
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Filter by beat, title, filename or status")
        self.search.addAction(line_icon("search", size=17), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(self.refresh)
        export = ActionButton("Export CSV", "ghost", "export"); export.clicked.connect(self.export)
        studio = ActionButton("Open in YouTube Studio", "secondary", "link"); studio.clicked.connect(self.open_studio)
        end_screen = ActionButton("Toggle End Screen", "secondary", "check"); end_screen.clicked.connect(self.toggle_end_screen)
        refresh = ActionButton("Refresh", "ghost", "refresh"); refresh.clicked.connect(self.refresh)
        bar.addWidget(self.search, 1); bar.addWidget(export); bar.addWidget(studio); bar.addWidget(end_screen); bar.addWidget(refresh)
        toolbar.body.addLayout(bar)
        root.addWidget(toolbar)
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(["Date", "Beat", "Filename", "Title", "Collaborator", "Preset", "Channel", "Status", "Scheduled", "YouTube Link", "End Screen"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.open_link)
        self.empty = EmptyState(
            "No upload history yet",
            "Completed and failed uploads will appear here.",
            "history",
        )
        root.addWidget(self.empty, 1)
        root.addWidget(self.table, 1); self.setLayout(root); self.refresh()

    def refresh(self, *_: object) -> None:
        needle = self.search.text().casefold() if hasattr(self, "search") else ""
        rows = [row for row in self.database.list_uploads() if not needle or needle in " ".join(str(v) for v in row.values()).casefold()]
        self.rows = rows
        self.empty.setVisible(not rows)
        self.table.setVisible(bool(rows))
        self.table.setRowCount(len(rows))
        keys = ["created_at", "beat_name", "original_filename", "title", "collaborator", "preset", "channel_name", "status", "publish_at", "youtube_url"]
        for r, row in enumerate(rows):
            for c, key in enumerate(keys): self.table.setItem(r, c, QTableWidgetItem(str(row.get(key, ""))))
            self.table.setItem(r, 10, QTableWidgetItem("Complete" if row.get("end_screen_done") else "Pending"))
            self.table.setCellWidget(
                r,
                7,
                StatusBadge(str(row.get("status", "")), UploadGeneratorPage._status_role(str(row.get("status", "")))),
            )
            self.table.setCellWidget(
                r,
                10,
                StatusBadge("Complete" if row.get("end_screen_done") else "Pending", "ready" if row.get("end_screen_done") else "waiting"),
            )

    def export(self) -> None:
        target, _ = QFileDialog.getSaveFileName(self, "Export Upload History", str(self.paths.exports / "upload_history.csv"), "CSV (*.csv)")
        if target: self.database.export_history_csv(Path(target))

    def open_link(self, row: int, column: int) -> None:
        if column == 9 and self.table.item(row, column).text(): webbrowser.open(self.table.item(row, column).text())

    def toggle_end_screen(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "rows", [])):
            QMessageBox.information(self, APP_NAME, "Select one upload-history row first.")
            return
        record = self.rows[row]
        self.database.set_end_screen_done(int(record["id"]), not bool(record.get("end_screen_done")))
        self.refresh()

    def open_studio(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "rows", [])):
            QMessageBox.information(self, APP_NAME, "Select one upload-history row first.")
            return
        video_id = self.rows[row].get("youtube_id", "")
        if video_id:
            webbrowser.open(f"https://studio.youtube.com/video/{video_id}/edit")
        else:
            QMessageBox.information(self, APP_NAME, "The selected row does not contain a YouTube video yet.")


class LogHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        timestamp = re.match(r"^\d{4}-\d{2}-\d{2}[^ ]*", text)
        if timestamp:
            muted = QTextCharFormat()
            muted.setForeground(QColor(COLORS.muted_text))
            self.setFormat(timestamp.start(), timestamp.end() - timestamp.start(), muted)
        for level, color in (
            ("ERROR", COLORS.error),
            ("WARNING", COLORS.warning),
            ("INFO", COLORS.info),
        ):
            start = text.find(level)
            if start >= 0:
                style = QTextCharFormat()
                style.setForeground(QColor(color))
                style.setFontWeight(700)
                self.setFormat(start, len(level), style)


class LogsPage(QWidget):
    def __init__(self, paths: AppPaths):
        super().__init__(); self.paths = paths
        root, _ = page_header("Logs", "Readable activity log; secrets and OAuth tokens are never logged")
        tools = SectionCard("Diagnostic Tools", "Inspect local events and create a safe diagnostic report", "logs")
        bar = QHBoxLayout(); refresh = ActionButton("Refresh", "secondary", "refresh"); refresh.clicked.connect(self.refresh)
        copy_report = ActionButton("Copy Diagnostic Report", "secondary", "logs"); copy_report.clicked.connect(self.copy_report)
        open_folder = ActionButton("Open Log Folder", "ghost", "folder"); open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths.logs))))
        bar.addWidget(refresh); bar.addWidget(open_folder); bar.addWidget(copy_report); bar.addStretch(); tools.body.addLayout(bar)
        root.addWidget(tools)
        viewer_card = SectionCard("Activity Log", "INFO, WARNING and ERROR entries are color-coded", "logs")
        self.viewer = QPlainTextEdit(); self.viewer.setObjectName("terminalLog"); self.viewer.setReadOnly(True)
        self.highlighter = LogHighlighter(self.viewer.document())
        viewer_card.body.addWidget(self.viewer, 1)
        root.addWidget(viewer_card, 1); self.setLayout(root); self.refresh()

    def refresh(self) -> None:
        path = self.paths.logs / "upload_plugg.log"
        self.viewer.setPlainText(path.read_text(encoding="utf-8", errors="replace")[-120000:] if path.exists() else "No log entries yet.")

    def copy_report(self) -> None:
        QApplication.clipboard().setText(f"{APP_NAME} {APP_VERSION}\nData folder: {self.paths.root}\n\n" + self.viewer.toPlainText()[-12000:])


class SettingsPage(QWidget):
    connect_requested = Signal(); disconnect_requested = Signal(); support_bundle_requested = Signal()

    def __init__(self, settings: SettingsStore, paths: AppPaths):
        super().__init__(); self.settings = settings; self.paths = paths
        root, _ = page_header("Settings", "Application, accessibility, connection, storage and diagnostics")
        app_box = SectionCard(
            "Application",
            "Accessibility, background behavior and upload resilience",
            "settings",
        )
        form = QFormLayout()
        self.reduce_motion = QCheckBox("Reduce Motion")
        self.reduce_motion.setChecked(settings.data["appearance"].get("reduce_motion", False))
        self.keep_awake = QCheckBox("Keep Windows awake during active uploads")
        self.keep_awake.setChecked(settings.data["upload"].get("keep_awake", True))
        self.retries = QSpinBox(); self.retries.setRange(0, 10); self.retries.setValue(settings.data["upload"].get("max_retries", 5))
        save = ActionButton("Save Settings", "primary", "check"); save.clicked.connect(self.save)
        form.addRow(self.reduce_motion); form.addRow(self.keep_awake); form.addRow("Maximum retries", self.retries); form.addRow(save)
        app_box.body.addLayout(form)
        root.addWidget(app_box)
        connection = SectionCard(
            "YouTube Connection",
            "Connect the Desktop OAuth client and manage the local authorization token",
            "link",
        )
        connection_layout = QHBoxLayout()
        connect = ActionButton("Connect YouTube Channel", "primary", "link"); connect.clicked.connect(self.connect_requested.emit)
        disconnect = ActionButton("Disconnect Channel", "danger", "stop"); disconnect.clicked.connect(self.disconnect_requested.emit)
        google_setup = ActionButton("Open Google OAuth Setup", "ghost", "settings")
        google_setup.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://console.cloud.google.com/apis/credentials"))
        )
        connection_layout.addWidget(connect); connection_layout.addWidget(disconnect); connection_layout.addWidget(google_setup); connection_layout.addStretch()
        connection.body.addLayout(connection_layout)
        root.addWidget(connection)
        storage = SectionCard(
            "Local Data",
            "Open, back up or safely reset local application data",
            "folder",
        )
        storage_layout = QGridLayout()
        open_data = ActionButton("Open Data Folder", "secondary", "folder"); open_data.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths.root))))
        clear_cache = ActionButton("Clear Cache", "warning", "trash"); clear_cache.clicked.connect(self.clear_cache)
        export_settings = ActionButton("Export Settings", "ghost", "export"); export_settings.clicked.connect(self.export_settings)
        import_settings = ActionButton("Import Settings", "ghost", "folder"); import_settings.clicked.connect(self.import_settings)
        reset_settings = ActionButton("Reset Settings", "danger", "warning"); reset_settings.clicked.connect(self.reset_settings)
        support = ActionButton("Export Support Bundle", "secondary", "logs"); support.clicked.connect(self.support_bundle_requested.emit)
        for index, control in enumerate(
            (open_data, clear_cache, export_settings, import_settings, reset_settings, support)
        ):
            storage_layout.addWidget(control, index // 3, index % 3)
        storage.body.addLayout(storage_layout)
        root.addWidget(storage)
        about = SectionCard(
            f"About {APP_NAME}",
            "High-speed Windows creator workflow",
            "upload",
        )
        about_layout = QHBoxLayout()
        about_icon = QLabel()
        about_icon.setPixmap(QApplication.windowIcon().pixmap(48, 48))
        about_layout.addWidget(about_icon)
        about_layout.addWidget(QLabel(f"{APP_NAME} {APP_VERSION}\n{CREATOR_CREDIT}\nWindows 10/11 64-bit creator upload workflow."), 1)
        about.body.addLayout(about_layout)
        root.addWidget(about); root.addStretch(); self.setLayout(root)

    def save(self) -> None:
        self.settings.data["appearance"]["reduce_motion"] = self.reduce_motion.isChecked()
        self.settings.data["upload"]["keep_awake"] = self.keep_awake.isChecked()
        self.settings.data["upload"]["max_retries"] = self.retries.value(); self.settings.save()
        QMessageBox.information(self, APP_NAME, "Settings saved.")

    def clear_cache(self) -> None:
        if QMessageBox.question(self, APP_NAME, "Delete temporary converted thumbnails and previews?") != QMessageBox.Yes: return
        for path in self.paths.cache.iterdir():
            if path.is_file():
                try: path.unlink()
                except OSError: pass
        QMessageBox.information(self, APP_NAME, "Temporary cache files cleared. Upload history was not changed.")

    def export_settings(self) -> None:
        target, _ = QFileDialog.getSaveFileName(self, "Export Settings", "UPLOAD_PLUGG_Settings.json", "JSON (*.json)")
        if target:
            safe = json.loads(json.dumps(self.settings.data))
            safe["channel"] = {"id": "", "name": safe.get("channel", {}).get("name", ""), "image_url": ""}
            Path(target).write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_settings(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON (*.json)")
        if not source:
            return
        if QMessageBox.question(self, APP_NAME, "Replace current preferences and presets with this settings file? Upload history is not changed.") != QMessageBox.Yes:
            return
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("presets"), list):
                raise ValueError("This is not a valid UPLOAD PLUGG settings export.")
            self.settings.data = payload
            self.settings.save()
            QMessageBox.information(self, APP_NAME, "Settings imported. Restart UPLOAD PLUGG to apply every change.")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Settings import failed: {exc}")

    def reset_settings(self) -> None:
        if QMessageBox.question(self, APP_NAME, "Reset preferences and presets to their initial values? Upload history is preserved.") != QMessageBox.Yes:
            return
        from ..settings import DEFAULT_SETTINGS
        self.settings.data = json.loads(json.dumps(DEFAULT_SETTINGS))
        self.settings.save()
        QMessageBox.information(self, APP_NAME, "Settings reset. Restart UPLOAD PLUGG to apply every change.")
