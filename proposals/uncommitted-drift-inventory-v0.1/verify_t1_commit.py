#!/usr/bin/env python3
"""Independently verify the post-execution claim about commit 8d2f2cb.

Claude-side review instrument for the T1 payload double-sign
(proposal 2026-07-28T14:49:54+09:00 / cosign 2026-07-28T15:02:12+09:00 /
execution receipt 2026-07-28T15:04:09+09:00).

This does NOT reuse t1_payload.py or trust its output. It reads the frozen
signed object T1_COMMIT_PAYLOAD.tsv byte-for-byte and asks git directly what
the commit actually contains.

Read-only: no git add, no index writes, no checkout.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "proposals/uncommitted-drift-inventory-v0.1/T1_COMMIT_PAYLOAD.tsv"

CLAIMED_FROZEN_SHA = "e6afe2ef014e634570eb7d07c14959d349e3dcd08cbbffa4d7bc00d09cb08df8"
CLAIMED_COMMIT = "8d2f2cb6329c35386e4c0132f5cb9569d629bb3e"
CLAIMED_BASE = "242fd219c628533a12d111113d7e0ca72edbb053"
CLAIMED_PAYLOAD_TOTAL = 478396


def git(*args, binary=False):
    r = subprocess.run(
        ["git", "-C", str(REPO), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return r.stdout if binary else r.stdout.decode("utf-8")


def main():
    out = {"checks": [], "mismatches": []}

    def check(name, ok, detail):
        out["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            out["mismatches"].append(name)

    # 1. the signed object itself must still be the bytes that were signed
    raw = FROZEN.read_bytes()
    frozen_sha = hashlib.sha256(raw).hexdigest()
    check("frozen_object_sha256", frozen_sha == CLAIMED_FROZEN_SHA,
          {"actual": frozen_sha, "claimed": CLAIMED_FROZEN_SHA, "bytes": len(raw)})
    check("frozen_object_shape",
          len(raw) == 8001 and raw.count(b"\n") == 44 and b"\r" not in raw
          and not raw.endswith(b"\n"),
          {"bytes": len(raw), "lf": raw.count(b"\n"), "cr": raw.count(b"\r"),
           "trailing_lf": raw.endswith(b"\n")})

    rows = []
    for line in raw.decode("utf-8").split("\n"):
        parts = line.split("\t")
        if len(parts) != 4:
            check("frozen_row_shape", False, {"line": line})
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 1
        rows.append({"path": parts[0], "oid": parts[1],
                     "size": int(parts[2]), "sha256": parts[3]})
    check("frozen_row_count", len(rows) == 45, {"rows": len(rows)})
    check("frozen_sorted_unique",
          [r["path"] for r in rows] == sorted({r["path"] for r in rows}),
          {"unique": len({r["path"] for r in rows})})

    # 2. the commit graph shape claimed by the executor
    head = git("rev-parse", "HEAD").strip()
    check("head_is_claimed_commit", head == CLAIMED_COMMIT,
          {"actual": head, "claimed": CLAIMED_COMMIT})
    parents = git("rev-list", "--parents", "-n", "1", CLAIMED_COMMIT).split()
    check("parent_is_claimed_base", parents[1:] == [CLAIMED_BASE],
          {"actual": parents[1:], "claimed": [CLAIMED_BASE]})

    # 3. the commit must add exactly the 45 signed paths and nothing else
    ns = git("diff-tree", "--no-commit-id", "-r", "-z", "--name-status",
             CLAIMED_BASE, CLAIMED_COMMIT)
    fields = [f for f in ns.split("\0") if f]
    changed = [(fields[i], fields[i + 1]) for i in range(0, len(fields), 2)]
    check("commit_changes_45_paths", len(changed) == 45, {"count": len(changed)})
    check("all_changes_are_adds",
          all(st == "A" for st, _ in changed),
          {"statuses": sorted({st for st, _ in changed})})
    check("changed_paths_equal_frozen_paths",
          sorted(p for _, p in changed) == sorted(r["path"] for r in rows),
          {"only_in_commit": sorted(set(p for _, p in changed)
                                    - set(r["path"] for r in rows)),
           "only_in_frozen": sorted(set(r["path"] for r in rows)
                                    - set(p for _, p in changed))})

    # 4. every blob in the commit tree must be the signed payload, byte for byte
    tree = {}
    for entry in git("ls-tree", "-r", "-z", CLAIMED_COMMIT).split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        _mode, _type, oid = meta.split()
        tree[path] = oid

    bad_oid, bad_bytes, total = [], [], 0
    for r in rows:
        oid = tree.get(r["path"])
        if oid != r["oid"]:
            bad_oid.append({"path": r["path"], "in_tree": oid,
                            "signed": r["oid"]})
            continue
        blob = git("cat-file", "blob", oid, binary=True)
        total += len(blob)
        actual = hashlib.sha256(blob).hexdigest()
        if len(blob) != r["size"] or actual != r["sha256"]:
            bad_bytes.append({"path": r["path"], "size": len(blob),
                              "signed_size": r["size"], "sha256": actual,
                              "signed_sha256": r["sha256"]})
    check("tree_blob_oids_match_signature", not bad_oid,
          {"mismatched": bad_oid})
    check("blob_payload_bytes_match_signature", not bad_bytes,
          {"mismatched": bad_bytes})
    check("payload_total_bytes", total == CLAIMED_PAYLOAD_TOTAL,
          {"actual": total, "claimed": CLAIMED_PAYLOAD_TOTAL})

    # 5. nothing was smuggled in: the commit tree must differ from base only here
    base_tree = set(
        e.split("\t", 1)[1]
        for e in git("ls-tree", "-r", "-z", CLAIMED_BASE).split("\0") if e
    )
    added = set(tree) - base_tree
    check("no_extra_new_paths", added == {r["path"] for r in rows},
          {"unexpected": sorted(added - {r["path"] for r in rows})})
    removed = base_tree - set(tree)
    check("no_paths_removed", not removed, {"removed": sorted(removed)})

    # 6. postcheck the executor claimed: real index empty, those 45 paths clean
    staged = [l for l in git("diff", "--cached", "--name-only").split("\n") if l]
    check("real_index_empty", not staged, {"staged": staged})
    st = git("status", "--porcelain", "-z", "--", *[r["path"] for r in rows])
    check("signed_paths_clean_in_worktree",
          not [f for f in st.split("\0") if f],
          {"dirty": [f for f in st.split("\0") if f]})

    # 7. explicitly-excluded artifacts must still be out of history
    excluded = ["proposals/uncommitted-drift-inventory-v0.1/t1_scope.py",
                "proposals/uncommitted-drift-inventory-v0.1/t1_payload.py",
                "proposals/uncommitted-drift-inventory-v0.1/T1_COMMIT_SCOPE.tsv",
                "proposals/uncommitted-drift-inventory-v0.1/T1_COMMIT_PAYLOAD.tsv"]
    leaked = [p for p in excluded if p in tree]
    check("excluded_helpers_not_committed", not leaked, {"leaked": leaked})

    # 8. commit ≠ push: confirm the executor did not push
    try:
        remotes = [l for l in git("branch", "-r", "--contains",
                                  CLAIMED_COMMIT).split("\n") if l.strip()]
    except subprocess.CalledProcessError:
        remotes = []
    check("commit_not_on_any_remote_branch", not remotes,
          {"remote_branches": remotes})

    out["verdict"] = "CONFIRMED" if not out["mismatches"] else "MISMATCH"
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not out["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
