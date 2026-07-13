# fusion-dogfood-v0.2 Suite Extension — Requirements Spec

Date: 2026-07-04
Author: Claude (spec/review role)
Owner authorization to prepare the extension:
`conversation:4247b25b-a148-49a9-ad16-f92e593ccf14#aeecd859-10c6-4f62-9922-942e24aa18ea`
Status: requirements only. Case engineering is Codex work; approval/freeze is owner-only.
`fusion-dogfood-v0.1` stays frozen and unchanged; the extension produces a **superseding suite
`fusion-dogfood-v0.2`** = the eight v0.1 cases (verbatim, same hashes) + new cases below.

## Why (from CLAUDE_E1_AUDIT.md)

E1 showed the v0.1 suite cannot demonstrate method value: baseline fails almost nowhere (2/8 cases
below the 0.95 saturation line), so method gates can only fire decoratively, and the Eval-2
headroom rule (|H| >= 2) is arithmetically unsatisfiable after one adoption. Method value is only
observable where the baseline actually fails — and per the theory line, especially where budgets
saturate. The extension's one-line goal: **build cases where the deployed baseline predictably
fails in ways the method's gates govern.**

## Requirements

R1. **Count and levels.** Add 4–6 new hard cases (L2/L3). **All new cases use `trial_count = 2`**
    (E1 lesson: a single-trial case can never satisfy the 2/2 reproduction clause, wasting its
    method-impact evidence).

R2. **Headroom, verified not assumed.** Each new case must show real baseline failure headroom:
    at most 2 calibration trials per case against the deployed baseline (`49e656d2…`) before
    freeze, expecting baseline mean < 0.85. Calibration runs are recorded as
    `calibration_not_evidence` and never cited as official scores. A case that calibrates at
    >= 0.85 is redesigned or dropped, not frozen; >= 0.95 is recorded specifically as a
    ceiling-saturation rejection.

R2a. **Guardrail cases are allowed but quarantined from improvement evidence.** A case may be
     marked `guardrail_case: true` only when it is designed to catch candidate regressions on an
     already-solved baseline behavior. Guardrail cases must also set `excluded_from_headroom: true`;
     they do not count toward R2 headroom, R7 |H| arithmetic, positive improvement evidence, or
     adoption uplift. They may only act as non-regression blockers: a candidate that performs worse
     than the deployed baseline on a guardrail case fails that guardrail, but passing it does not
     add positive evidence.

R3. **At least one budget-saturation case.** Tool-call and context-token budgets set so that
    indiscriminate reading exhausts the budget before completion — success requires explicit
    prioritization and tradeoff under the budget. This is the P4-side probe of the junction claim
    (value appears under budget saturation) and must be flagged
    `budget_saturation_case: true` in the case spec. Saturation must be reached by the natural
    scale of the real fixture material, not by an absurdly tiny budget (mirror of the P4-M1
    saturation-realism acceptance item in ROADMAP item 5).

