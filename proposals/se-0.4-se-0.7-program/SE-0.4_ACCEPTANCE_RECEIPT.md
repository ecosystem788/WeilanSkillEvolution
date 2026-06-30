# SE-0.4 candidate acceptance receipt

Status: `candidate_accepted_not_deployed`

Candidate tree at acceptance:

- files: `34`
- SHA-256: `5543a08d512e31bfd99726af568a001683a6597e681b0b27f063ec600128cace`

## Compatibility foundation

- Extracted shared storage, identity, atomic-write, and lock primitives into `scripts/runtime_core.py`.
- Preserved all 43 pre-program CLI commands.
- Preserved existing ledger paths, schemas, atomic writes, and scope-lock behavior.

## SE-0.4 behavior

- Added append-only scoped prospective goals with `ACTIVE`, `SATISFIED`, `SUPERSEDED`, and `COLLAPSED` lifecycle states.
- Added one causal event boundary for `user`, `tool`, `environment`, and `clock` observations.
- Added deterministic `QUIESCENT`, `AMBIGUOUS`, and `READY` cycle results.
- Observation never transitions a goal or performs an action automatically.
- Clock observations require one named active due condition and reject future or ambiguous conditions.
- All writes require an explicitly active scope.
- No timer, scheduler, daemon, heartbeat, wakeup, or background loop was added.

## Verification

- `test_prospective.py`: passed.
- `test_runtime_boundary.py`: passed.
- All 12 inherited candidate regression suites passed after the extraction and SE-0.4 additions.
- Total passing suites at this gate: `14`.

## Boundary

- The deployed Skill was not modified.
- SE-0.5 through SE-0.7 behavior was not claimed by this receipt.
- Prospective state is evidence only and cannot activate work or authorize action.
