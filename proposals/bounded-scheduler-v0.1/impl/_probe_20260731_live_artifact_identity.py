"""Read-only probe: what is the live solve-with-weilan artifact right now?

Independent of `evolution_cli.py candidate-freeze` (which stages a content-addressed
copy under the system Temp dir). This one only reads: it imports evolution_core's
tree_hash directly and never writes outside its own .out.json.

Claim under test (Codex, peer-chat 2026-07-31T00:14:49+09:00):
  live tree hash of D:\\CodexData\\skills\\solve-with-weilan == 5fd0a51d...
  and the archived receipt's after= 9872361c... is a 07-21 fact, not current state.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.evolution_core import tree_hash, tree_manifest  # noqa: E402

LIVE = Path(r"D:\CodexData\skills\solve-with-weilan")
CLAIMED_LIVE = "5fd0a51dc7f539e2b3f1c45f5a505d9ddea80c721de8d94fe04d7e9de52ad0ad"
RECEIPT_AFTER = "9872361cd77d4a3efaa23b2f00560288301d9ce921425c762687b2c58f551d9e"

out = {"probe": "live-artifact-identity", "live_root": str(LIVE)}

out["live_exists"] = LIVE.is_dir()
if out["live_exists"]:
    manifest = tree_manifest(LIVE)
    out["live_tree_hash"] = tree_hash(LIVE)
    out["live_file_count"] = len(manifest)
    out["matches_codex_claim"] = out["live_tree_hash"] == CLAIMED_LIVE
    out["matches_receipt_after"] = out["live_tree_hash"] == RECEIPT_AFTER
    out["bak_files"] = [r["path"] for r in manifest if r["path"].endswith(".bak")]

# Is there an archived artifact tree for either hash to diff against?
roots = []
for cand in (REPO / "artifacts", REPO / "evals" / "artifacts", REPO / "deployments"):
    if cand.is_dir():
        roots.append(cand)
found = {}
for r in roots:
    for h in (CLAIMED_LIVE, RECEIPT_AFTER):
        hits = [str(p.relative_to(REPO)) for p in r.rglob(h[:16] + "*") if p.is_dir()]
        if hits:
            found.setdefault(h, []).extend(hits)
out["archived_artifact_dirs_by_hash"] = found

# Provenance of the two receipts cited in the proposal: are they in git at all?
def git(*args):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()

receipts = {}
for dep in ("1751ce140fe3cbdf0dc55ec0", "a118135c1e1834e45cafac8c"):
    path = f"deployments/{dep}/DEPLOYMENT_RECEIPT.json"
    rc_ls, ls = git("ls-files", "--", path)
    rc_log, log = git("log", "--all", "--oneline", "--diff-filter=A", "--", f"deployments/{dep}/*")
    rc_ign, ign = git("check-ignore", "-v", "--", path)
    disk = REPO / path
    receipts[dep] = {
        "on_disk": disk.is_file(),
        "tracked_in_HEAD_index": bool(ls),
        "ever_added_on_any_branch": bool(log),
        "gitignored": rc_ign == 0,
        "after_artifact_hash": json.loads(disk.read_text(encoding="utf-8")).get("after_artifact_hash")
        if disk.is_file()
        else None,
        "before_artifact_hash": json.loads(disk.read_text(encoding="utf-8")).get("before_artifact_hash")
        if disk.is_file()
        else None,
    }
out["cited_receipts"] = receipts

# How many deployment dirs exist, and how many are in git?
dep_root = REPO / "deployments"
dirs = sorted(p.name for p in dep_root.iterdir() if p.is_dir())
rc, tracked = git("ls-files", "--", "deployments/")
tracked_dirs = sorted({line.split("/")[1] for line in tracked.splitlines() if line.startswith("deployments/")})
out["deployment_dirs_on_disk"] = dirs
out["deployment_dirs_tracked"] = tracked_dirs
out["deployment_dirs_untracked"] = sorted(set(dirs) - set(tracked_dirs))

print(json.dumps(out, ensure_ascii=False, indent=2))
Path(__file__).with_suffix(".out.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
