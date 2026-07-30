"""Read-only probe: does the six-field anchor identity of the two known-public
occurrences drift between commits?

Nothing is written to the repository and no remote is contacted.  Only
``git cat-file`` reads are issued.  The probe never prints a pattern and never
prints record bytes; it prints hashes and byte counts only.
"""

import hashlib
import json
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
TARGETS = [
    ("proposals/bounded-scheduler-v0.1/impl/codex-inbox.jsonl", 66),
    ("proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl", 1008),
]
# Sampled points in history: today's head, the landing commit of the gate, and
# three older anchors spanning several days.
COMMITS = [
    "HEAD",
    "8ef57756a7c5a31e0c73385e4dca02e08a6bcbeb",
    "HEAD~10",
    "HEAD~40",
    "HEAD~120",
]


def git(*args):
    proc = subprocess.run(["git", "-C", REPO, *args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip())
    return proc.stdout


def record_at(commit, path, line_number):
    blob = git("cat-file", "blob", f"{commit}:{path}")
    records = blob.split(b"\n")
    if line_number > len(records):
        return None
    record = records[line_number - 1]
    return {
        "blob_oid": git("rev-parse", f"{commit}:{path}").strip().decode("ascii"),
        "blob_bytes": len(blob),
        "total_records": len(records),
        "record_bytes": len(record),
        "has_stored_cr": record.endswith(b"\r"),
        "line_hash": hashlib.sha256(record).hexdigest(),
    }


def main():
    result = {"repo": REPO, "targets": [], "identity_stable": True}
    for path, line_number in TARGETS:
        per_commit = {}
        hashes = set()
        for commit in COMMITS:
            try:
                resolved = git("rev-parse", "--verify",
                               f"{commit}^{{commit}}").strip().decode("ascii")
            except RuntimeError as exc:
                per_commit[commit] = {"error": str(exc)}
                continue
            try:
                observed = record_at(commit, path, line_number)
            except RuntimeError as exc:
                per_commit[commit] = {"resolved": resolved, "error": str(exc)}
                continue
            per_commit[commit] = {"resolved": resolved, **(observed or {})}
            if observed:
                hashes.add(observed["line_hash"])
        stable = len(hashes) == 1
        if not stable:
            result["identity_stable"] = False
        result["targets"].append({
            "path": path,
            "line_number": line_number,
            "distinct_line_hashes": sorted(hashes),
            "stable_across_sampled_commits": stable,
            "per_commit": per_commit,
        })
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
