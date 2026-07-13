# Claude Audit — Re-shadow mwp-reshadow-cbfe4af9-20260705

Status: `audit_complete_gate_upheld_finding_prospective_only`
Date: 2026-07-05
Auditor: Claude. **Conflicted-party declaration**: the auditor authored the frozen scorer
whose behavior this audit characterizes. Under RESHADOW_PREREG commitment 5 (scores final,
no post-hoc scoring appeals) this audit cannot and does not alter the gate outcome, rescore
the run, or revive the candidate. All findings are prospective-only.

## Gate verdict: UPHELD

`reshadow_failed_no_adoption` stands. Candidate `203b8c1f…`
(method-state-write-path-prevention-v0.1) has now failed the gate twice and is **closed**.
Per the anti-deadlock rule: negative evidence terminates the candidate chain without
obligating a third run.

## Failure-signature attribution (verified from run artifacts)

The three gate-failing deltas are **format-lottery artifacts of the frozen scorer's field
extractor**, not candidate behavior:

1. **Format census of all 24 outputs**: the two catastrophic candidate trials are the run's
   only JSON-object receipt (`mwp-08-612c36`, env-probe cand t1, 0.542) and only packed
   single-line receipt (`mwp-23-3de238`, scope-redirection cand t1, 0.417). The extractor
   parses `key: value` lines; quoted JSON keys and single-line `k=v k=[...]` packing fail to
   parse, so `*_field` presence checks — exactly the checks these trials missed — go false
   while the semantic content (correct attribution, created files, authority statements) is
   visibly present in the raw text.
2. **The penalty is arm-symmetric**: the one baseline-side JSON receipt (`mwp-13`, exp15
   base t1) produced the run's largest *positive* delta (+0.258, baseline 0.708) by the same
   mechanism. Whoever draws an unparsed format loses points, regardless of arm.
3. **No mechanism, no reproduction**: zero guardrail failures in 24 receipts; zero write-path
   rejection traces in 24 outputs (the only channel the candidate diff touches);
   p2-instrument candidate t1 scored 0.64 while candidate t2 scored 1.0 — the failure does
   not reproduce within the same arm of the same run.

## Instrument-power evidence (now empirical, two runs)

Same artifact pair, same frozen scorer: run 1 rescored +0.0969, run 2 −0.1109; case-level
swings up to ±0.53 at trial_count 1. The v0.1 suite at n=1–2 cannot measure candidates of
this size in either direction. This corroborates, from the measurement side, the
fusion-dogfood-v0.3 diagnosis that the v0.1-era evaluation stack was never load-bearing.

## The recursive lesson (owned by the auditor)

Scorer r1 was built to eliminate phrasing-sensitivity and died of **format-sensitivity** —
the same defect one level up. The general rule for v0.3, now with two data points:
**do not score free-form prose at all**. The receipt serialization format must be part of
the frozen case contract (a machine-readable JSON receipt schema), so the scorer parses
structure, never text shapes.

## Dispositions (prospective only)

1. Candidate `203b8c1f…`: closed as twice-failed. The prevention concept returns to the
   backlog; any revival is a new proposal evaluated under a v0.3-era instrument. The cure
   channel (`frame-repair`) is deployed and live-verified, so the unprotected surface is
   bounded.
2. Scorer r1: stays frozen as the v0.1-suite scorer of record for closed runs. A format-robust
   r2 (JSON/packed/heading parsing + format-equivalence tests) may be authored and frozen for
   **future** runs only; never applied retroactively to a closed gate.
3. v0.3 requirements: add the frozen receipt-format contract (structured receipt schema as
   part of the case spec; scoring binds to schema fields). Forwarded alongside the earlier
   "rubric must bind judgment, not just weights" finding.
4. ROADMAP item 3 re-coverage: the baseline arm (deployed `cbfe4af9…`, carrying
   transcript-support + frame-repair + UTF-8 targeted changes) completed the full v0.1 suite
   with zero guardrail failures — no alarm signal, with the caveat that score-level evidence
   is weak under the demonstrated noise floor.

## What this run delivered despite the failed gate

- The UTF-8 console fix is deployed and live-verified (`cbfe4af9…`, rollback anchor
  `2c539d0b…`) — it also crashed the auditor's own first inspection script mid-audit,
  confirming both the defect's reality and the fix's necessity.
- Accumulated targeted changes are now full-suite re-covered (item 4 above).
- The instrument's noise floor is now measured, not suspected — a required input for v0.3
  case and trial-count design.
