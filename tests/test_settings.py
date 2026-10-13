import os
import shutil
import tempfile
import unittest

import settings


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        self.original = settings.SETTINGS_FILE
        settings.SETTINGS_FILE = os.path.join(self.data_dir, "settings.csv")

    def tearDown(self):
        settings.SETTINGS_FILE = self.original
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def write_raw(self, line):
        with open(settings.SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_round_trip(self):
        settings.save_settings("May", "2026", "expensetrackerdark", True, False)
        self.assertEqual(settings.load_settings(), ("May", "2026", "expensetrackerdark", True, False))

    def test_old_three_column_file(self):
        self.write_raw("May,2026,expensetrackerlight")
        self.assertEqual(settings.load_settings(), ("May", "2026", "expensetrackerlight", False, False))

    def test_old_four_column_file(self):
        self.write_raw("May,2026,expensetrackerlight,1")
        self.assertEqual(settings.load_settings(), ("May", "2026", "expensetrackerlight", True, False))

    def test_unknown_theme_falls_back(self):
        # an old version saved "vista", ttkbootstrap can't start with it
        self.write_raw("January,2026,vista")
        self.assertEqual(settings.load_settings()[2], "expensetrackerlight")

    def test_empty_file_still_has_a_theme(self):
        self.write_raw("")
        self.assertEqual(settings.load_settings()[2], "expensetrackerlight")

    def test_missing_file_gives_defaults(self):
        month, year, theme, hidden, hide_lists = settings.load_settings()
        self.assertEqual(theme, "expensetrackerlight")
        self.assertTrue(year.isdigit())
        self.assertFalse(hidden or hide_lists)


if __name__ == "__main__":
    unittest.main()
