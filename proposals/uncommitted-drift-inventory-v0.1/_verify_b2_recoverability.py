"""Independent, read-only re-check of the B2 recoverability claim (peer-chat 2650 vs 2651).

Deliberately does NOT use tools/evolution_core.tree_hash: that hasher skips
__pycache__/.pyc (and, in the uncommitted working-tree version, .pytest_cache),
so tree_hash equality cannot by itself carry a "byte-for-byte recoverable" claim.
This walks every file on disk and compares raw bytes, then asks the git object
database (not the index) whether each blob exists anywhere reachable from refs.

authority: none. Read-only. Re-runnable.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750"
CAPTURE = REPO / "proposals/capture-contract-source-authenticity-v0.1/candidate"
TRACKED = REPO / "proposals/projection-recall-staleness-v0.1/candidate"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_hash(p):
    h = hashlib.sha1()
    data = p.read_bytes()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def walk(root):
    """Every regular file under root, no exclusions at all."""
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def run(args):
    return subprocess.run(
        args, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def reachable_blobs():
    """Blob ids reachable from all refs (history), excluding the index/worktree."""
    proc = run(["git", "rev-list", "--all", "--objects"])
    ids = set()
    for line in proc.stdout.splitlines():
        if line:
            ids.add(line.split(" ", 1)[0])
    return ids


def compare(a_root, b_root):
    a, b = walk(a_root), walk(b_root)
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    differing = sorted(k for k in set(a) & set(b) if sha256_file(a[k]) != sha256_file(b[k]))
    return {
        "a_files": len(a),
        "b_files": len(b),
        "only_in_a": only_a,
        "only_in_b": only_b,
        "same_path_differing_bytes": differing,
        "byte_identical": not (only_a or only_b or differing),
    }


def find_roots(parent, name_hint="solve-with-weilan"):
    hits = [p for p in parent.rglob(name_hint) if p.is_dir()] if parent.exists() else []
    return hits


def main():
    out = {"repo": str(REPO), "head": run(["git", "rev-parse", "HEAD"]).stdout.strip()}

    frozen_skill = find_roots(FROZEN)
    tracked_skill = find_roots(TRACKED)
    capture_skill = find_roots(CAPTURE)
    out["roots"] = {
        "frozen": [str(p) for p in frozen_skill],
        "tracked_candidate": [str(p) for p in tracked_skill],
        "capture_candidate": [str(p) for p in capture_skill],
    }
    if not (frozen_skill and tracked_skill and capture_skill):
        out["error"] = "missing one of the three roots"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    # Claim under test #1 (Codex 2651): the 48 frozen files are byte-recoverable
    # from the tracked sibling candidate tree.
    out["frozen_vs_tracked_candidate"] = compare(frozen_skill[0], tracked_skill[0])

    # git-tracked status of the tracked candidate tree, per git itself.
    ls = run(["git", "ls-files", "--", str(tracked_skill[0].relative_to(REPO).as_posix())])
    st = run(["git", "status", "--porcelain", "--", str(tracked_skill[0].relative_to(REPO).as_posix())])
    out["tracked_candidate_git"] = {
        "tracked_files": len([l for l in ls.stdout.splitlines() if l]),
        "dirty_entries": [l for l in st.stdout.splitlines() if l],
    }

    # Claim under test #2 (Claude 2650, narrowed by Codex): the capture-contract
    # candidate has no git copy. Test against the object DB, not just paths.
    reach = reachable_blobs()
    cap_files = walk(capture_skill[0])
    present, absent = [], []
    for rel, p in cap_files.items():
        (present if git_blob_hash(p) in reach else absent).append(rel)
    out["capture_candidate_vs_git_objects"] = {
        "files": len(cap_files),
        "blobs_reachable_from_refs": len(present),
        "blobs_absent_from_history": len(absent),
        "sample_absent": sorted(absent)[:5],
        "reachable_paths": sorted(present),
    }

    # Cross-check: does the capture candidate happen to match the frozen/tracked tree?
    out["capture_vs_frozen"] = compare(capture_skill[0], frozen_skill[0])

    # Files the evolution_core hasher would have skipped (so tree_hash equality
    # would not have covered them) — quantifies the gap in the hash-only argument.
    def hidden(root):
        return sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file()
            and ("__pycache__" in p.parts or ".pytest_cache" in p.parts or p.suffix == ".pyc")
        )

    out["hasher_blind_spot"] = {
        "frozen": hidden(frozen_skill[0]),
        "tracked_candidate": hidden(tracked_skill[0]),
        "capture_candidate": hidden(capture_skill[0]),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
