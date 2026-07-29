"""Read-only measurement of the transaction shape v4 must pin down.

Codex rejected wiring proposal v3 at 2026-07-29T11:09:28+09:00 on one point:

    v3 chose "A and B land in the same deployment" while keeping v2's rollback
    statement ("A is irreversible / B and C are git revert / D goes through the
    deployment rollback artifact").  Those cannot both hold.  If "same deployment"
    means one commit, reverting B deletes A from an append-only ledger.  If it
    means two commits published together, the A-only false-negative window still
    exists on this machine.  Pick one shape and pin it.

Answering that requires knowing WHERE the reader-visible boundary actually is,
and v1-v3 never measured it -- they assumed the compiled view is the only reader
surface, so the boundary is D.  This probe measures the boundary instead:

  1. Census of every file that reads the corrections ledger, split into
     wake-path readers and non-wake-path (probe/test/doc) readers.
  2. Whether the live deployed skill references the compiler or the view at all.
  3. What the one live wake-path reader (peer_health_wake) outputs under the
     15-entry ledger vs the 23-entry post-A ledger -- using the REAL function by
     import, not a hand replica (that is exactly the section 11.4 lesson).
  4. Whether any post-A neutrality is structural or merely an artifact of
     append order, measured by re-running with the migration entries placed first.

It also freezes the two corrections Codex asked for: phase_matrix_probe's
INVENTORY length is 13, not 14.

Run from the repo root.  Exit 0 iff every frozen expectation below still holds.
Nothing in the repo is written; the raw and corrections sha256 are taken before
and after to prove it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

EVID = Path("proposals/correction-view-unwired-v0.1/evidence")
sys.path.insert(0, str(EVID))
sys.path.insert(0, str(Path("proposals/mutual-aid-v0.1")))

import phase_matrix_probe as PM  # noqa: E402

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
RAW = IMPL / "peer-chat.jsonl"
CORR = IMPL / "peer-chat.corrections.jsonl"
PEER_HEALTH = Path("proposals/mutual-aid-v0.1/peer_health_wake.py")
LIVE_SKILL = Path(r"D:\CodexData\skills\solve-with-weilan")

# ---------------------------------------------------------------------------
# Frozen expectations.  Hand-entered literals; drift exits non-zero.
# ---------------------------------------------------------------------------

# Codex's correction, verified: the inventory has 13 rows, not 14.
EXPECTED_INVENTORY_LEN = 13
# Of those, exactly four do not survive every phase (three Codex named, one found
# in v3).  Frozen so that a later edit cannot quietly change the phase geometry.
EXPECTED_NON_SURVIVING = 4

# Every tracked file that names the corrections ledger.  Split by whether the wake
# prompts actually invoke it.  A new name appearing here is a new reader and must
# be triaged before A lands.
EXPECTED_WAKE_PATH_READERS = {
    "proposals/mutual-aid-v0.1/peer_health_wake.py",
}
EXPECTED_OFF_PATH_READERS = {
    "proposals/correction-view-unwired-v0.1/FINDING.md",
    "proposals/correction-view-unwired-v0.1/evidence/changeset_v2_probe.py",
    "proposals/correction-view-unwired-v0.1/evidence/eol_pointer_probe.py",
    "proposals/correction-view-unwired-v0.1/evidence/hash_convention_probe.py",
    "proposals/correction-view-unwired-v0.1/evidence/phase_matrix_probe.py",
    "proposals/correction-view-unwired-v0.1/evidence/triage_probe.py",
    "proposals/correction-view-unwired-v0.1/evidence/wiring_spec_probe.py",
    "proposals/coverage-ladder-derivation-v0.1/FINDING.md",
    "proposals/ledger-timestamp-authority-v0.1/probe_forward_asymmetry.py",
    "proposals/ledger-timestamp-authority-v0.1/probe_timestamp_authority.py",
    "proposals/lineage-log-append-only-correction-v0.1/DELEGATION.md",
    "proposals/lineage-log-append-only-correction-v0.1/test_compile_view.py",
    "proposals/mutual-aid-v0.1/test_peer_health_wake.py",
}

# The deployed artifact today: it neither ships nor references the compiler or the
# compiled view, so no wake reads the view until D.
EXPECTED_LIVE_VIEW_REFERENCES = 0

# peer_health_wake's output over the real ledger today: three known_corrected, all
# pointing at the ORIGINAL correction entries by line number.
EXPECTED_KNOWN_CORRECTED_LINES = [858, 1532, 1539]
EXPECTED_KNOWN_CORRECTED_REFS = [4, 6, 7]
EXPECTED_PARSE_ERRORS = 0

# The load-bearing question: does appending A's eight entries change what this live
# reader emits?  Measured below in both orders.
EXPECTED_POST_A_APPEND_ORDER_IDENTICAL = True
EXPECTED_POST_A_MIGRATION_FIRST_IDENTICAL = False
# Under migration-first order the eight migration entries occupy refs 1..8, so every
# ref number shifts; that alone is not the finding.  The finding is WHICH lines end
# up matched by a migration entry rather than by the original: the two malformed
# A-class targets (#6 line 1532, #7 line 1539).  Line 858 is corrected by a
# non-A-class entry, so it still matches its original (shifted ref 4 -> 12).
MIGRATION_COUNT = 8
EXPECTED_MIGRATION_FIRST_MATCHED_BY_MIGRATION = [1532, 1539]
EXPECTED_MIGRATION_FIRST_REFS = [12, 3, 4]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def census() -> dict:
    """Every tracked file naming the corrections ledger, and the live artifact's refs."""
    # Code and prose only.  The ledgers themselves quote the filename in chat text,
    # and an archived rejection file names it as data -- neither is a reader.
    out = subprocess.run(
        ["git", "grep", "-l", "peer-chat.corrections.jsonl", "--", "*.py", "*.ps1", "*.md"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    named = {line.strip() for line in out.stdout.splitlines() if line.strip()}
    # This probe itself names the ledger; exclude it so the frozen sets stay stable.
    named.discard("proposals/correction-view-unwired-v0.1/evidence/txn_shape_probe.py")

    live_refs = []
    if LIVE_SKILL.exists():
        for path in LIVE_SKILL.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_bytes().decode("utf-8", "ignore")
            except OSError:
                continue
            if "compile_view" in text or "peer-chat.corrections" in text:
                live_refs.append(path.name)
    return {"named_by": sorted(named), "live_artifact_references": sorted(live_refs)}


def run_peer_health(module, corrections: list[dict]) -> dict:
    """Run the REAL _rows over the REAL raw ledger with a given corrections list."""
    parse_errors: list[dict] = []
    known: list[dict] = []
    module._rows(
        RAW,
        parse_errors=parse_errors,
        corrections=list(enumerate(corrections, start=1)),
        corrections_path=CORR,
        known_corrected=known,
    )
    return {
        "known_corrected": [
            {
                "line": item["line"],
                "matched_hash": item["matched_hash"],
                "correction_ref_line": int(item["correction_ref"].rsplit(":", 1)[1]),
            }
            for item in known
        ],
        "parse_errors": len(parse_errors),
    }


def main() -> int:
    failures = []
    raw_pre, corr_pre = sha(RAW.read_bytes()), sha(CORR.read_bytes())

    if len(PM.INVENTORY) != EXPECTED_INVENTORY_LEN:
        failures.append(f"inventory length: {len(PM.INVENTORY)}")
    non_surviving = [row for row in PM.INVENTORY if not (row[2] and row[3])]
    if len(non_surviving) != EXPECTED_NON_SURVIVING:
        failures.append(f"non-surviving assertions: {len(non_surviving)}")

    reader_census = census()
    named = set(reader_census["named_by"])
    wake_path = named & EXPECTED_WAKE_PATH_READERS
    off_path = named - EXPECTED_WAKE_PATH_READERS
    if wake_path != EXPECTED_WAKE_PATH_READERS:
        failures.append(f"wake-path readers drifted: {sorted(wake_path)}")
    if off_path != EXPECTED_OFF_PATH_READERS:
        failures.append(
            "off-path readers drifted; new: "
            f"{sorted(off_path - EXPECTED_OFF_PATH_READERS)} gone: "
            f"{sorted(EXPECTED_OFF_PATH_READERS - off_path)}"
        )
    if len(reader_census["live_artifact_references"]) != EXPECTED_LIVE_VIEW_REFERENCES:
        failures.append(
            f"live artifact now references the view: {reader_census['live_artifact_references']}"
        )

    peer_health = load_module(PEER_HEALTH, "peer_health_wake_probe")
    records = PM.load_records(CORR.read_bytes())
    migrations = PM.build_migration_entries(records)

    today = run_peer_health(peer_health, records)
    post_a_append = run_peer_health(peer_health, records + migrations)
    post_a_first = run_peer_health(peer_health, migrations + records)

    if [item["line"] for item in today["known_corrected"]] != EXPECTED_KNOWN_CORRECTED_LINES:
        failures.append(f"today known_corrected lines: {today['known_corrected']}")
    if [
        item["correction_ref_line"] for item in today["known_corrected"]
    ] != EXPECTED_KNOWN_CORRECTED_REFS:
        failures.append(f"today correction refs: {today['known_corrected']}")
    if today["parse_errors"] != EXPECTED_PARSE_ERRORS:
        failures.append(f"today parse errors: {today['parse_errors']}")

    append_identical = post_a_append == today
    if append_identical != EXPECTED_POST_A_APPEND_ORDER_IDENTICAL:
        failures.append(f"post-A append-order output changed: {post_a_append}")

    first_identical = post_a_first == today
    if first_identical != EXPECTED_POST_A_MIGRATION_FIRST_IDENTICAL:
        failures.append(
            "migration-first order produced identical output -- the append-order "
            "dependence this probe exists to show would not be real"
        )
    first_refs = [item["correction_ref_line"] for item in post_a_first["known_corrected"]]
    if first_refs != EXPECTED_MIGRATION_FIRST_REFS:
        failures.append(f"migration-first refs: {first_refs}")
    matched_by_migration = [
        item["line"]
        for item in post_a_first["known_corrected"]
        if item["correction_ref_line"] <= MIGRATION_COUNT
    ]
    if matched_by_migration != EXPECTED_MIGRATION_FIRST_MATCHED_BY_MIGRATION:
        failures.append(f"migration-first matched-by-migration: {matched_by_migration}")

    raw_post, corr_post = sha(RAW.read_bytes()), sha(CORR.read_bytes())
    if (raw_pre, corr_pre) != (raw_post, corr_post):
        failures.append("this probe modified the ledger -- it must not")

    print(
        json.dumps(
            {
                "ledger_untouched": (raw_pre, corr_pre) == (raw_post, corr_post),
                "raw_sha256": raw_pre,
                "corrections_sha256": corr_pre,
                "inventory_len": len(PM.INVENTORY),
                "non_surviving_assertions": [
                    {"probe": row[0], "assertion": row[1]} for row in non_surviving
                ],
                "reader_census": reader_census,
                "peer_health_today": today,
                "peer_health_post_a_append_order": post_a_append,
                "peer_health_post_a_migration_first": post_a_first,
                "post_a_append_order_identical": append_identical,
                "post_a_migration_first_identical": first_identical,
                "migration_first_matched_by_migration": matched_by_migration,
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
