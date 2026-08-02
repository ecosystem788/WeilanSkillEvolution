"""Read-only probe: is the gate's registry input order-sensitive the way the ruleset is?

Context.  8.3 (FINDING.md) measured that ``ruleset_digest`` is taken over
``"\n".join(patterns)`` and is therefore *order-sensitive*: two signers holding the
same private-string SET but in different line order get different digests, every
anchor goes stale, and the verdict can never reach KNOWN_PUBLIC_ONLY.

Open question this probe answers: does the same hold for the *registry*?  If it
does, a CHARTER clause may key "same input" on raw registry bytes.  If it does
not, keying on raw bytes would report divergence that provably cannot change any
verdict -- a false stop.

Method (nothing is written; the real registry is read but never modified):
  A. Load the real registry via the gate's own loader.
  B. Build occurrences whose identities are the real registry's identities, so
     anchoring is actually exercised rather than trivially empty.
  C. Run classify_occurrences with the registry list in original order, reversed
     order, and with every entry duplicated.  Compare the full classified output.
  D. Recompute stale_anchor_count exactly as scan_commit does (:380-382) under the
     same three arrangements.
  E. Serialize the three arrangements and sha256 them, to show whether a raw-bytes
     digest separates arrangements that the adjudication cannot separate.

Emits JSON to stdout and to the sibling .out.json.  Prints no pattern and no
private string: only identity tuples already present in the committed registry,
and even those only as counts/digests.
"""

import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(
    os.path.dirname(HERE), "scaffold-opensource-export-v0.1", "scan_only_gate.py")


def load_gate():
    spec = importlib.util.spec_from_file_location("scan_only_gate_probe", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def occurrences_from(registry, ruleset_digest):
    """One occurrence per registry entry carrying that entry's identity."""
    built = []
    for entry in registry:
        built.append({
            "path": entry["path"],
            "pattern_index": entry["pattern_index"],
            "where": entry["where"],
            "line_hash": entry["line_hash"],
            "occurrence_ordinal": entry["occurrence_ordinal"],
            "line_framing": "record",
            "line_number": None,
            "count": 1,
        })
    return built


def verdict_of(gate, occurrences, registry, ruleset_digest):
    fresh = [dict(item) for item in occurrences]
    classified, reason_codes = gate.classify_occurrences(
        fresh, registry, ruleset_digest)
    stale = sum(e["ruleset_digest"] != ruleset_digest for e in registry)
    unanchored = sum(not item["anchored"] for item in classified)
    if not classified:
        state, code = "CLEAN", 0
    elif not unanchored:
        state, code = "KNOWN_PUBLIC_ONLY", 3
    else:
        state, code = "NEW_MATCHES", 2
    body = json.dumps(classified, ensure_ascii=False, sort_keys=True)
    return {
        "state": state,
        "exit_code": code,
        "occurrence_count": len(classified),
        "unanchored_occurrence_count": unanchored,
        "stale_anchor_count": stale,
        "reason_codes": reason_codes,
        "classified_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def arrangement_digest(registry):
    body = "\n".join(
        json.dumps(entry, ensure_ascii=False, sort_keys=True) for entry in registry)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def anchor_set_digest(gate, registry):
    """Order-independent, duplicate-insensitive projection of the registry."""
    tuples = sorted(
        {json.dumps(list(gate.identity(e)) + [e["ruleset_digest"]],
                    ensure_ascii=False) for e in registry})
    return hashlib.sha256("\n".join(tuples).encode("utf-8")).hexdigest()


def main():
    gate = load_gate()
    registry_path = gate.DEFAULT_REGISTRY
    with open(registry_path, "rb") as fh:
        raw = fh.read()
    registry = gate.load_registry(registry_path)
    digests = sorted({e["ruleset_digest"] for e in registry})
    # Adjudicate against the digest the committed registry actually carries, so
    # the anchored branch is exercised.  If the registry is mixed, take the most
    # common one.
    counts = {d: sum(1 for e in registry if e["ruleset_digest"] == d) for d in digests}
    ruleset_digest = max(counts, key=lambda d: counts[d]) if counts else "0" * 64

    occurrences = occurrences_from(registry, ruleset_digest)
    arrangements = {
        "original": list(registry),
        "reversed": list(reversed(registry)),
        "duplicated": [e for e in registry for _ in (0, 1)],
    }
    results = {}
    for name, arrangement in arrangements.items():
        results[name] = {
            "entry_count": len(arrangement),
            "arrangement_sha256": arrangement_digest(arrangement),
            "anchor_set_sha256": anchor_set_digest(gate, arrangement),
            "verdict": verdict_of(gate, occurrences, arrangement, ruleset_digest),
        }

    verdict_keys = ("state", "exit_code", "occurrence_count",
                    "unanchored_occurrence_count", "reason_codes",
                    "classified_sha256")
    base = results["original"]["verdict"]
    verdict_identical = {
        name: all(results[name]["verdict"][k] == base[k] for k in verdict_keys)
        for name in results
    }
    out = {
        "probe": "registry_order_sensitivity",
        "read_only": True,
        "gate_path": GATE.replace("\\", "/"),
        "registry_path": registry_path.replace("\\", "/"),
        "registry_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "registry_entry_count": len(registry),
        "distinct_ruleset_digests_in_registry": len(digests),
        "adjudicating_ruleset_digest_prefix": ruleset_digest[:12],
        "arrangements": results,
        "verdict_identical_to_original": verdict_identical,
        "arrangement_digests_distinct": len(
            {results[n]["arrangement_sha256"] for n in results}),
        "anchor_set_digests_distinct": len(
            {results[n]["anchor_set_sha256"] for n in results}),
        "python": sys.version.split()[0],
    }
    text = json.dumps(out, ensure_ascii=False, indent=1)
    print(text)
    with open(os.path.join(HERE, "_probe_20260802_registry_order_sensitivity.out.json"),
              "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
