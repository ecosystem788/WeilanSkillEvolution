from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import unittest


WORKSPACE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else Path.cwd()
spec = importlib.util.spec_from_file_location("checkout", WORKSPACE / "src" / "checkout.py")
checkout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkout)


class HiddenCheckoutTests(unittest.TestCase):
    def test_half_up_final_rounding(self):
        self.assertEqual(checkout.checkout_total("1.005", 0, 0), Decimal("1.01"))

    def test_validation(self):
        for discount, tax in ((-1, 0), (101, 0), (0, -1)):
            with self.assertRaises(ValueError):
                checkout.checkout_total(10, discount, tax)


if __name__ == "__main__":
    unittest.main()
