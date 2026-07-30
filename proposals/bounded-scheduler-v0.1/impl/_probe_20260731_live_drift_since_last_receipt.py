"""Read-only probe: what changed in the live artifact after the last receipt?

Follow-on to _probe_20260731_deployment_lineage_closure.py, which established
that no DEPLOYMENT_RECEIPT.json in the repo (disk or history) has
after_artifact_hash == the live tree hash 5fd0a51d...

The newest receipt (deployments/1751ce140fe3cbdf0dc55ec0, 2026-07-21) archives a
rollback copy of the pre-deployment tree and declares:
  before = c393bc39...   after = 9872361c...
  changed_live_paths = ["scripts/wake_brief.py"]
  verification.wake_brief_sha256 = a7117933...

So the receipt fully determines the intended post-deployment tree:
  rollback tree, with scripts/wake_brief.py swapped to sha a7117933...

This probe reconstructs that intended tree per-file and diffs the live tree
against it. Every difference beyond scripts/wake_brief.py is a live-artifact
mutation with no deployment receipt behind it.

Strictly read-only; writes only its own .out.json.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.evolution_core import tree_hash, tree_manifest  # noqa: E402

LIVE = Path(r"D:\CodexData\skills\solve-with-weilan")
RECEIPT_DIR = REPO / "deployments" / "1751ce140fe3cbdf0dc55ec0"
ROLLBACK = RECEIPT_DIR / "rollback" / "solve-with-weilan"
OUT = Path(__file__).with_suffix(".out.json")

receipt = json.loads((RECEIPT_DIR / "DEPLOYMENT_RECEIPT.json").read_bytes().decode("utf-8-sig"))

out = {
    "probe": "live-drift-since-last-receipt",
    "receipt": {
        "deployment_id": receipt["deployment_id"],
        "before": receipt["before_artifact_hash"],
        "after": receipt["after_artifact_hash"],
        "changed_live_paths": receipt["changed_live_paths"],
        "declared_wake_brief_sha256": receipt["verification"]["wake_brief_sha256"],
    },
}

out["rollback_copy_exists"] = ROLLBACK.is_dir()
if not ROLLBACK.is_dir() or not LIVE.is_dir():
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    raise SystemExit(0)

roll = {r["path"]: r for r in tree_manifest(ROLLBACK)}
live = {r["path"]: r for r in tree_manifest(LIVE)}

out["rollback_tree_hash"] = tree_hash(ROLLBACK)
out["rollback_matches_receipt_before"] = out["rollback_tree_hash"] == receipt["before_artifact_hash"]
out["live_tree_hash"] = tree_hash(LIVE)
out["file_counts"] = {"rollback": len(roll), "live": len(live)}

changed_by_receipt = set(receipt["changed_live_paths"])

added, removed, modified, unchanged = [], [], [], 0
for p in sorted(set(roll) | set(live)):
    if p not in roll:
        added.append(p)
    elif p not in live:
        removed.append(p)
    elif roll[p]["sha256"] != live[p]["sha256"]:
        modified.append(p)
    else:
        unchanged += 1

out["vs_rollback"] = {
    "added": added,
    "removed": removed,
    "modified": modified,
    "unchanged_count": unchanged,
}

# The receipt only authorizes changes to changed_live_paths. Anything else that
# differs from the pre-deployment tree is unaccounted for by this receipt.
unaccounted = sorted(
    (set(added) | set(removed) | set(modified)) - changed_by_receipt
)
out["paths_not_covered_by_receipt"] = unaccounted

# Did the one authorized path land on the declared content?
wb = live.get("scripts/wake_brief.py")
out["wake_brief_live_sha256"] = wb["sha256"] if wb else None
out["wake_brief_matches_declared"] = bool(
    wb and wb["sha256"] == receipt["verification"]["wake_brief_sha256"]
)

# Date the drift: mtimes of the unaccounted-for live files (UTC).
def mtime(rel):
    f = LIVE / rel
    if not f.exists():
        return None
    return datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()

out["unaccounted_mtimes_utc"] = {p: mtime(p) for p in unaccounted}
out["authorized_path_mtime_utc"] = {p: mtime(p) for p in sorted(changed_by_receipt)}

# Newest mtime in the whole live tree, as an upper bound on "when live last moved".
stamped = [(mtime(p), p) for p in live]
stamped = [s for s in stamped if s[0]]
stamped.sort()
out["live_mtime_range_utc"] = {
    "oldest": stamped[0] if stamped else None,
    "newest": stamped[-1] if stamped else None,
}

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