R4. **Gate-jurisdiction coverage, real material only.** At least one stale-evidence trap
    (superseded logs/receipts that invite a wrong attribution — evidence-freshness jurisdiction)
    and at least one authority-pressure case (task framing that invites an unauthorized
    verdict/action — authority-boundary jurisdiction). All fixture material is copy-frozen from
    real sibling-workspace or this-repo evidence, time-sliced, per-file hashed — same B1/B2
    engineering discipline as v0.1 (explicit per-file `source-hashes.json`, hidden checks and
    rubric split under `evals/hidden/fusion-dogfood-v0.2/`, isolated execution config, redaction
    policy, `method_impact_trace` in every case's `expected_receipt_fields`).

R5. **Authority separation (hard rule).** Claude authored the successor candidate's method text and
    therefore **must not author hidden checks or rubric content** for cases that judge those gates.
    Codex engineers cases, fixtures, and hidden artifacts; Claude's pre-freeze spot-check is
    limited to public case specs, process discipline, and this requirements list; the owner
    approves and freezes. Candidates never see hidden artifacts.

R6. **No trap-to-answer leakage.** Case tasks must be natural work requests; the failure the case
    invites must be a failure the *baseline actually exhibits in calibration*, not a scripted
    gotcha only solvable by knowing the hidden check. Hidden checks judge observable receipt
    fields, never private phrasing.

R7. **Versioning and preregistration linkage.** Approval binds a new manifest + case-set hash for
    `fusion-dogfood-v0.2`; `evals/manifest.json` changes only at owner freeze. Successor v0.2's
    proposal will preregister its two-evaluation criteria against v0.2 (the E1/E2 count never
    started, so nothing is lost); the Eval-2 headroom rule (|H| >= 2 at < 0.95) must be
    *demonstrably satisfiable* on v0.2 given R2 calibration data from non-guardrail headroom
    cases — check this arithmetic before requesting freeze.

R8. **Calibration quarantine.** Calibration transcripts, raw outputs, and score breakdowns are
    never copied into public fixtures, candidate prompts, proposal rationale, or candidate skill
    text. The freeze package may publish only bounded aggregate calibration facts needed for R2/R7:
    case id, baseline artifact hash, trial count, weighted baseline mean, whether the case was
    kept/redesigned/dropped, and the calibration receipt hash. This prevents the extension from
    training the next candidate on the exact observed baseline mistakes.

R9. **No calibration overfitting.** If a draft case fails R2 and is redesigned, the freeze package
    must keep a short redesign ledger: original draft id, reason for redesign, changed public
    fixture/task dimensions, and the new calibration receipt. The hidden rubric must not be tuned
    to rescue a case after seeing a borderline baseline score; redesign changes must be visible at
    the public fixture/task level or the case is dropped.

R10. **Hidden-artifact independence receipt.** Because the previous candidate was co-authored by
     Claude and evaluated by Codex-run machinery, v0.2 needs an explicit hidden-artifact receipt:
     author, reviewer, file hashes, and a statement that hidden checks/rubric content were written
     without using candidate private outputs, run-local scorer patches, or calibration transcripts
     beyond the allowed aggregate facts in R8. Claude may spot-check process discipline under R5,
     but must not approve hidden rubric substance.

R11. **Executable freeze preflight.** Before requesting owner freeze, Codex must provide a preflight
     command or script that validates: v0.1 cases are byte-identical to their approved hashes; all
     new fixture files are per-file hashed; every new case has `trial_count = 2`;
     `method_impact_trace` is in every expected receipt field list; every budget-saturation case is
     flagged; every guardrail case is excluded from R2/R7; no calibration-only file is reachable
     from public fixtures or candidate prompts; and the R7 |H| arithmetic holds for non-guardrail
     headroom cases. Freeze request without this preflight result is incomplete.

R12. **Hidden-context firewall for candidate generation.** Any agent/thread that reads hidden
     checks, evaluator rubrics, or calibration transcripts for v0.2 must not later author or edit a
     successor candidate evaluated on v0.2. Candidate generation must run from public artifacts,
     aggregate calibration facts allowed by R8, and approved proposal text only. If this thread is
     used for hidden-artifact engineering, successor v0.2 candidate drafting must be handed to a
     fresh context that has not read hidden artifacts.

## Sequencing

1. Codex engineers draft cases + fixtures + hidden artifacts + calibration runs (R1–R4, R6,
   R8–R12).
2. Claude spot-check per R5 boundary; verdict recorded in `CLAUDE_REVIEW.md` here.
3. Owner one-shot approval freeze (manifest, hashes, `evals/manifest.json`).
4. Only then: successor v0.2 proposal (informed by the seed-replay verdict from
   `proposals/se-0.7-fusion-successor-v0.1/E1_CORRECTIONS_AND_SEED_REPLAY_SPEC.md` Part C).
