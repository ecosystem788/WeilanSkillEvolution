# Latency attempt 1 — bounded timeout

The first copied-ledger probe declared four `open` samples per arm, ordered
baseline → candidate → candidate → baseline → candidate → baseline → baseline → candidate.
The outer command reached its 600-second bound and exited 124 before the probe could write
its aggregate receipt. No production ledger or installed Skill tree was written; the probe
used a temporary copied ledger.

This is a probe-budget failure, not evidence that either artifact returned an invalid
`open`. The retry uses three samples per arm. That remains above the inbox contract's
explicit floor (“样本数别只有 2”) while removing only the self-imposed fourth sample.
