from decimal import Decimal
import unittest
from parcel_route import parse_manifest


class HiddenManifestTests(unittest.TestCase):
    def test_rejects_duplicates_and_bad_weight(self):
        for text in ("parcel_id,zone,weight\nP1,E,1\nP1,W,2\n", "parcel_id,zone,weight\nP1,E,0\n"):
            with self.assertRaises(ValueError): parse_manifest(text)

    def test_decimal_preserved(self):
        self.assertEqual(parse_manifest("parcel_id,zone,weight\nP1,north,0.10\n")[0]["weight"],Decimal("0.10"))


if __name__ == "__main__": unittest.main()
