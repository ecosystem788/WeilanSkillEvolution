# Public repository and release audit — 2026-07-14

Status: read-only finding. It does not authorize repository archival, history
rewrites, publication, deployment, or changes to the project authority files.

## Question

Verify whether `WeilanSkillEvolution`, `solve-with-weilan`, and
`weilan-memory` are redundant, and whether this workspace is currently usable
as a public distribution.

## Verified repository topology

The authenticated GitHub account currently owns five repositories: four public
repositories and one private repository (`agi`). The public surface is:

| Repository | Default branch | Public role seen in source | Release / license |
|---|---|---|---|
| `WeilanSkillEvolution` | `codex/se-0.4-0.7-program` | Evolution workshop: proposals, evaluations, deployments, charter and discussion evidence | no release; no detected license |
| `solve-with-weilan` | `main` | Installable Skill with `SKILL.md`, runtime scripts, README, examples and install instructions | no release; MIT |
| `weilan-memory` | `main` | Detached public snapshot of `method-state` | release `snapshot-2026-07-14`; no detected license |
| `WeiLan` | `master` | Earlier theory/model experiments | no release; no detected license |

Sources: GitHub repository/API state queried on 2026-07-14; repository roots;
`solve-with-weilan/README.md`; `weilan-memory/README.md` and
`EXPORT_POLICY.md`.

## They overlap, but they are not interchangeable

`WeilanSkillEvolution` and `solve-with-weilan` share Skill material, but the
copy in this workspace is explicitly a frozen evaluation baseline, not the
writable or deployed Skill. `AGENTS.md` says that
`packages/solve-with-weilan` is evidence and that the deployed Skill is outside
this project's write scope until adoption. That authority separation is also
reflected in `ARCHITECTURE.md` and `EVALUATION_POLICY.md`.

The remote tree comparison makes the distinction measurable:

- `WeilanSkillEvolution/packages/solve-with-weilan`: 27 blobs;
- public `solve-with-weilan`: 84 blobs;
- all 27 baseline paths also exist in the public Skill, but only 13 blob hashes
  are identical and 14 differ;
- the public Skill has 57 additional files, including its root README, MIT
  license, examples, and newer subsystem references.

Therefore deleting either repository as a name-level "duplicate" would erase a
real authority or distribution boundary. The public confusion is nevertheless
real because the workshop did not have a tracked root README on its published
default branch at the time of this audit.

`weilan-memory` is different again: 1,854 of its 1,856 blobs are under
`method-state/`. Its policy calls it a one-time, detached snapshot of the live
append-only ledger and requires a publication gate with reparse-point,
credential, image and per-file hash checks. It is audit data, not runtime code.
Merging that tree directly into the workshop would mix source authority with a
large, high-churn evidence snapshot and make the publication boundary harder to
see.

## Public deployment audit

The observer's deployment diagnosis is substantially confirmed:

- published `WeilanSkillEvolution` has 3,476 blobs (about 37.7 MB by GitHub tree
  sizes), no root README, no release, no detected license, and no root
  `setup.ps1`, dependency manifest, or package manifest;
- the default branch is a feature/program branch rather than `main`;
- live scheduler/dashboard code contains at least nine direct machine-path
  references to `D:\WeilanSkillEvolution` or a particular Claude/Codex Skill
  installation;
- the scheduler is built around PowerShell, VBS and Windows Task Scheduler;
  `launch_observe.py` explicitly rejects non-Windows systems;
- the dashboard intentionally defaults to `127.0.0.1`; changing that to public
  listening without authentication, TLS and a deployment boundary would be a
  security regression;
- a new installation must still supply Codex, Claude, Skill discovery and a
  local method-state location. A clone cannot and should not join the current
  community ledger automatically.

A root `README.md` exists in the local working tree at audit time but is
untracked and absent from the published tree. This finding does not modify or
claim ownership of that concurrent work.

## Observer direction after the first audit

At 2026-07-14 18:46–18:47, the observer clarified that the desired product
shape is not merely an umbrella page explaining several repositories. The
target is one active public repository, `WeilanSkillEvolution`, with convenient
deployment. This direction governs the recommendation below.

`weilan-memory` is **not a functional component**. It contains a detached
evidence snapshot. Its publication gate is useful and should survive, but its
1,854-file `method-state` tree should not become live application source.

## Revised recommendation: converge safely to one active public repository

1. Declare `WeilanSkillEvolution` the canonical public product and workshop.
   The root README should present the other repositories as migration/history
   sources, not as a permanent four-repository product constellation.
2. Do not equate the current 27-file frozen baseline with the public Skill's
   complete 84-file tree. Preserve the baseline as evaluation evidence. Build a
   generated, installable Skill payload from the currently adopted artifact in
   a new distribution path or release asset; changing the current package
   authority requires an explicit signed architecture change.
3. Add config/path discovery, dependency checks, `setup.ps1`, and deterministic
   install/start/stop/status/open-dashboard entry points. Publish and verify a
   tagged `WeilanSkillEvolution` release on a clean machine before retiring the
   standalone Skill repository.
4. After that release passes, replace `solve-with-weilan` with a short archival
   redirect to the exact monorepo release/install command. Preserve tags and
   history; do not delete first and attempt to reconstruct later.
5. Move the exported memory snapshot to a versioned
   `WeilanSkillEvolution` release asset (or an explicitly bounded evidence
   bundle), retaining its source/export manifests, publication receipt and
   hashes. Archive `weilan-memory` only after the migrated asset is independently
   downloadable and hash-equivalent. Future live ledger data remains local and
   passes the same export gate before publication.
6. Treat `WeiLan` as historical provenance. Archive it with a canonical link
   after the necessary theory/history sources are reachable from the main
   repository.
7. Keep the dashboard loopback-only in the first distribution. Mobile/LAN/public
   access is a separate authenticated deployment layer.

This converges toward one active public repository without collapsing distinct
authorities prematurely. README publication, authority-file changes, history
migration, repository archival, release publication and deployment are major
actions and require scoped dual-sign proposals with verification and rollback.

## Minimal acceptance boundary for a public runtime

- clean-machine install in at most ten minutes from one documented entry;
- no user-specific absolute paths in runtime configuration;
- explicit prerequisite failures for Python, Codex, Claude and Skill discovery;
- deterministic install / start / stop / status / open-dashboard commands;
- loopback bind by default and no implied access to the original community
  ledger;
- fresh local ledger bootstrap plus uninstall/rollback instructions;
- a tagged release with hashes, license decision and a clean-machine smoke-test
  receipt.
