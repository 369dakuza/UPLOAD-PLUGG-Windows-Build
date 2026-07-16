import unittest
import tempfile
from pathlib import Path

try:
    from PIL import Image
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

    from upload_plugg.paths import AppPaths
    from upload_plugg.settings import SettingsStore
    from upload_plugg.ui.main_window import MainWindow
    from upload_plugg.ui.pages import ThumbnailGeneratorPage

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "PySide6 is only installed in the Windows build environment")
class BackgroundTaskTests(unittest.TestCase):
    def test_worker_stays_alive_and_returns_result(self):
        application = QApplication.instance() or QApplication([])
        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.threads = {}
        result = []
        loop = QEventLoop()

        def done(value):
            result.append(value)
            QTimer.singleShot(150, loop.quit)

        QTimer.singleShot(5000, loop.quit)
        window.run_task(lambda: 42, (), {"done": done, "failed": self.fail})
        loop.exec()
        application.processEvents()

        self.assertEqual(result, [42])
        self.assertFalse(window.threads)
        window.deleteLater()
        application.processEvents()

    def test_thumbnail_page_folder_random_and_solid_controls(self):
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            paths = AppPaths.discover(Path(directory)).ensure()
            settings = SettingsStore(paths)
            settings.load()
            artwork = paths.root / "artwork"
            artwork.mkdir()
            image_path = artwork / "cover.png"
            Image.new("RGB", (800, 1200), "red").save(image_path)
            page = ThumbnailGeneratorPage(settings, paths)
            page.source.setText(str(artwork))
            page.background_mode.setCurrentIndex(1)
            page.solid_color = (12, 34, 56)
            page.crop_x.setValue(75)
            page.crop_y.setValue(25)

            options = page.options()
            button_texts = {button.text() for button in page.findChildren(QPushButton)}

            self.assertEqual(page.resolve_preview_source(force_random=True), image_path)
            self.assertEqual(options.background_mode, "solid")
            self.assertEqual(options.solid_color, (12, 34, 56))
            self.assertEqual(options.crop_x, 0.75)
            self.assertEqual(options.crop_y, 0.25)
            self.assertIn("New Random Preview", button_texts)
            self.assertIn("Generate Random Thumbnail", button_texts)
            page.preview_timer.stop()
            page.deleteLater()
            application.processEvents()


if __name__ == "__main__":
    unittest.main()
