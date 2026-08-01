"""Apply the cosigned digest remap to SHADOW_RESULT.json.

Cosign: proposal 2026-08-01T18:36:21+09:00 + Codex strong binding 2026-08-01T18:45:35+09:00.
Permitted change: the 11 checks[].evidence[].sha256 occurrences (6 unique files) move
from worktree-byte domain to Git/blob byte domain, plus the derived result_hash.
Nothing else may change; the leaf-level diff must be exactly 12 items and the new
result_hash must equal the value bound by the cosign, or this script writes nothing.

The edit is done as a literal string substitution on the file text so that byte-level
formatting (indent, key order, line endings, trailing newline) is preserved and no
other leaf can silently move.

Usage:  python _exec_20260801_claude_apply_blob_domain.py [--commit]
        (without --commit it is a dry run: it reports and writes nothing)
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
from evolution_core import canonical_json, sha256_text  # noqa: E402

SR = os.path.join(HERE, "SHADOW_RESULT.json")
MAPPING_SOURCE = os.path.join(HERE, "_exec_20260801_claude_blob_domain_remap.out.json")
BOUND_RESULT_HASH = "70ea86b2c2b042c3c4c8d76f103a861d014ba7e834e3ea7d99ada9bf125f7b9c"


def leaves(value, prefix=""):
    out = {}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(leaves(v, "%s.%s" % (prefix, k)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(leaves(v, "%s[%d]" % (prefix, i)))
    else:
        out[prefix] = value
    return out


def body_hash(doc):
    body = {k: v for k, v in doc.items() if k != "result_hash"}
    return sha256_text(canonical_json(body))


def main():
    commit = "--commit" in sys.argv
    remap = json.load(io.open(MAPPING_SOURCE, encoding="utf-8"))
    mapping = remap["proposed_mapping"]

    with io.open(SR, "r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    before = json.loads(raw)

    old_result_hash = before["result_hash"]
    recomputed_old = body_hash(before)

    # occurrence census straight off the parsed document
    occ = [
        (ci, ei, ev["ref"], ev["sha256"])
        for ci, c in enumerate(before.get("checks", []))
        for ei, ev in enumerate(c.get("evidence", []))
        if isinstance(ev, dict) and "sha256" in ev
    ]
    expected_counts = {}
    for _, _, ref, sha in occ:
        expected_counts[sha] = expected_counts.get(sha, 0) + 1

    report = {
        "probe": "_exec_20260801_claude_apply_blob_domain",
        "mode": "commit" if commit else "dry_run",
        "bound_result_hash": BOUND_RESULT_HASH,
        "old_result_hash": old_result_hash,
        "old_result_hash_recomputes": recomputed_old == old_result_hash,
        "occurrence_count": len(occ),
        "substitutions": [],
    }

    text = raw
    for _, _, ref, old_sha in occ:
        new_sha = mapping.get(ref)
        if new_sha is None:
            raise SystemExit("no mapping for %s" % ref)
    seen = set()
    for _, _, ref, old_sha in occ:
        if old_sha in seen:
            continue
        seen.add(old_sha)
        new_sha = mapping[ref]
        found = text.count(old_sha)
        report["substitutions"].append(
            {
                "ref": ref,
                "old": old_sha,
                "new": new_sha,
                "occurrences_in_document": expected_counts[old_sha],
                "occurrences_in_text": found,
                "text_count_matches": found == expected_counts[old_sha],
            }
        )
        if found != expected_counts[old_sha]:
            raise SystemExit(
                "literal %s appears %d times in text but %d times as evidence"
                % (old_sha, found, expected_counts[old_sha])
            )
        text = text.replace(old_sha, new_sha)

    after_partial = json.loads(text)
    new_result_hash = body_hash(after_partial)
    report["new_result_hash"] = new_result_hash
    report["new_result_hash_matches_binding"] = new_result_hash == BOUND_RESULT_HASH

    if text.count(old_result_hash) != 1:
        raise SystemExit("result_hash literal is not unique in the document text")
    text = text.replace(old_result_hash, new_result_hash)
    after = json.loads(text)

    lb, la = leaves(before), leaves(after)
    changed = sorted(k for k in set(lb) | set(la) if lb.get(k) != la.get(k))
    report["leaf_diff_count"] = len(changed)
    report["leaf_diff"] = changed
    report["leaf_diff_is_exactly_12"] = len(changed) == 12
    report["only_evidence_and_result_hash_changed"] = all(
        k.endswith(".sha256") or k == ".result_hash" for k in changed
    )
    for field in ("adoption_eligible", "gate_failures", "metrics_verified", "metrics_total"):
        report["unchanged_%s" % field] = before.get(field) == after.get(field)

    ok = (
        report["new_result_hash_matches_binding"]
        and report["leaf_diff_is_exactly_12"]
        and report["only_evidence_and_result_hash_changed"]
        and after["result_hash"] == BOUND_RESULT_HASH
    )
    report["ok"] = ok
    report["written"] = False

    if commit and ok:
        with io.open(SR, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        report["written"] = True
    elif commit and not ok:
        raise SystemExit("refusing to write: %s" % json.dumps(report, ensure_ascii=False))

    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in sorted(report) if k != "substitutions"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
