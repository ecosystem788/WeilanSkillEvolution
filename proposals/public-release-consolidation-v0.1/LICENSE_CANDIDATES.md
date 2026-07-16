# License and notices candidates for the Windows RC

Status: candidate analysis only. This file does not select, activate, or
publish a license. Any outward license decision remains a CHARTER dual-sign
action and must bind an exact frozen release-candidate tree.

## Verified release boundary

The current `install-manifest.json` has one payload mapping:

```text
skill/solve-with-weilan -> skills/solve-with-weilan
```

After applying the manifest's cache exclusions, that source tree contributes
47 payload files. Its `README.md` says that the Skill is MIT licensed and
points to the repository-root `LICENSE`. The root file (SHA-256
`870ca63340da46101bfb7bf356295b0ae589ffeead461ccddfcab3514fdcb087`)
contains the MIT text and the copyright line `Copyright (c) 2026 ecosystem788`.

No `LICENSE`, `NOTICE`, or `COPYING` file is present inside the 47-file Skill
payload. A standalone installed payload therefore cannot satisfy its README's
relative link to `../../LICENSE`. A source scan found no other SPDX,
copyright, or license declaration in the payload. This is a packaging fact,
not proof that every contribution's rights or provenance have been reviewed.

The exact RC is not frozen: `scripts/wake_brief.py` and
`scripts/test_conversation_evidence.py` currently differ from the previously
adopted live-tree anchor. License review must use the later immutable RC hash,
not the stale inclusion receipt.

## Candidate A — carry the repository MIT license with the Skill

At RC construction time, place a byte-for-byte copy of the approved root
`LICENSE` in the installed Skill payload and make the Skill README link to that
local copy. If attribution or bundled-content review finds additional notice
obligations, add a `NOTICE` file and include both files in the manifest and RC
hashes.

Why it is plausible: it matches the payload README and the repository's
current license text, while making the installed artifact self-describing.

Still required before selection:

- confirm that the root copyright line and license grant accurately cover the
  exact frozen payload and its contributors;
- inventory copied or derived third-party material and record any compatible
  notices or license texts;
- independently review the exact proposed `LICENSE`/`NOTICE` bytes and their
  target paths;
- rerun hygiene, tests, file accounting, and tree hashing after adding them.

## Candidate B — license only a containing source/archive distribution

Distribute the Skill only inside a repository or release archive whose root
license and notices are guaranteed to travel with it; do not claim that the
currently installed 47-file subtree is a complete standalone distribution.
The installer and documentation would need to preserve that containing
distribution boundary explicitly.

Why it is plausible: the current README already refers to a repository-root
license.

Why it is weaker for this RC: the stated product surface installs only the
Skill subtree, so this candidate either changes the packaging contract or
leaves the installed artifact without its referenced license text. Any such
contract change requires a narrow dual-sign proposal and new acceptance
evidence.

## Candidate C — keep publication blocked pending provenance review

Make no outward license representation and do not publish the RC until the
exact payload's authorship, copied-material provenance, attribution, and notice
requirements are reviewed.

Why it remains valid: absence of license markers is not evidence that no
third-party obligations exist. This candidate preserves the current
`NOT_RELEASE_READY` verdict if Candidate A or B cannot be supported.

## Decision packet required for dual-sign review

The later proposal that selects a license must include:

1. the immutable RC tree hash and complete file allowlist;
2. hashes and target paths for every `LICENSE` and `NOTICE` file;
3. the canonical source/provenance inventory
   (`SOURCE_PROVENANCE_INVENTORY.md`) for bundled or derived material, with
   `PROVENANCE_INVENTORY.md` retained as its independent peer-review replica;
4. the exact copyright and attribution text;
5. evidence that installed and archive forms both carry the promised texts;
6. rerun test, hygiene, and accounting receipts from the same immutable tree;
7. a rollback plan that removes an unpublished candidate or supersedes a
   published artifact without rewriting historical receipts.

Until that packet is independently reviewed and dual-signed, R13 remains
`OPEN / DUAL-SIGN` and the release remains `NOT_RELEASE_READY`.

This analysis file is review evidence, not a distributable RC file. It is not
present in `release_candidate_hygiene.py`'s `PROPOSAL_ALLOWLIST`; adding a
license or notice to the actual RC requires an explicit allowlist/manifest
change and a new hash receipt.

## Sources checked

- `proposals/public-release-consolidation-v0.1/install-manifest.json`
- `proposals/public-release-consolidation-v0.1/RELEASE_ACCEPTANCE_MATRIX.md`
- `skill/solve-with-weilan/README.md`
- `skill/solve-with-weilan/` (47-file inventory and license-marker scan)
- repository-root `LICENSE`
- `git status --short -- skill/solve-with-weilan`
