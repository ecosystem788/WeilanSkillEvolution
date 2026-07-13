# False Zero Guard v0.1

## Scope

This proposal patches only the isolated candidate skill at:

```text
proposals/false-zero-guard-v0.1/candidate/solve-with-weilan
```

It does not modify the installed skill at `D:\CodexData\skills\solve-with-weilan`, the frozen baseline under `packages/solve-with-weilan`, deployment receipts, roadmap, or evaluation authority files.

## Problem

Active semantic memories can declare `conflicts_with`, and `memory-conflicts` can list unresolved pairs, but recall/projection previously treated both sides as clean active semantic decisions. That lets a false-zero state persist: a conclusion is projected as settled while a live conflicting reference still consumes its difference.

## Change

- `active_semantic_entries(...)` now derives `contested_with` for every active semantic entry that conflicts with another active semantic entry.
- Contested entries remain searchable and remain projection sources.
- `projection-rebuild` excludes contested decision-like entries from clean `decisions` and `open_questions`.
- `projection-rebuild` preserves them under `contested_semantic_entries` and emits a warning.
- No side is deleted, superseded, retired, or preferred automatically.

## Adoption Notes

`memory-recall` reads the latest cached projection record. The guard therefore takes effect for recall after `projection-rebuild` has produced a new projection for the affected workspace/scope.

Adoption should include a rebuild pass for existing active scopes so old cached projections do not continue to expose contested entries as clean `decisions` or `open_questions`.

New conflicts created after a rebuild will appear in recall after the next rebuild. This is the existing projection-cache freshness window, not a new write-side authority. Making conflict consolidation trigger a rebuild should be treated as a separate follow-up candidate if immediate cold-start freshness becomes required.

## Verification

Commands run:

```powershell
python "D:\WeilanSkillEvolution\proposals\false-zero-guard-v0.1\candidate\solve-with-weilan\scripts\test_false_zero_guard.py" --temp-parent "D:\WeilanSkillEvolution\tmp"
python "D:\WeilanSkillEvolution\proposals\false-zero-guard-v0.1\candidate\solve-with-weilan\scripts\test_semantic_memory.py" --temp-parent "D:\WeilanSkillEvolution\tmp"
```

Both passed.
