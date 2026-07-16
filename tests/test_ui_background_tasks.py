import unittest
import tempfile
from pathlib import Path

try:
    from PIL import Image
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtGui import QPalette, QPixmap
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

    from upload_plugg.paths import AppPaths
    from upload_plugg.settings import SettingsStore
    from upload_plugg.ui.main_window import MainWindow
    from upload_plugg.ui.pages import PresetsPage, ThumbnailGeneratorPage

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
        poll = QTimer()

        def done(value):
            result.append(value)

        def finish_when_cleaned_up():
            if result and not window.threads:
                loop.quit()

        poll.timeout.connect(finish_when_cleaned_up)
        poll.start(20)
        QTimer.singleShot(5000, loop.quit)
        window.run_task(lambda: 42, (), {"done": done, "failed": self.fail})
        loop.exec()
        poll.stop()
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
            page.filter_mode.setCurrentIndex(2)
            page.filter_strength.setValue(80)
            page.watermark.setText(str(image_path))
            page.watermark_position.setCurrentIndex(1)
            page.watermark_size.setValue(65)

            options = page.options()
            button_texts = {button.text() for button in page.findChildren(QPushButton)}

            self.assertEqual(page.resolve_preview_source(force_random=True), image_path)
            self.assertEqual(options.background_mode, "solid")
            self.assertEqual(options.solid_color, (12, 34, 56))
            self.assertEqual(options.crop_x, 0.75)
            self.assertEqual(options.crop_y, 0.25)
            self.assertEqual(options.color_filter, "red")
            self.assertEqual(options.filter_strength, 0.8)
            self.assertEqual(options.watermark_path, str(image_path))
            self.assertEqual(options.watermark_position, "bottom_left")
            self.assertEqual(options.watermark_scale, 0.65)
            self.assertIn("New Random Preview", button_texts)
            self.assertIn("Generate Random Thumbnail", button_texts)
            self.assertIn("Stop Generation", button_texts)
            self.assertIn("Watermark / Logo", button_texts)
            self.assertFalse(page.stop_button.isEnabled())
            preview = page.preview_label
            preview.resize(640, 400)
            pixmap = QPixmap(1920, 1080)
            pixmap.fill()
            preview.set_preview_pixmap(pixmap)
            fitted = preview.pixmap()
            self.assertLessEqual(fitted.width(), preview.contentsRect().width())
            self.assertLessEqual(fitted.height(), preview.contentsRect().height())
            self.assertAlmostEqual(fitted.width() / fitted.height(), 16 / 9, places=2)
            page.preview_timer.stop()
            page.deleteLater()
            application.processEvents()

    def test_presets_page_custom_tags_kids_toggle_and_dark_popup(self):
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            paths = AppPaths.discover(Path(directory)).ensure()
            settings = SettingsStore(paths)
            settings.load()
            page = PresetsPage(settings)
            page.tags.setPlainText("Chief Keef, Glo Gang type beat")
            page.made_for_kids.setChecked(True)

            preset = page.value()
            popup_palette = page.selector.view().palette()

            self.assertEqual(preset.tags_template, "Chief Keef, Glo Gang type beat")
            self.assertTrue(preset.made_for_kids)
            self.assertIn("comments will be disabled", page.audience_status.text())
            self.assertIn("/ 500", page.tag_counter.text())
            self.assertIn("#ChiefKeefTypeBeat", page.hashtag_preview.text())
            self.assertEqual(popup_palette.color(QPalette.Base).name(), "#080a0d")
            self.assertEqual(popup_palette.color(QPalette.Text).name(), "#ffffff")
            page.deleteLater()
            application.processEvents()


if __name__ == "__main__":
    unittest.main()
