from __future__ import annotations

import json
import os
import webbrowser
from datetime import date, datetime, time
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
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
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION, CREATOR_CREDIT
from ..constants import MAX_BATCH_SIZE
from ..core.dry_run import export_dry_run
from ..core.filename_parser import parse_filename
from ..core.random_pool import assign_without_repeats, image_pool
from ..core.scanner import scan_videos, sha256_file
from ..core.scheduling import ScheduleError, calculate_schedule
from ..core.templates import generate_metadata, migrate_credit_line, producer_credits, tag_length
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


def page_header(title: str, subtitle: str) -> tuple[QVBoxLayout, QLabel]:
    layout = QVBoxLayout()
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

    def __init__(self, database: Database):
        super().__init__()
        self.database = database
        root, _ = page_header("Dashboard", "Creator workflow overview and quick actions")
        cards = QGridLayout()
        self.card_values: dict[str, QLabel] = {}
        for index, (key, label) in enumerate([
            ("waiting", "Videos Waiting"), ("completed", "Completed Uploads"),
            ("failed", "Failed Uploads"), ("thumbs", "Generated Thumbnails"),
        ]):
            card = panel()
            card_layout = QVBoxLayout(card)
            value = QLabel("0")
            value.setStyleSheet("font-size: 26pt; font-weight: 800; color: #ff5268")
            card_layout.addWidget(value)
            caption = QLabel(label)
            caption.setObjectName("muted")
            card_layout.addWidget(caption)
            cards.addWidget(card, index // 2, index % 2)
            self.card_values[key] = value
        root.addLayout(cards)
        actions = QGroupBox("Quick Actions")
        action_layout = QHBoxLayout(actions)
        for text, signal in [
            ("Create Upload Batch", self.quick_upload), ("Generate Thumbnails", self.quick_thumbnails),
            ("Open Schedule", self.quick_schedule), ("Connect Channel", self.quick_connect),
        ]:
            button = QPushButton(text)
            button.clicked.connect(signal.emit)
            action_layout.addWidget(button)
        root.addWidget(actions)
        root.addStretch()
        self.setLayout(root)

    def refresh(self, queue: list[UploadItem], generated_count: int = 0) -> None:
        rows = self.database.list_uploads()
        self.card_values["waiting"].setText(str(sum(item.selected for item in queue)))
        self.card_values["completed"].setText(str(sum(r["status"] == "Completed" for r in rows)))
        self.card_values["failed"].setText(str(sum(r["status"] == "Failed" for r in rows)))
        self.card_values["thumbs"].setText(str(generated_count))


class UploadGeneratorPage(QWidget):
    request_task = Signal(object, object, object)
    request_upload = Signal(object, object)
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
        root, _ = page_header("Upload Generator", "Prepare, validate and upload up to 30 finished MP4 videos")

        workflow = panel()
        controls = QGridLayout(workflow)
        self.folder = QLineEdit(settings.data["folders"].get("videos", ""))
        browse = QPushButton("Select Folder")
        browse.clicked.connect(self.choose_folder)
        self.batch = QSpinBox()
        self.batch.setRange(1, MAX_BATCH_SIZE)
        self.batch.setValue(10)
        self.sorting = QComboBox()
        self.sorting.addItems([
            "Natural numeric order", "Name, A–Z", "Name, Z–A", "Date created, oldest first",
            "Date created, newest first", "Date modified, oldest first", "Date modified, newest first",
            "Manual order",
        ])
        self.preset = QComboBox()
        self.refresh_presets()
        scan = QPushButton("Scan Folder")
        scan.clicked.connect(self.scan)
        metadata = QPushButton("Generate Metadata")
        metadata.clicked.connect(self.generate_all)
        controls.addWidget(QLabel("Video folder"), 0, 0)
        controls.addWidget(self.folder, 0, 1, 1, 4)
        controls.addWidget(browse, 0, 5)
        controls.addWidget(QLabel("Batch size"), 1, 0)
        controls.addWidget(self.batch, 1, 1)
        controls.addWidget(QLabel("Sorting"), 1, 2)
        controls.addWidget(self.sorting, 1, 3)
        controls.addWidget(QLabel("Preset"), 1, 4)
        controls.addWidget(self.preset, 1, 5)
        controls.addWidget(scan, 2, 4)
        controls.addWidget(metadata, 2, 5)
        root.addWidget(workflow)

        action_row = QHBoxLayout()
        random_button = QPushButton("Random Thumbnails")
        random_button.clicked.connect(self.random_thumbnails)
        schedule_button = QPushButton("Calculate Schedule")
        schedule_button.clicked.connect(self.schedule)
        validate_button = QPushButton("Validate Batch")
        validate_button.clicked.connect(self.validate)
        dry_button = QPushButton("Run Dry Test")
        dry_button.clicked.connect(self.dry_run)
        upload_button = QPushButton("Start Uploads")
        upload_button.setProperty("accent", True)
        upload_button.clicked.connect(self.start_uploads)
        for button in (random_button, schedule_button, validate_button, dry_button, upload_button):
            action_row.addWidget(button)
        root.addLayout(action_row)

        schedule_box = QGroupBox("Schedule")
        schedule_layout = QHBoxLayout(schedule_box)
        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.schedule_time = QTimeEdit(QTime(18, 0))
        self.timezone = QLineEdit("Europe/Berlin")
        self.day_checks: list[QCheckBox] = []
        for index, day in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            check = QCheckBox(day)
            check.setChecked(index in {1, 3, 4, 6})
            self.day_checks.append(check)
            schedule_layout.addWidget(check)
        schedule_layout.addWidget(QLabel("Start"))
        schedule_layout.addWidget(self.start_date)
        schedule_layout.addWidget(QLabel("Time"))
        schedule_layout.addWidget(self.schedule_time)
        schedule_layout.addWidget(QLabel("Timezone"))
        schedule_layout.addWidget(self.timezone)
        root.addWidget(schedule_box)
        self.preset.currentTextChanged.connect(self.apply_preset_defaults)

        self.summary = QLabel("Ready to scan a folder.")
        self.summary.setObjectName("muted")
        root.addWidget(self.summary)
        self.table = QueueTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setDragDropMode(QAbstractItemView.InternalMove)
        self.table.setDefaultDropAction(Qt.MoveAction)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setMinimumHeight(310)
        self.table.cellChanged.connect(self.cell_changed)
        self.table.currentCellChanged.connect(self.show_details)
        self.table.rows_reordered.connect(self.reorder_rows)
        root.addWidget(self.table, 1)

        details = QGroupBox("Selected Video Details")
        details_layout = QGridLayout(details)
        self.detail_description = QPlainTextEdit()
        self.detail_description.setPlaceholderText("Full generated description")
        self.detail_description.textChanged.connect(self.description_changed)
        self.detail_tags = QLineEdit()
        self.detail_tags.textEdited.connect(self.tags_changed)
        self.detail_credit = QLabel("Producer credits")
        self.detail_path = QLabel("Source path")
        self.detail_path.setWordWrap(True)
        self.detail_thumbnail = QLabel("No custom thumbnail")
        self.detail_thumbnail.setAlignment(Qt.AlignCenter)
        self.detail_thumbnail.setMinimumSize(240, 135)
        self.detail_thumbnail.setStyleSheet("background:#08090b;border:1px solid #292c33;border-radius:8px")
        details_layout.addWidget(QLabel("Description"), 0, 0)
        details_layout.addWidget(self.detail_description, 1, 0, 3, 3)
        details_layout.addWidget(QLabel("Tags"), 0, 3)
        details_layout.addWidget(self.detail_tags, 1, 3)
        details_layout.addWidget(self.detail_credit, 2, 3)
        details_layout.addWidget(self.detail_path, 3, 3)
        details_layout.addWidget(self.detail_thumbnail, 0, 4, 4, 1)
        root.addWidget(details)
        self.setLayout(root)
        self.apply_preset_defaults(self.preset.currentText())
        self.populate()

    def refresh_presets(self) -> None:
        selected = self.preset.currentText() if hasattr(self, "preset") else ""
        if hasattr(self, "preset"):
            self.preset.clear()
            self.preset.addItems([preset.name for preset in self.settings.presets()])
            index = self.preset.findText(selected or self.settings.data.get("active_preset", ""))
            self.preset.setCurrentIndex(max(0, index))

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
            {"done": self.scan_done, "failed": self.task_failed},
        )

    def scan_done(self, items: list[UploadItem]) -> None:
        self.items = items
        if items:
            self.generate_all()
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
            generate_metadata(item, self.current_preset())
        self.persist()
        self.populate()

    def validate(self, online: bool = False, connected: bool = False) -> tuple[int, int]:
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
                {"done": lambda result: self.finish_start_uploads(result, warnings), "failed": self.task_failed},
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

    def populate(self) -> None:
        self._populating = True
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
            for column in (1, 2, 3, 7, 8, 9, 10, 11, 12, 13):
                self.table.item(row, column).setFlags(self.table.item(row, column).flags() & ~Qt.ItemIsEditable)
        self._populating = False
        self.queue_changed.emit()

    def cell_changed(self, row: int, column: int) -> None:
        if self._populating or row >= len(self.items):
            return
        item = self.items[row]
        if column == 0:
            item.selected = self.table.item(row, 0).checkState() == Qt.Checked
        elif column == 4:
            item.beat_name = self.table.item(row, column).text().strip()
        elif column == 5:
            item.collaborator = self.table.item(row, column).text().strip()
        elif column == 6:
            item.display_title = self.table.item(row, column).text().strip()
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
        self.detail_credit.setText(producer_credits(preset.producer, item.collaborator, preset.credit_separator))
        self.detail_path.setText(item.source_path)
        if item.thumbnail_path and Path(item.thumbnail_path).is_file():
            preview = QPixmap(item.thumbnail_path).scaled(240, 135, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.detail_thumbnail.setPixmap(preview)
        else:
            self.detail_thumbnail.clear()
            self.detail_thumbnail.setText("No custom thumbnail")

    def description_changed(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.items):
            self.items[row].description = self.detail_description.toPlainText()
            self.persist()

    def tags_changed(self, text: str) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.items):
            self.items[row].tags = [value.strip() for value in text.split(",") if value.strip()]
            self.persist()

    def update_progress(self, item_id: str, percent: int, stage: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.progress = percent
                item.upload_status = stage
                break
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

    def __init__(self, settings: SettingsStore, paths: AppPaths):
        super().__init__()
        self.settings = settings
        self.paths = paths
        self.preview_source: Path | None = None
        self.preview_revision = 0
        self.solid_color = (18, 18, 20)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300)
        self.preview_timer.timeout.connect(self.refresh_live_preview)
        root, _ = page_header("Thumbnail Generator", "Offline 1920 × 1080 JPG processing from existing artwork")
        form_panel = panel()
        form = QGridLayout(form_panel)
        self.source = QLineEdit()
        self.output = QLineEdit(settings.data["folders"].get("thumbnail_output", ""))
        source_file = QPushButton("Source Image")
        source_file.clicked.connect(self.select_source)
        source_folder = QPushButton("Source Folder")
        source_folder.clicked.connect(self.select_source_folder)
        output_button = QPushButton("Output Folder")
        output_button.clicked.connect(self.select_output)
        self.mode = QComboBox()
        self.mode.addItem("Square Center + Blurred Sides", "square_blur")
        self.mode.addItem("Crop to Full 16:9", "crop_16_9")
        self.mode.addItem("Fit Entire Image + Background Fill", "fit_background")
        self.background_mode = QComboBox()
        self.background_mode.addItem("Artwork · Blur / Darken", "artwork")
        self.background_mode.addItem("Solid Color", "solid")
        self.color_button = QPushButton("Choose Background Color")
        self.color_button.clicked.connect(self.choose_background_color)
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
        self.saturation_label = QLabel("Background saturation · 75%")
        self.crop_x.setToolTip("Move the crop focus left or right. The preview updates automatically.")
        self.crop_y.setToolTip("Move the crop focus up or down. The preview updates automatically.")
        self.zoom.setToolTip("Zoom creates room for Crop X and Crop Y to reposition square artwork.")
        self.saturation.setToolTip("Change only the artwork used behind the centered cover.")
        form.addWidget(QLabel("Source"), 0, 0)
        form.addWidget(self.source, 0, 1, 1, 4)
        form.addWidget(source_file, 0, 5)
        form.addWidget(source_folder, 0, 6)
        form.addWidget(QLabel("Output"), 1, 0)
        form.addWidget(self.output, 1, 1, 1, 4)
        form.addWidget(output_button, 1, 5)
        form.addWidget(QLabel("Layout"), 2, 0)
        form.addWidget(self.mode, 2, 1)
        form.addWidget(QLabel("Background"), 2, 2)
        form.addWidget(self.background_mode, 2, 3)
        form.addWidget(self.color_button, 2, 4, 1, 2)
        form.addWidget(QLabel("Blur"), 3, 0)
        form.addWidget(self.blur, 3, 1)
        form.addWidget(QLabel("Darkness"), 3, 2)
        form.addWidget(self.darkness, 3, 3)
        form.addWidget(self.saturation_label, 3, 4)
        form.addWidget(self.saturation, 3, 5)
        form.addWidget(self.crop_x_label, 4, 0); form.addWidget(self.crop_x, 4, 1)
        form.addWidget(self.crop_y_label, 4, 2); form.addWidget(self.crop_y, 4, 3)
        form.addWidget(QLabel("Zoom"), 4, 4); form.addWidget(self.zoom, 4, 5)
        form.addWidget(QLabel("Center size"), 5, 0); form.addWidget(self.center_size, 5, 1)
        form.addWidget(QLabel("Quality"), 5, 2); form.addWidget(self.quality, 5, 3)
        form.addWidget(QLabel("Filename suffix"), 5, 4); form.addWidget(self.suffix, 5, 5)
        root.addWidget(form_panel)
        buttons = QHBoxLayout()
        preview = QPushButton("Generate Preview")
        preview.clicked.connect(self.preview)
        random_preview = QPushButton("New Random Preview")
        random_preview.clicked.connect(self.new_random_preview)
        generate_random = QPushButton("Generate Random Thumbnail")
        generate_random.clicked.connect(self.generate_random)
        generate = QPushButton("Generate Thumbnail(s)")
        generate.setProperty("accent", True)
        generate.clicked.connect(self.generate)
        buttons.addWidget(preview)
        buttons.addWidget(random_preview)
        buttons.addWidget(generate_random)
        buttons.addWidget(generate)
        buttons.addStretch()
        root.addLayout(buttons)
        self.preview_source_label = QLabel("Preview source: none")
        self.preview_source_label.setObjectName("muted")
        root.addWidget(self.preview_source_label)
        self.preview_label = QLabel("Preview appears here")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(360)
        self.preview_label.setStyleSheet("background:#060708;border:1px solid #292c33;border-radius:12px")
        root.addWidget(self.preview_label, 1)
        self.progress = QProgressBar()
        root.addWidget(self.progress)
        self.setLayout(root)
        self.source.textChanged.connect(self.source_changed)
        self.mode.currentIndexChanged.connect(self.option_changed)
        self.background_mode.currentIndexChanged.connect(self.background_changed)
        for control in (
            self.blur, self.darkness, self.quality, self.crop_x, self.crop_y,
            self.zoom, self.saturation, self.center_size,
        ):
            control.valueChanged.connect(self.option_changed)
        self.update_control_labels()
        self.update_background_controls()
        self.update_color_button()

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

    def source_changed(self, _text: str) -> None:
        self.preview_source = None
        self.preview_source_label.setText("Preview source: none")
        self.schedule_live_preview()

    def option_changed(self, *_: object) -> None:
        self.update_control_labels()
        self.schedule_live_preview()

    def background_changed(self, *_: object) -> None:
        self.update_background_controls()
        self.schedule_live_preview()

    def update_control_labels(self) -> None:
        self.crop_x_label.setText(f"Crop X · {self.crop_x.value()}%")
        self.crop_y_label.setText(f"Crop Y · {self.crop_y.value()}%")
        self.saturation_label.setText(f"Background saturation · {self.saturation.value()}%")

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

    def update_color_button(self) -> None:
        red, green, blue = self.solid_color
        brightness = (red * 299 + green * 587 + blue * 114) / 1000
        text = "#111111" if brightness > 150 else "white"
        self.color_button.setText(f"Color · #{red:02X}{green:02X}{blue:02X}")
        self.color_button.setStyleSheet(
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
            },
        )

    def preview_done(self, path: Path, revision: int) -> None:
        if revision != self.preview_revision:
            return
        pixmap = QPixmap(str(path)).scaled(960, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(pixmap)

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
            {"done": self.generated_done, "failed": self.failed},
        )

    def generate(self) -> None:
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
            function, args = generate_batch, (sources, output, self.options(), self.suffix.text())
            callbacks = {"done": self.generated_done, "failed": self.failed, "progress": self.generation_progress}
        else:
            function, args = generate_thumbnail, (source, output / f"{source.stem}{self.suffix.text()}.jpg", self.options())
            callbacks = {"done": self.generated_done, "failed": self.failed}
        self.progress.setValue(0)
        self.request_task.emit(function, args, callbacks)

    def generated_done(self, result: object) -> None:
        count = len(result) if isinstance(result, list) else 1
        self.progress.setValue(100)
        self.generated.emit(count)
        QMessageBox.information(self, APP_NAME, f"Generated {count} thumbnail(s). Original files were not changed.")

    def generation_progress(self, current: int, total: int) -> None:
        self.progress.setValue(round(current * 100 / max(total, 1)))

    def failed(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)


