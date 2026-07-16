import json
import tempfile
import unittest
from pathlib import Path

from upload_plugg.database import Database
from upload_plugg.models import LEGACY_AUTOMATIC_TAGS_TEMPLATE, UploadItem, UploadResult
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

    def test_settings_migration_removes_only_legacy_automatic_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.paths(Path(directory))
            store = SettingsStore(paths)
            store.path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "presets": [
                            {"name": "Legacy", "tags_template": LEGACY_AUTOMATIC_TAGS_TEMPLATE},
                            {"name": "Custom", "tags_template": "Chief Keef, Glo Gang"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = store.load()

            self.assertEqual(loaded["version"], 2)
            self.assertEqual(loaded["presets"][0]["tags_template"], "")
            self.assertEqual(loaded["presets"][1]["tags_template"], "Chief Keef, Glo Gang")

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
