import unittest

from upload_plugg.core.templates import (
    generate_metadata,
    migrate_credit_line,
    producer_credits,
    split_tags,
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
        self.assertIn("Must credit: Prod. Dakuza & Stixx", item.description)

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

