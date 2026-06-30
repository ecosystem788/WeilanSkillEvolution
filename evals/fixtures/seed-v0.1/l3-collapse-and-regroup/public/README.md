# Prepared migration recovery

Run `python migration.py source target.db`. The route in `route.json` has already produced the two failures under `attempts/`. Recover without weakening the standard: every source user and order must appear exactly once, order ownership must remain within its tenant, rerunning must be idempotent, and unseen tenant names and large legacy IDs must work.

Preserve `legacy_reader.py`. Produce `recovery.json` describing the collapse and regroup, and a verified `target.db`.
