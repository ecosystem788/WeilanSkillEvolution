# R4/R8 portable runtime wiring — spec v0.3 (PROPOSAL, pending dual-sign)

Status: spec only. This file has zero authority until a tearoom【提案】/【同意】
pair covers the implementation. Writing this file changes no frozen bytes: it is
outside the RC2 62-file candidate surface (freeze commit `7ffc2a6`, hygiene tree
`501fd0a7...`).

Author: Claude, 2026-07-17. v0.1 survey evidence gathered same day from live
tree. v0.2 same day, revising after Codex's【反对】(peer-chat 2026-07-17
15:13:12), which raised three load-bearing counterexamples; all three were
re-verified at source and are closed by this revision:

1. `impl/bounded_scheduler.py` has no `main`/CLI/agent-wake (verified: zero
   grep hits for `__main__|argparse|def main|sys.argv`) — pointing a Scheduled
   Task at it yields "task exists", not a real wake. → closed by §D1
   (`scheduler_cli.py`, a real shipped entry with observable tick receipts).
2. `observe.py` couples beyond the two path roots: hardcoded
   `WORKSPACE_KEY`/`SCOPE_KEY` (`observe.py:39-40`), `WAKE_AGENT =
   wake_agent.ps1` (`:46`, not on the release surface), six sibling
   inbox/chat write paths (`:48-54`), community `HEARTBEAT_TASK` (`:66`).
   Parameterizing only the two roots would ship dangling write entry points.
   → closed by §D3: observe.py is NOT shipped at all; a new read-only
   `dashboard.py` replaces it on the release surface.
3. v0.1 never defined PID/port ownership or reliable termination for the
   dashboard background process; the five-entry lifecycle could not prove
   zero residue. → closed by §D4 (pidfile ownership, idempotent stop, crash
   recovery, uninstall residue assertions).

v0.3 same day, revising after Codex's second【反对】(peer-chat 2026-07-17
15:40:11), which confirmed the three v0.1 counterexamples closed but raised
two new load-bearing conflicts inside v0.2 itself; both verified at source
and closed by this revision:

4. §D2 pinned the product task name `WeilanScheduler-<install_id>` while §D7
   authorized acceptance to register ONLY `WeilanReleaseTest-<random>` — the
   `start --tick-only` acceptance path had no compliant task name available,
   so any test run had to violate one of the two clauses. → closed by §D2a
   (constrained `--task-name` injection: refuses any value not prefixed
   `WeilanReleaseTest-`; all lifecycle entries operate on the recorded name,
   never a recomputed default).
5. §D2's task action was `python scheduler_cli.py tick --install-root <root>`
   — bare interpreter from PATH plus a relative script path. A Scheduled Task
   runs non-interactively with its own PATH and working directory, so the
   task could register successfully yet never produce a tick receipt: exactly
   the "task exists but nothing runs" failure this spec exists to kill. →
   closed by §D2b (absolute interpreter + absolute script + explicit working
   directory + quoting rule, all captured in a registration receipt with an
   action hash that re-entrant `start` and acceptance re-verify).

## Problem

R4 (BOUNDARY), R8 (PARTIAL), and R12 (BOUNDARY) are all blocked by the same
fact: the release ships no scheduler/dashboard runtime at all. The install
manifest carries a single payload (`skill/solve-with-weilan`), and the
generated `start`/`stop`/`open-dashboard` entries deliberately refuse real
activation (`release_installer.py` module docstring;
`INSTALL_OWNERSHIP_RECEIPT.json` `runtime_activation_ready: false`, boundary
text: "scheduler/dashboard sources still contain machine-specific paths").
The matrix target line requires the full install → start → status → dashboard
→ stop → uninstall lifecycle, so a Skill-only release cannot close these rows
without narrowing their meaning, which the R9 task already prohibited.

## Survey of the live runtime sources (2026-07-17, corrected in v0.2)

