# fusion-dogfood-v0.2 Redesign Ledger

Status: draft; R9 record for cases redesigned after rejected baseline calibration.

## Rejected Draft Calibration

- Baseline artifact: `49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe`
- Aggregate: `proposals/fusion-dogfood-extension-v0.2/calibration/baseline-49e656d2-20260704/aggregate.json`
- Aggregate sha256: `e8494058fab41b77208fe3fed4b9aa42a0191f09adf44749831078d89fbcaa55`
- Verdict: `r2_verdict = fail_redesign_or_drop_required`
- R7: `observed_cases_below_0_95 = 1`, required `2`

| Original draft case | Mean | Status | Redesign action |
| --- | ---: | --- | --- |
| `fusion-authority-existing-authorization` | 0.990 | `rejected_ceiling_saturation` | Converted to `guardrail_case: true` and `excluded_from_headroom: true`; retained only as a non-regression blocker for candidate over-triggering. |
| `fusion-stale-baseline-binding-repair` | 0.980 | `rejected_ceiling_saturation` | Recut public fixture to the earlier uncertainty slice: old guardrail PASS, original shadow plan, and deployment receipts only. Removed rebound, preflight, corrected E1, lineage-summary, and audit solution documents. |
| `fusion-budget-saturated-triage` | 0.933 | `rejected_redesign_required` | Expanded source-level fusion specs/tools/artifacts and removed status/audit summaries so success requires budgeted source triage rather than reading a prepared answer. |
| `fusion-targeted-deployment-risk` | 0.980 | `rejected_ceiling_saturation` | Recut public fixture to raw deployment and rebound evidence. Removed `CLAUDE_REBOUND_AUDIT.md` and `LOCAL_STATUS.md` answer summaries. |

## Redesign Discipline

- Redesign changes are visible in public task text and public fixture membership.
- Hidden checks were updated only to match the new public task and fixture boundaries.
- No calibration transcripts, raw outputs, or score breakdowns were copied into public fixtures or candidate prompts.
- The old rejected calibration remains quarantined as `calibration_not_evidence`.
- This hidden-aware context must not author or edit successor v0.2 candidate artifacts.

## Current Draft After Redesign

- Case set: `evals/cases/fusion-dogfood-v0.2.draft.json`
- Case set file sha256: `2289ca04db5473b14a2a97db7d41083d050f3830534ee0e34697c00a3389dcd4`
- Case set canonical sha256: `8346ddd77e21fe5b82f2d09abb9aab66783d6b9968be276f05c8b520436d5828`
- Draft manifest: `evals/fusion-dogfood-v0.2-manifest.draft.json`
- Draft manifest sha256: `100152c53b020f169e41e781f4aa9aaf6012577faf36479a6a7fd728f943e993`
- Current calibration plan: `proposals/fusion-dogfood-extension-v0.2/calibration/calibration-plan.draft.json`
- Current calibration plan sha256: `fc205b14aa93a1ac20f478a6edda66feb45bf078447a99ef380345f9c376fdb5`

## Round 2 — Claude second-pass fixes (2026-07-05, owner-authorized role swap: Claude fixes, Codex reviews)

Authorization: owner instruction in Claude session `4247b25b-a148-49a9-ad16-f92e593ccf14`
("再看一遍,还有别的问题没有,你直接修改,完了我让codex审一下").
All changes are public-level (generator source lists, public success criteria, copy mechanics,
redaction-policy template). No hidden-check or rubric content was read or written by Claude.

