# fusion-dogfood-v0.2 — Headroom Wall Diagnostic & Owner Decision Memo

Date: 2026-07-10
Author: Claude (spec/audit role, bounded wake episode)
Status: diagnostic + decision request. No authority file, manifest, freeze, or hidden artifact touched.
Scope: reversible analysis only. This memo does not redesign cases; it argues that a 4th redesign
round is the wrong next move and asks the owner to choose the fork instead.

## One-line

Three redesign rounds of the v0.2 headroom cases have failed calibration **identically**
(baseline mean 0.955–0.9925, all ≥ 0.95 ceiling-saturation rejects). The failures are not
engineering sloppiness — they are structural. Redesign round 4 will almost certainly hit the same
wall. The real decision is a fork, and it is the owner's.

## Evidence (grounded, public calibration only — no hidden artifacts read)

Latest calibration `baseline-49e656d2-20260705/` (`aggregate sha256 da6c8b12…`), 2 public trials/case:

| Case | Intended jurisdiction (R4) | Baseline mean | Verdict |
| --- | --- | ---: | --- |
| `fusion-stale-baseline-binding-repair` | evidence-freshness trap | 0.9925 | ceiling reject |
| `fusion-budget-saturated-triage` | budget-saturation (R3) | 0.9550 | ceiling reject |
| `fusion-targeted-deployment-risk` | attribution / open-risk | 0.9725 | ceiling reject |

Per-dimension breakdown is uniformly high, not lumpy. `fusion-budget-saturated-triage` trial 1:
`prioritization_under_budget 0.95`, `evidence_selection 0.95`, `saturation_discipline 1.0`,
`source_traceability 0.95`, `overhead 0.9`. The baseline is not squeaking by — it is near-perfect on
every axis the case scores. This is the same picture across all three cases and all three prior
rounds (0.99 → 0.99 → 0.99).

## The structural reason all three rounds fail

The v0.2 requirements set the target (`EXTENSION_REQUIREMENTS.md` R2/R4): build cases where "the
deployed baseline predictably fails **in ways the method's gates govern**," expecting mean < 0.85.

That target is close to self-defeating, and this is the crux:

1. **Every headroom case is in the skill's home domain.** All three are the same shape — *review
   fusion evidence → produce the correct disciplined disposition (cite / don't-cite, triage,
   attribute).* Disciplined evidence-analysis-to-verdict is exactly what SE-0.1…0.7 tuned the skill
   to do. Asking it to do that well is asking it to exercise its strength; the more realistic and
   well-specified the case, the more it plays to that strength.

2. **A failure "the method's gates govern" is a failure the gated method won't commit.** R4 asks
   for stale-evidence traps and authority-pressure traps. But evidence-freshness and
   authority-boundary are *existing gates the deployed baseline already enforces*. If a gate governs
   the trap, a working gated baseline steps around it — that is what a gate is for. So the very
   property that would make method value observable (the gate fires) is the property that keeps the
   baseline from failing (the gate already fired). The `fusion-authority-existing-authorization`
   case already collapsed this way: it could only survive as a quarantined `guardrail_case`, barred
   from headroom.

3. **0.6/0.7 hardening shrank the target to near-zero.** Headroom requires a failure mode that is
   (a) real and important, yet (b) **not already governed by an existing gate** — because anything
   an existing gate governs, the deployed baseline handles. After two rounds of gate hardening, the
   set of "real, important, ungoverned" analysis failures in this task family is small and
   shrinking. v0.1 already showed only 2/8 cases below 0.95. v0.2 has now shown 0/3 across two
   redesigns.

Net: **the fusion-workflow analysis family is measurement-saturated for this baseline.** You cannot
manufacture honest headroom by re-cutting cases inside a domain the method is at ceiling in.

## The fork (owner decision — I am not authorized to pick it unilaterally)

**Path A — change the case-construction axis, one bounded round.** Stop building competence cases;
build **tradeoff / trap cases that stress a failure mode no current gate governs.** Candidate axes
where the baseline could plausibly drop below 0.80 (all in-domain material, honest):
  - *Gate-conflict cases*: two disciplines the method holds simultaneously are put in genuine
    tension (e.g., "cite the freshest evidence" vs. "don't cite an unverified source") so that the
    correct answer requires *sacrificing* one discipline the scorer would otherwise reward — the
    baseline's instinct to satisfy every discipline becomes the wrong move.
  - *Budget-forces-a-normally-required-omission cases*: saturation so real that the correct triage
    must skip a step the method usually treats as mandatory, and must *say so*; a baseline that
    dutifully performs the mandatory step over-runs budget and scores worse.
  - *Ungoverned-failure cases*: a failure shape with no existing gate (e.g., a quantitative
    reasoning / arithmetic-over-receipts step, not a discipline step) where correctness is
    orthogonal to method discipline.
  This is bounded: **one** redesign round, calibrate, and if it *also* saturates ≥ 0.85, Path A is
  exhausted and Path B is forced. No open-ended churn.

**Path B — record the honest saturation disposition for SE-0.7.** If Path A saturates too, then the
honest reading is that SE-0.7's "two successive held-out improvements" gate is **not obtainable by
improving analysis quality on this task family**, because the family has no measurable headroom
left. That is not a failure to engineer — it is the method having reached its measurable ceiling
here. The honest options then are: (i) move the SE-0.7 improvement gate to a *different* task family
where the baseline is not at ceiling, or (ii) close SE-0.7 as **"saturated — no measurable headroom
on the fusion-workflow family"** rather than running a 5th/6th redesign to keep the item nominally
"in progress." Churning cases to keep the gate alive would be exactly the pretty-idling this project
exists to break.

## Recommendation (single path)

Authorize **Path A, one bounded round**, engineered under the existing authority-separation rule
(Codex engineers cases/fixtures/hidden artifacts; this Claude thread stays non-hidden-aware and does
not author candidate artifacts). Pre-commit the stop rule now: **if that round calibrates ≥ 0.85 on
every non-guardrail case, v0.2 stops and SE-0.7 goes to the Path B disposition decision** — no round
4. This caps the spend at one more calibration and forces an honest terminus either way.

## What this memo did NOT do (gate discipline)

No manifest / `evals/manifest.json` / ROADMAP / EVALUATION_POLICY edit. No freeze. No hidden artifact
read or written (`evals/hidden/**` untouched — this thread remains non-hidden-aware). No candidate
artifact authored. No calibration re-run. No adoption or deployment. Purely a reversible analysis of
existing public calibration receipts, offered to the owner as a decision frame.
