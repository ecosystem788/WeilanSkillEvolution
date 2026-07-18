# Windows first-release acceptance matrix — 2026-07-18

Target: an AI agent can install the complete Windows first release from one
documented `WeilanSkillEvolution` entry in at most ten minutes on a genuinely
fresh Windows environment that is not the development machine, without editing
source or inheriting this community's private/local runtime state, and retain a
machine-readable acceptance receipt.

Status: planning and evidence matrix only. `PASS` means the cited axis has
current evidence; it does not authorize adoption, deployment, publication, or
release. `BOUNDARY` means a narrower simulation or payload test passed while
the real host/runtime claim remains open. The runtime lifecycle claim is split
into **T1** — the full lifecycle runs error-free on the development machine
under an isolated install root — and **T2** — the same lifecycle on a genuinely
fresh Windows environment that is not the development machine. T1 evidence
proves the six-step mechanics on this host only and never satisfies T2. By the
owner's 2026-07-18 18:16:04 authorization, T2 remains an explicit unverified
boundary delegated to the user-side AI; it is no longer a prerequisite for R15
or publication.

| Gate | Acceptance criterion | Current evidence | Status | Next evidence / authority |
|---|---|---|---|---|
| R1 Canonical product surface | Root explains repository role, the local release-candidate state, and that no release is published | Tracked root `README.md`; `FINDING.md` | PASS for disclosure | Keep publication claims blocked until R16 |
| R2 Skill payload closure | Adopted Skill payload is fully accounted for; no cache noise or stale public copy is substituted | Historical RC1-RC4 anchors remain unchanged. `FREEZE_RECEIPT-RC5-049d6c7.json` binds the battery-safe scheduler revision and carried-forward AI-first contract to the exact 68-file allowlist at commit `049d6c79e683b829bd8fa0b9a5491f5a3796a0bb`, hygiene tree `fa917918d3598a1063f851322e4a6bc22fe32f41a2966fa2dd608766cbe56013` | PASS for frozen RC5 | Any candidate-byte drift requires a new freeze and R2 rebind; independent final code audit remains R15 |
| R3 Installer ownership | Install owns a manifest-closed file set and uninstall removes only owned, unchanged files | RC3 `INSTALL_OWNERSHIP_RECEIPT.json`: 61 owned files; real lifecycle, sentinel preservation, drift refusal, idempotent stop/uninstall, exact receipt-owned task cleanup, and zero owned residue pass. RC4 `8f3d388` T1 local smoke (2026-07-18) re-exercised 61-owned-file ownership, idempotent uninstall, and zero owned residue live on the development machine (see R12) | PASS on current host / frozen RC3 | Re-run on a genuinely clean Windows account/machine (T2) |
| R4 Deterministic entry points | `install`, `start`, `stop`, `status`, `open-dashboard` have predictable exit/results and errors | Real isolated install executes all five entries; a unique test task produces a tick receipt, status reports task+dashboard, stop twice succeeds, and uninstall removes owned runtime. RC4 `8f3d388` T1 local smoke (2026-07-18) re-ran all five entries live on the development machine with predictable exits (see R12) | PASS on current host / frozen RC3 | Clean-machine (T2) reproduction remains R12; contract changes require a new dual-sign proposal |
| R5 Prerequisite discovery | Missing Python, Codex, Claude, or Skill discovery fails early with actionable text | Candidate preflight now requires a nonempty ordinary `SKILL.md`, rejects missing/empty Skill roots, and rejects Windows drive-qualified/rooted manifest targets before writes; the combined candidate suite passes 26 tests | PASS for current candidate | Repeat from the frozen RC and on a real clean machine to capture environment-specific prerequisite messages |
| R6 No user-specific paths | Runtime and docs contain no user/machine-specific absolute paths; configuration/path discovery is portable | Candidate `wake_brief.py` now resolves sibling `weilan_trace.py` by default while retaining `WEILAN_TRACE_SCRIPT`; generated `bin/install.ps1` reads the discovered checkout path from the local install receipt instead of embedding the build checkout path; the installer rejects Windows drive-qualified/rooted manifest targets before path composition, rejects existing symlink/junction parents that resolve an owned path outside the install root, prunes reparse directories before uninstall cleanup can descend through them, prunes root-external payload junctions, and rejects contained payload junctions before recursive alias enumeration; the final 61-file hygiene scan hash is recorded outside this self-hashed matrix in the episode receipt | PASS FOR CURRENT CANDIDATE | Independent payload review and R2 closure remain required; live scheduler/dashboard findings remain outside this candidate and dual-sign gated |
| R7 Fresh ledger isolation | New install creates fresh local state and never joins the community ledger implicitly | Full runtime acceptance creates method state only below the isolated install root; an explicit shared-ledger before/after snapshot stayed unchanged during the isolated run. RC4 `8f3d388` T1 local smoke (2026-07-18) again left the shared method-state before=after (3286 files, sha256 unchanged) while creating fresh state only below the install root (see R12) | PASS on current host / frozen RC3 | Repeat on a genuinely clean machine (T2) |
| R8 Loopback dashboard | Dashboard binds to `127.0.0.1` by default and makes no unauthenticated LAN/public claim | Real installed dashboard returns HTTP 200 on loopback, rejects non-GET with 405, and refuses non-loopback bind without the second acknowledgement. RC4 `8f3d388` T1 local smoke (2026-07-18) reconfirmed loopback GET 200, non-GET 405, and non-loopback-without-ack refusal live on the development machine (see R12) | PASS on current host / frozen RC3 | Clean-machine (T2) reproduction remains R12 |
| R9 Rollback | Failed install leaves no partial owned output; uninstall is idempotent; drift is preserved and reported | Main and detached RC3 worktrees both pass the seven-scenario real-process fault harness; runtime acceptance additionally proves exact task/pid ownership, stale-pid cleanup, idempotent stop, and zero-residue uninstall | PASS for frozen RC3 | Keep both R9 and portable-runtime harnesses in every later freeze; any installer/runtime-byte drift reopens R9 |
| R10 Privacy and credentials | Frozen RC has zero credentials/private keys and excludes local inboxes, chats, logs, cursors, wake runs, and unrelated reports | Expanded scanner covers the 68-file RC5 surface, including portable runtime and redacted receipts; main and frozen trees both report 0 findings, 0 missing, `PASS`, tree `fa917918d3598a1063f851322e4a6bc22fe32f41a2966fa2dd608766cbe56013` | PASS for frozen RC5 | Any surface change requires a new hygiene freeze |
| R11 AI-operable installation contract | One documented command, prerequisite list, operation card, troubleshooting, uninstall, no source edits, and machine-readable evidence; no recurring human installation test | Candidate README, operation card, and troubleshooting guide define the AI operator, receipt fields, ownership/recovery boundaries, and minimal observer boundary; main and detached RC5 each pass 30 candidate tests plus 9 subtests and 7 R9 tests | PASS for frozen RC5 | Request minimal observation only for host-visible UI, permissions, or subjective facts that the AI cannot establish mechanically |
| R12 Clean-machine time | **T1 (local, done):** the isolated-root full lifecycle runs error-free on the development machine. **T2 (open/delegated):** an AI completes install → start → status → dashboard → stop → uninstall in ≤10 minutes on a genuinely fresh Windows environment that is not the development machine | `clean_home_rehearsal.py` passes 3 isolated-root tests and forces `clean_machine_acceptance=false` and `runtime_activation_performed=false` in its receipt. In-host nested-VM proxy (Weilan-R12-RC4) retired 2026-07-18: host Hyper-V/VBS holds VT-x, forcing VirtualBox onto NEM where Windows `specialize` deadlocked twice — structurally unclosable on this machine, and a test-prop limitation, not a repo/installer/RC defect; VM/VDI/ISO deregistered and deleted (registered VMs=0, running=0), with autounattend observations retained in peer-chat evidence while the source recipe was deleted with the VM. **T1 local lifecycle smoke (2026-07-18, RC4 `8f3d388`, development machine, isolated install root):** 10 ordered steps all as expected in 32.105 s — install / start / status healthy (task+dashboard) / dashboard loopback GET 200, non-GET 405, non-loopback-without-ack refused / stop twice idempotent / uninstall twice idempotent; shared method-state before=after (3286 files, sha256 `0a89f5ba…706ca`, unchanged), 61 owned files, zero residue. Receipt `weilan_local_lifecycle_smoke_receipt_v0.1` in `concurrent-receipts.jsonl`, `clean_machine_acceptance=false`, `runtime_activation_performed=true`, `site=development_machine`; proves the six-step mechanics on this host only and does NOT verify clean-machine (T2) compatibility | BOUNDARY (T1 PASS, T2 OPEN/DELEGATED) | T1 closed on the development machine (mechanics only). T2 remains delegated to the AI operator at a genuine non-development install site; no in-host VM rehearsal can satisfy it. From zero, that operator should verify prerequisite and path discovery plus the timed full lifecycle and retain the machine receipt. The missing T2 receipt is an accepted release boundary, not an R15 prerequisite and not evidence of compatibility. Verdict stays `NOT_RELEASE_READY` until R15 and R16 close. VM-retirement double-sign: proposal 2026-07-18 15:31:10 + agreement 15:39:11; owner authorization 15:22/15:25. T1 double-sign: proposal 2026-07-18 16:28:08 + agreement 16:40:02 (peer-chat). Release-boundary authorization: owner 2026-07-18 18:16:04; double-sign proposal 18:18:36 + agreement 18:33:10 |
| R13 License | Exact release contents have a clear, compatible license and notices | Root and payload `LICENSE` remain byte-identical at sha256 `0193cdbacc8174c2af478e8de69bd919a6b36edd7fbd039bd82d83e280aed4e1`; main and detached RC5 verification each passed 30 candidate tests plus 9 subtests, 7 R9 tests, and 68-file hygiene | PASS (bound to freeze commit `049d6c79e683b829bd8fa0b9a5491f5a3796a0bb`) | Any payload byte drift or new notice obligation reopens R13 |
| R14 RC integrity | Every included file is allowlisted and hashed; tests and scans bind to the same immutable RC tree | RC5 commit `049d6c79e683b829bd8fa0b9a5491f5a3796a0bb` (Git tree `b159368309de399587f5d768d6680674ee54277b`) and a fresh detached checkout produced hygiene `PASS/68/0/0`, tree `fa917918d3598a1063f851322e4a6bc22fe32f41a2966fa2dd608766cbe56013`, 73/73 signed paths at LF, 30 candidate tests plus 9 subtests, 7 R9 tests, and matching LICENSE hashes | PASS for frozen RC5 | Any change to the 68-file surface invalidates this receipt; independent final audit remains R15 |
| R15 Independent final audit | Reviewer checks exact artifact/commit hash, acceptance lines, test output, omissions, and sign-after-drift invalidation | Not yet performed | OPEN / DUAL-SIGN | Claude Opus may now perform the independent final audit of exact RC5 `049d6c7`; delegated T2 does not gate this audit |
| R16 Publication | Push/tag/release uses the signed RC and publishes hashes/rollback receipt | Owner directed: all work completes before push | BLOCKED BY POLICY | Separate dual-sign publication proposal after R1–R15 close; no push in this episode |

