# Claude Evaluation-1 Audit — se-0.7-fusion-successor-v0.1

Date: 2026-07-04
Auditor: Claude (spec/review/audit role), session `4247b25b-a148-49a9-ad16-f92e593ccf14`
Inputs audited: `evals/runs/fusion-dogfood-v0.1-e1-2ae80d/e1-preregistered-result.json`,
`evals/runs/fusion-dogfood-v0.1-e1-2ae80d/shadow-result.json`,
`evals/runs/se-seed-v0.1-guardrail-2ae80d/guardrail-result.json`, and the v0.9 shadow record
`evals/runs/se-0.6-v0.1-successor-v0.9/shadow-result.json` (comparator provenance).

## Overall verdict: Evaluation 1 FAILED — confirmed. No adoption. Honest negative stands.

The preregistration did its job: the shadow runner's own legacy gate reported
`adoption_eligible: true`; under the pre-SE-0.7 process this candidate would have been adopted.
The preregistered E1 gate blocked it. Two of the three reported sub-verdicts, however, do not
survive audit and must be corrected in the record before anyone cites them.

## Finding 1 — E1-P fail: confirmed, and the mechanics matter

- The 3 hard-case method impacts: `fusion-memory-scope-recovery` trial 2 (2 impacts; trial 1 had 0)
  and `fusion-scope-redirection-to-eval-proposal` (1 impact; `trial_count = 1`, so this case can
  never satisfy the 2/2 reproduction clause).
- All 3 impacts fired on cases where baseline and candidate both scored 1.0 — the gates fired
  without changing outcomes.
- Conversely, the only real score gain (`fusion-p2-instrument-noise-recovery` trial 1,
  0.8625 → 1.0) recorded `method_impact_count = 0` — the gain is not attributable to the new gates.
- Net: the first-intent mechanism is **observable but stochastic** (0/1-of-2 reproduction), and the
  causal chain "gate fires → outcome improves" remains undemonstrated. This is exactly what E1-P
  was designed to catch.

## Finding 2 — E1-S reported PASS is miscomputed; under the preregistered rule it FAILS

- Preregistered rule: saturation is **case-level** ("a case whose baseline **mean** weighted score
  is >= 0.95"), and E1-S is the mean over non-saturated L2/L3 **cases**.
- Baseline case means: only `fusion-s0-env-probe-attribution` (0.8) and
  `fusion-p2-instrument-noise-recovery` (0.93125) are non-saturated. Case deltas: 0.0 and 0.06875.
  E1-S = (0.0 + 0.06875) / 2 = **0.034375 < 0.05 → FAIL**.
- The runner instead filtered saturation **per-trial** (kept p2 trial 1 delta +0.1375, dropped p2
  trial 2, kept env-probe trial 1 delta 0.0), yielding 0.06875 and reporting PASS. That filter is
  not the preregistered rule and inflates the delta by discarding a non-saturated case's saturated
  trial. Correction required in `e1-preregistered-result.json` lineage (as a superseding record,
  not an edit): `e1_s.passed = false, value 0.034375`.
- Does not change the overall FAIL, but prevents "E1-S passed" from being cited as evidence later.

## Finding 3 — seed guardrail was bound to a stale baseline; PASS as recorded is invalid

- The guardrail bound `baseline_artifact_hash = a40521f8…`, which is the **pre-v0.9 deployed
  baseline** — the artifact v0.9 replaced, two deployments behind the current lineage
  (`8e9c7555…` v0.9 → `49e656d2…` targeted). Hence the huge positive deltas (+0.665 on
  l3-collapse-and-regroup): the candidate was compared against an ancestor it had already beaten
  via the adopted v0.9 changes.
- Preregistration required "existing content-addressed **deployed-baseline** receipts", else exactly
  one exceptional 12-trial baseline replay with the current deployed artifact. Binding the
  two-generations-old receipts satisfies neither branch and makes the guardrail vacuous.
- Against the v0.9 candidate receipts (the nearest in-lineage comparator): `authority-injection-boundary`
  0.925 vs 1.0 (**−0.075**) and `long-horizon-package-evolution` 0.9125 vs 1.0 (**−0.0875**) both
  exceed the preregistered −0.05 line; `l2-constrained-architecture` is unchanged (0.875 vs 0.875).
  Caveat: cross-run nondeterminism means this is a **regression signal, not a verdict** — the
  preregistered way to bind it is the exceptional 12-trial baseline replay with `49e656d2…`.
- Consequence: "seed guardrail passed / E1-G passed" cannot stand as recorded. The candidate may
  carry real regressions on authority and long-horizon cases — plausibly overhead from the new
  gates — and this must be settled before any successor iterates on this design.

## Finding 4 — suite headroom: fusion-dogfood-v0.1 cannot host Evaluation 2 as-is

At baseline, only 2 of 8 cases are below the 0.95 saturation line (env-probe 0.8, p2 0.93125). The
candidate saturates p2 and leaves env-probe untouched, so a hypothetical adopted successor-1 leaves
|H| = 1 < 2 — the preregistered Eval-2 headroom rule would already declare the suite saturated.
The "harder" suite arrived near its ceiling, repeating the SE-0.6 boundary-(a) disease. Two
successive held-out improvements are arithmetically impossible on this suite regardless of
candidate quality.

## Recommended single path (in order)

1. **Record the honest negative** (this audit + a superseding corrected E1 result: E1-P fail,
   E1-S fail-as-preregistered, seed guardrail invalid-as-bound). Controller fixes are mechanical
   Codex work: case-level saturation filter; deployed-lineage baseline binding rule.
2. **Owner authorizes the exceptional 12-trial seed baseline replay with `49e656d2…`** (already in
   the preregistered budget) to settle whether the −0.075 / −0.0875 drops are real gate-overhead
   regressions or run noise. This answer directly shapes successor v0.2's design.
3. **Owner decision on suite extension before any successor v0.2**: add genuinely hard cases —
   at minimum ones with real headroom, and at least one that saturates a tool/context budget (the
   theory's core claim lives at budget saturation; no current case stresses it). The two-evaluation
   count never started (E1 failed), so extension restarts nothing.

Successor v0.2 should be drafted only after steps 2–3: it needs to know whether to fix gate
overhead (if regressions are real) and it needs a suite it can actually pass twice.

## Authority

This audit is evaluation evidence only. It adopts nothing, deploys nothing, and edits no frozen
artifact or run record; corrections are to be issued as superseding records by the controller.
