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
| R2 Skill payload closure | Adopted Skill payload is fully accounted for; no cache noise or stale public copy is substituted | `INCLUSION_RECEIPT.json` remains valid for the previously adopted live tree. Candidate `wake_brief.py` now restores the dual-signed parse-diagnostic v0.3 implementation and differs from the impl copy only in the reviewed portable `_trace_script` default; candidate sha256 `b765d34abd282f6a0376c3c873ef0f6522e5566f7d958848484d2c1b2e491d36`. The mechanical merge passes the 26-test candidate suite and 61-file hygiene scan with 0 findings. Claude's single-file re-review (2026-07-16, `R2_INDEPENDENT_REVIEW.md` §F1 re-review) confirms the impl→candidate diff is exactly the reviewed portable default, and the parse-diagnostic contract tests pass when run against the candidate copy itself (4 passed) | PASS for current candidate | Recompute inclusion hashes at RC freeze without rewriting the old live-tree anchor |
| R3 Installer ownership | Install owns a manifest-closed file set and uninstall removes only owned, unchanged files | `INSTALL_OWNERSHIP_RECEIPT.json`: 55 owned files; clean/idempotent uninstall, sentinel preservation, drift refusal | BOUNDARY | Re-run from frozen candidate on a clean Windows account/machine |
| R4 Deterministic entry points | `install`, `start`, `stop`, `status`, `open-dashboard` have predictable exit/results and errors | Five-entry smoke is true in ownership receipt; status explicitly reports activation boundary | BOUNDARY | Exercise real portable runtime wiring; changing/merging scheduler or dashboard contracts requires a narrow dual-sign proposal |
| R5 Prerequisite discovery | Missing Python, Codex, Claude, or Skill discovery fails early with actionable text | Candidate preflight now requires a nonempty ordinary `SKILL.md`, rejects missing/empty Skill roots, and rejects Windows drive-qualified/rooted manifest targets before writes; the combined candidate suite passes 26 tests | PASS for current candidate | Repeat from the frozen RC and on a real clean machine to capture environment-specific prerequisite messages |
| R6 No user-specific paths | Runtime and docs contain no user/machine-specific absolute paths; configuration/path discovery is portable | Candidate `wake_brief.py` now resolves sibling `weilan_trace.py` by default while retaining `WEILAN_TRACE_SCRIPT`; generated `bin/install.ps1` reads the discovered checkout path from the local install receipt instead of embedding the build checkout path; the installer rejects Windows drive-qualified/rooted manifest targets before path composition, rejects existing symlink/junction parents that resolve an owned path outside the install root, prunes reparse directories before uninstall cleanup can descend through them, prunes root-external payload junctions, and rejects contained payload junctions before recursive alias enumeration; the final 61-file hygiene scan hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Independent payload review and R2 closure remain required; live scheduler/dashboard findings remain outside this candidate and dual-sign gated |
| R7 Fresh ledger isolation | New install creates fresh local state and never joins `D:\CodexData\home\method-state` or this community ledger implicitly | `RUNTIME_DEPLOYABILITY_RECEIPT.json`: fresh `WEILAN_METHOD_HOME`, recall=`NO_CONTEXT`, community ledger unused | PASS for Skill axis | Repeat through complete installer/runtime entry points and assert no state leakage |
| R8 Loopback dashboard | Dashboard binds to `127.0.0.1` by default and makes no unauthenticated LAN/public claim | `FINDING.md` verifies current loopback default | PARTIAL | Real installed `open-dashboard` smoke plus bind-address assertion |
| R9 Rollback | Failed install leaves no partial owned output; uninstall is idempotent; drift is preserved and reported | Installer tests now cover payload and receipt write failures, preservation of an old valid or unknown receipt, temporary-file cleanup, current-attempt payload rollback, idempotent uninstall, drift preservation, and refusal to follow an existing symlink/junction parent outside the install root | PARTIAL | Add concurrency and hard-kill/power-loss coverage, then repeat fault injection on the frozen RC |
| R10 Privacy and credentials | Frozen RC has zero credentials/private keys and excludes local inboxes, chats, logs, cursors, wake runs, and unrelated reports | The negative credential fixture is assembled only at runtime, its rejection regression still passes, and the code-owned final 61-file scan reports 0 findings and `PASS`; its exact tree hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Repeat against the immutable frozen RC and preserve the exact scanner/tree receipt |
| R11 Human installation UX | One documented command, prerequisite list, operation card, troubleshooting, uninstall, and no source edits required | Candidate README, operation card, and troubleshooting guide now cover install/status/uninstall, exit codes, recovery, and ownership boundaries; cross-review corrections are incorporated | PARTIAL | Have an unfamiliar reviewer run the instructions on a real clean machine and record time and ambiguities |
| R12 Clean-machine time | Complete install → start → status → dashboard → stop → uninstall in ≤10 minutes on a genuinely clean Windows environment | `clean_home_rehearsal.py` passes 3 isolated-root tests and forces `clean_machine_acceptance=false` and `runtime_activation_performed=false` in its receipt | BOUNDARY | Run and time the full lifecycle on a genuinely clean Windows environment; the local rehearsal cannot satisfy this row |
| R13 License | Exact release contents have a clear, compatible license and notices | Dual-signed revised Candidate A executed 2026-07-17 (Codex proposal 00:14:20 + Claude 同意, after Claude packet 00:03:05): root `LICENSE` copyright reattributed to `WeiLan` per owner attestation (peer-chat 2026-07-17 00:12:21, MIT confirmed), byte-identical copy at `skill/solve-with-weilan/LICENSE` (both sha256 `0193cdba…`, full hash in episode receipt), README license links point to the bundled copy, no NOTICE on the current 47-file provenance evidence; 26 tests + 9 subtests pass, hygiene PASS 62 files/0 missing/0 findings | PASS for current candidate, conditional on freeze-time rebind | Rebind LICENSE/README/tree hashes at RC freeze; any payload byte drift reopens verification; new notice obligations require a new dual-sign |
| R14 RC integrity | Every included file is allowlisted and hashed; tests and scans bind to the same immutable RC tree | After restoring parse-diagnostic v0.3 to candidate `wake_brief.py`, all 26 candidate tests pass (plus 9 subtests), and the scanner accounts for 14 proposal files plus 47 manifest payload files with 0 missing and 0 findings; the exact final tree hash is recorded outside this self-hashed matrix in the episode receipt. Claude's re-review reproduced the suite (26 passed, 9 subtests), the hygiene scan (PASS, 61 files, 0 findings, tree `f33c94c5…`), and closed R2; after the R13 license landing the scan surface is 14 proposal files plus 48 payload files (62 total, 0 missing, 0 findings, PASS, tree `2898e5a7…`, full hash in the episode receipt); the tree is still not frozen or independently adopted | PARTIAL | Freeze the exact candidate and rerun all checks without byte drift; do not change the old live anchor |
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
scheduler/dashboard wiring, a genuinely clean
Windows ≤10-minute run, license closure, frozen RC integrity, and independent
final audit are not closed.

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
