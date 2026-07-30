"""Read-only probe: does any deployment receipt account for the live artifact?

Context. On 2026-07-31T00:14:49+09:00 Codex blocked clause (A) of the ROADMAP
historicization proposal because it named `9872361c...` as the live artifact,
while the live tree hashes to `5fd0a51d...`. Both of us then treated the newest
archived receipt as the authority for "what is live". This probe asks the next
question neither of us asked: taking *every* deployment receipt in the repo --
on disk and in git history -- is there one whose after_artifact_hash equals the
live tree, and if not, where does the before/after chain stop?

Strictly read-only: reads files, runs read-only git plumbing, writes only its
own .out.json next to this file. It does not use `evolution_cli candidate-freeze`
(that stages a content-addressed copy under the system Temp dir).
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

out = {"probe": "deployment-lineage-closure", "repo": str(REPO)}


def git(*args):
    p = subprocess.run(
        ["git", "-C", str(REPO)] + list(args), capture_output=True
    )
    return p.returncode, p.stdout.decode("utf-8", "replace")


def load_json_bytes(raw):
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return None


# ---------------------------------------------------------------- live artifact
out["live_exists"] = LIVE.is_dir()
live_hash = None
if out["live_exists"]:
    live_hash = tree_hash(LIVE)
    out["live_tree_hash"] = live_hash
    out["live_file_count"] = len(tree_manifest(LIVE))

# -------------------------------------------------- receipts present on disk
disk = {}
dep_root = REPO / "deployments"
for path in sorted(dep_root.rglob("DEPLOYMENT_RECEIPT.json")):
    rec = load_json_bytes(path.read_bytes())
    if rec is None:
        continue
    rel = str(path.relative_to(REPO)).replace("\\", "/")
    disk[rel] = rec

# ------------------------------------- receipts that ever existed in git history
# Every blob at any DEPLOYMENT_RECEIPT.json path, across all refs.
rc, log = git(
    "log", "--all", "--pretty=format:%H|%ad", "--date=iso-strict",
    "--name-only", "--diff-filter=AM", "--", "deployments/**/DEPLOYMENT_RECEIPT.json",
)
history = {}
commit = None
cdate = None
for line in log.splitlines():
    line = line.strip()
    if not line:
        continue
    if "|" in line and len(line.split("|")[0]) == 40:
        commit, cdate = line.split("|", 1)
        continue
    if not line.endswith("DEPLOYMENT_RECEIPT.json"):
        continue
    rc2, blob = git("show", f"{commit}:{line}")
    if rc2 != 0:
        continue
    rec = load_json_bytes(blob.encode("utf-8", "replace"))
    if rec is None:
        continue
    key = line
    # keep the earliest-added version of each path plus note later rewrites
    history.setdefault(key, []).append(
        {"commit": commit, "commit_date": cdate, "receipt": rec}
    )

# ------------------------------------------------------- union of all receipts
def summarize(rel, rec, tracked, commits):
    return {
        "path": rel,
        "deployment_id": rec.get("deployment_id"),
        "schema_version": rec.get("schema_version"),
        "before": rec.get("before_artifact_hash"),
        "after": rec.get("after_artifact_hash"),
        "authority_source": rec.get("authority_source"),
        "changed_live_paths": rec.get("changed_live_paths"),
        "target": rec.get("target"),
        "tracked_in_git": tracked,
        "added_in_commits": commits,
    }


rc, tracked_out = git("ls-files", "--", "deployments")
tracked_paths = set(
    p.strip().replace("\\", "/") for p in tracked_out.splitlines() if p.strip()
)

records = []
for rel, rec in disk.items():
    commits = [h["commit"][:12] for h in history.get(rel, [])]
    records.append(summarize(rel, rec, rel in tracked_paths, commits))

# receipts that exist only in history (deleted from disk)
for rel, entries in history.items():
    if rel in disk:
        continue
    rec = entries[-1]["receipt"]
    records.append(
        summarize(rel, rec, rel in tracked_paths, [e["commit"][:12] for e in entries])
    )

out["receipt_count_on_disk"] = len(disk)
out["receipt_count_history_only"] = len(records) - len(disk)
out["receipts"] = records

# --------------------------------------------------------------- chain closure
afters = {r["after"]: r for r in records if r.get("after")}
befores = {r["before"]: r for r in records if r.get("before")}

out["live_hash_is_some_receipt_after"] = bool(live_hash and live_hash in afters)
out["live_hash_matching_receipt"] = (
    afters[live_hash]["path"] if live_hash in afters else None
)

# Which after-hashes are terminal (never consumed as a later before)?
terminal = [
    {"after": h, "path": r["path"], "deployment_id": r["deployment_id"]}
    for h, r in afters.items()
    if h not in befores
]
out["terminal_after_hashes"] = terminal

# Which before-hashes have no producing receipt (chain gaps / unrecorded deploys)?
orphan_befores = [
    {"before": h, "path": r["path"], "deployment_id": r["deployment_id"]}
    for h, r in befores.items()
    if h not in afters
]
out["before_hashes_with_no_producing_receipt"] = orphan_befores

# ------------------------------------------- does the live hash appear anywhere?
if live_hash:
    rc, hits = git("grep", "-l", live_hash[:32], "--", ".")
    out["live_hash_grep_tracked_hits"] = [
        h.strip() for h in hits.splitlines() if h.strip()
    ]
    rc, hist_hits = git("log", "--all", "-S", live_hash[:32], "--oneline")
    out["live_hash_history_hits"] = [
        h.strip() for h in hist_hits.splitlines() if h.strip()
    ]

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(
    {
        k: out[k]
        for k in (
            "live_tree_hash",
            "live_file_count",
            "receipt_count_on_disk",
            "receipt_count_history_only",
            "live_hash_is_some_receipt_after",
            "live_hash_matching_receipt",
            "terminal_after_hashes",
            "before_hashes_with_no_producing_receipt",
            "live_hash_grep_tracked_hits",
            "live_hash_history_hits",
        )
        if k in out
    },
    ensure_ascii=False,
    indent=1,
))
