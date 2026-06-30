import tempfile
import unittest
from pathlib import Path
from legacy_reader import read_source


class ReaderTests(unittest.TestCase):
    def test_reusable_reader_preserves_tenant_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "users.csv").write_text("tenant_id,legacy_id,name\na,1,A\nb,1,B\n", encoding="utf-8")
            (source / "orders.csv").write_text("order_id,tenant_id,user_legacy_id,amount_cents\n1,a,1,20\n", encoding="utf-8")
            users, orders = read_source(source)
            self.assertEqual([(u["tenant_id"], u["legacy_id"]) for u in users], [("a", 1), ("b", 1)])
            self.assertEqual(orders[0]["user_legacy_id"], 1)


if __name__ == "__main__":
    unittest.main()
