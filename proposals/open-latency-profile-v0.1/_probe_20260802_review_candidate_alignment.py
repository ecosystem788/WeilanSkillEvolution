"""Read-only review probe: does the candidate tree match the deployed baseline?

Acceptance criterion (1) of codex-inbox 3c7e91b4ad02: the per-file diff between
the candidate tree and the deployment baseline must be exactly one hunk in
scripts/weilan_trace.py. This probe re-derives that independently of the
delegate's own report: it walks both trees, hashes every file, and prints the
unified diff of any file whose bytes differ.
"""
import difflib
import hashlib
import json
import os
import sys

CAND = r"D:\WeilanSkillEvolution\proposals\open-latency-profile-v0.1\candidate\solve-with-weilan"
LIVE = r"D:\CodexData\skills\solve-with-weilan"


def walk(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as handle:
                out[rel] = hashlib.sha256(handle.read()).hexdigest()
    return out


def read_lines(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.readlines()


def main():
    cand = walk(CAND)
    live = walk(LIVE)
    only_cand = sorted(set(cand) - set(live))
    only_live = sorted(set(live) - set(cand))
    differing = sorted(k for k in (set(cand) & set(live)) if cand[k] != live[k])

    hunks = {}
    for rel in differing:
        diff = list(
            difflib.unified_diff(
                read_lines(os.path.join(LIVE, rel.replace("/", os.sep))),
                read_lines(os.path.join(CAND, rel.replace("/", os.sep))),
                fromfile="live/" + rel,
                tofile="candidate/" + rel,
                n=3,
            )
        )
        hunks[rel] = {
            "hunk_count": sum(1 for line in diff if line.startswith("@@")),
            "added": sum(1 for line in diff if line.startswith("+") and not line.startswith("+++")),
            "removed": sum(1 for line in diff if line.startswith("-") and not line.startswith("---")),
            "diff": "".join(diff),
        }

    report = {
        "candidate_root": CAND,
        "live_root": LIVE,
        "candidate_file_count": len(cand),
        "live_file_count": len(live),
        "only_in_candidate": only_cand,
        "only_in_live": only_live,
        "differing_files": differing,
        "hunks": hunks,
        "criterion_1_met": (
            not only_cand
            and not only_live
            and differing == ["scripts/weilan_trace.py"]
            and hunks.get("scripts/weilan_trace.py", {}).get("hunk_count") == 1
        ),
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
