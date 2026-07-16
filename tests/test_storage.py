import json
import tempfile
import unittest
from pathlib import Path

from upload_plugg.database import Database
from upload_plugg.models import (
    CHIEF_KEEF_DESCRIPTION_TEMPLATE,
    LEGACY_AUTOMATIC_TAGS_TEMPLATE,
    UploadItem,
    UploadResult,
)
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

            self.assertEqual(loaded["version"], 3)
            self.assertEqual(loaded["presets"][0]["tags_template"], "")
            self.assertEqual(loaded["presets"][1]["tags_template"], "Chief Keef, Glo Gang")

    def test_chief_keef_description_is_updated_without_changing_other_presets(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.paths(Path(directory))
            store = SettingsStore(paths)
            store.path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "presets": [
                            {
                                "name": "Chief Keef Type Beat",
                                "description_template": "Old description",
                            },
                            {"name": "Custom", "description_template": "Keep me"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = store.load()

            self.assertEqual(loaded["version"], 3)
            self.assertEqual(
                loaded["presets"][0]["description_template"],
                CHIEF_KEEF_DESCRIPTION_TEMPLATE,
            )
            self.assertEqual(loaded["presets"][1]["description_template"], "Keep me")

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

    def test_activity_events_are_persisted_with_real_status(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(self.paths(Path(directory)))
            database.add_activity(
                "metadata",
                "Metadata generated",
                "8 video(s)",
                "success",
            )

            activity = database.list_activities(1)[0]

            self.assertEqual(activity["kind"], "metadata")
            self.assertEqual(activity["message"], "Metadata generated")
            self.assertEqual(activity["detail"], "8 video(s)")
            self.assertEqual(activity["status"], "success")


if __name__ == "__main__":
    unittest.main()
