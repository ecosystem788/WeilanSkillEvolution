#!/usr/bin/env python3
"""Probe: are file-kind source refs cited by the wake read-path actually in git?

A source ref that exists only in this machine's working tree is defined for one
worktree only: a clean clone cannot open it. Read contracts that point at such a
file promise a reader something the repo cannot deliver.

Read-only. Enumerates file-shaped refs out of a captured wake_brief JSON and asks
git whether each is tracked at HEAD.
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(r"D:\WeilanSkillEvolution")


def norm(ref: str):
    """Return a repo-relative posix path, or None if ref is not a file path."""
    if ref.startswith(("frame:", "memory:", "command:", "goal:")):
        return None
    p = pathlib.Path(ref.replace("\\", "/"))
    try:
        rel = p.relative_to(REPO) if p.is_absolute() else p
    except ValueError:
        return None
    return rel.as_posix()


def tracked(rel: str) -> bool:
    rc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode
    return rc == 0


def main(brief_path: str) -> int:
    brief = json.loads(pathlib.Path(brief_path).read_text(encoding="utf-8-sig"))
    seen, rows = set(), []
    for src in brief.get("sources", []):
        ref = src.get("ref", "")
        rel = norm(ref)
        if rel is None or rel in seen:
            continue
        seen.add(rel)
        rows.append({
            "kind": src.get("kind"),
            "ref": ref,
            "rel": rel,
            "tracked": tracked(rel),
            "on_disk": (REPO / rel).exists(),
        })

    missing = [r for r in rows if not r["tracked"]]
    out = {
        "probe": "source_ref_trackedness",
        "brief": brief_path,
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                               capture_output=True, text=True).stdout.strip(),
        "file_refs_distinct": len(rows),
        "untracked_count": len(missing),
        "untracked": [
            {"kind": r["kind"], "rel": r["rel"], "on_disk": r["on_disk"]}
            for r in missing
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
