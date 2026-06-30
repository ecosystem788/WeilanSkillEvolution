# Frozen Runtime Capability Map

## Baseline and monitored deployment

The directory `packages/solve-with-weilan` is a byte-equivalent, cache-free snapshot of the deployed Skill taken when this project was created. `baseline/MEMORY_RUNTIME_0.7_MANIFEST.json` records every frozen file hash.

The frozen directory remains the rollback baseline. The deployed directory `D:\CodexData\skills\solve-with-weilan` now contains the user-authorized monitored SE-0.2/SE-0.3 release recorded at `deployments/20260630T134857Z-se-0.2-se-0.3/DEPLOYMENT_RECEIPT.json`. This monitored release does not claim the full SE-0.6 adoption gate because the fixed external evaluation set does not yet exist.

## Mapping to the authoritative SE roadmap

| SE stage | Reusable current capability | Gap before stage acceptance |
|---|---|---|
| SE-0.1 | Global Skill, collapse constitution, Frame/Trace validator | No material gap identified; retain regression coverage |
| SE-0.2 | scoped control, cold-start gate, deterministic projection rebuild, scoped episodic Frame search with provenance | accepted; retain field monitoring and regression coverage |
| SE-0.3 | resolvable conversation provenance, promotion gate, semantic index, explicit conflict, lifecycle, bounded forgetting, source freshness | accepted; retain field monitoring and regression coverage |
| SE-0.4 | GovernanceTarget, feedback pressure, causal lineage, finite foreground runner | no independent prospective-memory condition store; no unified event adapter; runner consumes caller manifests rather than generating the next causal trigger |
| SE-0.5 | append-only evidence and test scripts can support proposal evidence | no Skill proposal schema, immutable candidate builder, fixed real-task evaluation corpus, or independent evaluator |
| SE-0.6 | lineage can represent shadow branches; transactions and receipts may support deployment mechanics | no baseline/candidate Skill execution harness, comparison gate, adoption protocol, deployed-artifact switch, or Skill rollback |
| SE-0.7 | bounded runner, control gates, budgets, and idempotency are reusable concepts | no loop that proposes Skill changes, evaluates versions, decides through external authority, adopts, monitors, and rolls back |

## Existing runtime modules

- `scripts/weilan_trace.py`: global CLI and compatibility surface.
- `scripts/governance.py`: feedback pressure, target lifecycle, and read-only Self Projection.
- `scripts/metabolism.py`: read-only metabolic contracts and proposal admission.
- `scripts/transaction.py`: append-only transaction coordinator and receipts.
- `scripts/transition_planner.py`: one-step event materialization.
- `scripts/runner.py`: finite foreground manifest execution.
- `scripts/test_*.py`: mechanism regression tests, not the fixed real-task Skill evaluation set.

## Important distinctions

- The current finite Runner is not a wall-clock or autonomous Frame stream.
- Current mechanism tests verify runtime integrity; they do not measure whether a candidate Skill improves problem solving.
- Current transaction abort/recovery is not Skill-version rollback.
- Current governance holder competition is not old/new Skill shadow competition.
- Current Memory Runtime 0.7 is supporting infrastructure, not bounded Skill self-evolution.

## Risks to address before implementation

1. Version namespace collision has already obscured roadmap drift.
2. The global Skill combines method, memory, governance, execution, and evolution concerns.
3. The deployed directory currently doubles as source code and installation target.
4. The main CLI is monolithic; adding SE-0.4 through SE-0.7 directly would increase coupling and regression cost.
5. Physical archival remains incomplete, so long-term method-state growth is not yet bounded.
6. Self-referential Skill work cannot be the only evidence that the Skill improves real task execution.

SE-0.2/SE-0.3 acceptance and monitored deployment are complete. The next program must preserve the public CLI while separating runtime planes before adding SE-0.4 behavior, then introduce external real-task evaluation and method-impact evidence before any SE-0.6 adoption claim.
