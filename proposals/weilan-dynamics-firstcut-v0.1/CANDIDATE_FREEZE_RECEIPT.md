# Candidate Freeze Receipt - WeiLan Dynamics Firstcut v0.1

Status: `candidate_frozen_targeted_harness_passed`
Date: 2026-07-08

## Scope

- Proposal: `weilan-dynamics-firstcut-v0.1`
- Frozen design: `proposals/weilan-dynamics-firstcut-v0.1/DESIGN.md`
- Design SHA-256: `276627f3b6e680376745ec001021e25fe421e8d2456356d824b657ec217adc9f`
- Base source: `D:\CodexData\skills\solve-with-weilan`
- Candidate source: `proposals/weilan-dynamics-firstcut-v0.1/candidate/solve-with-weilan`
- Frozen artifact: `proposals/weilan-dynamics-firstcut-v0.1/artifacts/f28bc2b678d28d6b09caae31f29587e9bb882823acacad4619083848db7ff097/solve-with-weilan`
- Base artifact hash: `9b2130988817076de547dffe3627d31501d4f62e584a2d00daf979c8db36a3c9`
- Candidate artifact hash: `f28bc2b678d28d6b09caae31f29587e9bb882823acacad4619083848db7ff097`

## Changed Candidate Paths

- `scripts/dynamics_firstcut.py`
- `scripts/test_dynamics_firstcut.py`

## Implementation Summary

- Added a proposal-local semantic-slot dynamics arena with q-conserving flow toward self-read structural output.
- Added a q-based `displace` selector outside the existing `enforce_semantic_budget` validator.
- Added pre-registered exits for `collapse_emerges_from_conservation`, `collapse_needs_gate`, `inconclusive`, and `blocked_engineering`.
- Added a true stalled oligarch survival fixture: the oligarch has zero self-read structural output yet survives to `collapse_needs_gate` under weak bleed/high-q settings.
- Added a `(q, bleed, floor, horizon)` phase map with 144 cells: 56 `collapse_emerges_from_conservation`, 88 `collapse_needs_gate`, and all cells q-conserved.
- Added self-read proxy controls so a proxy flip becomes `inconclusive` rather than a false pass or false negative.
- Kept this as an isolated candidate harness; no deployed Skill, roadmap, evaluation set, deployment receipt, or authority file was changed.

## Verification

Targeted commands:

```powershell
python "D:\WeilanSkillEvolution\proposals\weilan-dynamics-firstcut-v0.1\candidate\solve-with-weilan\scripts\test_dynamics_firstcut.py"
python "D:\WeilanSkillEvolution\proposals\weilan-dynamics-firstcut-v0.1\candidate\solve-with-weilan\scripts\dynamics_firstcut.py" --json
```

Both passed. The machine-readable receipt is `TARGETED_VERIFICATION_RECEIPT.json`.

Freeze command:

```powershell
python tools/evolution_cli.py candidate-freeze --source "D:\WeilanSkillEvolution\proposals\weilan-dynamics-firstcut-v0.1\candidate\solve-with-weilan" --artifact-root "D:\WeilanSkillEvolution\proposals\weilan-dynamics-firstcut-v0.1\artifacts"
```

Result: `created: true`, artifact hash `f28bc2b678d28d6b09caae31f29587e9bb882823acacad4619083848db7ff097`.

## Boundaries

- No deployed Skill edit.
- No shadow run.
- No adoption.
- No deployment.
- No rollback authority.
- No `ROADMAP.md`, `ARCHITECTURE.md`, `EVALUATION_POLICY.md`, `evals/`, `deployments/`, `packages/`, or `tools/` candidate changes.