| Source (proposals/bounded-scheduler-v0.1/impl) | Machine/community coupling | Ship? |
|---|---|---|
| `bounded_scheduler.py` (292 lines) | no machine paths, but **no CLI entry at all** — pure importable reducer | ship as library; a new `scheduler_cli.py` provides the executable entry (§D1) |
| `observe.py` (911 lines) | `:37` repo root; `:38` `D:\CodexData\...` method state; `:39-40` hardcoded workspace/scope keys; `:46` `wake_agent.ps1` dependency (not on release surface); `:48-54` six sibling inbox/chat **write** paths; `:66` community `HEARTBEAT_TASK` name | **DO NOT ship** (v0.2 reversal). It is a write-capable community console, not a viewer. Replaced by new read-only `dashboard.py` (§D3) |
| `launch_observe.py` (310 lines) | launches observe.py | DO NOT ship (follows observe.py) |
| `run_wake_cron.ps1` | `:13` repo path; `:74-75` local proxy `127.0.0.1:2080`; delegates to `wake.py`/`wake_agent.ps1` → agent CLI with user credentials | DO NOT ship as-is; the agent leg of the chain is inherently user-configured (§D2) |
| `dashboard.html` | static snapshot embedding real community chat and `D:\CodexData\...` frame paths | DO NOT ship ever (R10 privacy) |
| `launch_observe_hidden.vbs` / `run_wake_cron_hidden.vbs` | wrappers over non-shipped scripts | DO NOT ship |

## Design

1. **Real executable entry (`scheduler_cli.py`).** New file
   `skill/solve-with-weilan/runtime/scheduler_cli.py`, shipped inside the
   existing single payload alongside a portable copy of
   `bounded_scheduler.py` (imported as a library). Subcommand `tick` performs
   one real, observable scheduler pass: load runtime config, evaluate due
   work via the reducer, invoke the configured `agent_command` if present
   (one bounded episode), and **always append a tick receipt** to
   `<install_root>/data/runtime/scheduler-ticks.jsonl` (`time_utc`, config
   hash, outcome: `agent_invoked` / `agent_failed(exit,stderr_hash)` /
   `no_agent_configured` / `nothing_due`). A registered task is therefore
   verifiable as a *running* entity by its receipt trail, never by mere task
   existence.
2. **Honest wake chain.** The community's real chain is Task Scheduler →
   `run_wake_cron.ps1` → `wake.py` + `wake_agent.ps1` → agent CLI with the
   operator's own credentials. The agent leg cannot ship. Portable contract:
   `runtime.json` (under the install data dir) may define `agent_command`
   (argv array, run from install root). `start` **refuses with actionable
   text** unless `agent_command` is configured or `--tick-only` is passed
   explicitly; tick-only mode is named in the task action and in every
   receipt, so a heartbeat-without-agent is an explicit, observable state —
   never a silent fake. `start` registers a per-user Scheduled Task; its
   name and action are pinned by §D2a/§D2b below.

   **D2a. Task name contract.** Product default:
   `WeilanScheduler-<install_id>` (install id from the local install
   receipt; never the community task name). `start` additionally accepts
   `--task-name <name>` for test harnesses ONLY: any value not prefixed
   `WeilanReleaseTest-` is refused with actionable text (exit non-zero,
   nothing registered). The chosen name — default or injected — is written
   to the registration receipt (§D2b), and `status`/`stop`/`uninstall`
   operate exclusively on the receipt's recorded name, never a recomputed
   default, so the full lifecycle works identically under a test name.
   Acceptance therefore registers real tasks only under the §D7-authorized
   prefix while the product default remains install-isolated.

   **D2b. Action contract.** At registration time `start` resolves and
   records: the absolute interpreter path (`sys.executable` of the running
   Python — never a bare `python` from PATH), the absolute path of the
   installed `scheduler_cli.py`, the explicit working directory (the
   install root), and the full argv. Quoting rule: every element of the
   action string is individually double-quoted; the canonical action string
   is `"<interpreter>" "<script>" tick --install-root "<root>"` (plus
   `--tick-only` when applicable) and its SHA-256 is the action hash. All
   of this is written to
   `<install_root>/data/runtime/task-registration.json` — `{task_name,
   interpreter, script, working_directory, argv, action_string,
   action_sha256, registered_utc}` — before `start` reports success.
   Re-entrant `start` queries the live task, recomputes the canonical
   action string, and verifies it against BOTH the receipt hash and the
   live task's registered action; any mismatch is re-asserted and logged,
   never silently accepted. If the resolved interpreter or script path does
   not exist at registration time, `start` refuses.
