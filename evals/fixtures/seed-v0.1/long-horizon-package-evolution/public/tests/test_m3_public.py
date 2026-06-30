import unittest
from parcel_route import build_plan


class PlanTests(unittest.TestCase):
    def test_integrates(self):
        manifest="parcel_id,zone,weight\nP1,east,1\n"
        routes=[{"route_id":"R1","zones":["EAST"],"cost":"2.50"}]
        self.assertEqual(build_plan(manifest,routes),{"assignments":[{"cost":"2.50","parcel_id":"P1","route_id":"R1"}],"total_cost":"2.50"})


if __name__ == "__main__": unittest.main()
