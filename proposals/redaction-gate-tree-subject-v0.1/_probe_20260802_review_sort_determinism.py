"""Read-only: is the unpinned sorted() step load-bearing for F1?

The suite lets a drop_sort mutant survive.  This asks whether that mutant is
merely a different-but-stable digest or an unstable one: it recomputes the
sort-free variant under several PYTHONHASHSEED values on the real registry
and on a wider synthetic set.  Divergence across seeds = F1 broken (the same
anchor set would print different digests run to run).  Writes only its
.out.json.
"""
import json
import os
import subprocess
import sys

REGISTRY = os.path.join(r"D:\WeilanSkillEvolution", "proposals",
                        "redaction-gate-tree-subject-v0.1",
                        "occurrence-registry.jsonl")
IDENTITY_FIELDS = ("path", "ruleset_digest", "pattern_index", "where",
                   "line_hash", "occurrence_ordinal")

CHILD = r'''
import hashlib, json, sys
IDENTITY_FIELDS = ("path", "ruleset_digest", "pattern_index", "where",
                   "line_hash", "occurrence_ordinal")
entries = json.loads(sys.argv[1])
rows = set()
for entry in entries:
    projected = []
    for field in IDENTITY_FIELDS:
        value = entry[field]
        if isinstance(value, bool):
            value = int(value)
        projected.append(value)
    rows.add(json.dumps(projected, ensure_ascii=False, separators=(",", ":")))
unsorted_body = "\n".join(rows).encode("utf-8")
sorted_body = "\n".join(sorted(rows)).encode("utf-8")
print(json.dumps({
    "unsorted": hashlib.sha256(unsorted_body).hexdigest(),
    "sorted": hashlib.sha256(sorted_body).hexdigest(),
}))
'''


def read_registry(path):
    entries = []
    with open(path, "rb") as fh:
        for raw in fh.read().split(b"\n"):
            if raw:
                entries.append(json.loads(raw.decode("utf-8")))
    return entries


def sample(entries, seeds):
    payload = json.dumps(entries, ensure_ascii=False)
    seen = {"unsorted": set(), "sorted": set()}
    for seed in seeds:
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        proc = subprocess.run([sys.executable, "-c", CHILD, payload],
                              env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True)
        got = json.loads(proc.stdout.decode("utf-8"))
        seen["unsorted"].add(got["unsorted"])
        seen["sorted"].add(got["sorted"])
    return {"distinct_unsorted_digests": len(seen["unsorted"]),
            "distinct_sorted_digests": len(seen["sorted"]),
            "unsorted_digests": sorted(seen["unsorted"]),
            "sorted_digest": sorted(seen["sorted"])}


def main():
    seeds = [1, 2, 3, 4, 5, 17, 99, 12345]
    real = read_registry(REGISTRY)
    template = real[0]
    synthetic = [dict(template, occurrence_ordinal=i, line_hash=f"{i:064d}")
                 for i in range(12)]
    result = {
        "seeds": seeds,
        "real_registry_entries": len(real),
        "real_registry": sample(real, seeds),
        "synthetic_12_entries": sample(synthetic, seeds),
        "reading": ("distinct_unsorted_digests > 1 means the sort-free "
                    "variant violates F1: one anchor set, several digests"),
    }
    out = __file__.replace(".py", ".out.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in result.items()
                      if k != "reading"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
