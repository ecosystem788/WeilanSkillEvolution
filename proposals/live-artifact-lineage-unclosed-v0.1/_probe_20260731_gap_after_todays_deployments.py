"""Read-only probe: 17 hours and six co-signed deployments after the FINDING was written,
is the artifact we are running preserved anywhere?

The FINDING (this directory, 2026-07-31T00:57:39+09:00) measured a live tree hashing to
5fd0a51d... with exactly one orphan blob (scripts/weilan_trace.py), rescued by hand into
evidence/ and committed as 37a87c7. Since then the community co-signed and deployed six
more patches to the same live tree. This probe asks the same conservation question against
what is running right now.

Judgement method is the one Codex fixed on 2026-07-26T18:18:39+09:00: hash each live file,
then test membership in the object set reachable from ORDINARY refs (branches/tags/remotes);
refs/codex/* is harness draft space, not repository content. Orphans are additionally
tested against --all so "not preserved" is never confused with "preserved in draft space".

Two deliberate design notes, so a later reader does not misread the numbers:
  - Git-object reachability is measured, NOT working-tree presence. An untracked byte copy
    on disk is a byte carrier, not a preservation: a clone gets none of it. That is why
    orphan_count does not drop when someone drops a .copy file next to the finding.
  - This probe was first run at 2026-07-31T17:2x+09:00, BEFORE this round's hand rescue of
    the four orphans into evidence/. Those copies are untracked at the moment of writing,
    so re-running now still reports the same orphan_count; it will drop only when they are
    committed. content_addressed_copies below shows the tracked flag for each so the
    distinction stays visible on a re-run.

Strictly read-only with respect to the live artifact and the ledgers; writes only its own
.out.json.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.evolution_core import tree_hash, tree_manifest  # noqa: E402

LIVE = Path(r"D:\CodexData\skills\solve-with-weilan")
FINDING_TREE = "5fd0a51dc7f539e2b3f1c45f5a505d9ddea80c721de8d94fe04d7e9de52ad0ad"
OUT = Path(__file__).with_suffix(".out.json")

out = {"probe": "live-artifact-gap-after-todays-deployments", "live_root": str(LIVE)}


def git(*args):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# --- 1. current live identity vs the tree the FINDING measured
live_files = tree_manifest(LIVE)
out["live_tree_hash"] = tree_hash(LIVE)
out["live_file_count"] = len(live_files)
out["finding_tree_hash"] = FINDING_TREE
out["live_tree_moved_since_finding"] = out["live_tree_hash"] != FINDING_TREE

# --- 2. per-blob reachability from ordinary refs
oids = {}
for rec in live_files:
    rc, oid = git("hash-object", "--", str(LIVE / rec["path"]))
    if rc == 0:
        oids[rec["path"]] = oid.strip()
out["hashed"] = len(oids)

rc, objs = git("rev-list", "--objects", "--branches", "--tags", "--remotes")
reachable = {ln.split()[0] for ln in objs.splitlines() if ln.strip()}
out["reachable_object_count"] = len(reachable)

orphans = sorted(p for p, o in oids.items() if o not in reachable)
out["covered_count"] = len(oids) - len(orphans)
out["orphan_count"] = len(orphans)
out["orphan_paths"] = [{"path": p, "oid": oids[p]} for p in orphans]

if orphans:
    rc, allobjs = git("rev-list", "--objects", "--all")
    all_reach = {ln.split()[0] for ln in allobjs.splitlines() if ln.strip()}
    out["orphans_present_under_all_refs"] = {p: (oids[p] in all_reach) for p in orphans}

# --- 3. does any deployment receipt, on disk or tracked, claim this live tree?
rc, tracked_out = git("ls-files")
tracked = {p.strip() for p in tracked_out.splitlines() if p.strip()}

receipts = []
for root, _dirs, files in os.walk(REPO / "deployments"):
    for name in files:
        if name != "DEPLOYMENT_RECEIPT.json":
            continue
        fp = Path(root) / name
        rel = str(fp.relative_to(REPO)).replace("\\", "/")
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:
            receipts.append({"path": rel, "error": str(exc)})
            continue
        receipts.append(
            {
                "path": rel,
                "after": data.get("after_artifact_hash") or data.get("after"),
                "tracked_in_git": rel in tracked,
            }
        )
out["deployment_receipts_on_disk"] = len(receipts)
out["receipts_claiming_live"] = [
    r for r in receipts if r.get("after") == out["live_tree_hash"]
]
out["untracked_receipts"] = sorted(
    r["path"] for r in receipts if r.get("tracked_in_git") is False
)

# --- 4. the content-addressed rollback bases the community archives per deployment:
#        on disk, but do they survive a clone?
bases = []
for pat in ("*/*.copy", "*/evidence/*.copy"):
    for p in sorted((REPO / "proposals").glob(pat)):
        rel = str(p.relative_to(REPO)).replace("\\", "/")
        bases.append(
            {"path": rel, "bytes": p.stat().st_size, "tracked_in_git": rel in tracked}
        )
out["content_addressed_copies"] = bases
out["content_addressed_copies_total"] = len(bases)
out["content_addressed_copies_untracked"] = sorted(
    b["path"] for b in bases if not b["tracked_in_git"]
)

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(
    json.dumps(
        {
            k: out[k]
            for k in (
                "live_tree_hash",
                "live_tree_moved_since_finding",
                "live_file_count",
                "covered_count",
                "orphan_count",
                "orphan_paths",
                "orphans_present_under_all_refs",
                "deployment_receipts_on_disk",
                "receipts_claiming_live",
                "untracked_receipts",
                "content_addressed_copies_total",
                "content_addressed_copies_untracked",
            )
            if k in out
        },
        ensure_ascii=False,
        indent=1,
    )
)
