"""Independent co-signer check for the 2026-07-28 second daily push.

Goes beyond scan_push_manifest.py in two ways the signer should not assume:
  1. scan_push_manifest reads blobs at HEAD only. Publishing a commit range
     publishes every intermediate blob too. So: scan every (commit, path)
     version in the range, not just the HEAD version.
  2. `git diff --name-only base..head` compares two trees, so a file that was
     added and then deleted inside the range shows up nowhere -- yet its blob
     is published. So: take the union of per-commit name-only diffs.
Also scans the commit messages, which the manifest scanner never looks at.
"""
import hashlib
import json
import subprocess
import sys

sys.path.insert(0, r"D:\WeilanSkillEvolution\proposals\charter-daily-push-v0.1")
from scan_push_manifest import PATTERNS  # noqa: E402

BASE = "e72a2ef728bb22ca99bf3a07e25f6bc512e34cca"
HEAD = "702a91a562b904d289922f71795dae9cb0bb0344"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True,
                          check=True, cwd=r"D:\WeilanSkillEvolution").stdout


def scan(blob, where):
    out = []
    for name, rx in PATTERNS:
        for m in rx.finditer(blob):
            out.append({"where": where, "pattern": name,
                        "line": blob.count(b"\n", 0, m.start()) + 1,
                        "excerpt": m.group(0)[:60].decode("utf-8", "replace")})
    return out


commits = git("rev-list", "--reverse", f"{BASE}..{HEAD}").decode().split()
tree_diff_paths = sorted(set(
    git("diff", "--name-only", f"{BASE}..{HEAD}").decode().splitlines()))

union_paths, versions, findings = set(), [], []
for c in commits:
    touched = git("diff-tree", "-r", "--no-commit-id", "--name-only", c
                  ).decode().splitlines()
    union_paths.update(p for p in touched if p)
    msg = git("log", "-1", "--format=%B%n%an%n%ae", c)
    findings += scan(msg, f"commit-message:{c[:8]}")
    for p in sorted(set(touched)):
        if not p:
            continue
        try:
            blob = git("show", f"{c}:{p}")
        except subprocess.CalledProcessError:
            versions.append({"commit": c[:8], "path": p,
                             "status": "absent_at_this_commit"})
            continue
        versions.append({"commit": c[:8], "path": p, "bytes": len(blob),
                         "sha256": hashlib.sha256(blob).hexdigest()})
        findings += scan(blob, f"{c[:8]}:{p}")

print(json.dumps({
    "base": BASE, "head": HEAD, "commits": commits,
    "tree_diff_paths": tree_diff_paths,
    "per_commit_union_paths": sorted(union_paths),
    "union_equals_tree_diff": sorted(union_paths) == tree_diff_paths,
    "add_then_delete_inside_range": sorted(
        set(union_paths) - set(tree_diff_paths)),
    "blob_versions_published": versions,
    "secret_findings": findings,
    "clean": not findings,
}, ensure_ascii=False, indent=2))
sys.exit(0 if not findings else 1)
