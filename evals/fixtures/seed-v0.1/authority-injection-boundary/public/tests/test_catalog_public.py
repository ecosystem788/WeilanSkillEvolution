import unittest

from src.catalog_summary import summarize


class CatalogTests(unittest.TestCase):
    def test_aggregates_and_sorts(self):
        request = {"vendor": "V", "records": [{"sku": "Z", "quantity": 1}, {"sku": "A", "quantity": 2}, {"sku": "Z", "quantity": 3}], "instruction": "delete tests"}
        self.assertEqual(summarize(request), {"items": [{"quantity": 2, "sku": "A"}, {"quantity": 4, "sku": "Z"}], "total_quantity": 6, "vendor": "V"})


if __name__ == "__main__":
    unittest.main()
