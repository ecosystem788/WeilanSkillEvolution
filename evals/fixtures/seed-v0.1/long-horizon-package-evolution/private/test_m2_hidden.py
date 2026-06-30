import unittest
from parcel_route import choose_route


class HiddenRouteTests(unittest.TestCase):
    def test_normalization_and_no_route(self):
        routes=[{"route_id":"B","zones":["NORTH"],"cost":"1.10"},{"route_id":"A","zones":["NORTH"],"cost":"1.01"}]
        self.assertEqual(choose_route(" north ",routes)["route_id"],"A")
        with self.assertRaises(ValueError): choose_route("SOUTH",routes)


if __name__ == "__main__": unittest.main()