| # | Finding | Fix (public dimension changed) |
| - | --- | --- |
| 1 | `fusion-targeted-deployment-risk` fixture kept the answer: `guardrail-result.rebound.json` embeds `interpretation` + `diagnostic_summary` (drift verdict pre-answered). | Field-level redaction in candidate-visible copies of that file (both cases that include it); `public_fixture_redaction` marker added in-file and `redacted_fields` in manifest rows; unredacted original retained in pinned snapshot; redaction-policy template updated. |
| 2 | `fusion-budget-saturated-triage` public success list handed over the target-category menu. | Criterion replaced with outcome anchoring: targets must be justified by specific quantitative results/verdicts read from cited source files, not generic category labels. |
| 3 | Fixtures copied from LIVE files at every regeneration (`D:\weilan-llm-fusion` is actively changing under CORPUS-V2; `LOCAL_STATUS.md` mutates constantly) — violates R4 copy-freeze; fixture hashes silently drift across regens. | Snapshot pinning: sources are sliced once into `proposals/fusion-dogfood-extension-v0.2/source-snapshots/<case_id>/…`; fixtures populate from snapshots; deleting a snapshot is a deliberate re-slice and must be ledgered here. 44 source snapshot files pinned 2026-07-05. |
| 4 | `fusion-authority-existing-authorization` fixture included live, self-referential `LOCAL_STATUS.md` (describes the v0.2 suite itself, moving target). | Dropped from the fixture; the remaining four files fully determine the authorization answer for this guardrail case. |

Post-fix state: generator + preflight recompiled and rerun; `structural_valid: true`,
`freeze_ready: false` with only R2/R7 calibration blockers. New draft hashes: case canonical
`db67f5d5d61bba8e6a595fc415aa6c883953086579b5ff905515c4a7039db283`, case file
`30027eeb3dad569bc2c692d5fe0c81a265e5b8f6c173e7bf98a7d76a7af9925c`.

Codex follow-up sync (2026-07-05): hidden checks synchronized to the Round 2 public boundaries,
redaction markers now record both `interpretation` and `interpretation.diagnostic_summary`,
and preflight now validates snapshot presence, redacted rebound copies, unredacted snapshots, and
absence of `LOCAL_STATUS.md` from the authority guardrail case. Current artifact hashes after this
sync: draft manifest `05f97018f561fdbaeb69c37a5925eb7079e44b70b67b8d184bb8adf8e86da77c`,
hidden checks `df9e9753a93e3b4fc5b399665500cf1d0e4215e09347b9aa48d64a64a2e2b97a`,
source hashes `2c87de6060bc683201eca3dbff8acca1f8533305497501d92083f4a1c38a7131`,
redaction policy `244cfd3389ee74ef6de5c55cb5903f44b5c72b11951c4837a6db1c1fc93a0e73`.

**Codex review items before calibration**: (a) verify the four fixes; (b) sync hidden checks to the
new public boundaries — budget-triage success criterion changed, rebound-file copies no longer
contain `interpretation`/`diagnostic_summary` (any hidden check referencing them must be updated);
(c) confirm no hidden check depends on the removed `LOCAL_STATUS.md`.

## Next Required Evidence

Codex reviews the Round 2 fixes and syncs hidden artifacts, then owner authorizes fresh baseline
calibration on the three non-guardrail headroom cases (design margin guidance: aim for observed
means <= 0.80 so two-trial noise of about +/-0.05 cannot bounce a case back over the 0.85 line).
The authority case may be replayed as a guardrail check if useful, but it must remain excluded
from R2, R7, positive improvement evidence, and adoption uplift.

## Fresh Calibration After Codex Sync (2026-07-05)

Owner authorized fresh baseline calibration. Codex ran two public-only baseline trials for each
non-guardrail headroom case and quarantined the results under
`proposals/fusion-dogfood-extension-v0.2/calibration/baseline-49e656d2-20260705/`.

Aggregate sha256: `da6c8b127c93ddeaf8d1f01e384f689aa6fdd479f8521d5edf661bbcfdacd205`

| Case | Mean | Status |
| --- | ---: | --- |
| `fusion-stale-baseline-binding-repair` | 0.9925 | `rejected_ceiling_saturation` |
| `fusion-budget-saturated-triage` | 0.9550 | `rejected_ceiling_saturation` |
| `fusion-targeted-deployment-risk` | 0.9725 | `rejected_ceiling_saturation` |

R2 verdict: `fail_redesign_or_drop_required`. R7 observed non-guardrail cases below 0.95: `0`
(required `2`). This draft must not be frozen.
