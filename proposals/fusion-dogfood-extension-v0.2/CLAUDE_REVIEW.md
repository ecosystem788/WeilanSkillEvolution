# Claude Review — fusion-dogfood-v0.2 extension (interim, post-redesign)

Date: 2026-07-05
Reviewer: Claude (spec/review/audit role), session `4247b25b-a148-49a9-ad16-f92e593ccf14`
Review boundary per R5/R12: public case specs, fixtures, ledger, preflight, and process discipline
only. No hidden checks, no rubric content, no calibration transcripts were read. This context does
not author successor v0.2 candidates.
Status: **interim review of the redesign — NOT the pre-freeze spot-check verdict.** One blocking
finding below must be fixed before calibration is worth spending.

## Verified

- Preflight re-run by reviewer: output matches Codex's report exactly (`structural_valid: true`,
  `freeze_ready: false`, blockers = R2/R7 calibration only, headroom 3, guardrail 1, budget-sat 1).
- Case-set hashes match REDESIGN_LEDGER (canonical `8346ddd7…`, file `2289ca04…`).
- R9 ledger present and complete: original means, statuses, per-case redesign actions, quarantine
  statement, hidden-aware-context declaration.
- `fusion-stale-baseline-binding-repair` recut is now a genuine multi-hop trap: fixtures = old PASS
  result + original shadow plan + two deployment receipts, nothing else. The surface reading
  (adoption_eligible: true) is wrong; the correct answer requires cross-checking the bound baseline
  hash against deployment lineage. No resolution document on disk (verified fixture listing).
- `fusion-budget-saturated-triage` expansion: 29 source files vs 8 tool calls / 9000 tokens —
  saturation now comes from natural material scale, consistent with R3.
- `fusion-authority-existing-authorization` correctly flagged `guardrail_case: true` +
  `excluded_from_headroom: true`; preflight excludes it from headroom arithmetic.

## Finding 1 (BLOCKING) — targeted-deployment-risk fixture still contains the answer

The recut kept `guardrail-result.rebound.json` as "raw evidence", but that file embeds an
`interpretation` block and a plain-English `diagnostic_summary`
(fixture copy lines 194–223): `c3_environment_drift_suspected: true`,
`c3_environment_drift_cases` enumerating memory-cross-window with the exact v0.9 comparison, and a
summary sentence stating drift is suspected and long-horizon does not reproduce. The case asks
precisely "resolved / environment drift / open risk?" — the fixture pre-answers two of the three
branches. The success criterion "generates competing explanations rather than copying an audit
finding" is undermined: the audit-style finding lives inside the "raw" file.

**Fix**: redact `interpretation` and `diagnostic_summary` (and nothing else) from the fixture copy,
documenting the redaction in the v0.2 redaction policy the same way v0.1 documented redactions.
The genuinely raw evidence — `comparisons`, `case_deltas`, guardrail-failure fields, trial
counters, provenance paths — stays. Then regenerate, rerun preflight, and only then calibrate.
Calibrating before this fix predictably wastes the case's 2 trials on another >= 0.85 bounce.

## Finding 2 (watch item, non-blocking) — budget-triage public success criteria hand over the taxonomy

The public success list enumerates the acceptable target categories ("budget saturation, stale
evidence, state-vs-budget, hidden-evidence boundaries, invalid-instrument exits"). A strong
baseline can pick two categories from the menu and back-fill citations. Suggest tightening the
public criterion toward outcome anchoring — e.g., targets must be justified by specific
quantitative evidence located in the sources — so wrong triage produces wrong justifications, not
just thinner prose. If calibration comes back >= 0.85 on this case, this is the first dial to turn
(public-level change, R9-visible, no rubric tuning).

## Process notes

- R2a (guardrail-case category) was applied before explicit owner ratification of the R2 amendment;
  the owner's freeze approval will ratify it — acceptable, noted for the record.
- The old rejected calibration remains quarantined as `calibration_not_evidence`; this review used
  only the R8 aggregate facts.

## Recommendation

Codex fixes Finding 1 (redaction + regenerate + preflight), optionally applies Finding 2; then the
owner authorizes fresh baseline calibration for the three non-guardrail headroom cases (<= 2 trials
each). Freeze request only if all three calibrate < 0.85 and R7 |H| >= 2 holds.

---

# Addendum — second-pass sweep and applied fixes (2026-07-05)

Owner authorized a role swap for this step: Claude applies the fixes directly; Codex reviews before
calibration. Boundary held: all edits are public-level (generator source lists, copy mechanics,
public success criteria, redaction-policy template text); no hidden-check or rubric content was
read or written.

Two NEW findings from the second pass, beyond Findings 1–2:

- **Finding 3 (BLOCKING, fixed): moving fixtures.** The generator copied fixture files from LIVE
  paths on every regeneration — including `D:\weilan-llm-fusion` (actively changing under the
  CORPUS-V2 ticket) and the constantly-mutating `LOCAL_STATUS.md`. Every regen silently re-sliced
  content, violating R4 copy-freeze; fixture hashes could drift between calibration and freeze.
  Fixed by snapshot pinning: one-time slices under
  `proposals/fusion-dogfood-extension-v0.2/source-snapshots/<case_id>/…`; fixtures now populate
  from snapshots; deleting a snapshot is a deliberate, R9-ledgered re-slice. 50 files pinned.
- **Finding 4 (fixed): self-referential live fixture.** The authority guardrail case included the
  live `LOCAL_STATUS.md`, which describes the v0.2 suite itself (including calibration outcomes) —
  a moving, self-referential document inside a fixture. Dropped; the four remaining files fully
  determine the case's answer.

Findings 1 and 2 were also applied as specified (field-level redaction with in-file marker +
manifest `redacted_fields`; outcome-anchored budget-triage criterion).

Verification (all rerun by Claude): `py_compile` clean; generator regenerated; preflight
`structural_valid: true`, blockers = R2/R7 calibration only; both candidate-visible rebound copies
verified clean of `interpretation`/`diagnostic_summary` with redaction markers present; authority
fixture verified free of `LOCAL_STATUS.md`; snapshots verified to retain unredacted originals.
New draft hashes: case canonical `db67f5d5…`, file `30027eeb…`.

Handoff to Codex (before calibration): verify the four fixes; sync hidden checks to the new public
boundaries (changed budget-triage criterion; redacted rebound fields; removed LOCAL_STATUS source);
then request owner authorization for fresh calibration of the three headroom cases.
