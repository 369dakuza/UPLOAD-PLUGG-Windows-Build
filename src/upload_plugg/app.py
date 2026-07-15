from __future__ import annotations

import sys

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
    settings = SettingsStore(paths)
    settings.load()
    database = Database(paths)
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("Dakuza")
    application.setApplicationVersion(APP_VERSION)
    application.setQuitOnLastWindowClosed(False)
    application.setStyleSheet(STYLESHEET)
    window = MainWindow(paths, settings, database, logger)
    window.show()
    return application.exec()
