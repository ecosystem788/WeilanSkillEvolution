"""Read-only measurement of the three load-bearing gaps Codex named at 2026-07-29T09:48:58+09:00.

Codex rejected wiring proposal v1 with three "undefined, cannot be left for the
implementer to guess" points:

    G1  #3 actually has kind=null, yet the proposal calls overlay the default AND
        calls #3 a batch-redaction.  A frozen, machine-checkable legacy
        discriminator is required -- no free-text, no fuzzy shape guessing.
    G2  C's preimage_redacted / preimage_eol_normalized must be recomputable from
        named structured fields by a named algorithm -- not hardcoded per entry
        ordinal, not parsed out of reason/chain prose.
    G3  D's deployment and rollback statements do not hold: the live skill has no
        compile_view dependency, and it is not a Git worktree, so git revert
        cannot roll it back.

This probe measures what each gap needs and freezes the answer as literals.  It
decides nothing.  Every expectation below is a hand-entered literal checked
against a fresh measurement; drift exits non-zero.

Run from the repo root.  Writes nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path("proposals/correction-view-unwired-v0.1/evidence")))
sys.path.insert(0, str(Path("tools")))

import triage_probe as T  # noqa: E402  frozen convention tables live there
import evolution_core as E  # noqa: E402  the existing artifact/tree-hash machinery

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
CORR = IMPL / "peer-chat.corrections.jsonl"

# The deployment target.  C:\Users\zy\.claude\skills is a directory junction whose
# realpath is D:\CodexData\skills -- the aliasing is directory-level, not per-file,
# so there is exactly one target and the existing deployment convention already
# names it (weilan_targeted_deployment_intent_v0.1, deploy-20260710-fefc8be1).
CLAUDE_SKILLS = r"C:\Users\zy\.claude\skills"
CODEX_SKILLS = r"D:\CodexData\skills"
LIVE_SKILL = r"D:\CodexData\skills\solve-with-weilan"

# ---------------------------------------------------------------------------
# G1: frozen legacy record-kind discriminator
# ---------------------------------------------------------------------------
# Key = the entry's exact sorted key set.  Structural, not ordinal.  Legacy is a
# closed set by construction: every new entry must carry an explicit kind, so this
# table can be frozen once and never grows.  An entry with no kind whose signature
# is absent from the table is NOT guessed -- it is unknown_record_kind.
LEGACY_SIGNATURES = {
    (
        "after_hash",
        "before_hash",
        "corrected_json",
        "corrects",
        "reason",
    ): "overlay",
    (
        "after_hash",
        "before_hash",
        "corrected_json",
        "corrects",
        "from",
        "reason",
        "time",
    ): "overlay",
    (
        "after_hash",
        "before_hash",
        "before_hash_convention",
        "corrected_json",
        "corrects",
        "from",
        "reason",
        "sentinel_equiv_convention",
        "sentinel_equiv_hash",
        "time",
    ): "overlay",
    (
        "after_hash",
        "after_hash_convention",
        "before_hash",
        "before_hash_convention",
        "corrected_json",
        "corrects",
        "from",
        "reason",
        "time",
        "time_authority",
    ): "overlay",
    (
        "corrects",
        "files",
        "from",
        "note",
        "reason",
        "time",
    ): "batch-redaction",
}

# 10 legacy overlays (four distinct signatures: 2 + 1 + 3 + 4) + #3 = 11 legacy
# entries; the remaining 4 carry an explicit kind.
EXPECTED_LEGACY_COUNTS = {"overlay": 10, "batch-redaction": 1}
EXPECTED_EXPLICIT_KINDS = {"re-pin": 1, "line-pointer-rebase": 2, "line-pointer-measured": 1}
EXPECTED_UNKNOWN_LEGACY = 0
# Digest over the frozen table itself, so a silent edit to it also trips.
EXPECTED_TABLE_DIGEST = "b261880abc2a95931db652e35cef177948d7c34aba48b398e2733854271c9856"

# ---------------------------------------------------------------------------
# G2: reason codes, recomputed from structured fields only
# ---------------------------------------------------------------------------
# Inputs: before_hash, corrected_json, after_hash (structured fields) plus the raw
# ledger bytes plus the two frozen convention tables in triage_probe.  No ordinals,
# no prose.  Codes are named after what is MEASURED; the diagnosed cause travels in
# a separate, explicitly non-load-bearing field.
CODE_EOL_VARIANT = "preimage_only_under_eol_variant"
CODE_SELF_INCONSISTENT = "preimage_unresolvable_and_entry_self_inconsistent"
CODE_UNDETERMINED = "preimage_unresolvable_cause_undetermined"

DIAGNOSIS = {
    CODE_EOL_VARIANT: "preimage_eol_normalized (inference, not measurement)",
    CODE_SELF_INCONSISTENT: "preimage_redacted (inference, not measurement)",
    CODE_UNDETERMINED: None,
}

# Frozen by before_hash -- a structured field of the entry, not its position.
EXPECTED_INVALID_HISTORICAL = {
    "d201d3e244ae2afc497f36fbe87fb8a3e6e47c4d9ce7a6c8262d3c73f71a2cfc": CODE_EOL_VARIANT,
    "e0d4ad52e85f2966e1a173c45c8566e82d7bd45a6b463bb23cdc0a378760c240": CODE_SELF_INCONSISTENT,
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def record_kind(rec):
    """G1: explicit kind wins; otherwise the frozen signature table; otherwise unknown."""
    kind = rec.get("kind")
    if isinstance(kind, str) and kind:
        return kind, "explicit"
    signature = tuple(sorted(rec.keys()))
    if signature in LEGACY_SIGNATURES:
        return LEGACY_SIGNATURES[signature], "frozen_legacy_signature"
    return "unknown_record_kind", "unmatched"


def invalid_reason_code(rec, live_hashes, by_form):
    """G2: for an overlay whose before_hash resolves to no live line, which code applies.

    Returns None when the binding is live (not a C-class entry at all).
    """
    before = rec.get("before_hash")
    if not isinstance(before, str):
        return None
    if before in live_hashes:
        return None
    hit_forms = sorted(f for f, idx in by_form.items() if before in idx)
    if hit_forms:
        return CODE_EOL_VARIANT, {"resolving_eol_forms": hit_forms}
    corrected = rec.get("corrected_json")
    if isinstance(corrected, dict):
        self_ok = sorted(
            name
            for name, fn in T.AFTER_CONVENTIONS.items()
            if rec.get("after_hash") == sha(fn(corrected))
        )
        if not self_ok:
            return CODE_SELF_INCONSISTENT, {"after_hash_verifies_under": []}
    return CODE_UNDETERMINED, {}


def main() -> int:
    failures = []

    table_digest = sha(
        canonical(sorted([list(k), v] for k, v in LEGACY_SIGNATURES.items()))
    )
    if table_digest != EXPECTED_TABLE_DIGEST:
        failures.append(f"frozen table digest drifted: {table_digest}")

    live_hashes, by_form = T.load_raw()
    records = [
        json.loads(line)
        for line in CORR.read_bytes().decode("utf-8").splitlines()
        if line.strip()
    ]

    # -- G1 -----------------------------------------------------------------
    legacy_counts: dict[str, int] = {}
    explicit_counts: dict[str, int] = {}
    unknown_legacy = 0
    for rec in records:
        kind, source = record_kind(rec)
        if source == "explicit":
            explicit_counts[kind] = explicit_counts.get(kind, 0) + 1
        elif source == "frozen_legacy_signature":
            legacy_counts[kind] = legacy_counts.get(kind, 0) + 1
        else:
            unknown_legacy += 1
    if legacy_counts != EXPECTED_LEGACY_COUNTS:
        failures.append(f"legacy kind counts drifted: {legacy_counts}")
    if explicit_counts != EXPECTED_EXPLICIT_KINDS:
        failures.append(f"explicit kind counts drifted: {explicit_counts}")
    if unknown_legacy != EXPECTED_UNKNOWN_LEGACY:
        failures.append(f"unmatched legacy entries: {unknown_legacy}")

    # -- G2 -----------------------------------------------------------------
    measured_codes = {}
    for rec in records:
        kind, _ = record_kind(rec)
        if kind != "overlay":
            continue
        result = invalid_reason_code(rec, live_hashes, by_form)
        if result is None:
            continue
        code, detail = result
        measured_codes[rec["before_hash"]] = {"code": code, "detail": detail}
    measured_map = {k: v["code"] for k, v in measured_codes.items()}
    if measured_map != EXPECTED_INVALID_HISTORICAL:
        failures.append(f"invalid-historical set or codes drifted: {measured_map}")
    if CODE_UNDETERMINED in measured_map.values():
        failures.append("an entry fell into the fail-closed undetermined branch")

    # -- G3 -----------------------------------------------------------------
    deployment = {
        "claude_skills_realpath": os.path.realpath(CLAUDE_SKILLS),
        "codex_skills_realpath": os.path.realpath(CODEX_SKILLS),
        "alias_is_directory_level": os.path.realpath(CLAUDE_SKILLS)
        == os.path.realpath(CODEX_SKILLS),
        "live_skill_is_git_worktree": Path(LIVE_SKILL, ".git").exists(),
        "live_has_compile_view": Path(LIVE_SKILL, "scripts", "compile_view.py").exists(),
        "live_artifact_tree_hash": E.tree_hash(LIVE_SKILL),
    }
    if not deployment["alias_is_directory_level"]:
        failures.append("the two skill paths no longer resolve to one directory")
    if deployment["live_skill_is_git_worktree"]:
        failures.append("live skill is now a git worktree -- the rollback argument changes")
    if deployment["live_has_compile_view"]:
        failures.append("live skill already ships compile_view -- D's premise changed")
    if deployment["live_artifact_tree_hash"] != EXPECTED_LIVE_ARTIFACT_HASH:
        failures.append(
            "live artifact hash drifted from the frozen deployment base: "
            + deployment["live_artifact_tree_hash"]
        )

    report = {
        "g1_legacy_kind_counts": legacy_counts,
        "g1_explicit_kind_counts": explicit_counts,
        "g1_unmatched_legacy": unknown_legacy,
        "g1_frozen_table_digest": table_digest,
        "g2_invalid_historical": measured_codes,
        "g2_diagnosis_is_non_load_bearing": DIAGNOSIS,
        "g3_deployment": deployment,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if failures else 0


EXPECTED_LIVE_ARTIFACT_HASH = (
    "5fd0a51dc7f539e2b3f1c45f5a505d9ddea80c721de8d94fe04d7e9de52ad0ad"
)


if __name__ == "__main__":
    raise SystemExit(main())
