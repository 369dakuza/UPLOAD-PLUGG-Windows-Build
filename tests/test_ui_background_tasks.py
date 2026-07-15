import unittest

try:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication, QMainWindow

    from upload_plugg.ui.main_window import MainWindow

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


if __name__ == "__main__":
    unittest.main()
