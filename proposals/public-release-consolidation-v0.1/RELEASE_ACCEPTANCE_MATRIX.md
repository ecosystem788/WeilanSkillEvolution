# Windows first-release acceptance matrix — 2026-07-16

Target: a human can install the complete Windows first release from one
documented `WeilanSkillEvolution` entry in at most ten minutes, without editing
source or inheriting this community's private/local runtime state.

Status: planning and evidence matrix only. `PASS` means the cited axis has
current evidence; it does not authorize adoption, deployment, publication, or
release. `BOUNDARY` means a narrower simulation or payload test passed while
the real host/runtime claim remains open.

| Gate | Acceptance criterion | Current evidence | Status | Next evidence / authority |
|---|---|---|---|---|
| R1 Canonical product surface | Root explains repository role and that a packaged release is not yet published | Tracked root `README.md`; `FINDING.md` | PASS for disclosure | Update install documentation only after the candidate interface is frozen |
| R2 Skill payload closure | Adopted Skill payload is fully accounted for; no cache noise or stale public copy is substituted | `INCLUSION_RECEIPT.json` remains the historical live-tree anchor. Candidate `wake_brief.py` restores parse-diagnostic v0.3 and differs from the impl copy only in the independently reviewed portable `_trace_script` default; candidate sha256 `b765d34abd282f6a0376c3c873ef0f6522e5566f7d958848484d2c1b2e491d36`. `FREEZE_RECEIPT.json` rebinds the exact 62-file surface to R9 freeze commit `7ffc2a6687e183b1c9035e2d69f35fdff09ac4ca` and hygiene tree `501fd0a7e1a4af34aa42b0c52849650ee50a8118d161acafed8d3cdbd5b256d3`; `FREEZE_RECEIPT-RC1-dba1132.json` preserves the old anchor | PASS for frozen RC2 | Any candidate-byte drift requires a new freeze and R2 rebind |
| R3 Installer ownership | Install owns a manifest-closed file set and uninstall removes only owned, unchanged files | `INSTALL_OWNERSHIP_RECEIPT.json`: 55 owned files; clean/idempotent uninstall, sentinel preservation, drift refusal | BOUNDARY | Re-run from frozen candidate on a clean Windows account/machine |
| R4 Deterministic entry points | `install`, `start`, `stop`, `status`, `open-dashboard` have predictable exit/results and errors | Five-entry smoke is true in ownership receipt; status explicitly reports activation boundary | BOUNDARY | Exercise real portable runtime wiring; changing/merging scheduler or dashboard contracts requires a narrow dual-sign proposal |
| R5 Prerequisite discovery | Missing Python, Codex, Claude, or Skill discovery fails early with actionable text | Candidate preflight now requires a nonempty ordinary `SKILL.md`, rejects missing/empty Skill roots, and rejects Windows drive-qualified/rooted manifest targets before writes; the combined candidate suite passes 26 tests | PASS for current candidate | Repeat from the frozen RC and on a real clean machine to capture environment-specific prerequisite messages |
| R6 No user-specific paths | Runtime and docs contain no user/machine-specific absolute paths; configuration/path discovery is portable | Candidate `wake_brief.py` now resolves sibling `weilan_trace.py` by default while retaining `WEILAN_TRACE_SCRIPT`; generated `bin/install.ps1` reads the discovered checkout path from the local install receipt instead of embedding the build checkout path; the installer rejects Windows drive-qualified/rooted manifest targets before path composition, rejects existing symlink/junction parents that resolve an owned path outside the install root, prunes reparse directories before uninstall cleanup can descend through them, prunes root-external payload junctions, and rejects contained payload junctions before recursive alias enumeration; the final 61-file hygiene scan hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Independent payload review and R2 closure remain required; live scheduler/dashboard findings remain outside this candidate and dual-sign gated |
| R7 Fresh ledger isolation | New install creates fresh local state and never joins `D:\CodexData\home\method-state` or this community ledger implicitly | `RUNTIME_DEPLOYABILITY_RECEIPT.json`: fresh `WEILAN_METHOD_HOME`, recall=`NO_CONTEXT`, community ledger unused | PASS for Skill axis | Repeat through complete installer/runtime entry points and assert no state leakage |
| R8 Loopback dashboard | Dashboard binds to `127.0.0.1` by default and makes no unauthenticated LAN/public claim | `FINDING.md` verifies current loopback default | PARTIAL | Real installed `open-dashboard` smoke plus bind-address assertion |
| R9 Rollback | Failed install leaves no partial owned output; uninstall is idempotent; drift is preserved and reported | Frozen RC2 adds a `Local\\` Windows named mutex keyed by the final resolved, case-folded install root. The external real-process harness passes two concurrent installs, an install/uninstall race, `os._exit` during payload write, and `os._exit` before receipt replace, plus alias/junction identity, distinct-root parallelism, and bounded actionable timeout checks (`7 tests OK`). `WAIT_ABANDONED` enters the ordinary recovery/conflict path. A half-owned RC1 remainder is not silently healed by status: it reports `drifted` with exact `missing` paths; a later install may safely repair or return an exact conflict. Main and frozen worktrees both passed the same harness | PASS for frozen RC2 | Keep the seven-scenario harness in every later freeze; any installer-byte drift reopens R9 |
| R10 Privacy and credentials | Frozen RC has zero credentials/private keys and excludes local inboxes, chats, logs, cursors, wake runs, and unrelated reports | The negative credential fixture is assembled only at runtime, its rejection regression still passes, and the code-owned final 61-file scan reports 0 findings and `PASS`; its exact tree hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Repeat against the immutable frozen RC and preserve the exact scanner/tree receipt |
| R11 Human installation UX | One documented command, prerequisite list, operation card, troubleshooting, uninstall, and no source edits required | Candidate README, operation card, and troubleshooting guide now cover install/status/uninstall, exit codes, recovery, and ownership boundaries; cross-review corrections are incorporated | PARTIAL | Have an unfamiliar reviewer run the instructions on a real clean machine and record time and ambiguities |
| R12 Clean-machine time | Complete install → start → status → dashboard → stop → uninstall in ≤10 minutes on a genuinely clean Windows environment | `clean_home_rehearsal.py` passes 3 isolated-root tests and forces `clean_machine_acceptance=false` and `runtime_activation_performed=false` in its receipt | BOUNDARY | Run and time the full lifecycle on a genuinely clean Windows environment; the local rehearsal cannot satisfy this row |
| R13 License | Exact release contents have a clear, compatible license and notices | Root `LICENSE` and `skill/solve-with-weilan/LICENSE` remain byte-identical at sha256 `0193cdbacc8174c2af478e8de69bd919a6b36edd7fbd039bd82d83e280aed4e1`; README license links and the 47-file provenance evidence are unchanged. Main and frozen RC2 verification each passed 26 candidate tests + 7 R9 tests and hygiene `PASS/62/0/0/tree=501fd0a7...`; `FREEZE_RECEIPT.json` binds these results to `7ffc2a6687e183b1c9035e2d69f35fdff09ac4ca` | PASS (bound to freeze commit `7ffc2a6687e183b1c9035e2d69f35fdff09ac4ca`) | Any payload byte drift or new notice obligation reopens R13 and requires a new dual-sign/freeze |
| R14 RC integrity | Every included file is allowlisted and hashed; tests and scans bind to the same immutable RC tree | R9 re-freeze commit `7ffc2a6687e183b1c9035e2d69f35fdff09ac4ca` (Git tree `48972870ad30d43a0d2e09270b018a77fb061ec3`) and a fresh detached checkout independently produced hygiene `PASS`, 62 files, 0 missing, 0 findings, tree `501fd0a7e1a4af34aa42b0c52849650ee50a8118d161acafed8d3cdbd5b256d3`, 67/67 signed paths at `eol=lf`, 26 candidate tests + 7 R9 tests, and matching LICENSE hashes. Exact hashes and dual-sign are in `FREEZE_RECEIPT.json`; RC1 receipt remains archived | PASS for frozen RC2 | Any change to the 62-file surface invalidates this receipt and requires a new freeze; independent final audit remains R15 |
| R15 Independent final audit | Reviewer checks exact artifact/commit hash, acceptance lines, test output, omissions, and sign-after-drift invalidation | Not yet performed | OPEN / DUAL-SIGN | Claude Opus final independent audit after all implementation gates close |
| R16 Publication | Push/tag/release uses the signed RC and publishes hashes/rollback receipt | Owner directed: all work completes before push | BLOCKED BY POLICY | Separate dual-sign publication proposal after R1–R15 close; no push in this episode |

