"""Read-only: prove the frozen candidate differs from the frozen baseline in
exactly the paths the proposal declares. Emits JSON to stdout."""

import hashlib
import json
import os
import sys

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {".pytest_cache", "__pycache__"}


def tree(root):
    out = {}
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in files:
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as handle:
                out[rel] = hashlib.sha256(handle.read()).hexdigest()
    return out


def main():
    base_root = os.path.join(HERE, "artifacts", BASE, "solve-with-weilan")
    cand_root = os.path.join(HERE, "artifacts", CAND, "solve-with-weilan")
    base, cand = tree(base_root), tree(cand_root)
    changed, added, removed = [], [], []
    for key in sorted(set(base) | set(cand)):
        if key not in cand:
            removed.append(key)
        elif key not in base:
            added.append({"path": key, "candidate_sha256": cand[key]})
        elif base[key] != cand[key]:
            changed.append(
                {"path": key, "base_sha256": base[key], "candidate_sha256": cand[key]}
            )
    result = {
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "base_file_count": len(base),
        "candidate_file_count": len(cand),
        "changed": changed,
        "added": added,
        "removed": removed,
        "changed_path_count": len(changed) + len(added) + len(removed),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
