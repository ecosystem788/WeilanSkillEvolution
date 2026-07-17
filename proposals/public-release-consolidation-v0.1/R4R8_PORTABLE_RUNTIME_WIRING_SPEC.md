# R4/R8 portable runtime wiring — spec v0.5 (PROPOSAL, pending dual-sign)

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

v0.4 same day, revising after Codex's third【反对】(peer-chat 2026-07-17
15:59:05), which confirmed the two v0.2 conflicts closed but found two
acceptance-level conflicts inside v0.3 itself; both verified against the
v0.3 text and closed by this revision:

6. The v0.3 task-name guard asserted "no task named `WeilanScheduler-*`
   exists" during and after the test run — a host-global assertion, not an
   ownership assertion. On a shared machine carrying another legitimate
   install, acceptance would misread pre-existing external state as leakage,
   and a cleanup step keyed on that assertion could touch tasks the test
   does not own. → closed by the rewritten Task-name guard: read-only
   baseline snapshot of the `WeilanScheduler-*` name set (assert unchanged
   after the run), creation/deletion asserted only for the test-owned unique
   name, and deletion authority limited to names recorded in the test's own
   registration receipts — never a name pattern.
7. §D2b declared "every element individually double-quoted" while its own
   canonical string left `tick` and `--install-root` unquoted; more
   fundamentally, a Scheduled Task's persisted shape is the Execute /
   Arguments / WorkingDirectory triple, which the query API returns in
   normalized form — byte-for-byte identity with any single shell string
   cannot be guaranteed. → closed by the rewritten §D2b: the structured
   triple is the sole authority, hashed via one canonical JSON
   serialization; live verification compares field-by-field after
   documented normalization; acceptance reproduction launches by argv (no
   shell) so invocation semantics never depend on cmd-vs-PowerShell string
   interpretation.

v0.5 same day, revising after Codex's fourth【反对】(peer-chat 2026-07-17
16:11:34), which confirmed the two v0.3 conflicts closed but found one
remaining load-bearing hash-domain conflict inside v0.4's §D2b; verified by
independent reproduction (a minimal triple hashes to `50882ab4...` raw and
`41aa00e6...` after casefold+normpath — different byte domains can never
share a SHA-256) and closed by this revision:

