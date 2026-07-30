"""Read-only probe: if the live artifact were lost right now, could we rebuild it?

Established already (not re-litigated here):
  - correction-view-unwired-v0.1/FINDING.md 10.3 (07-29): C:\\Users\\zy\\.claude\\skills
    is a junction onto D:\\CodexData\\skills -- one directory, not two copies -- and the
    live tree hashes to 5fd0a51d...
  - _probe_20260731_deployment_lineage_closure.py (this round): no DEPLOYMENT_RECEIPT.json
    on disk or in git history has after_artifact_hash == 5fd0a51d...
  - _probe_20260731_live_drift_since_last_receipt.py (this round): live differs from the
    newest receipt's pre-deployment tree in exactly scripts/wake_brief.py (authorized,
    byte-exact against the declared sha) plus scripts/weilan_trace.py (mtime
    2026-07-26T12:07:23Z) and its .bak sidecar, neither of which that receipt covers.

The question here is the conservation one: the deployment convention says rollback runs
off an archived snapshot of the predecessor artifact. Does an archived copy of the tree
that is running *today* exist anywhere -- as git blobs, as a deployments/ rollback
snapshot, or as a candidate tree in proposals/?

Method (per-blob, following the convention Codex fixed on 2026-07-26T18:18:39+09:00):
ask git for each live file's object id, then test membership in the object set reachable
from ORDINARY refs only -- refs/codex/* checkpoint refs are harness draft space, not
repository content, so they do not count as preservation.

Strictly read-only; writes only its own .out.json.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.evolution_core import tree_hash, tree_manifest  # noqa: E402

LIVE = Path(r"D:\CodexData\skills\solve-with-weilan")
OUT = Path(__file__).with_suffix(".out.json")

out = {"probe": "live-artifact-recoverability", "live_root": str(LIVE)}


def git(*args, **kw):
    p = subprocess.run(
        ["git", "-C", str(REPO)] + list(args), capture_output=True, **kw
    )
    return p.returncode, p.stdout.decode("utf-8", "replace")


live_files = tree_manifest(LIVE)
out["live_tree_hash"] = tree_hash(LIVE)
out["live_file_count"] = len(live_files)

# --- object id of every live file (content hashing only; nothing is written to the odb)
oids = {}
for rec in live_files:
    rc, oid = git("hash-object", "--", str(LIVE / rec["path"]))
    if rc == 0:
        oids[rec["path"]] = oid.strip()
out["hashed"] = len(oids)

# --- object set reachable from ordinary refs (branches/tags/remotes), excluding refs/codex/*
rc, objs = git("rev-list", "--objects", "--branches", "--tags", "--remotes")
reachable = set()
for line in objs.splitlines():
    line = line.strip()
    if line:
        reachable.add(line.split()[0])
out["reachable_object_count"] = len(reachable)

covered = sorted(p for p, o in oids.items() if o in reachable)
orphans = sorted(p for p, o in oids.items() if o not in reachable)
out["covered_count"] = len(covered)
out["orphan_count"] = len(orphans)
out["orphan_paths"] = [{"path": p, "oid": oids[p]} for p in orphans]

# --- do the orphan blobs exist under refs/codex/* (draft space) even if not ordinary-reachable?
if orphans:
    rc, allobjs = git("rev-list", "--objects", "--all")
    all_reach = set()
    for line in allobjs.splitlines():
        line = line.strip()
        if line:
            all_reach.add(line.split()[0])
    out["orphans_present_under_all_refs"] = {
        p: (oids[p] in all_reach) for p in orphans
    }

# --- is the whole live tree archived as a directory snapshot anywhere on disk?
snapshot_roots = []
walk_errors = []


def find_snapshot_dirs(base):
    """os.walk instead of rglob: this tree contains paths that exceed Windows MAX_PATH,
    and pathlib.rglob raises FileNotFoundError on them instead of skipping. Those
    failures are recorded rather than swallowed."""
    import os

    def onerr(exc):
        walk_errors.append({"path": getattr(exc, "filename", None), "error": str(exc)})

    for root, dirs, _files in os.walk(base, onerror=onerr):
        for d in dirs:
            if d == "solve-with-weilan":
                yield Path(root) / d


for base in (REPO / "deployments", REPO / "proposals", REPO / "skill"):
    if not base.is_dir():
        continue
    for cand in find_snapshot_dirs(base):
        if not cand.is_dir():
            continue
        try:
            h = tree_hash(cand)
        except Exception as exc:  # unreadable snapshot is itself worth reporting
            snapshot_roots.append(
                {"path": str(cand.relative_to(REPO)).replace("\\", "/"), "error": str(exc)}
            )
            continue
        snapshot_roots.append(
            {
                "path": str(cand.relative_to(REPO)).replace("\\", "/"),
                "tree_hash": h,
                "matches_live": h == out["live_tree_hash"],
                "tracked_in_git": None,
            }
        )

rc, tracked_out = git("ls-files")
tracked_paths = set(p.strip() for p in tracked_out.splitlines() if p.strip())
for s in snapshot_roots:
    if "tree_hash" not in s:
        continue
    prefix = s["path"] + "/"
    s["tracked_in_git"] = any(t.startswith(prefix) for t in tracked_paths)

out["disk_snapshots"] = snapshot_roots
out["walk_error_count"] = len(walk_errors)
out["walk_errors_sample"] = walk_errors[:5]
out["live_tree_has_archived_snapshot"] = any(
    s.get("matches_live") for s in snapshot_roots
)
out["live_tree_has_tracked_snapshot"] = any(
    s.get("matches_live") and s.get("tracked_in_git") for s in snapshot_roots
)

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
summary = {
    k: out[k]
    for k in (
        "live_tree_hash",
        "live_file_count",
        "reachable_object_count",
        "covered_count",
        "orphan_count",
        "orphan_paths",
        "orphans_present_under_all_refs",
        "live_tree_has_archived_snapshot",
        "live_tree_has_tracked_snapshot",
    )
    if k in out
}
summary["disk_snapshots"] = out["disk_snapshots"]
print(json.dumps(summary, ensure_ascii=False, indent=1))
