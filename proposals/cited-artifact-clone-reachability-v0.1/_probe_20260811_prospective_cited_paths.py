#!/usr/bin/env python3
"""Probe: which repo paths cited by the scoped prospective ledger are not in git?

Usage:
    python _probe_20260811_prospective_cited_paths.py <prospective-show.json>

Produce the input with (redirect to a file -- do NOT pipe, PS 5.1 adds a BOM):
    python .../weilan_trace.py prospective-show \
        --workspace "D:\\WeilanSkillEvolution" --scope skill-evolution > out.json

Read-only. Note the ledger itself lives outside the repo ($CODEX_HOME/method-state),
so a clean clone can rerun this script but must supply its own ledger dump.

Scope limits are documented in FINDING.md section 5 -- in particular the extension
whitelist means the reported count is a LOWER BOUND, not the full set.
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(r"D:\WeilanSkillEvolution")

# jsonl must precede json, else ".out.json" truncates to a path that never existed.
PAT = re.compile(
    r'(?:D:\\\\WeilanSkillEvolution\\\\|D:/WeilanSkillEvolution/)?'
    r'(proposals[/\\\\][^"\s,;:()（）、：]+?\.(?:md|py|jsonl|json|txt))'
)


def tracked(rel: str) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def commit_count(rel: str) -> int:
    out = subprocess.run(
        ["git", "log", "--oneline", "--all", "--", rel],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    return len([ln for ln in out.splitlines() if ln.strip()])


def main(dump_path: str) -> int:
    blob = json.dumps(
        json.loads(pathlib.Path(dump_path).read_text(encoding="utf-8-sig")),
        ensure_ascii=False,
    )
    cited = sorted({
        m.group(1).replace("\\\\", "/").replace("\\", "/")
        for m in PAT.finditer(blob)
    })

    ignored = set()
    if cited:
        r = subprocess.run(["git", "check-ignore", "--"] + cited,
                           cwd=REPO, capture_output=True, text=True)
        ignored = {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}

    never = [
        {
            "rel": rel,
            "on_disk": (REPO / rel).exists(),
            "commits": commit_count(rel),
        }
        for rel in cited
        if rel not in ignored and not tracked(rel)
    ]

    print(json.dumps({
        "probe": "prospective_cited_path_trackedness",
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                               capture_output=True, text=True).stdout.strip(),
        "cited_distinct": len(cited),
        "ignored_by_design": len(ignored),
        "not_in_git": len(never),
        "detail": never,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
