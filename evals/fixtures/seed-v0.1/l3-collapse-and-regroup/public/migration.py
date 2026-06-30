import sqlite3
import sys
from legacy_reader import read_source


def mapped_id(tenant, legacy_id):
    return legacy_id + (1_000_000 if tenant == "beta" else 0)


def migrate(source, target):
    users, orders = read_source(source)
    with sqlite3.connect(target) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, legacy_id INTEGER NOT NULL, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(order_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), tenant_id TEXT NOT NULL, amount_cents INTEGER NOT NULL);
        """)
        for row in users:
            db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (mapped_id(row["tenant_id"], row["legacy_id"]), row["tenant_id"], row["legacy_id"], row["name"]))
        for row in orders:
            db.execute("INSERT INTO orders VALUES (?, ?, ?, ?)", (row["order_id"], mapped_id(row["tenant_id"], row["user_legacy_id"]), row["tenant_id"], int(row["amount_cents"])))


if __name__ == "__main__":
    migrate(sys.argv[1], sys.argv[2])
