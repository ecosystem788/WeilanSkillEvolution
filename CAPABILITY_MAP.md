# Frozen Runtime Capability Map

## Baseline

The directory `packages/solve-with-weilan` is a byte-equivalent, cache-free snapshot of the deployed Skill taken when this project was created. `baseline/MEMORY_RUNTIME_0.7_MANIFEST.json` records every frozen file hash.

The deployed directory remains `D:\CodexData\skills\solve-with-weilan`. This project does not change it.

## Mapping to the authoritative SE roadmap

| SE stage | Reusable current capability | Gap before stage acceptance |
|---|---|---|
| SE-0.1 | Global Skill, collapse constitution, Frame/Trace validator | No material gap identified; retain regression coverage |
| SE-0.2 | scoped control, cold-start gate, projections, causal Frame files | no dedicated task-relevant episodic search/ranking API |
| SE-0.3 | conversation evidence, promotion, semantic index, lifecycle, source freshness | bounded forgetting policy and stable resolvable thread/turn provenance require audit |
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
4. Conversation provenance is partly opaque.
5. Physical archival remains incomplete, so long-term method-state growth is not yet bounded.

The first project task is an evidence-backed SE-0.2/SE-0.3 acceptance audit. Refactoring or new behavior must wait until that audit is complete.
