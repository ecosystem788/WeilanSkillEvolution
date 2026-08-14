#!/usr/bin/env python3
# sync_mirror_check.py
#
# Machine-check the byte-equality invariant between the in-repo mirror
# (skill/solve-with-weilan/scripts/) and the live install point
# (default: D:/CodexData/skills/solve-with-weilan/scripts/).
#
# Per proposals/skill-sync-discipline-v0.1/CONVENTION.md §四.
#
# Exit code:
#   0 - ok:true (all mirrored files byte-equal AND no head_only AND no unexpected live_only)
#   1 - drift detected
#   2 - setup error (git not found, live root missing, etc.)
#
# Output: JSON to stdout. Always. No decorative prints.

import argparse
import hashlib
import json
import os
import subprocess
import sys


SUBTREE_DEFAULT = "skill/solve-with-weilan/scripts"
LIVE_ROOT_DEFAULT = "D:/CodexData/skills/solve-with-weilan/scripts"

# Path whitelist for live-only files that are not considered drift.
# Adding to this whitelist requires a dual-signed revision of CONVENTION.md §四.c,
# per the convention text itself.
LIVE_ONLY_WHITELIST = {
    "__pycache__",
    ".pytest_cache",
}
LIVE_ONLY_WHITELIST_SUFFIXES = (
    ".pyc",
    ".bak",
    ".tmp",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def git_head_bytes(repo_root, rel_path):
    """Read the bytes of <repo_root>/<rel_path> at HEAD as a raw blob.

    Returns bytes. Raises subprocess.CalledProcessError if the path is not
    tracked in HEAD.
    """
    proc = subprocess.run(
        ["git", "-C", repo_root, "show", f"HEAD:{rel_path}"],
        capture_output=True,
        check=True,
    )
    return proc.stdout


def git_head_list_tracked(repo_root, subtree):
    """List the set of paths under <subtree> tracked at HEAD."""
    proc = subprocess.run(
        ["git", "-C", repo_root, "ls-tree", "-r", "--name-only", "HEAD", subtree],
        capture_output=True,
        check=True,
        text=True,
    )
    return set(line.strip() for line in proc.stdout.splitlines() if line.strip())


def list_live_files(live_root, subtree):
    """Map subpath -> live full path under live_root that mirrors the subtree path.

    The subtree path (e.g. 'skill/solve-with-weilan/scripts') is mapped to
    the basename only under live_root (e.g. '<live_root>/weilan_trace.py').
    Returns dict {basename: live_full_path}.
    """
    if not os.path.isdir(live_root):
        raise FileNotFoundError(f"live root not found: {live_root}")
    files = {}
    for name in os.listdir(live_root):
        full = os.path.join(live_root, name)
        if os.path.isfile(full):
            files[name] = full
    return files


def classify_live_only(basename):
    """Return (whitelisted: bool, reason: str)."""
    if basename in LIVE_ONLY_WHITELIST:
        return True, "whitelist_exact"
    for suffix in LIVE_ONLY_WHITELIST_SUFFIXES:
        if basename.endswith(suffix):
            return True, f"whitelist_suffix:{suffix}"
    return False, "not_whitelisted"


def check(repo_root, live_root, subtree):
    head_tracked_relpaths = git_head_list_tracked(repo_root, subtree)
    head_basenames = set(os.path.basename(p) for p in head_tracked_relpaths)
    live_files = list_live_files(live_root, subtree)
    live_basenames = set(live_files.keys())

    matches = []
    mismatches = []
    details = []

    for relpath in sorted(head_tracked_relpaths):
        basename = os.path.basename(relpath)
        if basename not in live_files:
            continue  # recorded as head_only below
        try:
            head_bytes = git_head_bytes(repo_root, relpath)
            head_sha = sha256_bytes(head_bytes)
        except subprocess.CalledProcessError as e:
            return {
                "ok": False,
                "setup_error": True,
                "reason": f"git show failed for {relpath}: {e.stderr.decode(errors='replace').strip()}",
                "subtree": subtree,
            }
        try:
            live_sha = file_sha256(live_files[basename])
        except OSError as e:
            return {
                "ok": False,
                "setup_error": True,
                "reason": f"read live file failed for {live_files[basename]}: {e}",
                "subtree": subtree,
            }
        equal = (head_sha == live_sha)
        entry = {
            "path": basename,
            "head_sha256": head_sha,
            "live_sha256": live_sha,
            "equal": equal,
        }
        details.append(entry)
        if equal:
            matches.append(basename)
        else:
            mismatches.append(basename)

    head_only = sorted(head_basenames - live_basenames)
    live_only = sorted(live_basenames - head_basenames)
    live_only_whitelisted = []
    live_only_unexpected = []
    for basename in live_only:
        whitelisted, reason = classify_live_only(basename)
        if whitelisted:
            live_only_whitelisted.append({"path": basename, "reason": reason})
        else:
            live_only_unexpected.append(basename)

    ok = (
        len(mismatches) == 0
        and len(head_only) == 0
        and len(live_only_unexpected) == 0
    )

    return {
        "ok": ok,
        "setup_error": False,
        "subtree": subtree,
        "scanned": len(matches) + len(mismatches),
        "matches": sorted(matches),
        "mismatches": sorted(mismatches),
        "head_only": head_only,
        "live_only_whitelisted": live_only_whitelisted,
        "live_only_unexpected": live_only_unexpected,
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Byte-equality check: in-repo mirror vs live install (per skill-sync-discipline-v0.1)."
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Path to the repo root (default: cwd).",
    )
    parser.add_argument(
        "--live-root",
        default=LIVE_ROOT_DEFAULT,
        help=f"Path to the live install scripts dir (default: {LIVE_ROOT_DEFAULT}).",
    )
    parser.add_argument(
        "--subtree",
        default=SUBTREE_DEFAULT,
        help=f"In-repo subtree to check (default: {SUBTREE_DEFAULT}).",
    )
    args = parser.parse_args()

    try:
        result = check(args.repo_root, args.live_root, args.subtree)
    except FileNotFoundError as e:
        json.dump({"ok": False, "setup_error": True, "reason": str(e)}, sys.stdout)
        sys.stdout.write("\n")
        return 2
    except subprocess.CalledProcessError as e:
        json.dump(
            {
                "ok": False,
                "setup_error": True,
                "reason": f"git command failed: {e.stderr.decode(errors='replace').strip() if e.stderr else str(e)}",
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 2

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