8. v0.4 §D2b hashed the RAW absolute-path triple at registration time
   (canonical JSON → `action_sha256`) while instructing live verification
   to rebuild the triple only AFTER case-folding + `normpath`, then require
   that hash to equal the receipt's `action_sha256`. Any path containing an
   uppercase character (e.g. every stock `C:\Python...` interpreter) makes
   verification fail unconditionally, and equivalent Windows paths that
   differ only in case can never match. → closed by the rewritten §D2b: one
   documented `action_normalize(triple)` (normpath then casefold, applied
   to exactly the four path-bearing positions; every other token byte-
   exact) runs at ALL three hash sites — registration receipt, freshly
   recomputed expected value, and live-task verification — before the one
   canonical JSON serialization. The raw triple remains what is actually
   registered and displayed, but it is never hashed.

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

   **D2b. Action contract.** The authoritative action is a structured
   triple, never a shell string: `execute` (absolute interpreter path —
   `sys.executable` of the running Python, never a bare `python` from
   PATH), `arguments` (an argv array: absolute path of the installed
   `scheduler_cli.py`, `tick`, `--install-root`, `<install_root>`, plus
   `--tick-only` when applicable), `working_directory` (the install root).

   *One hash domain (v0.5).* A single documented function
   `action_normalize(triple)` defines the ONLY byte domain that is ever
   hashed. It applies `os.path.normpath` followed by `str.casefold` to
   exactly the path-bearing positions — `execute`, `arguments[0]` (the
   installed script path), the element immediately following
   `--install-root`, and `working_directory` — and leaves every other
   token byte-identical (non-path tokens such as `tick`, `--install-root`,
   `--tick-only` are compared exactly, never normalized). Canonical
   serialization: the NORMALIZED triple encoded as the JSON object
   `{"arguments": [...], "execute": "...", "working_directory": "..."}`
   UTF-8 with sorted keys, `(",", ":")` separators, and no trailing
   newline; its SHA-256 is `action_sha256`. The raw (un-normalized) triple
   is what is actually registered and displayed; it is never hashed. All
   three hash sites — the registration receipt, the freshly recomputed
   expected value, and live-task verification — call the same
   `action_normalize` before serializing, so every comparison happens
   inside one byte domain.

   Registration derives the Task Scheduler fields from the RAW triple —
   Execute = interpreter; Arguments = the argv tail joined by the one
   documented quoting function (an element is double-quoted iff it
   contains whitespace or quotes, embedded quotes escaped per Windows argv
   rules); WorkingDirectory = install root — and writes
   `<install_root>/data/runtime/task-registration.json` — `{task_name,
   action: {execute, arguments, working_directory}` (raw, for
   registration/display), `action_sha256` (SHA-256 of the normalized
   triple), `arguments_display_string, registered_utc}` — before `start`
   reports success. Verification never compares shell strings: re-entrant
   `start` queries the live task, extracts the three fields, parses the
   live Arguments back into an argv array under the same documented
   Windows rules, applies `action_normalize`, rebuilds the canonical
   triple, and checks its SHA-256 against BOTH the receipt's
   `action_sha256` and the `action_normalize`d freshly recomputed expected
   triple; any mismatch is re-pinned and logged, never silently accepted.
   If the resolved interpreter or script path does not exist at
   registration time, `start` refuses.
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
   test (including on failure paths) with deletion authority limited to
   names recorded in the test's own registration receipts, and never
   touching the community's own scheduled tasks or root, nor any
   pre-existing `WeilanScheduler-*` task (see the Task-name guard's
   baseline-snapshot semantics). If the signer
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
- **Action contract proof (§D2b)**: query the registered task, extract
  Execute/Arguments/WorkingDirectory, parse Arguments back into argv, apply
  `action_normalize`, rebuild the canonical triple, and assert its SHA-256
  equals `task-registration.json`'s `action_sha256` AND the hash of the
  `action_normalize`d freshly recomputed expected triple; assert the
  recorded raw interpreter and script paths are absolute and exist.
  Domain probes (both directions): (a) re-run verification against a
  case-variant rendering of the live path fields (e.g. upper-cased drive
  letter) and assert it still matches — path case must be invisible inside
  the normalized domain; (b) negative control: assert the SHA-256 of the
  RAW triple's canonical JSON does NOT equal `action_sha256` whenever any
  path-bearing field changes under `action_normalize` — guards the
  implementation against silently hashing the wrong domain. Reproduction
  runs by argv, no shell: spawn `[execute] + arguments` with
  `cwd=working_directory` exactly as Task Scheduler would, from a parent
  process whose own working directory is NOT the install root and whose
  PATH contains no `python`, and assert a new tick receipt appears (proves
  no PATH/parent-cwd dependence without betting on cmd-vs-PowerShell string
  semantics). Then corrupt a NON-path token of the live task's Arguments in
  place (e.g. `tick` → `tock`), re-run `start`, and assert it detects the
  field-level mismatch, re-pins, and logs.
- **Task-name guard (§D2a)**: `start --task-name Foo` (non-prefixed) refuses
  with exit non-zero and registers nothing. Ownership, not host-global
  emptiness: before the run, snapshot the set of existing task names
  matching `WeilanScheduler-*` (read-only baseline); after the run —
  including every failure path — assert that set is exactly unchanged, and
  assert the test's own unique `WeilanReleaseTest-<random>` task was
  created and then deleted. Cleanup deletes ONLY task names recorded in
  this test run's own registration receipts — never anything else, even if
  it happens to match the test prefix (protects concurrent runs and
  pre-existing installs alike). `status`/`stop`/`uninstall` resolve the
  test task via the receipt's recorded name.
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
