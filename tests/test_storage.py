import shutil
import tempfile
import unittest

import storage


class StorageTestCase(unittest.TestCase):
    """every test gets its own empty data dir, the real %APPDATA% data is never touched"""

    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        self.original_dir = storage.BASE_DIR
        storage.BASE_DIR = self.data_dir
        self.month, self.year = "October", "2026"

    def tearDown(self):
        storage.BASE_DIR = self.original_dir
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def add(self, kind, text):
        save = storage.save_income if kind == "income" else storage.save_expense
        save(text, self.month, self.year)

    def expenses(self):
        return storage.load_items(self.month, self.year)[1]


class TestParsing(unittest.TestCase):
    def test_split_entry(self):
        self.assertEqual(storage.split_entry("527,38€ Opintotuki"), (527.38, "Opintotuki"))
        self.assertEqual(storage.split_entry("5€"), (5.0, ""))
        self.assertEqual(storage.split_entry("12.5€ kahvi ja pulla"), (12.5, "kahvi ja pulla"))

    def test_split_entry_without_amount(self):
        self.assertEqual(storage.split_entry("kahvi"), (None, "kahvi"))
        self.assertEqual(storage.split_entry(""), (None, ""))

    def test_parse_amount(self):
        self.assertEqual(storage.parse_amount("10,50€"), 10.5)
        self.assertIsNone(storage.parse_amount("abc"))
        self.assertIsNone(storage.parse_amount("1.000,50"))


class TestRows(StorageTestCase):
    def test_save_and_load(self):
        self.add("income", "100€ palkka")
        self.add("expense", "20€ ruoka")
        self.assertEqual(storage.load_items(self.month, self.year), (["100€ palkka"], ["20€ ruoka"]))

    def test_missing_month_is_empty(self):
        self.assertEqual(storage.load_items("May", "1999"), ([], []))

    def test_sums_skip_rows_without_amount(self):
        self.add("expense", "10€ a")
        self.add("expense", "2,50€ b")
        self.add("expense", "rikki")  # old data could have this, counts as 0
        self.assertAlmostEqual(storage.sum_expenses(self.month, self.year), 12.5)

    def test_delete_by_position_with_duplicates(self):
        for text in ["10€ a", "20€ b", "20€ b", "30€ c"]:
            self.add("expense", text)
        self.add("income", "100€ x")
        self.assertEqual(storage.delete_item("expense", 2, self.month, self.year), "20€ b")
        self.assertEqual(self.expenses(), ["10€ a", "20€ b", "30€ c"])

    def test_delete_out_of_range(self):
        self.add("expense", "10€ a")
        self.assertIsNone(storage.delete_item("expense", 5, self.month, self.year))

    def test_undo_puts_row_back_in_place(self):
        for text in ["10€ a", "20€ b", "30€ c"]:
            self.add("expense", text)
        text = storage.delete_item("expense", 1, self.month, self.year)
        storage.insert_item("expense", 1, text, self.month, self.year)
        self.assertEqual(self.expenses(), ["10€ a", "20€ b", "30€ c"])

    def test_update_keeps_other_rows(self):
        self.add("income", "100€ x")
        self.add("expense", "10€ a")
        self.add("expense", "20€ b")
        storage.update_item("expense", 1, "25€ b2", self.month, self.year)
        self.assertEqual(storage.load_items(self.month, self.year), (["100€ x"], ["10€ a", "25€ b2"]))

    def test_years_and_stats(self):
        self.add("expense", "10€ a")
        storage.save_income("5€ b", "March", "2025")
        self.assertEqual(storage.get_years_with_data(), {2025, 2026})
        self.assertEqual(storage.get_stats(), (2, 1, 1))


if __name__ == "__main__":
    unittest.main()
