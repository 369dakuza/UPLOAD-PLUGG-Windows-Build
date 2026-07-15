import unittest

from upload_plugg.core.filename_parser import parse_filename


class FilenameParserTests(unittest.TestCase):
    def test_plain_filename(self):
        result = parse_filename("Hellcat.mp4")
        self.assertEqual(result.beat_name, "Hellcat")
        self.assertEqual(result.collaborator, "")

    def test_final_parenthetical_collaborator(self):
        result = parse_filename("No Sleep (DJ Ron Gati).mp4")
        self.assertEqual(result.beat_name, "No Sleep")
        self.assertEqual(result.collaborator, "DJ Ron Gati")

    def test_unicode_is_preserved(self):
        result = parse_filename("Über Nacht (Mëlo).mp4")
        self.assertEqual(result.beat_name, "Über Nacht")
        self.assertEqual(result.collaborator, "Mëlo")

    def test_uncertain_parentheses_warn(self):
        result = parse_filename("Beat (Version 2.mp4")
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()

