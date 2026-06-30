import json
from pathlib import Path
import tempfile
import unittest
from parcel_route.cli import main


class FinalIntegrationTests(unittest.TestCase):
    def test_cli_writes_canonical_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); manifest=root/"manifest.csv"; routes=root/"routes.json"; output=root/"nested"/"plan.json"
            manifest.write_text("parcel_id,zone,weight\nP2,W,1\nP1,E,2\n",encoding="utf-8")
            routes.write_text(json.dumps([{"route_id":"RW","zones":["W"],"cost":"1.20"},{"route_id":"RE","zones":["E"],"cost":"2.30"}]),encoding="utf-8")
            self.assertEqual(main([str(manifest),str(routes),str(output)]),0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["total_cost"],"3.50")

    def test_invalid_input_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); manifest=root/"bad.csv"; routes=root/"routes.json"; output=root/"plan.json"
            manifest.write_text("parcel_id,zone,weight\nP1,E,0\n",encoding="utf-8"); routes.write_text("[]",encoding="utf-8")
            self.assertNotEqual(main([str(manifest),str(routes),str(output)]),0)
            self.assertFalse(output.exists())


if __name__ == "__main__": unittest.main()
