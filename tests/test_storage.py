import tempfile
import unittest
from pathlib import Path

from upload_plugg.database import Database
from upload_plugg.models import UploadItem, UploadResult
from upload_plugg.paths import AppPaths
from upload_plugg.settings import SettingsStore


class StorageTests(unittest.TestCase):
    def paths(self, root: Path) -> AppPaths:
        return AppPaths.discover(root).ensure()

    def test_settings_round_trip_and_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.paths(Path(directory))
            store = SettingsStore(paths)
            store.load()
            store.data["folders"]["videos"] = "C:/Übersicht/Beats"
            store.save()
            loaded = SettingsStore(paths)
            self.assertEqual(loaded.load()["folders"]["videos"], "C:/Übersicht/Beats")

    def test_database_migration_and_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(self.paths(Path(directory)))
            item = UploadItem("C:/Beats/Hellcat.mp4", "Hellcat", display_title="Title", file_size=100, file_hash="abc")
            database.add_upload(item, UploadResult(item.id, "Completed", youtube_id="123"), "channel")
            self.assertTrue(database.find_duplicates(item, "channel"))

    def test_queue_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(self.paths(Path(directory)))
            item = UploadItem("C:/Beats/Hellcat.mp4", "Hellcat")
            database.save_queue([item])
            self.assertEqual(database.load_queue()[0].id, item.id)


if __name__ == "__main__":
    unittest.main()

