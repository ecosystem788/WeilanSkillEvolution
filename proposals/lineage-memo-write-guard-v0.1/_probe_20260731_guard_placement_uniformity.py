"""Read-only probe: is the guard the FIRST statement at each guarded entrance?

Context: Codex's v1.1 proposal (peer-chat 2026-07-31T16:07:28+09:00) places
assert_guarded_write_entry_outside_derivation_memo() in command_open_lineaged
*after* canonical_workspace/normalize_scope and *before* contract_fence. The
other two guarded entrances put the guard on their literal first statement.
This probe measures whether that difference is observable, i.e. whether an
input that trips normalization inside a derivation memo yields the
normalization error rather than the stable guard error.

One-off: WEILAN_METHOD_HOME points at a tempfile root, no real ledger touched,
no writes to the deployed skill. Exits 0 on completion; findings are in the
emitted JSON, not in the exit code.
"""

import ast
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts")

GUARD = "assert_guarded_write_entry_outside_derivation_memo"
ENTRANCES = [
    "command_open_lineaged_fenced",
    "assert_transaction_write_allowed",
    "reconcile_runner_materialization",
]


def guard_position(tree, func_name):
    """Index of the guard call among the function's top-level statements."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            body = [s for s in node.body if not (
                isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                and isinstance(s.value.value, str))]
            for index, stmt in enumerate(body):
                for sub in ast.walk(stmt):
                    if (isinstance(sub, ast.Call)
                            and isinstance(sub.func, ast.Name)
                            and sub.func.id == GUARD):
                        return {"found": True, "stmt_index": index,
                                "is_first": index == 0,
                                "stmt_count": len(body),
                                "lineno": node.lineno}
            return {"found": False, "lineno": node.lineno}
    return {"found": False, "lineno": None}


def main():
    source_bytes = (SCRIPTS / "weilan_trace.py").read_bytes()
    result = {
        "live_weilan_trace_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "guard_placement": {},
        "error_identity_inside_memo": {},
    }

    tree = ast.parse(source_bytes.decode("utf-8"))
    for name in ENTRANCES:
        result["guard_placement"][name] = guard_position(tree, name)

    root = Path(tempfile.mkdtemp(prefix="weilan-probe-guard-placement-"))
    os.environ["WEILAN_METHOD_HOME"] = str(root)
    sys.path.insert(0, str(SCRIPTS))
    import weilan_trace as wt

    class Args:
        pass

    # An over-long scope trips normalize_scope, which today runs BEFORE the
    # fence and before the (inner) guard. Measure which error surfaces.
    for label, scope in (("valid_scope", "probe-scope"),
                         ("overlong_scope", "s" * 129)):
        args = Args()
        args.workspace = str(root / "ws")
        args.scope = scope
        args.branch = "main"
        args.relation = "root"
        args.parent = []
        args.problem = "probe"
        args.success = "probe"
        args.budget = None
        args.level = "L0"
        before = sorted(p.relative_to(root).as_posix()
                        for p in root.rglob("*"))
        try:
            with wt.derivation_memo_scope():
                wt.command_open_lineaged(args)
            outcome = {"raised": False}
        except Exception as exc:  # noqa: BLE001 - the error identity IS the datum
            outcome = {"raised": True, "type": type(exc).__name__,
                       "message": str(exc),
                       "is_guard_error": "derivation memo" in str(exc)}
        after = sorted(p.relative_to(root).as_posix()
                       for p in root.rglob("*"))
        outcome["state_entries_created"] = [p for p in after if p not in before]
        result["error_identity_inside_memo"][label] = outcome

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
