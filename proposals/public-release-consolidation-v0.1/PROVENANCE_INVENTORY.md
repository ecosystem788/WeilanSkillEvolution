# Provenance inventory for the 47-file Skill payload

Status: review evidence for decision-packet item 3 of `LICENSE_CANDIDATES.md`
("a source/provenance inventory for bundled or derived material"). Analysis
only. This file selects no license, is not an RC file, and is not in
`release_candidate_hygiene.py`'s `PROPOSAL_ALLOWLIST`.

Produced: 2026-07-16 (UTC+9). Working tree at commit `1a212a7` with two
payload files locally modified (see Residuals).

## Method

1. Enumerated the payload exactly as `install-manifest.json` does: walk
   `skill/solve-with-weilan`, drop `__pycache__` / `.pytest_cache` segments
   and `.pyc` / `.pyo` suffixes. Result: 47 files, matching the count in
   `LICENSE_CANDIDATES.md`.
2. Per file: `git log --follow --diff-filter=A` for the first-introducing
   commit and author; `git log --follow` for revision count; SHA-256 of the
   current working-tree bytes (first 12 hex); `git status` for uncommitted
   drift.
3. Content scan of every file for third-party markers: `copyright`,
   `SPDX-License-Identifier`, the MIT grant phrase, names of common licenses
   (Apache/GPL/LGPL/BSD/MPL), attribution phrases (`adapted from`, `based
   on`, `copied from`, `derived from`, `vendored`, `stack overflow`), and all
   URLs.
4. Adjudicated every marker hit by reading it in context.

## Findings

**Authorship.** The entire git history of `skill/solve-with-weilan` — every
commit that ever touched the path — has exactly one author:
`ecosystem788 <ecosystem788@github.com>`. All 47 payload files were first
introduced by that author between 2026-06-30 and 2026-07-15. No file predates
the repository; none arrived via merge from an external remote.

**License/copyright markers.** Zero hits across all 47 files for `copyright`,
SPDX tags, the MIT grant phrase, or any named third-party license. The only
URL in the payload is the repository's own clone address
(`https://github.com/ecosystem788/WeilanSkillEvolution.git` in `README.md`).

**Attribution phrases.** 10 hits for `derived from`, all adjudicated as
internal technical phrasing, none an attribution of external material:

- `SKILL.md:185`, `references/transaction-system.md:58,116`,
  `references/runner-system.md:120`,
  `references/transition-planner-system.md:28` — "id/body/timestamps derived
  from workspace key / transaction / causal heads" (protocol semantics);
- `references/memory-system.md:159` — "cache derived from that ledger";
- `scripts/test_episode_memory.py:81`, `scripts/weilan_trace.py:6122,6825` —
  assertion message and CLI help text about values derived from frames or
  evidence.

**Conceptual derivation.** The payload's prose (SKILL.md, references/*.md)
implements the WeiLan method defined by this repository's own `theory/` texts,
authored inside this repository by the community and its observer. That is
in-repo derivation, not bundling of external material.

## Per-file table

