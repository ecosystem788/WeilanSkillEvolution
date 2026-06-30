import csv
from pathlib import Path


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_source(root):
    root = Path(root)
    users = [{**row, "legacy_id": int(row["legacy_id"])} for row in read_csv(root / "users.csv")]
    orders = [{**row, "order_id": int(row["order_id"]), "user_legacy_id": int(row["user_legacy_id"])} for row in read_csv(root / "orders.csv")]
    return users, orders
