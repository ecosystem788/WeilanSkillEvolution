# lower-the-floor-tooth v0.1 implementation receipt

Status: implemented as an isolated candidate; not deployed.

Frozen SPEC: `SPEC.md` FROZEN v0.1a.

Candidate source:

```text
proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan
```

Content-addressed artifact:

```text
artifact_hash=9b2130988817076de547dffe3627d31501d4f62e584a2d00daf979c8db36a3c9
artifact_path=proposals/lower-the-floor-tooth-v0.1/artifacts/9b2130988817076de547dffe3627d31501d4f62e584a2d00daf979c8db36a3c9/solve-with-weilan
```

Implemented behavior:

- Added `memory-note`, an atomic single-command conversation path for `evidence-capture` + `evidence-promote`.
- Success path writes evidence, semantic memory, and PROMOTED promotion audit inside one scope `contract_fence`.
- Policy rejects write no evidence, no semantic memory, and no promotion audit.
- `stable`, `reusable`, and `privacy-reviewed` remain explicit required judgments.
- v0.1 keeps file/frame-only, multi-source, displace, supersedes, and conflicts-with unsupported.
- Candidate currently copies capture/promote gate checks into `memory-note`; full reject equivalence tests guard against gate drift.

Verification:

```powershell
python -m py_compile "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/weilan_trace.py" "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/test_memory_note.py"
python "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/test_memory_note.py" --temp-parent "D:\WeilanSkillEvolution\staging"
python "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/test_conversation_evidence.py" --temp-parent "D:\WeilanSkillEvolution\staging"
python "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/test_semantic_integrity.py" --temp-parent "D:\WeilanSkillEvolution\staging"
python "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/test_semantic_memory.py" --temp-parent "D:\WeilanSkillEvolution\staging"
python "proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan/scripts/test_runtime_boundary.py" --temp-parent "D:\WeilanSkillEvolution\staging"
python "tools/evolution_cli.py" candidate-freeze --source "D:\WeilanSkillEvolution\proposals\lower-the-floor-tooth-v0.1\candidate\solve-with-weilan" --artifact-root "D:\WeilanSkillEvolution\proposals\lower-the-floor-tooth-v0.1\artifacts"
python "proposals/lower-the-floor-tooth-v0.1/artifacts/9b2130988817076de547dffe3627d31501d4f62e584a2d00daf979c8db36a3c9/solve-with-weilan/scripts/test_memory_note.py" --temp-parent "D:\WeilanSkillEvolution\staging"
```

Focused harness result:

```json
{
  "valid": true,
  "floor_lowered": "2_to_1",
  "success_records": "evidence+semantic+promotion_audit",
  "rejects_are_atomic": true,
  "manual_equivalence": true,
  "reject_equivalence_full": true,
  "retry_no_duplicate": true,
  "non_durable_signals_tested": 3
}
```

Boundary:

This receipt is candidate evidence only. Adoption and deployment still require separate project authority.