3. **Read-only dashboard (`dashboard.py`).** New shipped file; a view-only
   derivation of observe.py's report layer. Parameters (no baked defaults):
   `--repo-root`, `--method-home`, `--port` (env overrides `WEILAN_REPO_ROOT`,
   `WEILAN_METHOD_HOME`, `WEILAN_DASHBOARD_PORT` honored, never required);
   workspace/scope keys discovered by enumerating the method home's
   projection tree, `--workspace-key`/`--scope-key` required only when
   ambiguous. GET-only HTTP surface; refuses non-GET with 405. No
   owner-inbox endpoint, no wake trigger, no `wake_agent.ps1`, no sibling
   jsonl writes, no community task name. The write-capable console
   (observe.py) remains community-internal and off the release surface.
4. **Process/task lifecycle (both runtime entities).**
   - *Ownership.* `open-dashboard` writes
     `<install_root>/data/runtime/dashboard.pid` — JSON `{pid, port,
     started_utc, cmdline_sha256}` — before serving. The process owns exactly
     that port on 127.0.0.1.
   - *Idempotence.* `open-dashboard` with a live matching pidfile prints the
     existing URL and exits 0 (no second process). `start` with the task
     already registered re-asserts its action/root and exits 0.
   - *`status`.* Reports: task registered (name, last/next run), age of last
     tick receipt, dashboard liveness (pid alive AND cmdline hash matches
     AND HTTP 200 on `/`), port. Exit 0 with a machine-parsable summary.
   - *Idempotent `stop`.* Unregisters the task if present; terminates the
     dashboard pid **only after re-verifying its cmdline hash** (recycled-PID
     guard), then removes the pidfile; exits 0 when there was nothing to
     stop.
   - *Crash recovery.* A stale pidfile (dead pid, or live pid with cmdline
     mismatch) is detected and cleaned by any of `status` / `stop` /
     `open-dashboard`; cleanup is logged, never silent.
   - *`uninstall`.* Runs `stop`, then asserts zero residue — task query by
     name returns nothing, pidfile gone, port closed — before removing owned
     files. A residue check failure aborts uninstall with actionable text.
5. **Config discovery.** All path roots are explicit parameters with
   receipt-derived defaults: entries read `install_root` from the local
   install receipt and pass `--repo-root` / `--method-home` explicitly.
   Default method home lives **under the install root's data directory** — a
   fresh install must never resolve to `D:\CodexData\home\method-state` or
   any path outside the install root unless the user sets the env override
   themselves (R7 regression guard).
6. **Bind policy (R8).** `dashboard.py` binds `127.0.0.1` unconditionally by
   default. A non-loopback bind requires an explicit `--bind` flag AND a
   second explicit acknowledgement flag; docs state the exposure. Acceptance
   asserts the real socket's local address is loopback (netstat/psutil), not
   just the config string.
7. **Host-task authorization (narrow; interface added in v0.3).** Acceptance
   tests may register a real Scheduled Task ONLY with a test-unique name
   prefix (`WeilanReleaseTest-<random>`), injected via the §D2a
   `--task-name` interface (the only way `start` accepts a non-default
   name), pointing ONLY at an isolated install root, deleted in the same
   test (including on failure paths), and never touching the community's
   own scheduled tasks or root. If the signer
   rejects real task registration, fallback: `start`/`stop` ship with a
   `--register-task` opt-in and the acceptance run exercises the
   no-Task-Scheduler direct-process path; R4 then stays BOUNDARY on the task
   axis and says so honestly.
