# Read-only probe: what tree does the push-time redaction gate actually judge?
#
# scan_only_gate.py takes --tree = a FILESYSTEM directory and os.walk()s it,
# skipping only {.git, __pycache__, .pytest_cache}.  A push publishes a GIT
# TREE.  This probe measures both subjects with the same pattern list and the
# same decode rule, then reports the set difference.
#
# Never prints a pattern; only pattern_index, exactly like the gate.
#
# Usage: python _probe_20260730_gate_tree_subject.py --commit <rev> [--tree <dir>]
import argparse
import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
DEFAULT_PRIVATE = os.path.join(
    REPO, "proposals", "scaffold-opensource-export-v0.1",
    "redaction-private-strings.local.txt")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}


def decode_text(raw):
    """Same rule as scan_only_gate.decode_text."""
    for enc in ("utf-8", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def git_bytes(*args):
    """Run git and return raw stdout bytes (never text=True: GBK would corrupt)."""
    proc = subprocess.run(["git", "-C", REPO, *args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise SystemExit("git %s failed rc=%d: %s"
                         % (args[0], proc.returncode, proc.stderr[:400]))
    return proc.stdout


def scan_one(relative, raw, patterns, hits):
    for index, pattern in enumerate(patterns):
        count = relative.count(pattern)
        if count:
            hits.append({"path": relative, "pattern_index": index,
                         "count": count, "where": "path"})
    text = decode_text(raw)
    if text is None:
        return
    for index, pattern in enumerate(patterns):
        count = text.count(pattern)
        if count:
            hits.append({"path": relative, "pattern_index": index,
                         "count": count, "where": "content"})


def scan_git_tree(commit, patterns):
    """Scan the raw blob bytes of every path tracked at `commit`."""
    listing = git_bytes("ls-tree", "-r", "-z", "--format=%(objectname) %(path)",
                        commit)
    entries = []
    for record in listing.split(b"\x00"):
        if not record:
            continue
        oid, _, path = record.partition(b" ")
        entries.append((oid.decode("ascii"), path.decode("utf-8")))

    hits = []
    # Stream every blob through one `cat-file --batch` process.
    proc = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for oid, path in entries:
            proc.stdin.write((oid + "\n").encode("ascii"))
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            size = int(header[2])
            raw = proc.stdout.read(size)
            proc.stdout.read(1)  # trailing LF emitted by --batch
            scan_one(path, raw, patterns, hits)
    finally:
        proc.stdin.close()
        proc.wait()
    return len(entries), hits


def scan_filesystem(tree, patterns, private_abs):
    """Reimplementation of scan_only_gate's walk, for a same-rule comparison."""
    hits = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(tree):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if os.path.abspath(path) == private_abs:
                continue
            relative = os.path.relpath(path, tree).replace("\\", "/")
            scanned += 1
            longpath = path if path.startswith("\\\\?\\") else "\\\\?\\" + os.path.abspath(path)
            with open(longpath, "rb") as fh:
                raw = fh.read()
            scan_one(relative, raw, patterns, hits)
    return scanned, hits


def key(hit):
    return (hit["path"], hit["pattern_index"], hit["where"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", default=REPO)
    parser.add_argument("--private-strings", default=DEFAULT_PRIVATE)
    args = parser.parse_args()

    private_abs = os.path.abspath(args.private_strings)
    with open(private_abs, encoding="utf-8") as fh:
        patterns = [ln.strip() for ln in fh if ln.strip()]

    resolved = git_bytes("rev-parse", args.commit).decode("ascii").strip()
    tree_count, tree_hits = scan_git_tree(resolved, patterns)
    fs_count, fs_hits = scan_filesystem(os.path.abspath(args.tree), patterns,
                                        private_abs)

    tree_keys = {key(h) for h in tree_hits}
    fs_keys = {key(h) for h in fs_hits}

    def tracked_at(path):
        rc = subprocess.run(["git", "-C", REPO, "cat-file", "-e",
                             "%s:%s" % (resolved, path)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        return rc == 0

    fs_only = sorted(fs_keys - tree_keys)
    report = {
        "commit": resolved,
        "pattern_count": len(patterns),
        "git_tree": {
            "paths_scanned": tree_count,
            "hit_count": len(tree_hits),
            "hits": sorted(tree_hits, key=key),
            "verdict": "PASS" if not tree_hits else "FAIL",
        },
        "filesystem": {
            "files_scanned": fs_count,
            "hit_count": len(fs_hits),
            "verdict": "PASS" if not fs_hits else "FAIL",
        },
        "divergence": {
            "filesystem_only_count": len(fs_only),
            "git_tree_only_count": len(tree_keys - fs_keys),
            "git_tree_only": sorted(tree_keys - fs_keys),
            "filesystem_only_paths_tracked_at_commit": sorted(
                {p for p, _, _ in fs_only if tracked_at(p)}),
            "filesystem_only_sample": fs_only[:5],
        },
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