class PresetsPage(QWidget):
    presets_changed = Signal()

    def __init__(self, settings: SettingsStore):
        super().__init__()
        self.settings = settings
        root, _ = page_header("Presets", "Reusable metadata, credits, tags and schedule defaults")
        chooser = QHBoxLayout()
        self.selector = QComboBox()
        self.selector.currentTextChanged.connect(self.load_selected)
        chooser.addWidget(QLabel("Preset"))
        chooser.addWidget(self.selector, 1)
        new_button = QPushButton("New")
        new_button.clicked.connect(self.new_preset)
        duplicate = QPushButton("Save As / Duplicate")
        duplicate.clicked.connect(self.duplicate)
        import_button = QPushButton("Import")
        import_button.clicked.connect(self.import_preset)
        export_button = QPushButton("Export")
        export_button.clicked.connect(self.export_preset)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_preset)
        delete = QPushButton("Delete")
        delete.setProperty("danger", True)
        delete.clicked.connect(self.delete)
        chooser.addWidget(new_button)
        chooser.addWidget(duplicate)
        chooser.addWidget(import_button)
        chooser.addWidget(export_button)
        chooser.addWidget(reset_button)
        chooser.addWidget(delete)
        root.addLayout(chooser)
        body = QHBoxLayout()
        meta = QGroupBox("Metadata")
        form = QFormLayout(meta)
        self.name = QLineEdit()
        self.producer = QLineEdit()
        self.artist = QLineEdit()
        self.second_artist = QLineEdit()
        self.title_template = QLineEdit()
        self.tags = QPlainTextEdit()
        self.tags.setMaximumHeight(90)
        self.separator = QComboBox()
        self.separator.addItems(["&", "x"])
        self.synthetic_media = QCheckBox("Contains realistic altered or synthetic media")
        self.preset_timezone = QLineEdit("Europe/Berlin")
        self.preset_time = QLineEdit("18:00")
        self.preset_days = QLineEdit("Tue, Thu, Fri, Sun")
        self.preset_batch = QSpinBox(); self.preset_batch.setRange(1, 30)
        for label, widget in [("Name", self.name), ("Producer", self.producer), ("Artist", self.artist), ("Second artist", self.second_artist), ("Title template", self.title_template), ("Tags", self.tags), ("Credit separator", self.separator), ("Schedule days", self.preset_days), ("Schedule time", self.preset_time), ("Timezone", self.preset_timezone), ("Default batch", self.preset_batch), ("YouTube disclosure", self.synthetic_media)]:
            form.addRow(label, widget)
        body.addWidget(meta, 1)
        description_box = QGroupBox("Description Template")
        description_layout = QVBoxLayout(description_box)
        hint = QLabel("Use Must credit: {PRODUCER_CREDITS} so collaborator names are added safely.")
        hint.setObjectName("muted")
        self.description = QPlainTextEdit()
        migrate = QPushButton("Offer Credit Placeholder Migration")
        migrate.clicked.connect(self.migrate)
        description_layout.addWidget(hint)
        description_layout.addWidget(self.description, 1)
        description_layout.addWidget(migrate)
        body.addWidget(description_box, 2)
        root.addLayout(body, 1)
        save = QPushButton("Save Preset")
        save.setProperty("accent", True)
        save.clicked.connect(self.save)
        root.addWidget(save)
        self.setLayout(root)
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
                self.synthetic_media.setChecked(preset.contains_synthetic_media)
                self.preset_timezone.setText(preset.timezone)
                self.preset_time.setText(preset.schedule_time)
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                self.preset_days.setText(", ".join(day_names[day] for day in preset.schedule_days))
                self.preset_batch.setValue(preset.default_batch_size)
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
        base.contains_synthetic_media = self.synthetic_media.isChecked()
        base.timezone = self.preset_timezone.text().strip() or "Europe/Berlin"
        base.schedule_time = self.preset_time.text().strip() or "18:00"
        day_map = {"mon": 0, "monday": 0, "tue": 1, "tuesday": 1, "wed": 2, "wednesday": 2, "thu": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5, "sun": 6, "sunday": 6}
        parsed_days = [day_map[token.strip().casefold()] for token in self.preset_days.text().split(",") if token.strip().casefold() in day_map]
        base.schedule_days = sorted(set(parsed_days)) or [1, 3, 4, 6]
        base.default_batch_size = self.preset_batch.value()
        return base

    def save(self) -> None:
        self.settings.upsert_preset(self.value())
        self.refresh()
        self.presets_changed.emit()

    def duplicate(self) -> None:
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


