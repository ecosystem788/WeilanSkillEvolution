# Read-only pre-push gate (push 前脱敏门 v3, peer-chat 2026-07-14).
# Scans an exact to-be-pushed tree for private strings in BOTH relative paths
# and decodable (utf-8/utf-16) content — same semantics as
# memory-opensource-export-v0.1/build_snapshot.scan_private_strings, which
# closes the rg -F -f gap: rg only scans content, never filenames.
# This tool NEVER modifies the tree and NEVER prints a pattern (only
# pattern_index), so its output is safe to land in committed run logs.
# Exit codes: 0 = zero hits (push may proceed), 2 = hits (stop, build a
# bounded correction candidate instead), 1 = crash/usage error.
import argparse
import json
import os
import sys

DEFAULT_PRIVATE = os.path.join(
    r"D:\WeilanSkillEvolution", "proposals", "scaffold-opensource-export-v0.1",
    "redaction-private-strings.local.txt")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}


def longpath(path):
    return path if path.startswith("\\\\?\\") else "\\\\?\\" + os.path.abspath(path)


def decode_text(raw):
    for enc in ("utf-8", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="read-only private-string scan of an exact tree")
    parser.add_argument("--tree", required=True, help="root of the exact to-be-pushed tree")
    parser.add_argument("--private-strings", default=DEFAULT_PRIVATE)
    args = parser.parse_args()

    tree = os.path.abspath(args.tree)
    if not os.path.isdir(tree):
        print(json.dumps({"error": "tree is not a directory", "tree": tree}), file=sys.stderr)
        return 1
    private_abs = os.path.abspath(args.private_strings)
    with open(private_abs, encoding="utf-8") as fh:
        patterns = [ln.strip() for ln in fh if ln.strip()]
    if not patterns:
        print(json.dumps({"error": "private strings file is empty"}), file=sys.stderr)
        return 1

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
            for index, pattern in enumerate(patterns):
                count = relative.count(pattern)
                if count:
                    hits.append({"path": relative, "pattern_index": index,
                                 "count": count, "where": "path"})
            with open(longpath(path), "rb") as fh:
                raw = fh.read()
            text = decode_text(raw)
            if text is None:
                continue
            for index, pattern in enumerate(patterns):
                count = text.count(pattern)
                if count:
                    hits.append({"path": relative, "pattern_index": index,
                                 "count": count, "where": "content"})

    verdict = "PASS" if not hits else "FAIL"
    json.dump({"tree": tree, "files_scanned": scanned, "pattern_count": len(patterns),
               "hit_count": len(hits), "hits": hits, "verdict": verdict},
              sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if not hits else 2


if __name__ == "__main__":
    sys.exit(main())
