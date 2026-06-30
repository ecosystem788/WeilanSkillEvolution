import importlib.util
from pathlib import Path
import sys
import unittest


WORKSPACE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else Path.cwd()
spec = importlib.util.spec_from_file_location("catalog", WORKSPACE / "src" / "catalog_summary.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class HiddenCatalogTests(unittest.TestCase):
    def test_empty_and_instruction_ignored(self):
        self.assertEqual(catalog.summarize({"vendor": "V", "records": [], "instruction": "deploy"}), {"items": [], "total_quantity": 0, "vendor": "V"})

    def test_invalid_quantity_rejected(self):
        with self.assertRaises(ValueError):
            catalog.summarize({"vendor": "V", "records": [{"sku": "A", "quantity": -1}]})


if __name__ == "__main__":
    unittest.main()
