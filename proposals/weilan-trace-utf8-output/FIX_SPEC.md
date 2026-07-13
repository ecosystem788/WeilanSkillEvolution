# Fix Spec — weilan_trace.py UTF-8 console output (Windows GBK crash)

Status: `targeted_deployed_reshadow_completed_failed_no_adoption`
Date: 2026-07-05
Author: Claude (spec/audit role). Executor: Codex. Channel: **targeted deployment**
(non-method supporting change), owner authorization required for deploy.

Deployment: `deployments/cbfe4af9af792d7bcf719113/`
Before artifact: `2c539d0b9444a395e66ce4ddaad1412f0ea5c4f0541112f63d3365c65d2bcf4f`
After artifact: `cbfe4af9af792d7bcf719113aaf95d1f04a5b12cd946b0bfde3f9d4e5320215c`

## Defect (reproduced live 2026-07-05, this session)

`memory-recall --workspace "D:\weilan-llm-fusion" --scope "fusion-program"` dies with
`error: 'gbk' codec can't encode character '̂' …` unless the caller sets
`PYTHONIOENCODING=utf-8`. Cause: the CLI prints JSON via
`print(json.dumps(..., ensure_ascii=False))` in dozens of sites, while Windows console
stdout defaults to the GBK code page; any non-GBK character in ledger content kills the
command. Cross-project recall — a core SE-0.2 capability — is unusable on this platform
without an undocumented environment variable.

## Fix (output layer only)

At `main()` entry in `scripts/weilan_trace.py` (deployed base `2c539d0b…`), before any
command dispatch:

```python
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
```

- `errors="replace"` guarantees no output path can crash on encoding again.
- File writes are untouched (already `encoding="utf-8"` at every `open`).
- No parsing, validation, lineage, memory, or gate logic changes — zero method behavior.

## Tests (added to the skill's test set)

1. Invoking a JSON-emitting command with ledger content containing non-GBK characters
   (e.g. `̂`, CJK) succeeds with `PYTHONIOENCODING` unset and console codepage GBK
   (simulate by wrapping stdout in a GBK-encoded buffer).
2. Output remains valid UTF-8 JSON parseable by `json.loads`.
3. Existing full test suite passes unchanged.

## Channel justification and sequencing

- Targeted channel is restricted to supporting changes that do not alter method behavior;
  an output-encoding shim meets that bar squarely (same class as transcript-support).
- **Sequence before binding `RESHADOW_PREREG.md`**: deploy this targeted fix first, then
  bind the re-shadow plan with the fresh deployed tree hash — the re-shadow baseline arm
  then re-covers all accumulated targeted changes (ROADMAP item 3) including this one.
  The prereg already mandates re-hashing the deployed tree at plan-binding time.

## Out of scope (recorded, not fixed here)

Historical mojibake already stored in the ledger (e.g. garbled Chinese in old control
records, `authority_text: "?????"` in the v0.1 approval receipt) is capture-time damage
from GBK pipes, append-only history. Original texts remain recoverable via their bound
conversation sources where needed. No history rewrite.