## RC3 → RC4 carry-forward (R3/R4/R7/R8/R9)

The R3/R4/R7/R8/R9 rows keep their `PASS on ... frozen RC3` wording as the
historical evidence anchor. This section adds only the derived applicability
conclusion for the RC4 freeze; it flips no gate and re-runs nothing.

Every byte these five gates bind is one and the same Git object at RC3
(`dbcd84d`, `release: bind RC3 portable runtime freeze`) and RC4 (`8f3d388`,
`release: pin RC4 AI-first installation contract`). Independently recomputed
object identities (RC3 side = RC4 side, byte-identical):

- Skill payload subtree `skill/solve-with-weilan`: `06fb2a58…74be`
- `proposals/public-release-consolidation-v0.1/release_installer.py`: `54bed92a`
- `proposals/public-release-consolidation-v0.1/release_candidate_hygiene.py`: `3ea53cf5`
- `proposals/public-release-consolidation-v0.1/test_portable_runtime.py`: `9e86f3d9`
- `proposals/public-release-consolidation-v0.1/test_release_installer.py`: `bef3a80b`
- `proposals/public-release-consolidation-v0.1/test_release_candidate_hygiene.py`: `86887bbb`
- `proposals/public-release-r9-fault-injection-v0.1/test_release_installer_r9_faults.py`: `0eeecc46`

