# Local event-ingestion architecture fixture

Choose and prototype a local, single-process event store using only the Python standard library.

Frozen constraints:

- Acknowledgement is durable when `ingest_batch` returns.
- Nearest-rank p95 acknowledgement latency is at most 75 ms for a 64-event batch.
- After close, all files below the store path total at most 1.50 times the canonical payload bytes.
- `rollback_last_batch` completes within 1000 ms and restores the exact prior event digest.
- Preserve event order and source events. No network access.

Implement the API in `prototype.py`. Produce `decision.json`, `evidence.json`, and `tests/test_discriminating.py`.
