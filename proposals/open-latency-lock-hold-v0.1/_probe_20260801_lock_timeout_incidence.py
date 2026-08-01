"""Read-only census: how often did a real wake actually hit the lineage lock?

Byte-level search so UTF-16-LE run logs are not silently skipped (the failure
mode named in proposals/redaction-gate-tree-subject-v0.1: undecodable/other-
encoding blobs get zero hits and the zero is read as zero input).

Every token is searched as utf-8 AND utf-16-le bytes over the raw file bytes.
No decoding, no writes.

Usage:  python _probe_20260801_lock_timeout_incidence.py
Output: JSON on stdout.
"""
import json
import os
import sys

ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"

TOKENS = {
    "lock_timeout_message": "lock timeout on",
    "lock_timeout_cause": "another weilan session holds it",
    "lineage_lock_name": ".lineage.lock",
    # control token: something that certainly occurs, to prove the byte search
    # actually reaches the content of each corpus rather than returning 0 for
    # structural reasons.
    "control_frame_open": "frame",
}

CORPORA = [
    ("wake-codex-runs", os.path.join(ROOT, "wake-codex-runs")),
    ("wake-agent-runs", os.path.join(ROOT, "wake-agent-runs")),
]

SINGLE_FILES = [
    ("wake-cron.log", os.path.join(ROOT, "wake-cron.log")),
    ("wake-codex.log", os.path.join(ROOT, "wake-codex.log")),
    ("wake-agent.log", os.path.join(ROOT, "wake-agent.log")),
]


def encoded_variants(token):
    return {
        "utf8": token.encode("utf-8"),
        "utf16le": token.encode("utf-16-le"),
    }


VARIANTS = {name: encoded_variants(tok) for name, tok in TOKENS.items()}


def scan_bytes(blob):
    """Return {token_name: {encoding: count}} for one blob of raw bytes."""
    out = {}
    for name, variants in VARIANTS.items():
        out[name] = {enc: blob.count(pat) for enc, pat in variants.items()}
    return out


def merge(acc, one, path, hit_paths):
    for name, per_enc in one.items():
        for enc, n in per_enc.items():
            if n:
                acc[name][enc] += n
                if name != "control_frame_open":
                    hit_paths.setdefault(name, []).append(
                        {"path": path, "encoding": enc, "count": n}
                    )


def blank_acc():
    return {name: {"utf8": 0, "utf16le": 0} for name in TOKENS}


def census():
    report = {"root": ROOT, "corpora": [], "single_files": []}

    for label, directory in CORPORA:
        acc = blank_acc()
        hit_paths = {}
        files = 0
        total_bytes = 0
        unreadable = []
        if os.path.isdir(directory):
            for entry in sorted(os.listdir(directory)):
                path = os.path.join(directory, entry)
                if not os.path.isfile(path):
                    continue
                files += 1
                try:
                    with open(path, "rb") as handle:
                        blob = handle.read()
                except OSError as exc:
                    unreadable.append({"path": path, "error": str(exc)})
                    continue
                total_bytes += len(blob)
                merge(acc, scan_bytes(blob), path, hit_paths)
        report["corpora"].append(
            {
                "label": label,
                "directory": directory,
                "exists": os.path.isdir(directory),
                "files_scanned": files,
                "bytes_scanned": total_bytes,
                "unreadable": unreadable,
                "token_counts": acc,
                "hit_paths": hit_paths,
            }
        )

    for label, path in SINGLE_FILES:
        acc = blank_acc()
        hit_paths = {}
        exists = os.path.isfile(path)
        size = 0
        if exists:
            with open(path, "rb") as handle:
                blob = handle.read()
            size = len(blob)
            merge(acc, scan_bytes(blob), path, hit_paths)
        report["single_files"].append(
            {
                "label": label,
                "path": path,
                "exists": exists,
                "bytes_scanned": size,
                "token_counts": acc,
                "hit_paths": hit_paths,
            }
        )

    return report


if __name__ == "__main__":
    json.dump(census(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
