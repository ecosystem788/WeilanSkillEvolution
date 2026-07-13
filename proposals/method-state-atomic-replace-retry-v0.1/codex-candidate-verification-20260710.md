# Codex Candidate Verification - 2026-07-10

## Candidate scope

- Candidate tree: `proposals/method-state-atomic-replace-retry-v0.1/candidate/solve-with-weilan`
- Deployed tree left unchanged: `D:\CodexData\skills\solve-with-weilan`
- Runtime change: `scripts/runtime_core.py`

Diff against deployed `runtime_core.py` is intentionally one behavioral line:

```diff
-        os.replace(temporary, path)
+        replace_with_retry(temporary, path)
```

Only `write_event_file_atomic` changes. `write_json_atomic`, `replace_with_retry`,
locking, and the rest of the runtime surface are unchanged in the candidate copy.

## Added tests

- `scripts/test_event_atomic_replace_retry.py`

Coverage:

- transient `PermissionError` from `os.replace` is retried until success;
- retry exhaustion raises `PermissionError`, preserves the existing frame file, and leaves no temp shard;
- isolated method-state concurrent frame writes remain complete while a sibling scanner reads the frames directory.

## Verification

Targeted test:

```text
python -m pytest -q "proposals\method-state-atomic-replace-retry-v0.1\candidate\solve-with-weilan\scripts\test_event_atomic_replace_retry.py"
...                                                                      [100%]
3 passed in 3.84s
```

Full candidate script regression:

```text
cd proposals\method-state-atomic-replace-retry-v0.1\candidate\solve-with-weilan\scripts
python -m pytest -q
............................................................             [100%]
60 passed, 1 warning in 24.45s
```

Warning observed during full regression:

```text
PytestCacheWarning: could not create cache path ...\.pytest_cache ... [WinError 5]
```

The warning affected pytest cache creation only; all tests passed. It is consistent
with the same Windows atomic replace pressure and is not a failure of the candidate
runtime tests.

## Boundary

This is an isolated candidate and verification artifact only. It does not adopt,
deploy, modify `wake_codex.ps1`, or patch the deployed `runtime_core.py`.
