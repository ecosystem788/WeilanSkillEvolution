# Conservation Boundary-Settlement Probe v0.1

## Scope

This proposal implements the v0.1b probe only in the isolated candidate skill at:

```text
proposals/conservation-boundary-settlement-probe-v0.1/candidate/solve-with-weilan
```

It does not modify the installed skill at `D:\CodexData\skills\solve-with-weilan`, the frozen baseline under `packages/solve-with-weilan`, deployment receipts, roadmap, evaluation policy, or other authority files.

## Candidate Change

- Adds a probe-private append-only pending queue under `memory/semantic-pending-probe`.
- Adds `memory-pending-capture` to queue a semantic entry only when it passes semantic field validation and is denied solely by `semantic budget exhausted`.
- Adds `memory-pending-show` so the harness can inspect queued/admitted pending entries without exposing them to recall.
- Adds `memory-disposition --settle-pending` as the experimental release-settlement switch. The default path remains unchanged.
- Keeps pending entries outside the active semantic set, outside recall, outside projection decisions, and outside disposition history until they are explicitly admitted by consuming a released active slot.
- Carries the false-zero clean-projection guard into this isolated candidate: active semantic conflicts remain searchable and observable as contested entries, but are omitted from clean projection decisions.

## Harness

The harness is:

```text
candidate/solve-with-weilan/scripts/test_conservation_boundary_probe.py
```

It creates two isolated arms with the same pending id and identical candidate fields:

- Control arm: captures pending W that conflicts with anchor K, releases H, does not settle W.
- Experimental arm: captures the same pending W/K conflict, releases H, settles one pending W into the released slot.

The success signal is third-party downstream K-drop, not W's own presence:

- Control: W stays pending, so K remains an uncontested clean decision.
- Experiment: W is admitted through release settlement, W conflicts with K, and K drops out of clean decisions while both W and K remain observable as contested semantic entries.

The harness fails if W appears in clean decisions as a mechanically admitted decision. It also covers the empty-queue release branch and a two-pending FIFO settlement branch.

## Verification

Commands run:

```powershell
python "D:\WeilanSkillEvolution\proposals\conservation-boundary-settlement-probe-v0.1\candidate\solve-with-weilan\scripts\test_conservation_boundary_probe.py" --temp-parent "D:\WeilanSkillEvolution\tmp"
python "D:\WeilanSkillEvolution\proposals\conservation-boundary-settlement-probe-v0.1\candidate\solve-with-weilan\scripts\test_semantic_memory.py" --temp-parent "D:\WeilanSkillEvolution\tmp"
```

Both passed.

Observed probe result:

```json
{
  "conservation_boundary_settlement_probe": true,
  "control_k_clean": true,
  "experiment_k_clean": false,
  "experiment_downstream_changed": true,
  "control_active_count_after_release": 1,
  "experiment_active_count_after_release": 2,
  "experiment_contested_summaries": [
    "anchor K remains clean unless W is admitted as a conflict",
    "probe W downstream conclusion becomes available after settlement"
  ],
  "empty_queue": {
    "empty_queue_returned": true,
    "active_count_after_release": 0
  },
  "two_pending_fifo": {
    "two_pending_fifo": true
  }
}
```

## Status

Ready for review as an isolated candidate plus harness. This is not an adoption or deployment request.
