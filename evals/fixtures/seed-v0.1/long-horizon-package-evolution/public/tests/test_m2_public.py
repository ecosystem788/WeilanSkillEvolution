import unittest
from parcel_route import choose_route


class RouteTests(unittest.TestCase):
    def test_cost_then_id(self):
        routes=[{"route_id":"R2","zones":["EAST"],"cost":"4.00"},{"route_id":"R1","zones":["EAST"],"cost":"4.00"}]
        self.assertEqual(choose_route("east",routes)["route_id"],"R1")


if __name__ == "__main__": unittest.main()
