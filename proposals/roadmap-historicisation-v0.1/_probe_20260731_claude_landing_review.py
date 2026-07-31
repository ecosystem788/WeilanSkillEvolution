#!/usr/bin/env python3
"""Read-only independent review of the ROADMAP historicisation v4 landing receipt.

Claims under test come from Codex's execution receipt (peer-chat.jsonl,
from=codex, time=2026-07-31T18:06:17+09:00) and its consent
(time=2026-07-31T18:01:25+09:00).

Everything here reads git objects and the working tree only; nothing is written
except this script's own .out.json companion (written by the caller, not here --
this script prints JSON to stdout).
"""
import hashlib
import json
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
LANDING = "5d2aea08f7aa132e1cd40cf052d94d30bb1de97d"
PARENT = "98efccc9f80fc8d2ad2337fcd35d2b1ae3089a92"

CLAIM = {
    "commit_paths": 6,
    "peer_chat_blob_oid": "264bc29f6c250cc84cb584b4884b286ce2193daf",
    "proposal_line": 3164,
    "proposal_record_sha256": "4b5d24f9f6788044b8457c6a235e8884364e27fb12dedc2591043a469d661b30",
    "consent_line": 3166,
    "consent_record_sha256": "45d4e4838d9dc9feda101f6994bb255f33c17fbd50f3461cfbb535f050faa1bc",
    "base_sha256": "3bd2a43f0b20e6dc5332de152a76862881e880ded2abc947ec5fdfea7957f717",
    "base_bytes": 11984,
    "final_sha256": "bd32917c74701e672187d3270b57ee9124e09238949609536d69048623ba5031",
    "final_bytes": 16879,
    "roadmap_blob_oid": "c226ac8ab18803bcbe8f3d3f5ddf7113d6b56219",
    "shape": {"additions": 14, "deletions": 1, "pre": 215, "post": 228, "lcs": 214},
    "allowed_sections": [
        "## SE-0.6 \u2014 Shadow competition, adoption, and rollback",
        "## Immediate next stage",
    ],
    "artifacts": {
        "ROADMAP.base.sidecar": "a6f6d01e284f13f560bec7ff8e93fab41f5ad574",
        "postcheck-receipt.json": "acf53ccda62d1eaae7fcdb2da807089021a4a5ea",
        "preflight-state.json": "3867de93025719dfd93536c3415a098a5a76c31f",
        "preflight-state.json.witness": "874e7bd02576846365cb34ad4bbf54a6fad74d5d",
    },
    "artifact_prefix": "proposals/roadmap-historicisation-v0.1/execution-wf-20260731-085718-011b52/",
    "witness_digest": "6375ce290a48f328fa2929d543f535d67d74ece9c78073ebab2828c63d84f085",
}


def git(*args, binary=False):
    out = subprocess.run(
        ["git", "-C", REPO] + list(args), capture_output=True, check=True
    ).stdout
    return out if binary else out.decode("utf-8", "replace")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def lcs_len(a, b):
    """Classic O(n*m) LCS length over line lists, two-row rolling."""
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(cur[j], prev[j + 1]))
        prev = cur
    return prev[-1]


def sections_touched(pre_lines, post_lines):
    """Conservative superset: every '## ' heading owning a changed line.

    Uses a plain LCS backtrace to mark which post-lines are additions and which
    pre-lines are deletions, then attributes each to its enclosing heading.
    """
    n, m = len(pre_lines), len(post_lines)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = (
                dp[i + 1][j + 1] + 1
                if pre_lines[i] == post_lines[j]
                else max(dp[i + 1][j], dp[i][j + 1])
            )
    i = j = 0
    added, deleted = [], []
    while i < n and j < m:
        if pre_lines[i] == post_lines[j]:
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            deleted.append(i)
            i += 1
        else:
            added.append(j)
            j += 1
    deleted.extend(range(i, n))
    added.extend(range(j, m))

    def owner(lines, idx):
        for k in range(idx, -1, -1):
            if lines[k].startswith("## "):
                return lines[k]
        return "<preamble>"

    touched = {owner(post_lines, k) for k in added}
    touched |= {owner(pre_lines, k) for k in deleted}
    return sorted(touched), len(added), len(deleted)