8. **Consequences accepted.** Candidate byte surface grows → RC2 signatures
   die by design: new freeze (RC3), R2/R13/R14 rebind, R10 hygiene rescan
   over the enlarged surface (extend the private-string patterns to cover at
   minimum `CodexData`, the local user name, proxy endpoints, and the
   community task/workspace/scope identifiers), full 26+7+new tests green in
   main AND frozen checkout.
9. **Rollback.** All changes are new files plus entry-wiring diffs in
   `release_installer.py`; revert = git revert of the implementation commits;
   RC2 receipts (`FREEZE_RECEIPT.json`, RC1 archive) remain untouched as
   historical anchors. No push (owner directive 2026-07-16 20:04:36 stands).

## Acceptance (feeds matrix rows; no row-narrowing)

- **R4 lifecycle**: in an isolated install root with fresh method home: all
  five entries exit 0 with predictable output; each failure mode (missing
  prerequisite, busy root, drifted install, unconfigured `agent_command`
  without `--tick-only`) produces actionable text; uninstall leaves nothing
  owned behind.
- **Real-runtime proof (anti-"task exists")**: after `start --tick-only
  --task-name WeilanReleaseTest-<random>` in the isolated root, trigger the
  task once and assert a new receipt line in `scheduler-ticks.jsonl` with
  outcome `nothing_due`/`no_agent_configured`; with a stub `agent_command`
  (test-local script), assert outcome `agent_invoked` and the stub's
  side-effect file exists.
- **Action contract proof (§D2b)**: query the registered task and assert its
  live action string equals `task-registration.json`'s `action_string`
  byte-for-byte and matches `action_sha256`; assert the recorded interpreter
  and script paths are absolute and exist; run the recorded action string
  verbatim from a shell whose working directory is NOT the install root and
  with a PATH containing no `python`, and assert it still appends a tick
  receipt (proves no PATH/cwd dependence). Re-run `start` after manually
  corrupting the task action and assert it detects, re-asserts, and logs the
  mismatch.
- **Task-name guard (§D2a)**: `start --task-name Foo` (non-prefixed) refuses
  with exit non-zero and registers nothing; during and after the whole test
  run, no task named `WeilanScheduler-*` exists (the product default never
  leaks into acceptance); `status`/`stop`/`uninstall` resolve the test task
  via the receipt's recorded name.
- **Lifecycle/residue**: `status` truthfully reports both entities in all
  four states (neither / task only / dashboard only / both); `stop` twice in
  a row both exit 0; kill -9 the dashboard, assert the next `status` reports
  it dead and cleans the stale pidfile; after `uninstall`, task query is
  empty, port is closed, no owned file remains.
- **Read-only dashboard**: every non-GET request returns 405; grep of the
  shipped `dashboard.py` finds no reference to `wake_agent`, owner-inbox,
  codex-inbox, or peer-chat write paths; loopback + HTTP 200 + zero
  non-loopback sockets owned by the process; `--bind` without the
  acknowledgement flag refuses.
- **R7 regression**: after the full lifecycle, community ledger
  (`D:\CodexData\home\method-state`) byte-identical (hash before/after), and
  the new method home exists under the isolated root.
- **Hygiene**: release_candidate_hygiene over the new surface: 0 findings;
  explicitly assert the shipped runtime contains no `observe.py`, no
  `dashboard.html` snapshot, no proxy config, no drive-qualified defaults,
  no community task/workspace/scope identifiers.
- **Freeze discipline**: implementation stops and reports (no silent drift)
  if any step would mutate RC2 frozen bytes before the new freeze lands.

## Division of labor

Spec + review: Claude. Implementation + harness + RC3 freeze mechanics: Codex
(inbox task follows the tearoom sign). R15 final audit remains open and
unclaimed by this proposal.
