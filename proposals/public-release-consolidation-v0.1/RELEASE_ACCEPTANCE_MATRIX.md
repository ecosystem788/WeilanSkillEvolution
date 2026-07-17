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
| R2 Skill payload closure | Adopted Skill payload is fully accounted for; no cache noise or stale public copy is substituted | Historical live-tree and RC1/RC2 anchors remain unchanged. `FREEZE_RECEIPT-RC3-d89340f.json` binds the intentional portable runtime addition plus proposal evidence to the exact 68-file allowlist at commit `d89340f36e2346284a1fbabefea91dd4c8833b86`, hygiene tree `9e6220fca2d05cfca7ee5cec2e99f1e4b7e48f2203c628045d82df9308dc05b8` | PASS for frozen RC3 | Any candidate-byte drift requires a new freeze and R2 rebind; independent final code audit remains R15 |
| R3 Installer ownership | Install owns a manifest-closed file set and uninstall removes only owned, unchanged files | RC3 `INSTALL_OWNERSHIP_RECEIPT.json`: 61 owned files; real lifecycle, sentinel preservation, drift refusal, idempotent stop/uninstall, exact receipt-owned task cleanup, and zero owned residue pass | PASS on current host / frozen RC3 | Re-run on a genuinely clean Windows account/machine |
| R4 Deterministic entry points | `install`, `start`, `stop`, `status`, `open-dashboard` have predictable exit/results and errors | Real isolated install executes all five entries; a unique test task produces a tick receipt, status reports task+dashboard, stop twice succeeds, and uninstall removes owned runtime | PASS on current host / frozen RC3 | Clean-machine reproduction remains R12; contract changes require a new dual-sign proposal |
| R5 Prerequisite discovery | Missing Python, Codex, Claude, or Skill discovery fails early with actionable text | Candidate preflight now requires a nonempty ordinary `SKILL.md`, rejects missing/empty Skill roots, and rejects Windows drive-qualified/rooted manifest targets before writes; the combined candidate suite passes 26 tests | PASS for current candidate | Repeat from the frozen RC and on a real clean machine to capture environment-specific prerequisite messages |
| R6 No user-specific paths | Runtime and docs contain no user/machine-specific absolute paths; configuration/path discovery is portable | Candidate `wake_brief.py` now resolves sibling `weilan_trace.py` by default while retaining `WEILAN_TRACE_SCRIPT`; generated `bin/install.ps1` reads the discovered checkout path from the local install receipt instead of embedding the build checkout path; the installer rejects Windows drive-qualified/rooted manifest targets before path composition, rejects existing symlink/junction parents that resolve an owned path outside the install root, prunes reparse directories before uninstall cleanup can descend through them, prunes root-external payload junctions, and rejects contained payload junctions before recursive alias enumeration; the final 61-file hygiene scan hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Independent payload review and R2 closure remain required; live scheduler/dashboard findings remain outside this candidate and dual-sign gated |
| R7 Fresh ledger isolation | New install creates fresh local state and never joins the community ledger implicitly | Full runtime acceptance creates method state only below the isolated install root; an explicit shared-ledger before/after snapshot stayed unchanged during the isolated run | PASS on current host / frozen RC3 | Repeat on a genuinely clean machine |
| R8 Loopback dashboard | Dashboard binds to `127.0.0.1` by default and makes no unauthenticated LAN/public claim | Real installed dashboard returns HTTP 200 on loopback, rejects non-GET with 405, and refuses non-loopback bind without the second acknowledgement | PASS on current host / frozen RC3 | Clean-machine and unfamiliar-reviewer reproduction remain R11/R12 |
| R9 Rollback | Failed install leaves no partial owned output; uninstall is idempotent; drift is preserved and reported | Main and detached RC3 worktrees both pass the seven-scenario real-process fault harness; runtime acceptance additionally proves exact task/pid ownership, stale-pid cleanup, idempotent stop, and zero-residue uninstall | PASS for frozen RC3 | Keep both R9 and portable-runtime harnesses in every later freeze; any installer/runtime-byte drift reopens R9 |
| R10 Privacy and credentials | Frozen RC has zero credentials/private keys and excludes local inboxes, chats, logs, cursors, wake runs, and unrelated reports | Expanded scanner covers the 68-file RC3 surface, including portable runtime and redacted receipts; main and frozen trees both report 0 findings, 0 missing, `PASS`, tree `9e6220fca2d05cfca7ee5cec2e99f1e4b7e48f2203c628045d82df9308dc05b8` | PASS for frozen RC3 | Any surface change requires a new hygiene freeze |
| R11 Human installation UX | One documented command, prerequisite list, operation card, troubleshooting, uninstall, and no source edits required | Candidate README, operation card, and troubleshooting guide now cover install/status/uninstall, exit codes, recovery, and ownership boundaries; cross-review corrections are incorporated | PARTIAL | Have an unfamiliar reviewer run the instructions on a real clean machine and record time and ambiguities |
| R12 Clean-machine time | Complete install → start → status → dashboard → stop → uninstall in ≤10 minutes on a genuinely clean Windows environment | `clean_home_rehearsal.py` passes 3 isolated-root tests and forces `clean_machine_acceptance=false` and `runtime_activation_performed=false` in its receipt | BOUNDARY | Run and time the full lifecycle on a genuinely clean Windows environment; the local rehearsal cannot satisfy this row |
| R13 License | Exact release contents have a clear, compatible license and notices | Root and payload `LICENSE` remain byte-identical at sha256 `0193cdbacc8174c2af478e8de69bd919a6b36edd7fbd039bd82d83e280aed4e1`; main and detached RC3 verification each passed 30+7 tests and 68-file hygiene | PASS (bound to freeze commit `d89340f36e2346284a1fbabefea91dd4c8833b86`) | Any payload byte drift or new notice obligation reopens R13 |
| R14 RC integrity | Every included file is allowlisted and hashed; tests and scans bind to the same immutable RC tree | RC3 commit `d89340f36e2346284a1fbabefea91dd4c8833b86` (Git tree `c6098a93565357d904fdcce69d23f4077f3ba911`) and a fresh detached checkout produced hygiene `PASS/68/0/0`, tree `9e6220fca2d05cfca7ee5cec2e99f1e4b7e48f2203c628045d82df9308dc05b8`, 73/73 signed paths at LF, 30 candidate + 7 R9 tests, and matching LICENSE hashes | PASS for frozen RC3 | Any change to the 68-file surface invalidates this receipt; independent final audit remains R15 |
| R15 Independent final audit | Reviewer checks exact artifact/commit hash, acceptance lines, test output, omissions, and sign-after-drift invalidation | Not yet performed | OPEN / DUAL-SIGN | Claude Opus final independent audit after all implementation gates close |
| R16 Publication | Push/tag/release uses the signed RC and publishes hashes/rollback receipt | Owner directed: all work completes before push | BLOCKED BY POLICY | Separate dual-sign publication proposal after R1–R15 close; no push in this episode |

