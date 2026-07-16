import unittest

from upload_plugg.core.templates import (
    description_hashtags,
    generate_metadata,
    migrate_credit_line,
    producer_credits,
    preset_metadata_signature,
    split_tags,
    synchronize_metadata,
    unresolved_placeholders,
)
from upload_plugg.models import Preset, UploadItem


class TemplateTests(unittest.TestCase):
    def test_credit_without_collaborator(self):
        self.assertEqual(producer_credits("Dakuza", ""), "Prod. Dakuza")

    def test_credit_with_collaborator(self):
        self.assertEqual(producer_credits("Dakuza", "Stixx"), "Prod. Dakuza & Stixx")

    def test_generate_metadata(self):
        item = UploadItem("C:/Beats/Hellcat (Stixx).mp4", "Hellcat", "Stixx")
        generate_metadata(item, Preset())
        self.assertEqual(item.display_title, '[FREE] Chief Keef Type Beat - "Hellcat"')
        self.assertTrue(
            item.description.startswith(
                "#ChiefKeef #ChiefKeefTypeBeat #ChiefKeefTypeBeat"
            )
        )
        self.assertIn("Must credit: [Prod. Dakuza & Stixx]", item.description)
        self.assertIn("www.instagram.com/369dakuza", item.description)
        self.assertIn("Email: 369dakuza@gmail.com", item.description)
        self.assertIn("Chief Keef type beat", item.description)
        self.assertEqual(item.tags, [])

    def test_custom_youtube_tags_are_used_without_automatic_additions(self):
        item = UploadItem("C:/Beats/Hellcat.mp4", "Hellcat")
        preset = Preset(tags_template="Chief Keef, Glo Gang type beat, Chicago trap")
        generate_metadata(item, preset)
        self.assertEqual(
            item.tags,
            ["Chief Keef", "Glo Gang type beat", "Chicago trap"],
        )

    def test_stale_queue_metadata_is_synchronized_with_current_preset(self):
        item = UploadItem(
            "C:/Beats/Hellcat.mp4",
            "Hellcat",
            description="Replace this example with your complete YouTube description.",
            tags=["Chief Keef type beat", "Hellcat", "Dakuza", "2026 type beat"],
        )
        preset = Preset(tags_template="")

        synchronize_metadata(item, preset)

        self.assertEqual(item.tags, [])
        self.assertIn("www.instagram.com/369dakuza", item.description)
        self.assertEqual(item.metadata_signature, preset_metadata_signature(preset))

    def test_manual_tags_survive_other_preset_metadata_updates(self):
        item = UploadItem(
            "C:/Beats/Hellcat.mp4",
            "Hellcat",
            tags=["My exact tag"],
            manual_metadata_fields=["tags"],
        )

        synchronize_metadata(item, Preset(tags_template="Preset tag"))

        self.assertEqual(item.tags, ["My exact tag"])
        self.assertIn("Chief Keef", item.display_title)

    def test_three_description_hashtags_use_artist_and_publication_year(self):
        item = UploadItem(
            "C:/Beats/Hellcat.mp4",
            "Hellcat",
            publish_at="2027-01-02T18:00:00+01:00",
        )
        generate_metadata(item, Preset(artist="Chief Keef"))
        self.assertEqual(
            item.description.splitlines()[0],
            "#ChiefKeef #ChiefKeefTypeBeat #ChiefKeefTypeBeat2027",
        )
        self.assertIn("Chief Keef type beat 2027", item.description)

    def test_hashtags_fall_back_to_preset_name_when_artist_is_empty(self):
        self.assertEqual(
            description_hashtags(Preset(name="Future Type Beat", artist=""), 2026),
            ["#Future", "#FutureTypeBeat", "#FutureTypeBeat2026"],
        )

    def test_unresolved_placeholders(self):
        self.assertEqual(unresolved_placeholders("{ARTIST} {MISSING}"), ["{ARTIST}", "{MISSING}"])

    def test_duplicate_tags_removed_case_insensitive(self):
        self.assertEqual(split_tags("Chief Keef, beat, chief keef\nnew"), ["Chief Keef", "beat", "new"])

    def test_credit_migration_requires_exact_line(self):
        result, found = migrate_credit_line("Text\nMust credit: Prod. Dakuza\nEnd", "Dakuza")
        self.assertTrue(found)
        self.assertIn("Must credit: {PRODUCER_CREDITS}", result)


if __name__ == "__main__":
    unittest.main()