## Current verdict

`NOT_RELEASE_READY`.

The principal method/runtime payload and isolated ownership mechanics are real
progress, not placeholders: R3/R4/R9 have bounded passing evidence, and the
current candidate now clears its 61-file path/privacy scan. The candidate
payload fixes intentionally make the old live-tree inclusion receipt stale.
The parse-diagnostic v0.3 omission found during independent review is
mechanically repaired, locally verified, and closed by Claude's single-file
re-review of the exact merged `wake_brief.py` (2026-07-16); the old anchor
must not move to manufacture a pass. Portable
scheduler/dashboard wiring, a genuinely clean Windows ≤10-minute run, and
independent final audit are not closed. License binding and frozen RC integrity
are now closed for RC1 by `FREEZE_RECEIPT.json`; signatures do not survive
candidate-byte drift.

## Order of work without Claude

The currently authorized Claude-free sequence is limited to reversible
candidate work:

1. Complete candidate-only prerequisite, path/config, error, idempotency, and
   rollback behavior without activating the real Task Scheduler or dashboard.
2. Add isolated HOME, negative prerequisite, ledger-isolation, five-entry
   simulation, path/privacy/credential, and hash tests.
3. Draft README, operation card, troubleshooting, and license candidates; do
   not select or publish a license unilaterally.
4. Run and label a local clean-HOME rehearsal; never call it a clean-machine
   result.

Stop and route through a narrow dual-sign proposal before modifying or formally
merging scheduler/wake/dashboard contracts, deploying or starting real host
tasks, selecting the outward license, changing project authorities, adopting a
live Skill, or performing push/tag/release.