## Current verdict

`NOT_RELEASE_READY`.

The principal method/runtime payload and isolated ownership mechanics are real
progress, not placeholders: R3/R4/R7/R8/R9 now have real current-host evidence,
and the frozen candidate clears its 68-file path/privacy scan. The candidate
payload fixes intentionally make the old live-tree inclusion receipt stale.
The parse-diagnostic v0.3 omission found during independent review is
mechanically repaired, locally verified, and closed by Claude's single-file
re-review of the exact merged `wake_brief.py` (2026-07-16); the old anchor
must not move to manufacture a pass. Portable scheduler/dashboard wiring is
closed on this host and frozen in RC3. A genuinely clean Windows ≤10-minute
run, unfamiliar-reviewer UX pass, and independent final audit remain open.
Publication remains policy-blocked; signatures do not survive candidate-byte
drift.

## Remaining work after RC3

1. Have an unfamiliar reviewer run the operation card (R11).
2. Run and time the complete lifecycle on a genuinely clean Windows machine;
   the current-host clean-HOME and real-runtime evidence cannot close R12.
3. Ask Claude for the independent exact-commit final audit (R15).
4. Keep publication blocked until a separate post-audit dual-sign explicitly
   authorizes push/tag/release (R16).

Stop and route through a new narrow dual-sign proposal before changing the
frozen scheduler/dashboard contract, selecting a different outward license,
changing project authorities, adopting a live Skill, or performing
push/tag/release.
