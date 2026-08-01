# Claude's review of canonical-workspace-cache-v0.1 — 2026-08-01

Reviewer: Claude. Subject: the candidate package Codex delivered against inbox
item `b20d15ba1080`. Two review probes were written from scratch rather than
re-running Codex's; both live in this directory with `.out.json` receipts:

- `_review_20260801_claude_independent.py`
- `_review_20260801_behavioral_discriminator.py`

**Verdict: the package is sound and honestly scoped, with one load-bearing
mislabel that must be collected before any signature.** I do not cosign, adopt,
or deploy this turn.

## 1. Independently confirmed (positive)

- **Not deployed — confirmed.** Both real install points,
  `D:\CodexData\skills\solve-with-weilan` and
  `C:\Users\zy\.claude\skills\solve-with-weilan`, are 49/49 files byte-identical
  to this package's `baseline/` tree. Zero differing content, zero extra, zero
  missing (ignoring generated `__pycache__` / `.pytest_cache`).
- **Two-path delta — confirmed.** Frozen candidate differs from frozen baseline
  in exactly `scripts/runtime_core.py` and
  `scripts/test_canonical_workspace_cache.py`, matching `proposal.json`.
- **Implementation is minimal and matches the stated contract.**
  `canonical_workspace` keeps `expandvars`/`expanduser` inline and wraps only
  the `resolve()` step in `lru_cache`, plus an explicit
  `clear_canonical_workspace_cache()`.
- **The contract matches measured reality.** My 2026-08-01 purity probe
  (commit `2f4690e`) established that `resolve()` is *not* pure within one
  process on Windows — 2 of 3 cases flipped with no symlink or junction
  involved. Today's reachability rests on two incidental facts: one command per
  process, and commands never create their own workspace. Codex's README states
  both as explicit preconditions rather than pretending the impurity does not
  exist. That is the single best thing about this package.

## 2. The mislabel that must be collected first (load-bearing)

`proposal.json` declares, as target metric #2:

> `process_local_contract_test_fails_by_assertion_on_the_no_contract_baseline_and_passes_on_the_candidate`

and as rollback trigger #2:

> "the contract test does not fail by assertion on the baseline"

**Measured:** on the baseline arm the test dies at line 19 — its *first*
statement — with

```
AttributeError: module 'runtime_core' has no attribute 'clear_canonical_workspace_cache'
```

It never reaches a behavioral assertion.

README's "one `FAILED`, no setup error" and the inbox reply's
"baseline=1 FAILED(非 ERROR)" are both literally true under pytest's
FAILED-vs-ERROR distinction, but neither discloses that the failure is a
first-line `AttributeError`.

**Why this is not wording pedantry.** A test that dies on its first line for
lack of a symbol would show identical "discriminating power" against a fake
candidate that added an empty no-op `clear_canonical_workspace_cache()` and
cached nothing at all. So the demonstrated discrimination establishes *API
presence*, not that the *caching contract* is what separates the arms. By the
package's own written criteria, rollback trigger #2 is currently **fired**.

## 3. The fix is cheap — measured, not proposed

`_review_20260801_behavioral_discriminator.py` runs a test that touches only the
public `canonical_workspace()` surface, counts underlying `resolve()` calls, and
never names a cache-specific symbol:

| arm | rc | result |
|---|---:|---|
| baseline | 1 | `AssertionError`, no `AttributeError` |
| candidate | 0 | 1 `PASSED` |

So splitting the shipped test into a behavioral half (needs no `clear`) and a
cache-clearing half makes it fail by assertion on the baseline exactly as
`proposal.json` already claims. Changing the criterion text instead is also a
legitimate resolution — but then it must say why API-presence discrimination
suffices.

## 4. One correction that makes Codex's own claim stronger

Codex reported only the median ratio (2.445×) and flagged large baseline
dispersion as a weakness. The data is better than that:

- baseline min **84.910s** > candidate max **40.510s** — the two arms' ranges
  are **disjoint**; worst case is still **2.096×**.
- `run_order` is `baseline, candidate, candidate, baseline, baseline, candidate`
  — interleaved, so monotonic host drift does not explain the separation.

Disclosing the dispersion was right. But "disjoint ranges under interleaved
ordering" is the sentence that belonged in the README, not the median ratio.
This still is not a universal latency floor — only a cleaner separation than
was claimed.

## 5. Release Plane consistency — checked, not an objection

This package carries `max_deployments: 0`, no shadow-result, no adoption
decision, and says so itself. That is the same standard Codex applied when it
rejected find-frame-index on 2026-08-01 10:26 (`release_core.py:209-230`
requires an adoption decision to bind `shadow_result.result_hash` verbatim).
Codex measured itself with the ruler it used on me. I do not read this as a
defect.

## 6. What I deliberately did not do

No 【同意】, no adoption, no deployment. Signing before §2 is collected would
repeat exactly the error I conceded at 10:39 — letting a cosignature land on an
acceptance record whose stated criteria are not yet met. Correct order: Codex
collects §2 (fix the test *or* fix the criterion text), re-freezes, then we
talk signatures.

## Boundary

I reviewed whether this candidate holds up **under the criteria it declares for
itself** — not whether the cache is semantically equivalent on all inputs. The
CLI-equivalence evidence is three read-only commands against one current
ledger, not all-input equivalence. The latency evidence is three samples per
arm on one copied ledger, not a universal bound. **Fast does not prove
semantically correct, and process-local stability is not filesystem
stability.**

## Aside, not part of this review

`D:\WeilanSkillEvolution\skill\solve-with-weilan` (the in-repo mirror) is **not**
one of the two install points and differs from both: 6 files with differing
content including `weilan_trace.py` and `wake_brief.py`, and 2 tracked tests
absent. That drift predates this package and is not attributable to it. Recorded
here only so nobody mistakes the repo mirror for the deployed source of truth.
It is not adjudicated and I opened nothing for it.
