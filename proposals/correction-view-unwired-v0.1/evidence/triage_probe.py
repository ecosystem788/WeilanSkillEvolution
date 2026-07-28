"""Read-only triage of every correction entry against the three terminal outcomes.

Codex 2026-07-29T08:33:27+09:00 set a cosign gate on any future proposal that wires
compile_view into a load-bearing read path: every entry of the real ledger must first
reach one of three explicit outcomes --

    A  APPLIED_OVERLAY      the overlay is applied to the view
    B  META_VISIBLE         a meta-event, recognised as such and visibly not applied
    C  REJECTED_INVALID     genuinely invalid, therefore rejected

This probe measures which outcome each entry can reach and what must hold first.
It decides nothing: where an outcome depends on an unmade decision it says so.

Run from the repo root. Writes nothing; reads three files.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
RAW = IMPL / "peer-chat.jsonl"
CORR = IMPL / "peer-chat.corrections.jsonl"
ARCHIVED_REJECTIONS = Path(
    "proposals/correction-view-unwired-v0.1/evidence"
    "/peer-chat.view.rejections.20260729.jsonl"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_delegation(value) -> bytes:
    """DELEGATION section 3's specified function -- the one compile_view uses."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


AFTER_CONVENTIONS = {
    "delegation(sort_keys,compact)": canonical_delegation,
    "no_sort,default_sep": lambda x: json.dumps(x, ensure_ascii=False).encode("utf-8"),
    "no_sort,compact": lambda x: json.dumps(
        x, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8"),
    "ensure_ascii=True,sort_keys,compact": lambda x: json.dumps(
        x, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"),
    "no_sort,compact+LF": lambda x: (
        json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8"),
}

# compile_view hashes line_without_lf(physical_line); a line stored CRLF therefore
# hashes with its CR still attached. Section 7.3 measured #8 against exactly this set.
EOL_FORMS = {
    "payload": lambda p: p,
    "payload+CR": lambda p: p + b"\r",
    "payload+LF": lambda p: p + b"\n",
    "payload+CRLF": lambda p: p + b"\r\n",
}


def load_raw():
    lines = RAW.read_bytes().splitlines(keepends=True)
    payloads = [ln[:-1] if ln.endswith(b"\n") else ln for ln in lines]
    payloads = [p[:-1] if p.endswith(b"\r") else p for p in payloads]
    by_form = {}
    for name, fn in EOL_FORMS.items():
        by_form[name] = {sha(fn(p)): n for n, p in enumerate(payloads, 1)}
    # what compile_view actually indexes: line_without_lf, CR left in place
    live = {sha(ln[:-1] if ln.endswith(b"\n") else ln): n for n, ln in enumerate(lines, 1)}
    return live, by_form


def replicate_compile_view_reason(rec, live_hashes) -> str:
    """Exact replication of _load_corrections' branch order (compile_view.py:59-75)."""
    before = rec.get("before_hash")
    corrected = rec.get("corrected_json")
    if not isinstance(before, str) or before not in live_hashes:
        return "before_hash_not_found"
    if not isinstance(corrected, dict):
        return "corrected_json_not_object"
    if rec.get("after_hash") != sha(canonical_delegation(corrected)):
        return "after_hash_mismatch"
    return "accepted"


def triage(rec, live_hashes, by_form):
    """Terminal outcome + the precondition that must hold to reach it."""
    is_overlay = isinstance(rec.get("corrected_json"), dict)
    before = rec.get("before_hash")

    if not is_overlay:
        return "B", "META_VISIBLE", (
            "schema must gain a record-kind discriminator; today the entry is "
            "rejected under a reason that misdescribes it"
        )

    # overlay-shaped: does its binding still resolve to a physical line?
    if not isinstance(before, str):
        return "C", "REJECTED_INVALID", "overlay entry carries no before_hash"
    hit_forms = [f for f, idx in by_form.items() if before in idx]
    if before not in live_hashes:
        if hit_forms:
            return "C", "REJECTED_INVALID", (
                f"pre-image is {'/'.join(hit_forms)}, which no longer exists on disk; "
                "reachable only via a re-pin, i.e. depends on strand B"
            )
        return "C", "REJECTED_INVALID", (
            "pre-image unresolvable under all four EOL forms; binding permanently dead"
        )

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
        raw = physical[:-1] if physical.endswith(b"\n") else physical
        records.append((n, json.loads(raw.decode("utf-8"))))

    print(f"raw   {RAW}  sha256={sha(RAW.read_bytes())}")
    print(f"corr  {CORR}  sha256={sha(CORR.read_bytes())}")
    print(f"entries={len(records)}  raw_lines={len(live_hashes)}\n")

    buckets: dict[str, list[int]] = {"A": [], "B": [], "C": []}
    reasons: dict[str, int] = {}
    rows = []
    for n, rec in records:
        reason = replicate_compile_view_reason(rec, live_hashes)
        reasons[reason] = reasons.get(reason, 0) + 1
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
    print(f"\n--- replicated reject distribution --- {reasons}")

    # cross-check the replication against the archived run
    archived = [json.loads(l) for l in
                ARCHIVED_REJECTIONS.read_bytes().decode("utf-8").splitlines() if l.strip()]
    arch_dist: dict[str, int] = {}
    for item in archived:
        arch_dist[item["reason"]] = arch_dist.get(item["reason"], 0) + 1
    print(f"--- archived  reject distribution --- {arch_dist}")
    agree = arch_dist == {k: v for k, v in reasons.items() if k != "accepted"}
    print(f"replication agrees with archived run: {agree}")
    return 0 if agree else 1


if __name__ == "__main__":
    raise SystemExit(main())
