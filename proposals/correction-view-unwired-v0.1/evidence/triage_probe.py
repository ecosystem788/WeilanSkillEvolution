"""Read-only triage of every correction entry against the three terminal outcomes.

Codex 2026-07-29T08:33:27+09:00 set a cosign gate on any future proposal that wires
compile_view into a load-bearing read path: every entry of the real ledger must first
reach one of three explicit outcomes --

    A  APPLIED_OVERLAY      the overlay is applied to the view
    B  META_VISIBLE         a meta-event, recognised as such and visibly not applied
    C  REJECTED_INVALID     genuinely invalid, therefore rejected

This probe measures which outcome each entry can reach and what must hold first.
It decides nothing: where an outcome depends on an unmade decision it says so.

Run from the repo root. Writes nothing; reads the compiler plus three evidence files.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
RAW = IMPL / "peer-chat.jsonl"
CORR = IMPL / "peer-chat.corrections.jsonl"
COMPILE_VIEW_PATH = Path(
    "proposals/lineage-log-append-only-correction-v0.1/compile_view.py"
)
SPEC = importlib.util.spec_from_file_location("correction_view_compiler", COMPILE_VIEW_PATH)
CV = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CV)

EXPECTED_COMPILER_SUMMARY = {"applied": 0, "meta_visible": 5, "rejected": 10}
EXPECTED_REJECTION_REASONS = {
    "after_hash_mismatch": 8,
    "preimage_only_under_eol_variant": 1,
    "preimage_unresolvable_and_entry_self_inconsistent": 1,
}


def sha(data: bytes) -> str:
    return CV.sha256_hex(data)


AFTER_CONVENTIONS = CV.AFTER_CONVENTIONS
EOL_FORMS = CV.EOL_FORMS


def load_raw():
    lines = RAW.read_bytes().splitlines(keepends=True)
    return CV.build_line_index(lines)


def triage(rec, live_hashes, by_form):
    """Terminal outcome + the precondition that must hold to reach it."""
    kind, basis = CV.record_kind(rec)
    if kind != "overlay":
        return "B", "META_VISIBLE", (
            f"record_kind={kind} via {basis}; compiler visibly does not apply it"
        )

    is_overlay = isinstance(rec.get("corrected_json"), dict)
    before = rec.get("before_hash")

    if not is_overlay:
        return "B", "META_VISIBLE", (
            "schema must gain a record-kind discriminator; today the entry is "
            "rejected under a reason that misdescribes it"
        )

    # overlay-shaped: does its binding still resolve to a physical line?
    if not isinstance(before, str):
        code, diagnosis = CV.invalid_binding_code(rec, by_form)
        return "C", "REJECTED_INVALID", f"{code}; diagnosis={diagnosis}"
    if before not in live_hashes:
        code, diagnosis = CV.invalid_binding_code(rec, by_form)
        return "C", "REJECTED_INVALID", f"{code}; diagnosis={diagnosis}"

    matched = [n for n, fn in AFTER_CONVENTIONS.items()
               if rec.get("after_hash") == sha(fn(rec["corrected_json"]))]
    if "delegation(sort_keys,compact)" in matched:
        return "A", "APPLIED_OVERLAY", "already satisfies the specified convention"
    if matched:
        return "A", "APPLIED_OVERLAY", (
            f"binding live; blocked only by the canonical-function split "
            f"(after_hash matches {matched[0]})"
        )
    return "C", "REJECTED_INVALID", "after_hash matches none of the five tested conventions"


def diagnose_against_pre_redaction(n: int, rec: dict) -> str | None:
    """For an after_hash that matches nothing on current bytes, re-test it against the
    same record's pre-redaction payload from ef0b844^.

    The 2026-07-14 owner-directed redaction (ef0b844) rewrote peer-chat.corrections.jsonl
    itself, not only peer-chat.jsonl. A correction whose corrected_json was redacted keeps
    its self-declared after_hash, which then pins bytes that survive only in git history.
    """
    import subprocess

    blob = subprocess.run(
        ["git", "show",
         "ef0b844^:proposals/bounded-scheduler-v0.1/impl/peer-chat.corrections.jsonl"],
        capture_output=True,
    ).stdout
    lines = blob.splitlines()
    if n > len(lines):
        return None
    old = json.loads(lines[n - 1].decode("utf-8"))
    if old.get("after_hash") != rec.get("after_hash"):
        return None  # not the same record
    old_cj = old.get("corrected_json")
    if not isinstance(old_cj, dict):
        return None
    for name, fn in AFTER_CONVENTIONS.items():
        if rec.get("after_hash") == sha(fn(old_cj)):
            return name
    return None


def main() -> int:
    live_hashes, by_form = load_raw()
    records = []
    for n, physical in enumerate(CORR.read_bytes().splitlines(keepends=True), 1):
        raw = CV.line_without_lf(physical)
        records.append((n, raw.decode("utf-8"), json.loads(raw.decode("utf-8"))))

    print(f"raw   {RAW}  sha256={sha(RAW.read_bytes())}")
    print(f"corr  {CORR}  sha256={sha(CORR.read_bytes())}")
    print(f"entries={len(records)}  raw_lines={len(live_hashes)}\n")

    accepted, rejected, meta_visible = CV._load_corrections(
        CORR, (live_hashes, by_form)
    )
    rejected_by_raw = {item["correction_raw"]: item["reason"] for item in rejected}
    meta_by_raw = {
        item["correction_raw"]: f"META_VISIBLE:{item['kind']}:{item['basis']}"
        for item in meta_visible
    }
    compiler_summary = {
        "applied": len(accepted),
        "meta_visible": len(meta_visible),
        "rejected": len(rejected),
    }
    rejection_reasons: dict[str, int] = {}
    for item in rejected:
        reason = item["reason"]
        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

    failures = []
    if compiler_summary != EXPECTED_COMPILER_SUMMARY:
        failures.append(f"compiler summary drifted: {compiler_summary}")
    if rejection_reasons != EXPECTED_REJECTION_REASONS:
        failures.append(f"rejection reasons drifted: {rejection_reasons}")

    buckets: dict[str, list[int]] = {"A": [], "B": [], "C": []}
    rows = []
    for n, correction_raw, rec in records:
        reason = rejected_by_raw.get(correction_raw) or meta_by_raw.get(correction_raw)
        if reason is None:
            before_hash = rec.get("before_hash")
            if before_hash in accepted:
                reason = "accepted"
            else:
                failures.append(f"entry #{n} was not accounted for by the compiler")
                reason = "UNACCOUNTED"
        cls, name, precond = triage(rec, live_hashes, by_form)
        buckets[cls].append(n)
        rows.append((n, rec, reason, cls, name, precond))
        print(f"#{n:<3} from={str(rec.get('from')):8} kind={str(rec.get('kind')):22}"
              f" reject={reason:26} -> {cls} {name}")
        print(f"     precondition: {precond}")
        # after_hash is tested for every overlay entry, independently of which branch
        # triage() returned on -- #1 dies on its before_hash first and would otherwise
        # never have its after_hash examined at all.
        if isinstance(rec.get("corrected_json"), dict):
            matched = [nm for nm, fn in AFTER_CONVENTIONS.items()
                       if rec.get("after_hash") == sha(fn(rec["corrected_json"]))]
            print(f"     after_hash over CURRENT bytes: {matched or 'NO MATCH (5 tested)'}")
            if not matched:
                hit = diagnose_against_pre_redaction(n, rec)
                if hit:
                    print(f"     DIAGNOSIS: matches '{hit}' over this record's"
                          f" PRE-redaction corrected_json (ef0b844^) -- the specified"
                          f" function WAS used; ef0b844 rewrote the payload and left"
                          f" the self-declared hash standing.")

    print("\n--- terminal buckets ---")
    for cls in "ABC":
        print(f"  {cls}: n={len(buckets[cls])}  entries={buckets[cls]}")
    print(f"\n--- compiler summary --- {compiler_summary}")
    print(f"--- compiler rejection distribution --- {rejection_reasons}")
    print(f"--- failures --- {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
