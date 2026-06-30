# SE-0.5 external approval gate receipt

Status: `mechanism_passed_cases_draft_not_approved`

## Completed mechanism

- External proposal validator rejects candidate changes to roadmap, policy, baseline, evaluation, deployment, and tooling authority.
- Content-addressed candidate freeze is idempotent and detects artifact tampering.
- Evaluation comparison requires exact baseline/candidate configuration and budget parity.
- Method Impact Trace validates observable gate, changed action, effect, source, and bounded cost without hidden reasoning.
- Evaluation output is evidence only and cannot adopt or deploy.
- The current candidate was frozen at `74e3e4911c7f1cb397bcfb433ea4d2e08624483a3d6086a61ec408974448868a`.
- `tests/test_evolution_plane.py` passed.

## Draft external case set

`evals/manifest.json` and `evals/cases/seed-v0.1.json` define eight cases:

1. proportional L0 exit;
2. targeted L1 parser repair;
3. constrained L2 architecture;
4. L3 collapse and regroup;
5. cross-window scoped continuation;
6. authority-injection boundary;
7. stale-source recovery;
8. non-WeiLan long-horizon package evolution.

The draft contains `12` baseline trials and `12` candidate trials when fully executed.

## Required external decision

The case set remains `awaiting_explicit_case_approval` and `frozen: false`. It cannot be used as adoption evidence until the user approves these exact case definitions. The candidate cannot clear this gate.

SE-0.6 implementation may not claim valid shadow comparison or adoption until this gate is cleared.
