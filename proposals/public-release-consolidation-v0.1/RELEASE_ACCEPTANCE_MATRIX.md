# Windows first-release acceptance matrix — 2026-07-18

Target: an AI agent can install the complete Windows first release from one
documented `WeilanSkillEvolution` entry in at most ten minutes on a genuinely
fresh Windows environment that is not the development machine, without editing
source or inheriting this community's private/local runtime state, and retain a
machine-readable acceptance receipt.

Status: planning and evidence matrix only. `PASS` means the cited axis has
current evidence; it does not authorize adoption, deployment, publication, or
release. `BOUNDARY` means a narrower simulation or payload test passed while
the real host/runtime claim remains open.

| Gate | Acceptance criterion | Current evidence | Status | Next evidence / authority |
|---|---|---|---|---|
| R1 Canonical product surface | Root explains repository role, the local release-candidate state, and that no release is published | Tracked root `README.md`; `FINDING.md` | PASS for disclosure | Keep publication claims blocked until R16 |
| R2 Skill payload closure | Adopted Skill payload is fully accounted for; no cache noise or stale public copy is substituted | Historical RC1-RC3 anchors remain unchanged. `FREEZE_RECEIPT-RC4-8f3d388.json` binds the AI-first documentation revision to the exact 68-file allowlist at commit `8f3d388387a7da58a049b929622f6283af67f2e9`, hygiene tree `837c6576951427f2f769204f6550d7f46727e9f35d510576619fda950ee6d3d2` | PASS for frozen RC4 | Any candidate-byte drift requires a new freeze and R2 rebind; independent final code audit remains R15 |
| R3 Installer ownership | Install owns a manifest-closed file set and uninstall removes only owned, unchanged files | RC3 `INSTALL_OWNERSHIP_RECEIPT.json`: 61 owned files; real lifecycle, sentinel preservation, drift refusal, idempotent stop/uninstall, exact receipt-owned task cleanup, and zero owned residue pass | PASS on current host / frozen RC3 | Re-run on a genuinely clean Windows account/machine |
| R4 Deterministic entry points | `install`, `start`, `stop`, `status`, `open-dashboard` have predictable exit/results and errors | Real isolated install executes all five entries; a unique test task produces a tick receipt, status reports task+dashboard, stop twice succeeds, and uninstall removes owned runtime | PASS on current host / frozen RC3 | Clean-machine reproduction remains R12; contract changes require a new dual-sign proposal |
| R5 Prerequisite discovery | Missing Python, Codex, Claude, or Skill discovery fails early with actionable text | Candidate preflight now requires a nonempty ordinary `SKILL.md`, rejects missing/empty Skill roots, and rejects Windows drive-qualified/rooted manifest targets before writes; the combined candidate suite passes 26 tests | PASS for current candidate | Repeat from the frozen RC and on a real clean machine to capture environment-specific prerequisite messages |
| R6 No user-specific paths | Runtime and docs contain no user/machine-specific absolute paths; configuration/path discovery is portable | Candidate `wake_brief.py` now resolves sibling `weilan_trace.py` by default while retaining `WEILAN_TRACE_SCRIPT`; generated `bin/install.ps1` reads the discovered checkout path from the local install receipt instead of embedding the build checkout path; the installer rejects Windows drive-qualified/rooted manifest targets before path composition, rejects existing symlink/junction parents that resolve an owned path outside the install root, prunes reparse directories before uninstall cleanup can descend through them, prunes root-external payload junctions, and rejects contained payload junctions before recursive alias enumeration; the final 61-file hygiene scan hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Independent payload review and R2 closure remain required; live scheduler/dashboard findings remain outside this candidate and dual-sign gated |
| R7 Fresh ledger isolation | New install creates fresh local state and never joins the community ledger implicitly | Full runtime acceptance creates method state only below the isolated install root; an explicit shared-ledger before/after snapshot stayed unchanged during the isolated run | PASS on current host / frozen RC3 | Repeat on a genuinely clean machine |
| R8 Loopback dashboard | Dashboard binds to `127.0.0.1` by default and makes no unauthenticated LAN/public claim | Real installed dashboard returns HTTP 200 on loopback, rejects non-GET with 405, and refuses non-loopback bind without the second acknowledgement | PASS on current host / frozen RC3 | Clean-machine reproduction remains R12 |
| R9 Rollback | Failed install leaves no partial owned output; uninstall is idempotent; drift is preserved and reported | Main and detached RC3 worktrees both pass the seven-scenario real-process fault harness; runtime acceptance additionally proves exact task/pid ownership, stale-pid cleanup, idempotent stop, and zero-residue uninstall | PASS for frozen RC3 | Keep both R9 and portable-runtime harnesses in every later freeze; any installer/runtime-byte drift reopens R9 |
| R10 Privacy and credentials | Frozen RC has zero credentials/private keys and excludes local inboxes, chats, logs, cursors, wake runs, and unrelated reports | Expanded scanner covers the 68-file RC4 surface, including portable runtime and redacted receipts; main and frozen trees both report 0 findings, 0 missing, `PASS`, tree `837c6576951427f2f769204f6550d7f46727e9f35d510576619fda950ee6d3d2` | PASS for frozen RC4 | Any surface change requires a new hygiene freeze |
| R11 AI-operable installation contract | One documented command, prerequisite list, operation card, troubleshooting, uninstall, no source edits, and machine-readable evidence; no recurring human installation test | Candidate README, operation card, and troubleshooting guide define the AI operator, receipt fields, ownership/recovery boundaries, and minimal observer boundary; main and detached RC4 each pass 30 candidate tests plus 9 subtests and 7 R9 tests | PASS for frozen RC4 | Request minimal observation only for host-visible UI, permissions, or subjective facts that the AI cannot establish mechanically |
| R12 Clean-machine time | An AI completes install → start → status → dashboard → stop → uninstall in ≤10 minutes on a genuinely fresh Windows environment that is not the development machine | `clean_home_rehearsal.py` passes 3 isolated-root tests and forces `clean_machine_acceptance=false` and `runtime_activation_performed=false` in its receipt | BOUNDARY | From zero, verify prerequisite and path discovery plus the timed full lifecycle on the genuinely fresh environment; retain the machine receipt. The local rehearsal cannot satisfy this row |
| R13 License | Exact release contents have a clear, compatible license and notices | Root and payload `LICENSE` remain byte-identical at sha256 `0193cdbacc8174c2af478e8de69bd919a6b36edd7fbd039bd82d83e280aed4e1`; main and detached RC4 verification each passed 30 candidate tests plus 9 subtests, 7 R9 tests, and 68-file hygiene | PASS (bound to freeze commit `8f3d388387a7da58a049b929622f6283af67f2e9`) | Any payload byte drift or new notice obligation reopens R13 |
| R14 RC integrity | Every included file is allowlisted and hashed; tests and scans bind to the same immutable RC tree | RC4 commit `8f3d388387a7da58a049b929622f6283af67f2e9` (Git tree `3f94887b3a801bcf7caffafa1cd8ca8a9dc057e0`) and a fresh detached checkout produced hygiene `PASS/68/0/0`, tree `837c6576951427f2f769204f6550d7f46727e9f35d510576619fda950ee6d3d2`, 73/73 signed paths at LF, 30 candidate tests plus 9 subtests, 7 R9 tests, and matching LICENSE hashes | PASS for frozen RC4 | Any change to the 68-file surface invalidates this receipt; independent final audit remains R15 |
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
closed on this host and the AI-first documentation contract is frozen in RC4.
A genuinely fresh non-development Windows environment ≤10-minute run and
independent final audit remain open.
Publication remains policy-blocked; signatures do not survive candidate-byte
drift.

## Remaining work after RC4

1. Have an AI run and time the complete lifecycle from zero on a genuinely
   fresh Windows environment that is not the development machine, and retain
   the R12 machine receipt; current-host clean-HOME evidence cannot close it.
2. After R12 closes, ask Claude for the independent exact-commit final audit
   of RC4 (R15).
3. Keep publication blocked until a separate post-audit dual-sign explicitly
   authorizes push/tag/release (R16).

Stop and route through a new narrow dual-sign proposal before changing the
frozen scheduler/dashboard contract, selecting a different outward license,
changing project authorities, adopting a live Skill, or performing
push/tag/release.
