"""Independent Claude-side review probe for the lineage memo write-guard v1.1.

Checks, against the DEPLOYED scripts, four things Codex's receipt asserts:
  A. non-memo lineaged open still works end to end (guard is not spurious);
  B. inside a derivation memo, outer command_open_lineaged fails closed with the
     guard error and leaves the state tree byte-identical (cold and warm);
  C. an invalid (129-char) scope inside a memo yields the SAME guard error,
     i.e. the guard really precedes normalize_scope;
  D. that same 129-char scope outside a memo raises a DIFFERENT (scope) error,
     so C is not vacuous.

Runs entirely inside a temp WEILAN_METHOD_HOME; touches no real ledger.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")

sandbox = Path(tempfile.mkdtemp(prefix="weilan-guard-probe-"))
os.environ["WEILAN_METHOD_HOME"] = str(sandbox / "method-state")
sys.path.insert(0, str(SCRIPTS))

import weilan_trace  # noqa: E402

WORKSPACE = str(sandbox / "ws")
Path(WORKSPACE).mkdir(parents=True, exist_ok=True)
SCOPE = "probe-scope"
LONG_SCOPE = "x" * 129


def tree_digest(root):
    root = Path(root)
    entries = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                entries.append(
                    (
                        str(path.relative_to(root)).replace("\\", "/"),
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                )
    blob = json.dumps(entries, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(entries)


def ns(**kw):
    base = dict(
        workspace=WORKSPACE,
        scope=SCOPE,
        branch="main",
        relation="root",
        parent=[],
        problem="probe",
        success="probe success criteria",
        budget=None,
        level="L1",
    )
    base.update(kw)
    return argparse.Namespace(**base)


def attempt(fn):
    try:
        value = fn()
        return {"raised": False, "value_kind": type(value).__name__}
    except Exception as exc:  # noqa: BLE001 - probe records whatever surfaces
        return {"raised": True, "type": type(exc).__name__, "message": str(exc)}


results = {"sandbox": str(sandbox), "checks": {}}
root = Path(os.environ["WEILAN_METHOD_HOME"])

# --- B (cold): memo-guarded outer open on an empty state tree -----------------
before = tree_digest(root)
with weilan_trace.derivation_memo_scope():
    outcome = attempt(lambda: weilan_trace.command_open_lineaged(ns()))
after = tree_digest(root)
results["checks"]["B_cold_memo_outer_open"] = {
    "outcome": outcome,
    "digest_before": before,
    "digest_after": after,
    "zero_state_change": before == after,
}

# --- C: invalid scope inside memo -> same guard error -------------------------
before = tree_digest(root)
with weilan_trace.derivation_memo_scope():
    outcome_long = attempt(
        lambda: weilan_trace.command_open_lineaged(ns(scope=LONG_SCOPE))
    )
after = tree_digest(root)
results["checks"]["C_memo_invalid_scope"] = {
    "outcome": outcome_long,
    "zero_state_change": before == after,
    "same_message_as_valid_scope": (
        outcome_long.get("message")
        == results["checks"]["B_cold_memo_outer_open"]["outcome"].get("message")
    ),
}

# --- D: invalid scope OUTSIDE memo -> different (scope) error -----------------
before = tree_digest(root)
outcome_d = attempt(lambda: weilan_trace.command_open_lineaged(ns(scope=LONG_SCOPE)))
after = tree_digest(root)
results["checks"]["D_nonmemo_invalid_scope"] = {
    "outcome": outcome_d,
    "zero_state_change": before == after,
    "differs_from_guard_message": (
        outcome_d.get("message")
        != results["checks"]["B_cold_memo_outer_open"]["outcome"].get("message")
    ),
}

# --- A: non-memo open must still succeed --------------------------------------
before = tree_digest(root)
outcome_a = attempt(lambda: weilan_trace.command_open_lineaged(ns()))
after = tree_digest(root)
results["checks"]["A_nonmemo_open_still_works"] = {
    "outcome": outcome_a,
    "digest_before": before,
    "digest_after": after,
    "state_grew": after[1] > before[1],
}

# --- B (warm): repeat guard check now that state exists -----------------------
before = tree_digest(root)
with weilan_trace.derivation_memo_scope():
    outcome_warm = attempt(lambda: weilan_trace.command_open_lineaged(ns(relation="continue")))
after = tree_digest(root)
results["checks"]["B_warm_memo_outer_open"] = {
    "outcome": outcome_warm,
    "zero_state_change": before == after,
}

# --- placement: guard is the literal first statement ---------------------------
import inspect  # noqa: E402

src = inspect.getsource(weilan_trace.command_open_lineaged).splitlines()
results["checks"]["placement"] = {
    "def_line": src[0].strip(),
    "first_statement": src[1].strip(),
    "is_guard_first": src[1].strip()
    == "assert_guarded_write_entry_outside_derivation_memo()",
}

verdict = (
    results["checks"]["B_cold_memo_outer_open"]["outcome"].get("raised") is True
    and results["checks"]["B_cold_memo_outer_open"]["zero_state_change"]
    and results["checks"]["B_warm_memo_outer_open"]["zero_state_change"]
    and results["checks"]["C_memo_invalid_scope"]["same_message_as_valid_scope"]
    and results["checks"]["D_nonmemo_invalid_scope"]["differs_from_guard_message"]
    and results["checks"]["A_nonmemo_open_still_works"]["outcome"]["raised"] is False
    and results["checks"]["placement"]["is_guard_first"]
)
results["all_expectations_met"] = verdict
print(json.dumps(results, ensure_ascii=False, indent=2))
