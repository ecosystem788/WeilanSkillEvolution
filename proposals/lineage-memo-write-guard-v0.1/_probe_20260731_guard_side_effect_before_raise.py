"""Does the memo write guard fail CLOSED, or fail closed AFTER touching disk?

Codex's execution receipt claims the eight named entrances raise a stable
ValueError with "state-root zero change". This probe tests one entrance the
static review cannot settle: command_open_lineaged.

The guard call sits inside command_open_lineaged_fenced, but command_open_lineaged
enters contract_fence FIRST:

    def command_open_lineaged(args):
        with contract_fence(state_root(), wk, sk):      # <-- lock acquisition
            return command_open_lineaged_fenced(args, ...)   # <-- guard raises here

contract_fence -> workspace_contract_fence / exclusive_file_lock, and
exclusive_file_lock does `path.parent.mkdir(parents=True, exist_ok=True)` then
opens the lock file "a+b", writing a b"\\x00" byte when the file is new
(transaction.py:252-260). So on a state root where the fence paths do not yet
exist, the raise happens only after directories and lock files are created.

Method: one-shot temp WEILAN_METHOD_HOME (never the real ledger). Snapshot every
path under the state root, run the entrance inside an active derivation memo,
catch the ValueError, snapshot again, diff.

Read-only with respect to the real ledger. Writes only its own .out.json and a
tempdir it removes.
"""

import json
import os
import sys
import tempfile
import shutil
import hashlib
import argparse
from pathlib import Path

SCRIPTS = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts"


def snapshot(root):
    """Every file and directory under root, with content hash for files."""
    out = {}
    root = Path(root)
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if p.is_dir():
            out[rel + "/"] = "<dir>"
        else:
            try:
                out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            except OSError as exc:
                out[rel] = "<unreadable:%s>" % exc.__class__.__name__
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", default=SCRIPTS)
    args_ns = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="weilan-guard-probe-")
    state = os.path.join(tmp, "method-state")
    os.environ["WEILAN_METHOD_HOME"] = state
    os.environ["WEILAN_LOCK_TIMEOUT_S"] = "10"
    sys.path.insert(0, args_ns.scripts)

    result = {
        "probe": "guard_side_effect_before_raise",
        "state_root": state,
        "live_script_sha256": hashlib.sha256(
            Path(args_ns.scripts, "weilan_trace.py").read_bytes()
        ).hexdigest(),
    }

    try:
        import weilan_trace as wt

        result["state_root_seen_by_module"] = str(wt.state_root())

        workspace = tmp  # a real existing dir, so canonical_workspace resolves
        scope = "probe-scope"

        class A:
            pass

        a = A()
        a.workspace = workspace
        a.scope = scope
        a.branch = "main"
        a.relation = "continue"
        a.parent = []
        a.problem = "probe"
        a.constraints = []
        a.source = []
        a.causal_event_id = None

        before = snapshot(state)

        raised = None
        with wt.derivation_memo_scope():
            try:
                wt.command_open_lineaged(a)
            except Exception as exc:  # noqa: BLE001 - we are classifying it
                raised = {"type": type(exc).__name__, "message": str(exc)}

        after = snapshot(state)

        created = sorted(set(after) - set(before))
        changed = sorted(k for k in set(after) & set(before) if after[k] != before[k])
        removed = sorted(set(before) - set(after))

        result["raised"] = raised
        result["raised_is_the_guard"] = bool(
            raised
            and raised["type"] == "ValueError"
            and "derivation memo" in raised["message"]
        )
        result["state_root_before_count"] = len(before)
        result["paths_created_before_raise"] = created
        result["paths_changed"] = changed
        result["paths_removed"] = removed
        result["zero_state_root_change"] = not (created or changed or removed)

        # Control: same entrance, no memo scope -> what does a real run create?
        # (only to show which of the created paths are fence artifacts vs ledger)
        result["note"] = (
            "paths_created_before_raise are side effects that occurred despite "
            "the guard raising; classify each as fence-lock vs ledger content"
        )
    except Exception as exc:  # noqa: BLE001
        result["probe_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        out = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
