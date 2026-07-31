"""Read-only: Claude's INDEPENDENT structural check of the revised candidate.

Answers four questions the reviewer should not take on the implementer's word:
  Q1 does the revised frozen tree fb16689a... differ from the frozen baseline in
     exactly the two paths proposal.json declares?
  Q2 is the frozen tree a byte-for-byte copy of the in-repo candidate/ directory
     (i.e. is what a third party can read the thing that was measured)?
  Q3 does the frozen tree's own content address recompute to fb16689a...?
  Q4 do the .out.json probe artifacts sitting in this directory describe the
     candidate the proposal now points at, or a superseded one?

Q3 uses the same content-addressing the freeze tool uses, recomputed here rather
than re-invoking the tool, so the check is independent of the tool's own claim.
Writes nothing outside its own stdout.
"""

import hashlib
import json
import os
import sys

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
OLD_CAND = "794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b"
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


def content_address(root):
    """Reimplementation of tools/evolution_core.tree_hash: sha256 over the
    canonical JSON of [{path, size, sha256}] for every non-pyc, non-cache file,
    sorted by full path. Written out here rather than imported so the check does
    not rest on the same code that produced the address.

    The sort key is the *absolute* path, case-folded. The original sorts
    pathlib.Path objects, and on Windows PurePath ordering compares a lowercased
    string form -- so a plain case-sensitive sort produces a different address.
    Measured, not assumed: the case-sensitive variant reproduces neither the
    baseline's long-frozen address nor the candidate's, and the case-folded one
    reproduces both.
    """
    root = os.path.abspath(root)
    rows = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in files:
            if name.endswith(".pyc"):
                continue
            path = os.path.join(current, name)
            with open(path, "rb") as handle:
                body = handle.read()
            rows.append((path.lower(), {
                "path": os.path.relpath(path, root).replace(os.sep, "/"),
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }))
    rows.sort(key=lambda row: row[0])
    canonical = json.dumps([row[1] for row in rows], ensure_ascii=False,
                           sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main():
    base_root = os.path.join(HERE, "artifacts", BASE, "solve-with-weilan")
    cand_root = os.path.join(HERE, "artifacts", CAND, "solve-with-weilan")
    live_root = os.path.join(HERE, "candidate", "solve-with-weilan")
    base, cand, live = tree(base_root), tree(cand_root), tree(live_root)

    changed, added, removed = [], [], []
    for key in sorted(set(base) | set(cand)):
        if key not in cand:
            removed.append(key)
        elif key not in base:
            added.append({"path": key, "candidate_sha256": cand[key]})
        elif base[key] != cand[key]:
            changed.append({"path": key, "base_sha256": base[key],
                            "candidate_sha256": cand[key]})

    frozen_vs_live = sorted(
        k for k in set(cand) | set(live) if cand.get(k) != live.get(k)
    )

    stale = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".out.json"):
            continue
        with open(os.path.join(HERE, name), "rb") as handle:
            raw = handle.read().decode("utf-8-sig", "replace")
        row = {"file": name,
               "mentions_revised_candidate": CAND in raw,
               "mentions_superseded_candidate": OLD_CAND in raw}
        stale.append(row)

    readme = os.path.join(HERE, "README.md")
    with open(readme, "rb") as handle:
        readme_text = handle.read().decode("utf-8-sig", "replace")

    result = {
        "probe": "claude_revision_structure",
        "checked_by": "claude (reviewer, not implementer)",
        "q1_declared_scope": {
            "base_file_count": len(base),
            "candidate_file_count": len(cand),
            "changed": changed,
            "added": added,
            "removed": removed,
            "changed_path_count": len(changed) + len(added) + len(removed),
        },
        "q2_frozen_tree_equals_in_repo_candidate": {
            "differing_paths": frozen_vs_live,
            "identical": not frozen_vs_live,
        },
        "q3_recomputed_content_address": {
            "declared": CAND,
            "recomputed": content_address(cand_root),
            "matches": content_address(cand_root) == CAND,
            "baseline_declared": BASE,
            "baseline_recomputed": content_address(base_root),
            "baseline_matches": content_address(base_root) == BASE,
        },
        "q4_probe_artifacts_in_this_directory": stale,
        "q5_readme": {
            "mentions_revised_candidate": CAND in readme_text,
            "mentions_superseded_candidate": OLD_CAND in readme_text,
        },
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
