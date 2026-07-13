# Harness Signal Addendum v0.1c

This addendum records the implementation target for the corrected conservation
boundary-settlement probe signal.

## Corrected Signal

The harness must measure third-party downstream change, not W's own admission.

- W is captured as pending with `--conflicts-with <K.memory_id>`.
- Control keeps W pending and asserts `K_SUMMARY` remains in clean decisions.
- Experiment settles W, asserts `K_SUMMARY` drops from clean decisions, asserts
  `W_SUMMARY` also stays out of clean decisions, and preserves both W/K under
  `contested_semantic_entries`.
- The accepted success signal is `control_k_clean=true`,
  `experiment_k_clean=false`, and `experiment_downstream_changed=true`.

A result based on `W_SUMMARY in decisions` is invalid because it only measures
mechanical admission of W into the active set.

## Coverage Additions

- Empty queue: `--settle-pending` with no queued pending consumer returns
  `no_pending_consumer` without minting a semantic entry.
- Two pending entries: one released slot admits the first queued pending entry
  and leaves the second queued, exercising FIFO settlement.
