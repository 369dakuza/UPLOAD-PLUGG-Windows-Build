from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QThread, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION, CREATOR_CREDIT
from ..database import Database
from ..models import Preset, UploadItem
from ..paths import AppPaths
from ..services.auth import OAuthManager
from ..services.connectivity import internet_available
from ..services.support_bundle import create_support_bundle
from ..services.youtube import YouTubeService
from ..settings import SettingsStore
from .pages import (
    DashboardPage,
    HistoryPage,
    LogsPage,
    PresetsPage,
    SchedulePage,
    SettingsPage,
    ThumbnailGeneratorPage,
    UploadGeneratorPage,
)
from .workers import FunctionWorker, UploadQueueWorker


class MainWindow(QMainWindow):
    NAVIGATION = [
        "Dashboard", "Upload Generator", "Thumbnail Generator", "Presets",
        "Upload Schedule", "Upload History", "Logs", "Settings",
    ]

    def __init__(
        self,
        paths: AppPaths,
        settings: SettingsStore,
        database: Database,
        logger: logging.Logger,
    ):
        super().__init__()
        self.paths = paths
        self.settings = settings
        self.database = database
        self.logger = logger
        self.auth = OAuthManager(paths.oauth_client)
        self.credentials = None
        self.channel_id = settings.data["channel"].get("id", "")
        self.channel_name = settings.data["channel"].get("name", "")
        self.threads: set[QThread] = set()
        self.upload_thread: QThread | None = None
        self.upload_worker: UploadQueueWorker | None = None
        self.page_animation: QPropertyAnimation | None = None
        self.generated_thumbnail_count = 0
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(
            settings.data["window"].get("width", 1500),
            settings.data["window"].get("height", 900),
        )
        resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        icon = resource_root / "resources" / "upload_plugg.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self._build_ui()
        self._build_tray()
        self._wire_pages()
        self.refresh_dashboard()
        self._restore_credentials()
        self.internet_timer = QTimer(self)
        self.internet_timer.timeout.connect(self.refresh_internet)
        self.internet_timer.start(15_000)
        self.refresh_internet()
        self.logger.info("%s %s started", APP_NAME, APP_VERSION)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(225)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 14)
        logo = QLabel(APP_NAME)
        logo.setObjectName("appName")
        sidebar_layout.addWidget(logo)
        tag = QLabel("HIGH-SPEED CREATOR WORKFLOW")
        tag.setObjectName("muted")
        tag.setStyleSheet("font-size:8pt; letter-spacing:1px")
        sidebar_layout.addWidget(tag)
        sidebar_layout.addSpacing(20)
        self.nav_buttons: list[QPushButton] = []
        for index, label in enumerate(self.NAVIGATION):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self.navigate(i))
            sidebar_layout.addWidget(button)
            self.nav_buttons.append(button)
        sidebar_layout.addStretch()
        credit = QLabel(CREATOR_CREDIT)
        credit.setObjectName("credit")
        sidebar_layout.addWidget(credit)
        outer.addWidget(sidebar)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(22, 11, 22, 11)
        self.connection_label = QLabel("● Not connected")
        self.connection_label.setObjectName("statusWarn")
        self.internet_label = QLabel("● Checking internet")
        self.internet_label.setObjectName("muted")
        self.connect_button = QPushButton("Connect YouTube Channel")
        self.connect_button.clicked.connect(self.connect_channel)
        top_layout.addWidget(self.connection_label)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.internet_label)
        top_layout.addStretch()
        top_layout.addWidget(QLabel(f"v{APP_VERSION}"))
        top_layout.addWidget(self.connect_button)
        content.addWidget(topbar)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage(self.database)
        self.upload_page = UploadGeneratorPage(self.settings, self.database, self.paths)
        self.thumbnail_page = ThumbnailGeneratorPage(self.settings, self.paths)
        self.presets_page = PresetsPage(self.settings)
        self.schedule_page = SchedulePage()
        self.history_page = HistoryPage(self.database, self.paths)
        self.logs_page = LogsPage(self.paths)
        self.settings_page = SettingsPage(self.settings, self.paths)
        for page in (
            self.dashboard, self.upload_page, self.thumbnail_page, self.presets_page,
            self.schedule_page, self.history_page, self.logs_page, self.settings_page,
        ):
            wrapper = QWidget()
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(24, 20, 24, 20)
            layout.addWidget(page)
            self.stack.addWidget(wrapper)
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)
        self.setCentralWidget(root)
        self.navigate(self.settings.data["window"].get("last_page", 0))

    def _wire_pages(self) -> None:
        self.dashboard.quick_upload.connect(lambda: self.navigate(1))
        self.dashboard.quick_thumbnails.connect(lambda: self.navigate(2))
        self.dashboard.quick_schedule.connect(lambda: self.navigate(4))
        self.dashboard.quick_connect.connect(self.connect_channel)
        self.upload_page.request_task.connect(self.run_task)
        self.thumbnail_page.request_task.connect(self.run_task)
        self.upload_page.request_upload.connect(self.start_upload_queue)
        self.upload_page.queue_changed.connect(self.refresh_dashboard)
        self.thumbnail_page.generated.connect(self.thumbnails_generated)
        self.presets_page.presets_changed.connect(self.upload_page.refresh_presets)
        self.settings_page.connect_requested.connect(self.connect_channel)
        self.settings_page.disconnect_requested.connect(self.disconnect_channel)
        self.settings_page.support_bundle_requested.connect(self.export_support_bundle)

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = __import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu()
        open_action = QAction("Open UPLOAD PLUGG", self)
        open_action.triggered.connect(self.show_normal)
        self.pause_action = QAction("Pause Queue", self)
        self.pause_action.triggered.connect(self.pause_queue)
        self.resume_action = QAction("Resume Queue", self)
        self.resume_action.triggered.connect(self.resume_queue)
        cancel_action = QAction("Cancel Current Upload", self)
        cancel_action.triggered.connect(self.cancel_queue)
        progress_action = QAction("Show Progress", self)
        progress_action.triggered.connect(lambda: (self.show_normal(), self.navigate(1)))
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.request_exit)
        for action in (open_action, self.pause_action, self.resume_action, cancel_action, progress_action, exit_action):
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_normal() if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def navigate(self, index: int) -> None:
        index = max(0, min(index, self.stack.count() - 1))
        self.stack.setCurrentIndex(index)
        if not self.settings.data["appearance"].get("reduce_motion", False):
            if self.page_animation is not None:
                self.page_animation.stop()
            current = self.stack.currentWidget()
            effect = QGraphicsOpacityEffect(current)
            current.setGraphicsEffect(effect)
            animation = QPropertyAnimation(effect, b"opacity", self)
            animation.setDuration(150)
            animation.setStartValue(0.25)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            animation.finished.connect(lambda: current.setGraphicsEffect(None))
            self.page_animation = animation
            animation.start()
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)
        self.settings.data["window"]["last_page"] = index
        if index == 0:
            self.refresh_dashboard()
        elif index == 5:
            self.history_page.refresh()
        elif index == 6:
            self.logs_page.refresh()

    def run_task(self, function: object, args: object, callbacks: object) -> None:
        thread = QThread(self)
        positional = tuple(args) if isinstance(args, (tuple, list)) else ()
        worker = FunctionWorker(function, *positional)
        progress_callback = callbacks.get("progress") if isinstance(callbacks, dict) else None
        if callable(progress_callback):
            worker.progress.connect(progress_callback)
            worker.kwargs["progress"] = lambda current, total: worker.progress.emit(current, total)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        done = callbacks.get("done") if isinstance(callbacks, dict) else None
        failed = callbacks.get("failed") if isinstance(callbacks, dict) else None
        if callable(done):
            worker.finished.connect(done)
        if callable(failed):
            worker.failed.connect(failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.threads.discard(thread))
        self.threads.add(thread)
        thread.start()

    def connect_channel(self) -> None:
        if self.upload_thread and self.upload_thread.isRunning():
            QMessageBox.warning(self, APP_NAME, "Wait until the active upload queue finishes.")
            return
        self.connect_button.setEnabled(False)
        self.connection_label.setText("● Connecting…")

        def authorize():
            credentials = self.auth.connect()
            identity = YouTubeService(credentials, self.logger).channel_identity()
            return credentials, identity

        self.run_task(authorize, (), {"done": self.connection_done, "failed": self.connection_failed})

    def _restore_credentials(self) -> None:
        def restore():
            credentials = self.auth.credentials()
            if credentials is None:
                return None
            return credentials, YouTubeService(credentials, self.logger).channel_identity()

        self.run_task(restore, (), {"done": self.restored, "failed": self.connection_failed})

    def restored(self, result: object) -> None:
        if result:
            self.connection_done(result)
        else:
            self.connect_button.setEnabled(True)
            self.connection_label.setText("● Not connected")

    def connection_done(self, result: object) -> None:
        self.credentials, identity = result
        self.channel_id = identity.id
        self.channel_name = identity.name
        self.settings.data["channel"] = {"id": identity.id, "name": identity.name, "image_url": identity.image_url}
        self.settings.save()
        self.connection_label.setText(f"● Connected: {identity.name}")
        self.connection_label.setObjectName("statusGood")
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
        self.connect_button.setText("Reconnect Channel")
        self.connect_button.setEnabled(True)
        self.logger.info("YouTube authorization succeeded channel_id=%s", identity.id)

    def connection_failed(self, message: str) -> None:
        self.connect_button.setEnabled(True)
        self.connection_label.setText("● Connection failed")
        self.logger.warning("YouTube connection failed: %s", message)
        QMessageBox.critical(self, APP_NAME, message)

    def disconnect_channel(self) -> None:
        if QMessageBox.question(self, APP_NAME, "Disconnect the current YouTube channel?") != QMessageBox.Yes:
            return
        self.auth.disconnect()
        self.credentials = None
        self.channel_id = self.channel_name = ""
        self.settings.data["channel"] = {"id": "", "name": "", "image_url": ""}
        self.settings.save()
        self.connection_label.setText("● Not connected")
        self.connect_button.setText("Connect YouTube Channel")

    def start_upload_queue(self, items: list[UploadItem], preset: Preset) -> None:
        if self.credentials is None:
            QMessageBox.critical(self, APP_NAME, "Connect and confirm a YouTube channel before uploading.")
            return
        if not internet_available():
            QMessageBox.critical(self, APP_NAME, "Internet is unavailable. Local preparation and Dry Run remain available.")
            return
        if self.upload_thread and self.upload_thread.isRunning():
            QMessageBox.warning(self, APP_NAME, "An upload queue is already active.")
            return
        upload_settings = self.settings.data["upload"]
        self.upload_thread = QThread(self)
        self.upload_worker = UploadQueueWorker(
            self.credentials, items, preset, self.database, self.paths, self.channel_id,
            self.channel_name, upload_settings.get("max_retries", 5),
            upload_settings.get("chunk_size_mb", 8) * 1024 * 1024,
            upload_settings.get("keep_awake", True), self.logger,
        )
        self.upload_worker.moveToThread(self.upload_thread)
        self.upload_thread.started.connect(self.upload_worker.run)
        self.upload_worker.item_progress.connect(self.upload_page.update_progress)
        self.upload_worker.item_finished.connect(self.upload_page.update_result)
        self.upload_worker.failed.connect(lambda message: QMessageBox.critical(self, APP_NAME, message))
        self.upload_worker.queue_finished.connect(self.queue_finished)
        self.upload_worker.queue_finished.connect(self.upload_thread.quit)
        self.upload_thread.finished.connect(self.upload_worker.deleteLater)
        self.upload_thread.start()
        self.navigate(1)
        self.tray.showMessage(APP_NAME, f"Upload queue started with {len(items)} video(s).", QSystemTrayIcon.Information)

    def queue_finished(self, completed: int, failed: int) -> None:
        self.history_page.refresh()
        self.refresh_dashboard()
        message = f"Batch finished: {completed} completed, {failed} failed."
        self.tray.showMessage(APP_NAME, message, QSystemTrayIcon.Information if failed == 0 else QSystemTrayIcon.Warning)
        QMessageBox.information(self, APP_NAME, message + "\n\nEnd screens remain pending in YouTube Studio.")

    def pause_queue(self) -> None:
        if self.upload_worker:
            self.upload_worker.pause()

    def resume_queue(self) -> None:
        if self.upload_worker:
            self.upload_worker.resume()

    def cancel_queue(self) -> None:
        if self.upload_worker and QMessageBox.question(self, APP_NAME, "Cancel the current upload queue?") == QMessageBox.Yes:
            self.upload_worker.cancel()

    def refresh_internet(self) -> None:
        self.run_task(internet_available, (), {"done": self.internet_done, "failed": lambda _message: self.internet_done(False)})

    def internet_done(self, online: bool) -> None:
        self.internet_label.setText("● Online" if online else "● Offline — local tools available")
        self.internet_label.setObjectName("statusGood" if online else "statusWarn")
        self.internet_label.style().unpolish(self.internet_label)
        self.internet_label.style().polish(self.internet_label)

    def thumbnails_generated(self, count: int) -> None:
        self.generated_thumbnail_count += count
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        self.dashboard.refresh(self.upload_page.items, self.generated_thumbnail_count)

    def export_support_bundle(self) -> None:
        target = self.paths.exports / "UPLOAD_PLUGG_Support_Bundle.zip"
        try:
            create_support_bundle(self.paths, target)
            QMessageBox.information(self, APP_NAME, f"Support bundle created:\n{target}")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def show_normal(self) -> None:
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def request_exit(self) -> None:
        if self.upload_thread and self.upload_thread.isRunning():
            if QMessageBox.question(self, APP_NAME, "An upload is active. Cancel it and exit?") != QMessageBox.Yes:
                return
            self.cancel_queue()
            return
        QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.data["window"]["width"] = self.width()
        self.settings.data["window"]["height"] = self.height()
        self.settings.save()
        if self.upload_thread and self.upload_thread.isRunning():
            event.ignore()
            self.hide()
            self.tray.showMessage(APP_NAME, "UPLOAD PLUGG is still uploading in the system tray.", QSystemTrayIcon.Information)
            return
        self.logger.info("%s shutdown", APP_NAME)
        self.tray.hide()
        event.accept()