The single documented install payload source is `skill/solve-with-weilan`
(`install-manifest.json`); the RC3→RC4 delta is documentation-only and touches
none of these objects. Therefore the RC3 evidence for R3/R4/R7/R8/R9 carries
forward to the RC4 freeze by object identity, not by re-run. The only dimension
still open for these five gates on RC4 is genuine clean-machine reproduction,
which continues to be tracked by R12; it is not reopened by the doc-only RC4
revision.

Supplementing that object-identity argument, the 2026-07-18 T1 local lifecycle
smoke (RC4 `8f3d388`, development machine, isolated install root; see R12) also
re-exercised R3 (61-owned-file ownership, idempotent uninstall, zero residue),
R4 (all five entries, predictable exits), R7 (shared method-state before=after),
R8 (dashboard 200 / 405 / non-loopback-without-ack refused), and R9 (idempotent
stop/uninstall, zero owned residue) as a live run rather than by identity alone.
This adds current-host RC4 evidence for the mechanics; it is a T1 result and
does not close T2 clean-machine reproduction, which stays open under R12.

Boundaries preserved: verdict remains `NOT_RELEASE_READY`; no gate is flipped;
R12 still records T2 as open/delegated, while R15, R16, and the no-push policy
remain open; the RC4 freeze contract is untouched. Double-sign: proposal
2026-07-18 04:46:20 + agreement 2026-07-18
04:53:08 (peer-chat). T1 local-smoke double-sign: proposal 2026-07-18 16:28:08 +
agreement 16:40:02 (peer-chat).

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
closed on this host; the AI-first documentation contract carries forward into
RC5, whose current anchor adds the battery-safe scheduler settings.
The RC4 `8f3d388` T1 local lifecycle smoke passed on the development machine
(2026-07-18, 32.105 s, isolated install root, zero residue, shared ledger
unchanged) — evidence for the six-step mechanics only. A genuinely fresh
non-development Windows environment ≤10-minute run (T2) remains unverified and
is explicitly delegated to the user-side AI; this accepted boundary no longer
blocks R15. Independent R15 final audit and R16 dual-sign publication remain
open, so the verdict is still `NOT_RELEASE_READY`.
Publication remains policy-blocked; signatures do not survive candidate-byte
drift.

## Remaining work after RC5

1. Keep T2 visibly open/delegated in release materials. When a user-side AI
   reaches a genuinely fresh non-development Windows environment, it should
   run and time the lifecycle from zero and retain the R12 machine receipt;
   neither current-host clean-HOME evidence nor the 2026-07-18 T1 smoke closes
   T2, but its absence is no longer a release prerequisite.
2. T2 is accepted as a delegated boundary; ask Claude now for the independent
   exact-commit final audit of RC5 `049d6c7` (R15).
3. Keep publication blocked until a separate post-audit dual-sign explicitly
   authorizes push/tag/release (R16).

Stop and route through a new narrow dual-sign proposal before changing the
frozen scheduler/dashboard contract, selecting a different outward license,
changing project authorities, adopting a live Skill, or performing
push/tag/release.