def main():
    r = {"landing": LANDING, "parent": PARENT, "checks": {}}

    def check(name, actual, expected):
        r["checks"][name] = {
            "ok": actual == expected,
            "actual": actual,
            "expected": expected,
        }

    # 1. commit path count and exact path set
    names = [
        l.split("\t", 1)[1]
        for l in git("show", "--name-status", "--format=", LANDING).splitlines()
        if "\t" in l
    ]
    check("commit_path_count", len(names), CLAIM["commit_paths"])
    r["commit_paths"] = sorted(names)

    # 2. peer-chat blob oid at landing + record hashes of the two signature rows
    pc_path = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
    pc_oid = git("rev-parse", f"{LANDING}:{pc_path}").strip()
    check("peer_chat_blob_oid", pc_oid, CLAIM["peer_chat_blob_oid"])
    pc_blob = git("cat-file", "blob", pc_oid, binary=True)
    # physical records: split keeping terminators, then strip exactly one trailing LF
    raw_lines = pc_blob.split(b"\n")
    if raw_lines and raw_lines[-1] == b"":
        raw_lines.pop()

    def record(idx1):  # 1-indexed blob line
        return raw_lines[idx1 - 1]

    for tag, ln, want in (
        ("proposal", CLAIM["proposal_line"], CLAIM["proposal_record_sha256"]),
        ("consent", CLAIM["consent_line"], CLAIM["consent_record_sha256"]),
    ):
        rec = record(ln)
        obj = json.loads(rec.decode("utf-8"))
        check(f"{tag}_record_sha256", sha256(rec), want)
        r["checks"][f"{tag}_identity"] = {
            "from": obj.get("from"),
            "time": obj.get("time"),
            "head": obj["text"].splitlines()[0][:60],
        }

    # 3. base / final bytes
    base = git("cat-file", "blob", f"{PARENT}:ROADMAP.md", binary=True)
    check("base_sha256", sha256(base), CLAIM["base_sha256"])
    check("base_bytes", len(base), CLAIM["base_bytes"])
    rm_oid = git("rev-parse", f"{LANDING}:ROADMAP.md").strip()
    check("roadmap_blob_oid", rm_oid, CLAIM["roadmap_blob_oid"])
    final = git("cat-file", "blob", rm_oid, binary=True)
    check("final_sha256", sha256(final), CLAIM["final_sha256"])
    check("final_bytes", len(final), CLAIM["final_bytes"])

    # working-tree ROADMAP must still equal the landed final (no drift since)
    with open(rf"{REPO}\ROADMAP.md", "rb") as fh:
        wt = fh.read()
    check("worktree_matches_final", sha256(wt), CLAIM["final_sha256"])

    # proposed-final artifact must be the same blob as the landed ROADMAP
    pf_oid = git(
        "rev-parse",
        f"{LANDING}:proposals/roadmap-historicisation-v0.1/ROADMAP.proposed-final.md",
    ).strip()
    check("proposed_final_same_blob", pf_oid, CLAIM["roadmap_blob_oid"])

    # 4. shape + section confinement, recomputed independently
    pre = base.decode("utf-8").split("\n")
    post = final.decode("utf-8").split("\n")
    if pre and pre[-1] == "":
        pre.pop()
    if post and post[-1] == "":
        post.pop()
    l = lcs_len(pre, post)
    check(
        "shape",
        {
            "pre": len(pre),
            "post": len(post),
            "lcs": l,
            "additions": len(post) - l,
            "deletions": len(pre) - l,
        },
        CLAIM["shape"],
    )
    touched, n_add, n_del = sections_touched(pre, post)
    check("sections_touched", touched, sorted(CLAIM["allowed_sections"]))
    r["checks"]["backtrace_counts"] = {"added": n_add, "deleted": n_del}

    # 5. archived artifacts: present under the claimed prefix at the claimed oids
    for name, oid in CLAIM["artifacts"].items():
        got = git("rev-parse", f"{LANDING}:{CLAIM['artifact_prefix']}{name}").strip()
        check(f"artifact:{name}", got, oid)

    # 6. postcheck-receipt self-consistency: its own claimed values vs ours
    pr = json.loads(
        git("cat-file", "blob", CLAIM["artifacts"]["postcheck-receipt.json"]).lstrip(
            "﻿"
        )
    )
    r["postcheck_receipt"] = pr

    # 7. no side effects claimed absent: the commit touches nothing outside
    #    ROADMAP.md, the ledger, and the artifact prefix
    stray = [
        p
        for p in names
        if p != "ROADMAP.md" and p != pc_path and not p.startswith(CLAIM["artifact_prefix"])
    ]
    check("no_stray_paths", stray, [])

    r["all_ok"] = all(v.get("ok", True) for v in r["checks"].values())
    json.dump(r, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
