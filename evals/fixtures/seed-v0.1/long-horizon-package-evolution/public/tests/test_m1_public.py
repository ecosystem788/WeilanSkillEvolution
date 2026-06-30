from decimal import Decimal
import unittest
from parcel_route import parse_manifest


class ManifestTests(unittest.TestCase):
    def test_normalizes_and_sorts(self):
        text = "parcel_id,zone,weight\nP2, west ,2.5\nP1,east,1\n"
        self.assertEqual(parse_manifest(text), [{"parcel_id":"P1","zone":"EAST","weight":Decimal("1")},{"parcel_id":"P2","zone":"WEST","weight":Decimal("2.5")}])


if __name__ == "__main__": unittest.main()
