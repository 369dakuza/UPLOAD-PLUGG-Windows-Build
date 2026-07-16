from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import APP_NAME, APP_VERSION
from .database import Database
from .paths import AppPaths
from .services.logging_setup import configure_logging
from .settings import SettingsStore
from .ui.main_window import MainWindow
from .ui.theme import STYLESHEET


def main() -> int:
    paths = AppPaths.discover().ensure()
    logger = configure_logging(paths)

    def report_unhandled_exception(kind, value, traceback) -> None:
        logger.critical(
            "Unhandled application exception",
            exc_info=(kind, value, traceback),
        )
        sys.__excepthook__(kind, value, traceback)

    # PySide routes exceptions raised by button slots through sys.excepthook.
    # Recording them turns a silent-looking crash into an actionable log entry.
    sys.excepthook = report_unhandled_exception
    settings = SettingsStore(paths)
    settings.load()
    database = Database(paths)
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("Dakuza")
    application.setApplicationVersion(APP_VERSION)
    resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    icon = resource_root / "resources" / "upload_plugg.ico"
    if icon.exists():
        application.setWindowIcon(QIcon(str(icon)))
    # Closing the main window means exiting the application. The former tray-only
    # behaviour left Python and Qt worker threads running after the user clicked X.
    application.setQuitOnLastWindowClosed(True)
    application.setStyleSheet(STYLESHEET)
    window = MainWindow(paths, settings, database, logger)
    window.show()
    return application.exec()
