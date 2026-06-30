import unittest
from parcel_route import build_plan


class HiddenPlanTests(unittest.TestCase):
    def test_sorted_and_totals(self):
        manifest="parcel_id,zone,weight\nP2,W,1\nP1,E,2\n"
        routes=[{"route_id":"RW","zones":["W"],"cost":"1.20"},{"route_id":"RE","zones":["E"],"cost":"2.345"}]
        plan=build_plan(manifest,routes)
        self.assertEqual([x["parcel_id"] for x in plan["assignments"]],["P1","P2"])
        self.assertEqual(plan["total_cost"],"3.55")


if __name__ == "__main__": unittest.main()
