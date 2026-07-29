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
    9: ("no_sort,default_sep", 2786, "parses",
        "0c0e9147a6eb9d9079710179245ce7af3f5f56346cd1e4aac203a3ac0522bbe1"),
    10: ("no_sort,default_sep", 2788, "parses",
         "bd82e5eefb3ad4d6ce52d446937b59958ffc54cf1ddcc72205d681c5e05f23d9"),
    11: ("no_sort,default_sep", 2789, "parses",
         "da4f3073ccf545dbd27a757836e3840948eb97b564b8d26a94afe050396d0dad"),
    12: ("no_sort,default_sep", 2865, "parses",
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
    ok1 = part1_migration_cost()
    ok2 = part2_delivery_cost()
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
