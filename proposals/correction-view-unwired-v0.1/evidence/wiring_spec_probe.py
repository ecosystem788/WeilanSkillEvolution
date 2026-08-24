"""Read-only measurement of the two things a strand-B wiring proposal must fix.

Codex adjudicated at 2026-07-29T09:09:59+09:00: keep DELEGATION section 3's canonical,
migrate the write side and the existing entries to it (option B of the four), and require
a minimal closed loop -- A canonical migration + B record-kind discrimination + C real
invalidation state + wake_brief end-to-end reading that view.

Part 1 asks what "migrate the existing entries" actually costs, per entry.
Part 2 asks what "wake_brief reads that view" actually costs, in bytes.

It decides nothing and writes nothing inside the repo. The compiled view goes to a
temp dir outside the repo; the raw ledger's sha256 is taken before and after to prove it.

Run from the repo root. Exit 0 iff every frozen expectation below still holds.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
RAW = IMPL / "peer-chat.jsonl"
CORR = IMPL / "peer-chat.corrections.jsonl"
COMPILER_DIR = Path("proposals/lineage-log-append-only-correction-v0.1")

# V3.1 §七 D.2 (闭环 Codex 4495 新 1 + Codex 4499 G3): module-level import so main()
# can directly read CV.AFTER_CONVENTIONS without going through a function-local alias.
# Module-level import failure is fail-closed (SystemExit(1)) -- this is the only place
# "skipped" is allowed to be replaced by an honest failure. The helper docstring no
# longer promises a "byte_equivalence self-check skipped" string.
sys.path.insert(0, str(COMPILER_DIR))
try:
    import compile_view as CV  # noqa: E402  module-level, visible to main()
except (ImportError, ModuleNotFoundError) as _imp_err:
    sys.stderr.write(
        f"FAIL: cannot import compile_view at module level: {_imp_err}\n"
    )
    raise SystemExit(1)

# Frozen at 2026-07-29 by this probe's own first run. These are hand-carried literals,
# not values recomputed by the code under test -- same discipline as
# test_canonical_contract.py (FINDING section 4). A drift here is a real change, not noise.
A_CLASS = (2, 5, 6, 7, 9, 10, 11, 12)
EXPECTED_MIGRATION = {
    2: ("no_sort,default_sep", 873, "parses",
        "4797c70a9d8f19424e70ae873dd8421549418ff906985b78e541fac90df1ed11"),
    5: ("no_sort,compact", 1518, "parses",
        "13ae33d1f0e8a40d4ff28bd5b05da87caf2d7ce51e8f90ef05225aea58cc8a42"),
    6: ("no_sort,default_sep", 1532, "MALFORMED",
        "7e4ba76d14a05661881d17ea2a272e455a23805cb469184cd68c19845217c077"),
    7: ("no_sort,default_sep", 1539, "MALFORMED",
        "641ba1148ea60b43d5d8d2d784c0b5a3333e367f587d2dca57c9c83c333d2404"),
    9: ("no_sort,default_sep", 2785, "parses",
        "0c0e9147a6eb9d9079710179245ce7af3f5f56346cd1e4aac203a3ac0522bbe1"),
    10: ("no_sort,default_sep", 2787, "parses",
         "bd82e5eefb3ad4d6ce52d446937b59958ffc54cf1ddcc72205d681c5e05f23d9"),
    11: ("no_sort,default_sep", 2788, "parses",
         "da4f3073ccf545dbd27a757836e3840948eb97b564b8d26a94afe050396d0dad"),
    12: ("no_sort,default_sep", 2864, "parses",
         "b1055343e0e39bf9e66c3ed9ff8b769984f4e71643ee44312d5993c473a5fc2b"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_delegation(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


AFTER_CONVENTIONS = {
    "delegation": canonical_delegation,
    "no_sort,default_sep": lambda x: json.dumps(x, ensure_ascii=False).encode("utf-8"),
    "no_sort,compact": lambda x: json.dumps(
        x, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8"),
    "ascii,sort,compact": lambda x: json.dumps(
        x, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"),
    "no_sort,compact+LF": lambda x: (
        json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8"),
}


# V3.1 §七 D.2 (闭环 Codex 4499 反对 4): bidirectional rename table covers the case
# where CV picks the long alias ("delegation(sort_keys,compact)" / "ensure_ascii=...")
# instead of the short one. key_sets_match below uses both sides' RENAME_BIDIR coverage.
RENAME_BIDIR = {
    "delegation": {"delegation", "delegation(sort_keys,compact)"},
    "delegation(sort_keys,compact)": {"delegation", "delegation(sort_keys,compact)"},
    "no_sort,default_sep": {"no_sort,default_sep"},
    "no_sort,compact": {"no_sort,compact"},
    "ascii,sort,compact": {"ascii,sort,compact", "ensure_ascii=True,sort_keys,compact"},
    "ensure_ascii=True,sort_keys,compact": {"ascii,sort,compact", "ensure_ascii=True,sort_keys,compact"},
    "no_sort,compact+LF": {"no_sort,compact+LF"},
}


def key_sets_match(local: set, cv: set) -> bool:
    """Two key sets match iff there's a bijection whose every edge is in RENAME_BIDIR.

    Greedy bipartite matching is sufficient here: each key has at most 2 equivalent names,
    so no greedy-vs-optimal mismatch can occur for sets of size <= 7.
    """
    if len(local) != len(cv):
        return False
    unmatched_local = set(local)
    unmatched_cv = set(cv)
    for lk in list(unmatched_local):
        allowed = RENAME_BIDIR.get(lk, {lk})
        for ck in list(unmatched_cv):
            if ck in allowed:
                unmatched_local.discard(lk)
                unmatched_cv.discard(ck)
                break
    return not unmatched_local and not unmatched_cv


# V3.1 §七 D.2 (闭环 Codex 4495 新 3 + Codex 4499 G1/G2): representative payload
# byte-equivalence self-check.  Helper does NOT hardcode short aliases; uses
# EQUIVALENCE_CLASSES + _resolve_alias() so mutation 1/2 (rename one alias to its peer)
# still finds an alias on each side and can detect function-body drift.
REPRESENTATIVE_PAYLOADS = [
    # (label, value)
    ("ascii_only", {"b": 1, "a": 2, "c": [3, 4]}),
    ("with_cjk", {"键": "值", "列表": [1, "二", 3]}),
    ("key_order_swapped", {"z": 1, "a": 2, "m": 3}),
]

# Each equivalence class lists the allowed aliases. Mutation 1/2 (rename one alias to
# its peer) keeps at least one alias reachable on each side from _resolve_alias.
EQUIVALENCE_CLASSES = [
    ("ascii_sort_compact", ["ascii,sort,compact", "ensure_ascii=True,sort_keys,compact"]),
    ("delegation", ["delegation", "delegation(sort_keys,compact)"]),
]


def _resolve_alias(d: dict, aliases: list):
    """Return (key, fn) for the first alias that exists in d, or (None, None)."""
    for a in aliases:
        if a in d:
            return a, d[a]
    return None, None


def probe_byte_equivalence() -> list:
    """Assert that the two equivalence classes produce byte-identical output on every
    representative payload.  Returns a list of drift strings (one per failed pair).
    Each drift names the class + payload label + both alias keys + 8-hex hash prefix.
    """
    drifts: list = []
    for class_label, aliases in EQUIVALENCE_CLASSES:
        wiring_key, wiring_fn = _resolve_alias(AFTER_CONVENTIONS, aliases)
        cv_key, cv_fn = _resolve_alias(CV.AFTER_CONVENTIONS, aliases)
        if wiring_fn is None or cv_fn is None:
            drifts.append(
                f"byte_equivalence: missing alias on {class_label} "
                f"(wiring_key={wiring_key}, cv_key={cv_key}, allowed={aliases})"
            )
            continue
        for label, payload_value in REPRESENTATIVE_PAYLOADS:
            h_wiring = sha(wiring_fn(payload_value))
            h_cv = sha(cv_fn(payload_value))
            if h_wiring != h_cv:
                drifts.append(
                    f"byte_equivalence drift on {class_label}/{label} "
                    f"(wiring={wiring_key} vs cv={cv_key}): "
                    f"wiring={h_wiring[:8]} cv={h_cv[:8]} differ"
                )
    return drifts


def payload(line: bytes) -> bytes:
    return line[:-1] if line.endswith(b"\n") else line


def part1_migration_cost() -> bool:
    """Per A-class entry: is migrating its after_hash a re-encoding or a new claim?

    An after_hash that verifies under ANY convention authenticates the SAME
    corrected_json value -- the convention split changes whether a reader can check the
    commitment, not what content the author committed to. So where exactly one candidate
    convention verifies, recomputing under section 3's canonical is a derivation from an
    author-signed value, not a fresh assertion by the migrator. Where none verifies, it
    would be a fresh assertion, and this probe says so instead of hiding it.
    """
    lines = RAW.read_bytes().splitlines(keepends=True)
    live = {sha(payload(ln)): n for n, ln in enumerate(lines, 1)}

    print("--- part 1: migration cost per A-class entry ---")
    print("  (conv = the convention whose hash the author actually wrote)")
    ok = True
    for n, physical in enumerate(CORR.read_bytes().splitlines(keepends=True), 1):
        if n not in A_CLASS:
            continue
        rec = json.loads(payload(physical).decode("utf-8"))
        corrected = rec["corrected_json"]
        matched = [
            name for name, fn in AFTER_CONVENTIONS.items()
            if rec.get("after_hash") == sha(fn(corrected))
        ]
        target = sha(canonical_delegation(corrected))
        line_no = live.get(rec["before_hash"])
        try:
            json.loads(payload(lines[line_no - 1]).decode("utf-8"))
            state = "parses"
        except (UnicodeDecodeError, json.JSONDecodeError):
            state = "MALFORMED"

        verdict = "DERIVABLE" if len(matched) == 1 else (
            "AMBIGUOUS" if matched else "NEW_ASSERTION")
        print(f"  #{n:<3} line={line_no:<5} raw={state:<10} conv={','.join(matched):<20}"
              f" {verdict:<13} target_after={target}")

        want = EXPECTED_MIGRATION[n]
        got = (matched[0] if len(matched) == 1 else ",".join(matched),
               line_no, state, target)
        if got != want:
            print(f"       DRIFT: expected {want}, measured {got}")
            ok = False
    print(f"  frozen expectations hold: {ok}")
    return ok


def part2_delivery_cost() -> bool:
    """What the compiled view costs the reader wake_brief actually hands bytes to.

    wake_brief tails peer-chat.jsonl from a stored byte_offset (wake_brief.py:344-351).
    Two numbers decide whether "point wake_brief at the view" is a one-line change:
    how many view lines are byte-identical to their raw line, and whether the line
    count is preserved.
    """
    sys.path.insert(0, str(COMPILER_DIR))
    import compile_view as cv  # noqa: E402

    before = sha(RAW.read_bytes())
    tmp = Path(tempfile.mkdtemp(prefix="wl_view_"))
    result = cv.compile_view(RAW, None, tmp / "v.jsonl", tmp / "r.jsonl")
    after = sha(RAW.read_bytes())

    view_lines = (tmp / "v.jsonl").read_bytes().splitlines()
    raw_lines = RAW.read_bytes().splitlines()
    identical = sum(1 for a, b in zip(view_lines, raw_lines) if a == b)

    print("\n--- part 2: delivery cost ---")
    print(f"  raw sha256 pre==post (nothing in the repo was touched): {before == after}")
    print(f"  compile result: {result}")
    print(f"  view lines={len(view_lines)}  raw lines={len(raw_lines)}"
          f"  line count preserved={len(view_lines) == len(raw_lines)}")
    print(f"  byte-identical lines: {identical} / {len(raw_lines)}"
          f"  ({len(raw_lines) - identical} differ)")
    print(f"  view bytes={(tmp / 'v.jsonl').stat().st_size}"
          f"  raw bytes={RAW.stat().st_size}")
    print(f"  temp dir (outside repo): {tmp}")

    ok = before == after and len(view_lines) == len(raw_lines)
    print(f"  invariants hold (raw untouched, 1:1 line mapping): {ok}")
    return ok


def main() -> int:
    print(f"raw   {RAW}  sha256={sha(RAW.read_bytes())}")
    print(f"corr  {CORR}  sha256={sha(CORR.read_bytes())}\n")

    # V3.1 §七 D.2 (闭环 Codex 4499 反对 4): bidirectional key-set match.
    cv_keys = set(CV.AFTER_CONVENTIONS.keys())
    local_keys = set(AFTER_CONVENTIONS.keys())
    if not key_sets_match(local_keys, cv_keys):
        sys.stderr.write(
            f"AFTER_CONVENTIONS key set drifted:\n"
            f"  wiring_spec_probe.py local: {sorted(local_keys)}\n"
            f"  CV.AFTER_CONVENTIONS:       {sorted(cv_keys)}\n"
            f"  RENAME_BIDIR table covers:  {sorted(RENAME_BIDIR.keys())}\n"
        )
        return 1
    if local_keys != cv_keys:
        print("WARN: AFTER_CONVENTIONS key naming drifted; bidirectional rename covers it.")

    # V3.1 §七 D.2 (闭环 Codex 4495 新 3 + Codex 4499 G2): byte-equivalence drift
    # fails the probe (does NOT just WARN). Drift entries already include class +
    # label + dual alias keys + 8-hex hash prefix.
    drifts = probe_byte_equivalence()
    if drifts:
        print("FAIL: AFTER_CONVENTIONS function-body equivalence drift across rename pairs:")
        for d in drifts:
            print(f"  - {d}")
        return 1

    ok1 = part1_migration_cost()
    ok2 = part2_delivery_cost()
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
