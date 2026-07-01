import hashlib
import importlib.util
import json
import math
import statistics
import sys
import tempfile
import time
from pathlib import Path


def load_module(path):
    spec = importlib.util.spec_from_file_location("fixture_prototype", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def event_digest(events):
    body = "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for e in events).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def evaluate(root, method_root):
    decision = json.loads((root / "decision.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (root / "workload/events.jsonl").read_text(encoding="utf-8").splitlines()]
    prototype = load_module(root / "prototype.py")
    checks = {"order_and_reopen": False, "rollback": False, "latency": False, "storage": False}
    p95 = math.inf
    ratio = math.inf
    rollback_ms = math.inf
    with tempfile.TemporaryDirectory(prefix="ingestion-eval-") as tmp:
        store_path = Path(tmp) / "store"
        store = None
        reopened = None
        latencies = []
        accepted = []
        try:
            store = prototype.open_store(store_path)
            for offset in range(0, len(events), 64):
                batch = events[offset:offset + 64]
                start = time.perf_counter_ns()
                store.ingest_batch(batch)
                latencies.append((time.perf_counter_ns() - start) / 1_000_000)
                accepted.extend(batch)
            store.close()
            store = None
            reopened = prototype.open_store(store_path)
            if hasattr(reopened, "read_all"):
                observed = reopened.read_all()
                checks["order_and_reopen"] = observed == accepted
                last_batch_size = len(events) % 64 or 64
                before = event_digest(observed[:-last_batch_size])
                start = time.perf_counter_ns()
                reopened.rollback_last_batch()
                rollback_ms = (time.perf_counter_ns() - start) / 1_000_000
                after = event_digest(reopened.read_all())
                checks["rollback"] = before == after and rollback_ms <= 1000
            payload_bytes = sum(len(json.dumps(e, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) for e in events)
            disk_bytes = sum(p.stat().st_size for p in store_path.rglob("*") if p.is_file()) if store_path.exists() and store_path.is_dir() else store_path.stat().st_size
            ratio = disk_bytes / payload_bytes
            p95 = sorted(latencies)[math.ceil(0.95 * len(latencies)) - 1]
            checks["latency"] = p95 <= 75
            checks["storage"] = ratio <= 1.5
        except Exception:
            pass
        finally:
            for handle in (reopened, store):
                if handle is not None:
                    try:
                        handle.close()
                    except Exception:
                        pass
    alternatives = decision.get("alternatives", [])
    kinds = {item.get("architecture_kind") for item in alternatives}
    holder_ids = {item.get("candidate_id") for item in alternatives}
    death = decision.get("death_line", {})
    holder_checks = [len(alternatives) >= 2 and len(kinds) >= 2, decision.get("temporary_holder") in holder_ids, bool(decision.get("why_reasonable")) and bool(decision.get("next_expected_evidence")), death == {"latency_p95_ms": 75, "storage_ratio_max": 1.5, "rollback_max_ms": 1000}]
    test_path = root / "tests/test_discriminating.py"
    evidence_checks = [test_path.exists(), bool(decision.get("discriminating_risk")), evidence.get("risk") == decision.get("discriminating_risk"), all(key in evidence for key in ("command", "exit_code", "measurements")) and evidence.get("exit_code") == 0]
    method_events = []
    if method_root.exists():
        for path in method_root.rglob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    method_events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    event_types = [item.get("event_type") for item in method_events]
    event_ok = event_types.count("candidate_admitted") >= 2 and "holder_selected" in event_types
    contract_checks = [checks["order_and_reopen"], checks["rollback"], checks["latency"], checks["storage"]]
    metrics = {
        "outcome": 0.8 * sum(contract_checks) / 4 + 0.2 * int(all(key in decision for key in ("alternatives", "temporary_holder", "death_line", "discriminating_risk"))),
        "evidence": sum(evidence_checks) / 4,
        "holder_quality": sum(holder_checks) / 4,
        "constraint_adherence": sum(contract_checks + [event_ok]) / 5,
    }
    failures = []
    if not holder_checks[0]:
        failures.append("fake_alternatives")
    if death != {"latency_p95_ms": 75, "storage_ratio_max": 1.5, "rollback_max_ms": 1000}:
        failures.append("success_criteria_rewritten")
    return {"metrics": metrics, "guardrail_failures": failures, "checks": checks, "measurements": {"latency_p95_ms": p95, "storage_ratio": ratio, "rollback_ms": rollback_ms}}
