# Targeted Adoption and Deployment Plan

Status: authorized by the project owner on 2026-07-10.

## Exact binding

- Proposal: `method-state-atomic-replace-retry-v0.1`
- Deployed base hash: `847e1ad769dab389b1a75c2ed8c7ae90f6887e5fb614edbe9f139ab7ff462e74`
- Candidate artifact hash: `fefc8be133103844ab1987ff756c3d8b96fe685e7bb8d0356fb2c605adf70ff1`
- Deployment target: `D:\CodexData\skills\solve-with-weilan`
- Changed deployed paths: `scripts/runtime_core.py` and `scripts/test_event_atomic_replace_retry.py`

## Adoption gate

1. Revalidate `proposal.json`.
2. Re-freeze the candidate and require the exact candidate artifact hash.
3. Require the current deployment target to match the exact base hash.
4. Require exactly two candidate differences from the deployed base.
5. Run the focused retry tests and the complete candidate script regression.
6. Record adoption without mutating the deployment target.

## Deployment transaction

1. Prevent new bounded wake episodes and wait for existing episode locks to clear.
2. Copy the complete current deployment tree into a content-addressed rollback directory.
3. Require the rollback copy to match the exact base hash.
4. Atomically install only the two candidate differences.
5. Require the final deployment tree to match the exact candidate hash.
6. Run the focused retry tests and complete deployed script regression.
7. Open and close one real method-state canary frame using the deployed runtime.
8. Restore bounded wake operation and write the deterministic deployment receipt.

If a pre-commit check fails, deployment stops before target mutation. If target
verification fails during the deployment transaction, restore the verified
predecessor before releasing the wake pause and report the failed transaction.

## Boundary

This targeted channel is limited to a supporting storage-durability change. It
does not modify method decisions, `wake_codex.ps1`, project authority files, or
the fixed evaluation set. The change must be covered by the next full-suite
shadow together with other accumulated targeted deployments.
