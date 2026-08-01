# canonical-workspace-cache-v0.1 — candidate only

This package implements candidate A from `frame-latency-profile-v0.1`: cache
`canonical_workspace` by exact expanded path for one process. It does not adopt or deploy
the change. Both installed Skill trees remained at baseline throughout this work.

## Artifacts

| role | content-addressed tree hash |
|---|---|
| baseline | `ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad` |
| candidate | `8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a` |

`proposal.json` validates with `valid: true` and `changed_path_count: 2`. The frozen trees
differ only at:

- `scripts/runtime_core.py`
- `scripts/test_canonical_workspace_cache.py`

`artifacts/` is ignored because it is deterministically regenerated from the tracked
`baseline/` and `candidate/` trees with `candidate-freeze`.

## Executable contract

The cache key is the exact string after `expanduser` and `expandvars`. Within one process,
the first resolution of that expanded path remains fixed. A new process resolves it again.
Long-lived callers that change path existence, links, or on-disk spelling must call
`clear_canonical_workspace_cache()` before resolving again.

This is not pure-function memoization. It intentionally relies on the current CLI shape:
one command per process, and commands do not create or replace their own workspace.

`_probe_contract_discrimination.out.json` grafts the candidate test onto the frozen
baseline and then runs the same test on the candidate. The behavioral half names no
cache-control symbol; the explicit-clear half is visibly skipped when that boundary is
absent:

| tree | pytest rc | node verdict |
|---|---:|---|
| baseline + grafted test | 1 | one `FAILED` by `AssertionError`, one `SKIPPED`, no `AttributeError` |
| candidate | 0 | two `PASSED` |

The first test behaviorally discriminates repeated in-process resolution without relying
on candidate-only API presence. The second pins explicit clearing and fresh-subprocess
resolution on the candidate, but it is a contract-documentation test rather than a second
independent discriminator: Claude's no-cache sham candidate passes that second test while
failing the first by `AssertionError`.

## Equivalence and complete regressions

`_probe_cli_equivalence.out.json` records byte-identical output for baseline and candidate:

- `memory-recall`: 40,847 bytes, sha256 `20af84c7…`
- `prospective-show`: 209,079 bytes, sha256 `9336284e…`
- `lineage-show`: 1,409,733 bytes, sha256 `c1c6de04…`

This is evidence on one current ledger, not equivalence over every possible input.

`_probe_suite_acceptance.out.json` now records the complete mixed suite under identical
conditions for the revised candidate `8602bb0f…`:

| tree | pytest nodes | passed | failed | main-style nonzero |
|---|---:|---:|---:|---|
| baseline | 93 | 92 | 1 | `test_slow_loop.py` |
| revised candidate | 95 | 94 | 1 | `test_slow_loop.py` |

The sole failure on both trees is
`test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`. Candidate-only failures
are empty, baseline-only nodes are empty, and the two candidate-only nodes are exactly the
two revised contract-test functions. The suite is therefore not described as “all green.”
Claude's independent 1500-second-per-arm run in
`_review2_20260801_claude_independent_suite.out.json` corroborates the same node-set and
failure-equivalence conclusions. The earlier 600-second attempt had not emitted this
receipt when the 13:19:59 revision receipt was authored, but the machine-readable result
appeared on disk afterward; that earlier “not claimed” wording is superseded by the current
artifacts rather than treated as current package state.

## Real `open` latency

The first probe attempt asked for four samples per arm and exceeded its 600-second outer
budget before it could write an aggregate receipt. `LATENCY_ATTEMPT_1.md` preserves that
probe-budget failure. The bounded retry used three samples per arm, satisfying the inbox
requirement that the sample count not be only two.

`_probe_real_open_latency.out.json` ran the actual frozen-tree `open` command against one
temporary copied snapshot of the live ledger, with identical arguments and a 240-second
per-run bound. The production ledger was not written.

| arm | samples (s) | median (s) | mean (s) |
|---|---|---:|---:|
| baseline | 192.747, 84.910, 95.163 | 95.163 | 124.273 |
| candidate | 36.983, 40.510, 38.923 | 38.923 | 38.805 |

All six commands returned rc 0 and a frame id. The median ratio is 2.445×. More strongly
for this observation, the interleaved arms have disjoint ranges: baseline minimum 84.910s
exceeds candidate maximum 40.510s, a worst observed cross-arm ratio of 2.096×. Host load
was uncontrolled and baseline dispersion is large, so these observations do not establish
a universal latency floor or guarantee.

That latency receipt names the previous candidate `ec236760…`. The current revision changes
only `scripts/test_canonical_workspace_cache.py`; `_probe_candidate_tree_diff.out.json`
verifies that `scripts/runtime_core.py` is byte-identical across the two candidate hashes.
The latency result is therefore inherited implementation evidence, not a fresh timing trial
against the revised content address.

## Authority and boundary

This directory contains no shadow result, adoption decision, deployment budget, deployment
receipt, or rollback authorization. Candidate evidence cannot grant those authorities.
Both installed trees were independently re-hashed after measurement and remained baseline
`ae0537da…`.

Fast does not prove semantically correct, and process-local stability is not filesystem
stability. A future long-lived embedding must use the explicit clear operation at the
contract boundary or reject this candidate.

## Re-run

From the repository root:

```powershell
python tools/evolution_cli.py proposal-validate --proposal proposals/canonical-workspace-cache-v0.1/proposal.json
python tools/evolution_cli.py candidate-freeze --source proposals/canonical-workspace-cache-v0.1/baseline/solve-with-weilan --artifact-root proposals/canonical-workspace-cache-v0.1/artifacts
python tools/evolution_cli.py candidate-freeze --source proposals/canonical-workspace-cache-v0.1/candidate/solve-with-weilan --artifact-root proposals/canonical-workspace-cache-v0.1/artifacts
cd proposals/canonical-workspace-cache-v0.1
python -X utf8 _probe_candidate_tree_diff.py
python -X utf8 _probe_contract_discrimination.py
python -X utf8 _probe_cli_equivalence.py
python -X utf8 _probe_suite_acceptance.py
python -X utf8 _probe_real_open_latency.py
```
