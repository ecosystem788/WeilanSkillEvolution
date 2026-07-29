"""Read-only measurement of which acceptance assertions survive which phase.

Codex rejected wiring proposal v2 at 2026-07-29T10:29:53+09:00 on one point:

    v2's master gate says "all three probes exit 0", but changeset_v2_probe freezes
    pre-image facts as success conditions -- explicit kind counts (which A's append
    necessarily changes) and live-artifact facts (which D's deployment necessarily
    changes).  A pre-image measurement was being used as a post-image acceptance
    test, so the gate is unsatisfiable after its own changeset lands.

This probe answers that by measurement rather than by argument.  For every frozen
expectation in the three probes it asks: does this assertion survive phase A
(appending 8 canonical-migration entries) and phase D (deploying a candidate skill
artifact that ships the compiler)?

The post-A answer is measured, not reasoned: the eight migration entries are
constructed in memory from the real ledger, written to a temp corrections file
OUTSIDE the repo, and the real compile_view and the real probe decision functions
are run over the resulting 23-entry set.  Nothing in the repo is touched; the raw
and corrections sha256 are taken before and after to prove it.

The post-D answer is measured where it can be: a copy of the live skill tree with
the compiler added is tree-hashed in a temp dir, showing the frozen live-artifact
hash is necessarily violated by D.  The candidate's final hash is not knowable
until the candidate is frozen, so this probe measures that the assertion breaks,
not what it becomes.

Run from the repo root.  Exit 0 iff every frozen expectation below still holds.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

EVID = Path("proposals/correction-view-unwired-v0.1/evidence")
sys.path.insert(0, str(EVID))
sys.path.insert(0, str(Path("tools")))
sys.path.insert(0, str(Path("proposals/lineage-log-append-only-correction-v0.1")))

import triage_probe as T  # noqa: E402
import changeset_v2_probe as C2  # noqa: E402
import wiring_spec_probe as W  # noqa: E402
import compile_view as CV  # noqa: E402
import evolution_core as E  # noqa: E402

IMPL = Path("proposals/bounded-scheduler-v0.1/impl")
RAW = IMPL / "peer-chat.jsonl"
CORR = IMPL / "peer-chat.corrections.jsonl"
LIVE_SKILL = Path(r"D:\CodexData\skills\solve-with-weilan")
COMPILER = Path("proposals/lineage-log-append-only-correction-v0.1/compile_view.py")

# ---------------------------------------------------------------------------
# Frozen expectations.  Hand-entered literals; drift exits non-zero.
# ---------------------------------------------------------------------------

# Phase 0 (preflight) -- the state every probe was frozen against.
EXPECTED_PRE_ENTRY_COUNT = 15

# Phase A -- measured by running the REAL compiler over 15 real + 8 constructed
# entries.  This is the post-A counting surface Codex asked to be made explicit.
EXPECTED_POST_A_ENTRY_COUNT = 23
EXPECTED_POST_A_APPLIED = 8
EXPECTED_POST_A_REJECTIONS = {
    "before_hash_not_found": 6,
    "after_hash_mismatch": 8,
    "corrected_json_not_object": 1,
}
# G1 counts recomputed over the 23-entry set with changeset_v2_probe's own function.
EXPECTED_POST_A_LEGACY_COUNTS = {"overlay": 10, "batch-redaction": 1}
EXPECTED_POST_A_EXPLICIT_KINDS = {
    "re-pin": 1,
    "line-pointer-rebase": 2,
    "line-pointer-measured": 1,
    "canonical-migration": 8,
}
EXPECTED_POST_A_UNMATCHED_LEGACY = 0
# G2 set recomputed over the 23-entry set: must be unchanged (migration entries are
# not kind=overlay, so they never enter the C-class scan).
EXPECTED_POST_A_INVALID_HISTORICAL = dict(C2.EXPECTED_INVALID_HISTORICAL)

# Phase D -- the frozen live-artifact facts, and whether adding the compiler alone
# already violates them.
EXPECTED_PRE_LIVE_HAS_COMPILE_VIEW = False
EXPECTED_PRE_LIVE_TREE_HASH = C2.EXPECTED_LIVE_ARTIFACT_HASH
EXPECTED_CANDIDATE_HASH_DIFFERS = True

# The replica/compiler agreement that triage_probe's green currently rests on.
EXPECTED_REPLICA_AGREES_TODAY = True

# The assertion inventory.  survives_A / survives_D are the CLAIM; the measurements
# below either confirm or contradict each one that can be measured.
INVENTORY = [
    # (probe, assertion, survives_A, survives_D, note)
    ("changeset_v2_probe", "frozen legacy table digest", True, True,
     "pure code table; legacy is a closed set by construction"),
    ("changeset_v2_probe", "legacy kind counts == {overlay:10, batch-redaction:1}", True, True,
     "migration entries carry an explicit kind, so they never reach the legacy table"),
    ("changeset_v2_probe", "explicit kind counts == {re-pin:1, rebase:2, measured:1}", False, True,
     "A adds canonical-migration:8 -- this is the assertion Codex named"),
    ("changeset_v2_probe", "unmatched legacy == 0", True, True,
     "same reason as the legacy counts"),
    ("changeset_v2_probe", "invalid-historical set and codes", True, True,
     "the C-class scan is restricted to kind=overlay"),
    ("changeset_v2_probe", "skill path alias is directory-level", True, True,
     "filesystem topology, untouched by either phase"),
    ("changeset_v2_probe", "live skill is not a git worktree", True, True,
     "deployment convention copies a tree; it does not create a worktree"),
    ("changeset_v2_probe", "live has no compile_view", True, False,
     "D exists precisely to put the compiler in the live artifact"),
    ("changeset_v2_probe", "live tree_hash == 5fd0a51d...", True, False,
     "any content change to the deployed tree changes its tree hash"),
    ("triage_probe", "replicated reject distribution == archived 6/8/1", True, True,
     "MEASURED post-A below; migration entries are accepted, and accepted rows are "
     "excluded from the compared distribution"),
    ("triage_probe", "replica still describes the real compiler", True, False,
     "NOT named by Codex, and not a D-phase break either: it breaks at B. The replica "
     "is a hand copy (triage_probe.py:79-89), not an import, so it cannot notice that "
     "B changed the compiler's branch order. Its green survives and stops meaning what "
     "it means today."),
    ("wiring_spec_probe", "per-entry migration cost table (8 rows)", True, True,
     "indexed by physical line 1..15, which append-only growth does not move"),
    ("wiring_spec_probe", "raw untouched + 1:1 line mapping", True, True,
     "part 2 passes corrections=None and imports the in-repo compiler, not the live one"),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def load_records(raw_bytes: bytes):
    return [
        json.loads(line.decode("utf-8"))
        for line in raw_bytes.splitlines()
        if line.strip()
    ]


def build_migration_entries(records):
    """Construct the eight canonical-migration entries exactly as the proposal specifies.

    before_hash unchanged, corrected_json verbatim, after_hash = section 3 canonical of
    that same verbatim value, plus the supersession and provenance fields.  Nothing here
    is invented: every field is copied or derived from the entry being migrated.
    """
    out = []
    for n in W.A_CLASS:
        old = records[n - 1]
        corrected = old["corrected_json"]
        conv, _line, _state, frozen_after = W.EXPECTED_MIGRATION[n]
        after = sha(canonical(corrected))
        if after != frozen_after:
            raise SystemExit(
                f"#{n}: recomputed canonical after_hash {after} != frozen {frozen_after}"
            )
        out.append(
            {
                "kind": "canonical-migration",
                "before_hash": old["before_hash"],
                "corrected_json": corrected,
                "after_hash": after,
                "supersedes_after_hash": old.get("after_hash"),
                "migrated_from_convention": conv,
                "corrects": old.get("corrects"),
                "from": "claude",
                "reason": "encoding migration to DELEGATION section 3 canonical; "
                          "content authority remains with the superseded entry",
                "time": "SIMULATED",
                "time_authority": "clock",
            }
        )
    return out


def measure_post_a(records):
    """Run the REAL compiler over 15 real + 8 constructed entries, outside the repo."""
    migrations = build_migration_entries(records)
    combined = records + migrations

    tmp = Path(tempfile.mkdtemp(prefix="wl_phase_"))
    corr_sim = tmp / "sim.corrections.jsonl"
    corr_sim.write_bytes(
        b"".join(
            json.dumps(r, ensure_ascii=False).encode("utf-8") + b"\n" for r in combined
        )
    )
    result = CV.compile_view(RAW, corr_sim, tmp / "v.jsonl", tmp / "r.jsonl")
    rejections = [
        json.loads(l) for l in (tmp / "r.jsonl").read_bytes().decode("utf-8").splitlines() if l.strip()
    ]
    dist: dict[str, int] = {}
    for item in rejections:
        dist[item["reason"]] = dist.get(item["reason"], 0) + 1

    # the same G1/G2 functions changeset_v2_probe uses, over the 23-entry set
    legacy: dict[str, int] = {}
    explicit: dict[str, int] = {}
    unmatched = 0
    for rec in combined:
        kind, source = C2.record_kind(rec)
        if source == "explicit":
            explicit[kind] = explicit.get(kind, 0) + 1
        elif source == "frozen_legacy_signature":
            legacy[kind] = legacy.get(kind, 0) + 1
        else:
            unmatched += 1

    live_hashes, by_form = T.load_raw()
    codes = {}
    for rec in combined:
        kind, _ = C2.record_kind(rec)
        if kind != "overlay":
            continue
        got = C2.invalid_reason_code(rec, live_hashes, by_form)
        if got is not None:
            codes[rec["before_hash"]] = got[0]

    # triage_probe's compared distribution excludes accepted rows
    replicated: dict[str, int] = {}
    for rec in combined:
        reason = T.replicate_compile_view_reason(rec, live_hashes)
        replicated[reason] = replicated.get(reason, 0) + 1

    return {
        "entry_count": len(combined),
        "compiler_result": result,
        "compiler_rejections": dist,
        "g1_legacy": legacy,
        "g1_explicit": explicit,
        "g1_unmatched": unmatched,
        "g2_invalid_historical": codes,
        "triage_replicated_nonaccepted": {k: v for k, v in replicated.items() if k != "accepted"},
        "tmp": str(tmp),
    }


def measure_post_d():
    """Copy the live skill tree, add the compiler, tree-hash it -- does D break the freeze?"""
    tmp = Path(tempfile.mkdtemp(prefix="wl_cand_"))
    dest = tmp / "solve-with-weilan"
    shutil.copytree(
        LIVE_SKILL, dest, ignore=shutil.ignore_patterns("__pycache__")
    )
    pre = E.tree_hash(str(dest))
    shutil.copy2(COMPILER, dest / "scripts" / "compile_view.py")
    post = E.tree_hash(str(dest))
    return {
        "live_has_compile_view": (LIVE_SKILL / "scripts" / "compile_view.py").exists(),
        "live_tree_hash": E.tree_hash(str(LIVE_SKILL)),
        "copied_tree_hash": pre,
        "copy_reproduces_live_hash": pre == E.tree_hash(str(LIVE_SKILL)),
        "candidate_tree_hash_with_compiler": post,
        "candidate_differs_from_frozen": post != C2.EXPECTED_LIVE_ARTIFACT_HASH,
        "tmp": str(tmp),
    }


def measure_replica_agreement(records):
    """Does triage_probe's hand replica still describe the real compiler, today?"""
    live_hashes, _ = T.load_raw()
    accepted, rejected = CV._load_corrections(CORR, set(live_hashes))
    real = [item["reason"] for item in rejected]
    replica = [
        T.replicate_compile_view_reason(rec, live_hashes)
        for rec in records
        if T.replicate_compile_view_reason(rec, live_hashes) != "accepted"
    ]
    return {
        "real_compiler_rejections": real,
        "replica_rejections": replica,
        "agree": real == replica,
        "real_accepted": len(accepted),
    }


