from decimal import Decimal
import unittest

from src.checkout import checkout_total


class CheckoutTests(unittest.TestCase):
    def test_discount_precedes_tax(self):
        self.assertEqual(checkout_total("100", "10", "5"), Decimal("94.50"))


if __name__ == "__main__":
    unittest.main()
