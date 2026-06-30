# SE-0.5 external approval gate receipt

Status: `accepted`

## Completed mechanism

- External proposal validator rejects candidate changes to roadmap, policy, baseline, evaluation, deployment, and tooling authority.
- Content-addressed candidate freeze is idempotent and detects artifact tampering.
- Evaluation comparison requires exact baseline/candidate configuration and budget parity.
- Method Impact Trace validates observable gate, changed action, effect, source, and bounded cost without hidden reasoning.
- Evaluation output is evidence only and cannot adopt or deploy.
- The current candidate was frozen at `74e3e4911c7f1cb397bcfb433ea4d2e08624483a3d6086a61ec408974448868a`.
- `tests/test_evolution_plane.py` passed.

## Approved external case set

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

## External decision

The user explicitly approved these exact eight case definitions in `conversation:019f18f6-9ae3-7353-ad25-0529c599f732#019f18f6-afb9-77c3-9167-fbe1ccb8fff7`.

The case set and manifest are frozen under suite `se-seed-v0.1`; the manifest binds the canonical case-set hash. Any case change requires a new suite id and explicit external approval. This clears the SE-0.5 authority gate but does not itself provide shadow results or authorize adoption.
