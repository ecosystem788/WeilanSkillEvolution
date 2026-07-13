# wake_brief runtime cursor permission observation v0.1

**Observer:** Codex bounded wake episode.
**Time:** 2026-07-10 22:00:05.
**Status:** green-zone observation only. No deployed code, wake prompt, scheduler, or ledger code changed.

## Observation

The first Codex wake after the supervised `wake_brief.py` deployment attempted the configured brief step:

```powershell
python "D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py" --workspace "D:\WeilanSkillEvolution" --scope "skill-evolution"
```

It failed before emitting a brief:

```text
PermissionError: [Errno 13] Permission denied: 'D:\CodexData\skills\solve-with-weilan\scripts\wake-cursor.json.tmp'
```

The fallback discipline still worked: Codex ignored the brief and read the inbox/tea-room files directly.

## Source evidence

The deployed script currently derives the cursor beside the script:

```text
D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py:280: cursor_path = root / "wake-cursor.json"
```

The original green-zone build spec instead scoped the only write to the proposal implementation area:

```text
proposals/bounded-scheduler-v0.1/impl/wake-cursor.json
```

The current deployed location is under the deployed skill tree, which is outside this Codex wake's writable roots. That makes the cursor write fail even though the rest of the brief is conceptually read-only.

## Conclusion

Deployment is functionally present, but Codex's current sandbox cannot use the incremental brief path because the cursor target is not writable. The failure is not an authority failure and does not corrupt state; it degrades to the original direct-read path.

## Minimal fix direction

Keep `wake_brief.py` read-only with respect to ledgers and inbox/chat files, but move or parameterize the cursor path so the deployed invocation writes only inside an authorized workspace/runtime location, for example:

- `D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\wake-cursor.json`, preserving the original prototype contract; or
- a method-state/runtime cursor location explicitly allowed for this purpose.

Do not patch this from an unattended wake. A supervised follow-up should update the deployed script or wake prompt contract, run full-rescan and incremental checks, and verify fallback behavior still works when cursor writes are denied.
