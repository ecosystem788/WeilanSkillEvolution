# R13 license decision packet — dual-sign proposal (Candidate A, bounded)

Date: 2026-07-17. Author: Claude. Status: **PROPOSAL — pending Codex
counter-signature and observer attestation.** This file does not itself select,
activate, or publish a license. It is not in the hygiene `PROPOSAL_ALLOWLIST`
and is not a distributable RC file.

## What is proposed

Select **Candidate A** from `LICENSE_CANDIDATES.md` — carry the repository MIT
license inside the Skill payload — with the mechanics below written to exact
objects, and with the outward legal representation gated on an explicit
observer attestation that only the rights holder can give.

## Bound objects (verified 2026-07-17 against the current candidate tree)

- Repository-root `LICENSE`: MIT text, copyright line
  `Copyright (c) 2026 ecosystem788`, SHA-256
  `870ca63340da46101bfb7bf356295b0ae589ffeead461ccddfcab3514fdcb087`.
- Candidate payload: working-tree `skill/solve-with-weilan`, 47 files, whose
  only difference from HEAD is `scripts/wake_brief.py`
  `b765d34abd282f6a0376c3c873ef0f6522e5566f7d958848484d2c1b2e491d36`
  (R2-closed). Last hygiene receipt: PASS, 61 files, 0 findings, tree
  `f33c94c5…` (full hash in the episode receipt, outside this file).
- `install-manifest.json` maps `skill/solve-with-weilan` →
  `skills/solve-with-weilan`; `release_candidate_hygiene.py` enumerates payload
  files dynamically from the manifest payload roots (verified: no hardcoded
  47/61 counts in any candidate `.py`), so the added file is picked up by both
  the installer and the scanner without code changes.

## Mechanical changes (dual-sign scope; executed only after【同意】)

1. Copy root `LICENSE` byte-for-byte to `skill/solve-with-weilan/LICENSE`.
   Acceptance: SHA-256 of the copy equals
   `870ca63340da46101bfb7bf356295b0ae589ffeead461ccddfcab3514fdcb087`.
2. Edit the License section of `skill/solve-with-weilan/README.md` (currently
   two links `../../LICENSE`, EN and ZH lines) to point to the payload-local
   `LICENSE`. Record the new README SHA-256 in the execution receipt.
3. Add **no** `NOTICE` file. Rationale: `SOURCE_PROVENANCE_INVENTORY.md` found
   no vendored or third-party source in the 47-file payload; `pytest` is a
   test-time dependency, not bundled material. If later review finds a notice
   obligation, that is a new dual-sign change, not a silent edit.
4. Rerun the 26-test candidate suite and `release_candidate_hygiene.py`
   (payload becomes 48 files, scan surface 62). Record pass/fail and the new
   final tree hash in the execution receipt and episode frame.
5. Update `RELEASE_ACCEPTANCE_MATRIX.md` R13 to
   `PASS for current candidate, conditional on observer attestation and
   freeze-time rebind`; note the surface change in R14's evidence text.

## External precondition — observer attestation (not satisfiable by dual-sign)

`SOURCE_PROVENANCE_INVENTORY.md` questions 1, 2, and 4 are the rights holder's
to answer, not ours. Before the license representation is treated as closed,
the observer must state (a reply in the tea room or owner channel suffices;
it will be captured as evidence):

1. `Copyright (c) 2026 ecosystem788` is the attribution ta intends for the
   frozen release tree, covering the model-generated contributions made under
   ta's direction; and
2. ta authorizes MIT for the exact frozen payload, including the prose derived
   from ta's own `theory/` texts (same rights holder, so no extra attribution
   notice is required unless ta wants one).

Without this attestation the mechanics may still land (they are reversible and
truthful — the file *is* the repository's license), but R13 stays annotated
`attestation pending` and R16 publication remains blocked.

## Agent attestation (evidence, not proof — question 3)

As the generating agents of this payload, Claude and Codex state for the
record: the implementation and prose were written in-session against the
repository's own theory texts and the Python standard library; neither recalls
copying or adapting external third-party source into the payload. The scan
evidence in `SOURCE_PROVENANCE_INVENTORY.md` corroborates (no SPDX/copyright
markers, no vendored tree). This is testimony plus scan, not a legal clearance.

## Sign-after-drift invalidation

The execution receipts bind to the exact tree they were produced on. Any later
payload byte change re-opens R13 verification (rerun steps 1–4 acceptance).
The packet completes — per `LICENSE_CANDIDATES.md` item 1 — only at RC freeze,
when the immutable tree hash and full allowlist are recorded; this proposal
authorizes the content of that packet, not a premature freeze.

## Rollback

Nothing is published (owner no-push directive stands). To roll back: delete
`skill/solve-with-weilan/LICENSE`, `git restore skill/solve-with-weilan/README.md`
(then re-apply the reviewed wake_brief candidate if the restore touches it —
it does not; README and wake_brief are distinct files), rerun hygiene, and
revert the R13 matrix row to `OPEN / DUAL-SIGN`. No historical receipt is
rewritten.

## Why Candidate A over B/C

B changes the packaging contract (the installed subtree would ship without its
referenced license text) and C blocks release indefinitely. A makes the
installed artifact self-describing at the cost of one byte-identical file and
a two-link README edit, and it degrades gracefully: if the observer declines
the attestation, C's protection (no outward representation, no publication) is
preserved by the R16 block.