def main() -> int:
    failures = []
    raw_pre, corr_pre = sha(RAW.read_bytes()), sha(CORR.read_bytes())
    records = load_records(CORR.read_bytes())
    if len(records) != EXPECTED_PRE_ENTRY_COUNT:
        failures.append(f"preflight entry count drifted: {len(records)}")

    post_a = measure_post_a(records)
    post_d = measure_post_d()
    replica = measure_replica_agreement(records)

    if post_a["entry_count"] != EXPECTED_POST_A_ENTRY_COUNT:
        failures.append(f"post-A entry count: {post_a['entry_count']}")
    if post_a["compiler_result"].get("applied") != EXPECTED_POST_A_APPLIED:
        failures.append(f"post-A applied: {post_a['compiler_result']}")
    if post_a["compiler_rejections"] != EXPECTED_POST_A_REJECTIONS:
        failures.append(f"post-A compiler rejections: {post_a['compiler_rejections']}")
    if post_a["g1_legacy"] != EXPECTED_POST_A_LEGACY_COUNTS:
        failures.append(f"post-A legacy counts: {post_a['g1_legacy']}")
    if post_a["g1_explicit"] != EXPECTED_POST_A_EXPLICIT_KINDS:
        failures.append(f"post-A explicit kinds: {post_a['g1_explicit']}")
    if post_a["g1_unmatched"] != EXPECTED_POST_A_UNMATCHED_LEGACY:
        failures.append(f"post-A unmatched legacy: {post_a['g1_unmatched']}")
    if post_a["g2_invalid_historical"] != EXPECTED_POST_A_INVALID_HISTORICAL:
        failures.append(f"post-A invalid-historical: {post_a['g2_invalid_historical']}")
    if post_a["triage_replicated_nonaccepted"] != EXPECTED_POST_A_REJECTIONS:
        failures.append(
            f"post-A triage distribution: {post_a['triage_replicated_nonaccepted']}"
        )

    if post_d["live_has_compile_view"] != EXPECTED_PRE_LIVE_HAS_COMPILE_VIEW:
        failures.append("live skill already ships the compiler -- D's premise changed")
    if post_d["live_tree_hash"] != EXPECTED_PRE_LIVE_TREE_HASH:
        failures.append(f"live tree hash drifted: {post_d['live_tree_hash']}")
    if not post_d["copy_reproduces_live_hash"]:
        failures.append("the copied tree does not reproduce the live hash -- "
                        "the post-D measurement below would be meaningless")
    if post_d["candidate_differs_from_frozen"] != EXPECTED_CANDIDATE_HASH_DIFFERS:
        failures.append("adding the compiler did NOT change the tree hash")

    if replica["agree"] != EXPECTED_REPLICA_AGREES_TODAY:
        failures.append(f"replica/compiler agreement: {replica['agree']}")

    raw_post, corr_post = sha(RAW.read_bytes()), sha(CORR.read_bytes())
    if (raw_pre, corr_pre) != (raw_post, corr_post):
        failures.append("this probe modified the ledger -- it must not")

    print(json.dumps(
        {
            "ledger_untouched": (raw_pre, corr_pre) == (raw_post, corr_post),
            "raw_sha256": raw_pre,
            "corrections_sha256": corr_pre,
            "phase_0_entries": len(records),
            "phase_A_measured": post_a,
            "phase_D_measured": post_d,
            "replica_agreement_today": replica,
            "assertion_inventory": [
                {
                    "probe": p,
                    "assertion": a,
                    "survives_A": sa,
                    "survives_D_or_B": sd,
                    "note": note,
                }
                for p, a, sa, sd, note in INVENTORY
            ],
            "failures": failures,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