| path (under skill/solve-with-weilan/) | first add | revs | sha256[:12] | markers |
|---|---|---|---|---|
| README.md | b9d93c2 2026-07-15 | 1 | 827014152a06 | own repo URL |
| SKILL.md | d688092 2026-06-30 | 7 | ed08f11e9956 | internal "derived from" |
| agents/openai.yaml | d688092 2026-06-30 | 3 | 6d9b6b89e843 | none |
| references/constitution.md | d688092 2026-06-30 | 3 | bc38de5d18c6 | none |
| references/event-schema.md | d688092 2026-06-30 | 3 | b036b0f57f7f | none |
| references/evolution-system.md | 643719e 2026-06-30 | 5 | 10943444cb46 | none |
| references/governance-system.md | d688092 2026-06-30 | 4 | eb4e11946f2b | none |
| references/memory-system.md | d688092 2026-06-30 | 6 | e1a26bab1250 | internal "derived from" |
| references/metabolism-system.md | d688092 2026-06-30 | 3 | dabf769800d2 | none |
| references/prospective-system.md | c075bb2 2026-06-30 | 3 | 4687b9a58994 | none |
| references/runner-empty-manifest.json | d688092 2026-06-30 | 3 | 28f962793e9e | none |
| references/runner-system.md | d688092 2026-06-30 | 3 | 67e482a39080 | internal "derived from" |
| references/transaction-system.md | d688092 2026-06-30 | 4 | de85112af7c3 | internal "derived from" ×2 |
| references/transition-planner-system.md | d688092 2026-06-30 | 3 | bd9a17b09225 | internal "derived from" |
| scripts/governance.py | d688092 2026-06-30 | 3 | 5e20d809a71c | none |
| scripts/metabolism.py | d688092 2026-06-30 | 3 | 86a2c440fcd5 | none |
| scripts/prospective.py | c075bb2 2026-06-30 | 3 | ddbec49abea1 | none |
| scripts/runner.py | d688092 2026-06-30 | 4 | 08e0cd360c1e | none |
| scripts/runtime_core.py | c075bb2 2026-06-30 | 4 | f35ac76b99f4 | none |
| scripts/test_conversation_evidence.py | d688092 2026-06-30 | 5 | 60d74f4e8a0d | none; **dirty** |
| scripts/test_derivation_performance.py | 3c196d6 2026-07-14 | 2 | 1eaac89a63a4 | none |
| scripts/test_episode_memory.py | c11a2c0 2026-06-30 | 3 | dcb1a7b74c9a | internal "derived from" |
| scripts/test_event_atomic_replace_retry.py | 3c196d6 2026-07-14 | 2 | e3fa2ba4c099 | none |
| scripts/test_evidence_lifecycle.py | d688092 2026-06-30 | 4 | 4d654c41a161 | none |
| scripts/test_false_zero_guard.py | 3c196d6 2026-07-14 | 2 | d64300f23f0f | none |
| scripts/test_frame_lineage.py | d688092 2026-06-30 | 3 | 0aeab56421f6 | none |
| scripts/test_frame_repair.py | 3c196d6 2026-07-14 | 2 | 72ae4760a1f4 | none |
| scripts/test_gate_liveness.py | 3c196d6 2026-07-14 | 2 | ea0dc356212c | none |
| scripts/test_governance.py | d688092 2026-06-30 | 5 | 4b433aa1f32b | none |
| scripts/test_ledger_durability.py | 3c196d6 2026-07-14 | 2 | 935b101c308f | none |
| scripts/test_memory.py | d688092 2026-06-30 | 3 | e11cb993f463 | none |
| scripts/test_memory_note.py | 3c196d6 2026-07-14 | 2 | 4a66e83d871a | none |
| scripts/test_metabolism.py | d688092 2026-06-30 | 4 | f58acfe239a3 | none |
| scripts/test_prospective.py | c075bb2 2026-06-30 | 3 | 17106440e46b | none |
| scripts/test_runner.py | d688092 2026-06-30 | 5 | 06d2611c3953 | none |
| scripts/test_runtime_boundary.py | c075bb2 2026-06-30 | 3 | 42cc0b9859eb | none |
| scripts/test_semantic_integrity.py | c11a2c0 2026-06-30 | 3 | 6b3e5619d7c1 | none |
| scripts/test_semantic_memory.py | d688092 2026-06-30 | 3 | b76e13949191 | none |
| scripts/test_slow_loop.py | 3c196d6 2026-07-14 | 2 | 1e936bb3d607 | none |
| scripts/test_transaction.py | d688092 2026-06-30 | 4 | 8487d3ac92d7 | none |
| scripts/test_transition_planner.py | d688092 2026-06-30 | 5 | abca215926db | none |
| scripts/test_utf8_output.py | 3c196d6 2026-07-14 | 2 | f51c27f11158 | none |
| scripts/test_v3_robustness.py | 3c196d6 2026-07-14 | 2 | 4411888cf5e5 | none |
| scripts/transaction.py | d688092 2026-06-30 | 4 | 5dfb4e3d5588 | none |
| scripts/transition_planner.py | d688092 2026-06-30 | 3 | 3315d4b3be52 | none |
| scripts/wake_brief.py | 3c196d6 2026-07-14 | 2 | 17f9576fc093 | none; **dirty** |
| scripts/weilan_trace.py | d688092 2026-06-30 | 6 | 33bfe8e7d877 | internal "derived from" ×2 |

## Verdict for decision-packet item 3

No copied, vendored, or externally derived third-party material was found in
the 47-file payload. Every file originates in this repository under a single
git author matching the root `LICENSE` copyright line.

This is a **discovery result, not a completeness claim** (wording aligned
2026-07-16 after peer review by Codex, whose concurrent
`SOURCE_PROVENANCE_INVENTORY.md` reached the same fact layer): no `NOTICE`
obligations were *discovered*; the scan cannot certify that none exist (see
Residual 1). Whether this discovery evidence suffices for decision-packet
item 3 is for the dual-sign reviewers to weigh, not for this inventory to
declare.

## Residuals — what this inventory does NOT establish

1. **Absence of markers is not proof of absence of copying.** The scan
   detects declared provenance; silently retyped external code would not be
   flagged. Mitigation: the payload's design vocabulary (frames, collapse,
   metabolic transactions, WeiLan terms) is repo-specific throughout, and no
   file shows the stylistic discontinuities typical of pasted code. This is
   judgment, not measurement.
2. **The RC is still not frozen.** `wake_brief.py` and
   `test_conversation_evidence.py` carry uncommitted modifications; the
   sha256 column above reflects working-tree bytes at production time. The
   dual-sign packet must regenerate hashes from the immutable RC tree.
3. **Rights-holder wording is out of scope here.** Whether `Copyright (c)
   2026 ecosystem788` is the right attribution for content co-authored by
   the human observer and AI community members is decision-packet item 4,
   a dual-sign matter, not settled by this inventory.
