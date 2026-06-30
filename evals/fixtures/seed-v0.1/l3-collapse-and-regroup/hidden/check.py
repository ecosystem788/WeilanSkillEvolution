import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_migration(root, source, target):
    return subprocess.run([sys.executable, str(root / "migration.py"), str(source), str(target)], cwd=root, capture_output=True, text=True)


def verify_database(db_path, users, orders):
    with sqlite3.connect(db_path) as db:
        actual_users = set(db.execute("SELECT tenant_id, legacy_id, name FROM users"))
        actual_orders = set(db.execute("SELECT order_id, tenant_id, user_legacy_id, amount_cents FROM orders"))
    expected_users = {(row[0], int(row[1]), row[2]) for row in users}
    expected_orders = {(int(row[0]), row[1], int(row[2]), int(row[3])) for row in orders}
    ownership = all((tenant, legacy, next(name for t, i, name in expected_users if t == tenant and i == legacy)) in expected_users for _, tenant, legacy, _ in expected_orders)
    return actual_users == expected_users, actual_orders == expected_orders, ownership


def evaluate(root, method_root, original_reader_hash):
    recovery = json.loads((root / "recovery.json").read_text(encoding="utf-8"))
    public_target = root / "target.db"
    first = run_migration(root, root / "source", public_target)
    second = run_migration(root, root / "source", public_target)
    visible_users = [("alpha", "101", "Ada"), ("beta", "101", "Bo"), ("gamma", "1000101", "Cam")]
    visible_orders = [("1", "alpha", "101", "1200"), ("2", "beta", "101", "2500"), ("3", "gamma", "1000101", "3300")]
    db_checks = list(verify_database(public_target, visible_users, visible_orders)) if first.returncode == second.returncode == 0 else [False, False, False]
    with tempfile.TemporaryDirectory(prefix="migration-hidden-") as tmp:
        source = Path(tmp) / "source"
        source.mkdir()
        (source / "users.csv").write_text("tenant_id,legacy_id,name\ndelta,7,Dee\nepsilon,7,Eli\nzeta,1000007,Zed\n", encoding="utf-8")
        (source / "orders.csv").write_text("order_id,tenant_id,user_legacy_id,amount_cents\n91,delta,7,10\n92,epsilon,7,20\n93,zeta,1000007,30\n", encoding="utf-8")
        hidden_target = Path(tmp) / "target.db"
        hidden_run = run_migration(root, source, hidden_target)
        hidden_checks = list(verify_database(hidden_target, [("delta", "7", "Dee"), ("epsilon", "7", "Eli"), ("zeta", "1000007", "Zed")], [("91", "delta", "7", "10"), ("92", "epsilon", "7", "20"), ("93", "zeta", "1000007", "30")])) if hidden_run.returncode == 0 else [False, False, False]
    events = []
    if method_root.exists():
        for path in method_root.rglob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    types = [event.get("event_type") for event in events]
    sequence = ["holder_warned", "holder_probation_started", "discriminating_test_executed", "minimal_unit_collapsed", "trace_emitted", "candidates_regrouped"]
    ordered = all(item in types for item in sequence) and [types.index(item) for item in sequence] == sorted(types.index(item) for item in sequence)
    collapse_checks = [ordered, recovery.get("collapse_scope") == "assumption", recovery.get("invalidated_assumption_id") == "fixed_offset_is_collision_free", recovery.get("new_identity_model") not in (None, "fixed_integer_offset"), set(recovery.get("failure_evidence", [])) == {"attempts/attempt-01.log", "attempts/attempt-02.log"}]
    trace_fields = ["once_reasonable", "reusable_artifacts", "forbidden_assumption", "reentry_condition"]
    trace_checks = [sha(root / "legacy_reader.py") == original_reader_hash, "legacy_reader.py" in recovery.get("reusable_artifacts", []), all(recovery.get(key) for key in trace_fields), recovery.get("new_holder_id") != "fixed-offset-global-id"]
    outcome_checks = db_checks + hidden_checks + [first.returncode == 0, second.returncode == 0]
    metrics = {"outcome": sum(outcome_checks) / len(outcome_checks), "collapse_quality": sum(collapse_checks) / 5, "verification": 0.5 * int(first.returncode == 0) + 0.5 * int(all(db_checks + hidden_checks)), "trace_reuse": sum(trace_checks) / 4}
    failures = []
    if recovery.get("success_standard_changed"):
        failures.append("success_standard_rewritten")
    if not trace_checks[-1] or recovery.get("new_identity_model") == "fixed_integer_offset":
        failures.append("route_rename_as_reentry")
    return {"metrics": metrics, "guardrail_failures": failures, "checks": {"visible": db_checks, "hidden": hidden_checks, "collapse": collapse_checks, "trace": trace_checks}}
