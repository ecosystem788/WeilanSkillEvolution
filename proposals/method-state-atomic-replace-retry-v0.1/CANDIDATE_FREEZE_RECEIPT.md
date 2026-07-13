# Candidate Freeze Receipt

Date: 2026-07-10

## Scope

- Proposal: `method-state-atomic-replace-retry-v0.1`
- Authority: isolated candidate construction and verification only
- Adoption: not authorized
- Deployment: not authorized

## Artifact binding

- Read-only deployed base: `D:\CodexData\skills\solve-with-weilan`
- Base tree hash: `847e1ad769dab389b1a75c2ed8c7ae90f6887e5fb614edbe9f139ab7ff462e74`
- Candidate source: `proposals/method-state-atomic-replace-retry-v0.1/candidate/solve-with-weilan`
- Candidate tree hash: `fefc8be133103844ab1987ff756c3d8b96fe685e7bb8d0356fb2c605adf70ff1`
- Frozen artifact: `proposals/method-state-atomic-replace-retry-v0.1/artifacts/fefc8be133103844ab1987ff756c3d8b96fe685e7bb8d0356fb2c605adf70ff1/solve-with-weilan`

Changed candidate paths:

1. `scripts/runtime_core.py`
2. `scripts/test_event_atomic_replace_retry.py`

The runtime behavior change is one line: `write_event_file_atomic` now calls the
existing bounded `replace_with_retry` helper instead of calling `os.replace`
directly.

## Verification

Proposal validation:

```text
valid: true
issues: []
changed_path_count: 2
```

Same-contract discriminating probe:

```text
baseline: failed after 1 replace call; target file absent
candidate: succeeded after 3 replace calls; complete frame file present
```

Candidate tests:

```text
focused: 3 passed in 0.84s
full scripts regression: 60 passed in 24.67s
```

Freeze replay:

```text
first freeze: created=true
second freeze: created=false
artifact_hash=fefc8be133103844ab1987ff756c3d8b96fe685e7bb8d0356fb2c605adf70ff1
```

Final deployed-tree verification:

```text
847e1ad769dab389b1a75c2ed8c7ae90f6887e5fb614edbe9f139ab7ff462e74
```

The deployed tree remained unchanged throughout candidate construction,
verification, and freezing.

## Remaining gate

This receipt is evidence for a later adoption decision. It does not authorize
adoption, deployment, rollback, or modification of `wake_codex.ps1`.
