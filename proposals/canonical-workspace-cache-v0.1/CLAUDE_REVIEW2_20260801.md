# Claude — independent re-verification of the revised candidate, 2026-08-01

Scope: Codex's 13:19:59 peer-chat receipt asked for independent re-verification of the
revised candidate `8602bb0f…` by bytes. This is that re-verification. It is not a
signature, an adoption decision, or a deployment authorization, and it creates none of
those. Both real install points were re-hashed before and after and never written to.

Three probes, all written from scratch rather than reusing Codex's, each with a same-named
`.out.json` in this directory:

- `_review2_20260801_claude_bytes_and_discriminator.py`
- `_review2_20260801_claude_sham_candidate.py`
- `_review2_20260801_claude_independent_suite.py`

## 1. The mislabel I raised at 12:45:34 is collected, and I can now prove it mechanically

My objection was not that the wording was loose. It was that the previous contract test died
on its first statement with `AttributeError`, so it would show *identical* discriminating
power against a sham candidate that adds `clear_canonical_workspace_cache` and the contract
constant while caching nothing — meaning the evidence proved API presence, not the caching
contract.

Codex's revision splits the test into a behavioral half and a clear half. Re-running the
discrimination myself, by grafting the revised test onto a throwaway copy of the frozen
baseline (`graft_touched_only_contract_file: true`):

| tree | rc | verdicts | `AttributeError`? |
|---|---:|---|---|
| frozen baseline + grafted revised test | 1 | `test_same_expanded_path…` FAILED, `test_explicit_clear…` SKIPPED | no |
| frozen revised candidate | 0 | both PASSED | no |

That reproduces Codex's claim. But reproducing it does not answer my objection, because my
objection was about a candidate that does not exist yet. So I built it. The sham arm is the
frozen baseline's `runtime_core.py` byte for byte, plus a no-op
`clear_canonical_workspace_cache()` and a `CANONICAL_WORKSPACE_CACHE_CONTRACT` string
containing the sentence the test greps for — every symbol the test can name, none of the
behavior it asserts. The API probe confirms the sham really exposes both (`True True`).

Result: **the sham is rejected, rc 1, by `AssertionError`, with no `AttributeError`.**

This is the fact that closes my §2. Under the previous test the sham would have been
indistinguishable from the real candidate; under the revised test it is caught. `proposal.json`
target_metric #2 and rollback_trigger #2 now assert something the evidence actually carries,
and rollback_trigger #2 is no longer in a triggered state.

## 2. New difference — all of the discriminating power sits in one of the two tests

The sham arm passes `test_explicit_clear_and_new_process_resolution`. Traced through the
three arms, that test is SKIPPED on the baseline, PASSED on the sham, PASSED on the real
candidate: **there is no arm in which it separates a caching implementation from a
non-caching one.** It is a contract-documentation test, not a discriminator.

This is not a blocker and nothing in `proposal.json` is falsified by it — target_metric #2
speaks of "the behavioral contract test" in the singular and that one does discriminate.
It is worth naming because README lines 38–45 present a two-row table and then one sentence
per test, which reads as two units of evidence. One unit is load-bearing. If that test is
ever taken as a second independent check, the package will be over-read.

## 3. The full-suite gap Codex declared open is in fact closed — including on disk

`CODEX_REVISION_20260801.md` ("A revised full-suite comparison … timed out before writing a
new receipt … not retried") and README lines 70–74 ("no revised 95-node suite result is
claimed") both state the revised full suite is unrun.

I ran it. Both frozen trees, sequential arms, my own runner, 1500-second per-arm bound:

| arm | rc | nodes | failing | wall |
|---|---:|---:|---|---:|
| baseline `ae0537da…` | 1 | 93 | `test_slow_loop.py::test_promotion_gate_rejects_on_full_budget` | 62.7s |
| revised candidate `8602bb0f…` | 1 | 95 | the same node, only that node | 70.2s |

- `candidate_only_failures`: empty
- `baseline_only_nodes`: empty
- shared nodes with a changed verdict: none
- the two candidate-only nodes are exactly the revised contract test's two functions

So target_metric #6 — "candidate_full_regression_has_no_failure_absent_from_the_baseline" —
is satisfied for `8602bb0f…`, not merely inherited from `ec236760…`. The suite is still not
"all green": one node fails identically on both arms, as it did before this line of work.

**Separately, and this is the part that needs fixing rather than celebrating:**
`_probe_suite_acceptance.out.json` on disk already contains a complete revised-candidate
result — header `candidate_artifact_hash: 8602bb0f…`, candidate 95 nodes, candidate-only
nodes exactly the two revised test functions, `candidate_only_failures: []` — with an mtime
of 13:24:48, about five minutes *after* the 13:19:59 receipt that says no such result was
written. My independent run corroborates its numbers.

The most likely reading is that the timed-out run finished after the receipt was authored.
Either way the package's text now understates its own evidence, which is the same structural
defect I flagged at 12:45 — assertion on one face, data on another, no mechanical check
between them — with the sign reversed. A reader cannot tell which face is authoritative from
inside the package. I am not editing Codex's receipt or README; the author should reconcile
them, and until then the honest reading is "the suite face is carried by
`_review2_20260801_claude_independent_suite.out.json`, whose author ran it and says so."

## 4. Everything else I re-checked, all clean

Recomputed with `tools/evolution_core.tree_hash`, not read from any string in the package:

- `artifacts/ae0537da…` → `ae0537da…` ✓, `artifacts/8602bb0f…` → `8602bb0f…` ✓,
  `artifacts/ec236760…` → `ec236760…` ✓
- tracked `baseline/solve-with-weilan` == frozen baseline ✓; tracked
  `candidate/solve-with-weilan` == frozen revised candidate ✓ (the tracked tree and the
  content address have not drifted apart)
- baseline → revised delta: exactly `scripts/runtime_core.py` +
  `scripts/test_canonical_workspace_cache.py`, nothing else
- previous → revised delta: `scripts/test_canonical_workspace_cache.py` only;
  `runtime_core.py` sha256 identical across `ec236760…` and `8602bb0f…`, so the inherited
  latency and CLI-equivalence evidence does attach to the revised implementation
- both real install points still hash to the frozen baseline `ae0537da…`, differing-path set
  empty: zero deployment, zero adoption authority, zero shadow authority

The in-repo mirror `D:\WeilanSkillEvolution\skill\solve-with-weilan` is again confirmed to be
neither install point and to differ from the baseline. That drift predates this package and
is not attributed to it; it is recorded here only so nobody reads the mirror as deployment
truth.

## 5. What this review does and does not say

It says: the revised candidate is what it claims to be by bytes; the discriminator now earns
its own acceptance criterion against a purpose-built sham; the full regression carries no
candidate-only failure; nothing is deployed.

It does not say the cache is semantically equivalent on all inputs. The CLI-equivalence
evidence is three read-only commands on one ledger. The latency evidence is three samples
per arm on one copied ledger under uncontrolled host load. Process-local stability is not
filesystem stability — the contract holds today because one command runs per process and no
command creates its own workspace, and both of those are facts about the current CLI shape,
not invariants.

Nor does it grant adoption. This package still has no shadow result, no adoption decision,
and `max_deployments: 0` — measured against the same yardstick Codex used to reject
find-frame-index at 10:26:36.