class SchedulePage(QWidget):
    def __init__(self):
        super().__init__()
        root, _ = page_header("Upload Schedule", "Preview chronological publication slots with Europe/Berlin daylight-saving support")
        form_box = panel()
        form = QHBoxLayout(form_box)
        self.count = QSpinBox(); self.count.setRange(1, 30); self.count.setValue(10)
        self.start = QDateEdit(QDate.currentDate()); self.start.setCalendarPopup(True)
        self.time = QTimeEdit(QTime(18, 0))
        self.zone = QLineEdit("Europe/Berlin")
        self.days: list[QCheckBox] = []
        for index, text in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")):
            box = QCheckBox(text); box.setChecked(index in {1, 3, 4, 6}); self.days.append(box); form.addWidget(box)
        form.addWidget(QLabel("Videos")); form.addWidget(self.count)
        form.addWidget(self.start); form.addWidget(self.time); form.addWidget(self.zone)
        root.addWidget(form_box)
        button = QPushButton("Preview Schedule"); button.setProperty("accent", True); button.clicked.connect(self.preview)
        root.addWidget(button)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Weekday", "Local Time", "UTC Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        self.table.setRowCount(len(slots))
        for row, slot in enumerate(slots):
            values = (str(row + 1), slot.strftime("%A"), slot.strftime("%Y-%m-%d %H:%M %Z"), slot.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"))
            for column, value in enumerate(values): self.table.setItem(row, column, QTableWidgetItem(value))


class HistoryPage(QWidget):
    def __init__(self, database: Database, paths: AppPaths):
        super().__init__()
        self.database = database; self.paths = paths
        root, _ = page_header("Upload History", "Local records, results, links and post-upload tasks")
        bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Filter by beat, title, filename or status")
        self.search.textChanged.connect(self.refresh)
        export = QPushButton("Export History to CSV"); export.clicked.connect(self.export)
        studio = QPushButton("Open in YouTube Studio"); studio.clicked.connect(self.open_studio)
        end_screen = QPushButton("Toggle End Screen Complete"); end_screen.clicked.connect(self.toggle_end_screen)
        refresh = QPushButton("Refresh"); refresh.clicked.connect(self.refresh)
        bar.addWidget(self.search, 1); bar.addWidget(export); bar.addWidget(studio); bar.addWidget(end_screen); bar.addWidget(refresh); root.addLayout(bar)
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(["Date", "Beat", "Filename", "Title", "Collaborator", "Preset", "Channel", "Status", "Scheduled", "YouTube Link", "End Screen"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self.open_link)
        root.addWidget(self.table, 1); self.setLayout(root); self.refresh()

    def refresh(self, *_: object) -> None:
        needle = self.search.text().casefold() if hasattr(self, "search") else ""
        rows = [row for row in self.database.list_uploads() if not needle or needle in " ".join(str(v) for v in row.values()).casefold()]
        self.rows = rows
        self.table.setRowCount(len(rows))
        keys = ["created_at", "beat_name", "original_filename", "title", "collaborator", "preset", "channel_name", "status", "publish_at", "youtube_url"]
        for r, row in enumerate(rows):
            for c, key in enumerate(keys): self.table.setItem(r, c, QTableWidgetItem(str(row.get(key, ""))))
            self.table.setItem(r, 10, QTableWidgetItem("Complete" if row.get("end_screen_done") else "Pending"))

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


class LogsPage(QWidget):
    def __init__(self, paths: AppPaths):
        super().__init__(); self.paths = paths
        root, _ = page_header("Logs", "Readable activity log; secrets and OAuth tokens are never logged")
        bar = QHBoxLayout(); refresh = QPushButton("Refresh"); refresh.clicked.connect(self.refresh)
        copy_report = QPushButton("Copy Diagnostic Report"); copy_report.clicked.connect(self.copy_report)
        open_folder = QPushButton("Open Log Folder"); open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths.logs))))
        bar.addWidget(refresh); bar.addWidget(open_folder); bar.addWidget(copy_report); bar.addStretch(); root.addLayout(bar)
        self.viewer = QPlainTextEdit(); self.viewer.setReadOnly(True); root.addWidget(self.viewer, 1); self.setLayout(root); self.refresh()

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
        app_box = QGroupBox("Application")
        form = QFormLayout(app_box)
        self.reduce_motion = QCheckBox("Reduce Motion")
        self.reduce_motion.setChecked(settings.data["appearance"].get("reduce_motion", False))
        self.keep_awake = QCheckBox("Keep Windows awake during active uploads")
        self.keep_awake.setChecked(settings.data["upload"].get("keep_awake", True))
        self.retries = QSpinBox(); self.retries.setRange(0, 10); self.retries.setValue(settings.data["upload"].get("max_retries", 5))
        save = QPushButton("Save Settings"); save.clicked.connect(self.save)
        form.addRow(self.reduce_motion); form.addRow(self.keep_awake); form.addRow("Maximum retries", self.retries); form.addRow(save)
        root.addWidget(app_box)
        connection = QGroupBox("YouTube Connection")
        connection_layout = QHBoxLayout(connection)
        connect = QPushButton("Connect YouTube Channel"); connect.setProperty("accent", True); connect.clicked.connect(self.connect_requested.emit)
        disconnect = QPushButton("Disconnect Channel"); disconnect.clicked.connect(self.disconnect_requested.emit)
        google_setup = QPushButton("Open Google OAuth Setup")
        google_setup.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://console.cloud.google.com/apis/credentials"))
        )
        connection_layout.addWidget(connect); connection_layout.addWidget(disconnect); connection_layout.addWidget(google_setup); connection_layout.addStretch()
        root.addWidget(connection)
        storage = QGroupBox("Local Data")
        storage_layout = QHBoxLayout(storage)
        open_data = QPushButton("Open Data Folder"); open_data.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths.root))))
        clear_cache = QPushButton("Clear Cache"); clear_cache.clicked.connect(self.clear_cache)
        export_settings = QPushButton("Export Settings"); export_settings.clicked.connect(self.export_settings)
        import_settings = QPushButton("Import Settings"); import_settings.clicked.connect(self.import_settings)
        reset_settings = QPushButton("Reset Settings"); reset_settings.clicked.connect(self.reset_settings)
        support = QPushButton("Export Support Bundle"); support.clicked.connect(self.support_bundle_requested.emit)
        storage_layout.addWidget(open_data); storage_layout.addWidget(clear_cache); storage_layout.addWidget(export_settings); storage_layout.addWidget(import_settings); storage_layout.addWidget(reset_settings); storage_layout.addWidget(support); storage_layout.addStretch()
        root.addWidget(storage)
        about = QGroupBox(f"About {APP_NAME}")
        about_layout = QVBoxLayout(about)
        about_layout.addWidget(QLabel(f"{APP_NAME} {APP_VERSION}\n{CREATOR_CREDIT}\nWindows 10 64-bit creator upload workflow."))
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
