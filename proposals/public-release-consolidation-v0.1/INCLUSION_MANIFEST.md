# Inclusion gap manifest — 2026-07-14 (Claude wake)

Status: read-only finding, extends FINDING.md. Verification data for the
owner's 19:02 inclusion directive ("WeilanSkillEvolution fully contains the
installable Skill"). Authorizes nothing; migration steps remain dual-sign.

Method: `gh api` tree of public `solve-with-weilan@main` (84 blobs, pre-fix
HEAD 3ba51af) compared by git blob hash against (a) the live installed Skill
at `C:/Users/zy/.claude/skills/solve-with-weilan` (64 files) and (b) the
frozen baseline `packages/solve-with-weilan` (27 files). Raw hash lists were
in `tmp/` at run time; counts below are the durable result.

## 1. The public Skill repo is BEHIND the live installed Skill

- Missing from public repo entirely: `scripts/wake_brief.py` (deployed live
  2026-07-10, dual-signed) and `scripts/test_event_atomic_replace_retry.py`.
- Content drift (installed newer, 7 files): `scripts/prospective.py`,
  `runtime_core.py`, `weilan_trace.py`, `test_episode_memory.py`,
  `test_memory.py`, `test_prospective.py`, `test_semantic_memory.py`.
- Installed-only extras beyond those two are all `__pycache__`/`.pytest_cache`
  noise (15 files) — exclude from any payload.

Consequence: the migration payload's runtime source of truth is the **live
installed Skill** (minus cache noise), not the public repo. Copying the
public repo alone would ship stale runtime.

## 2. What the public repo has that the installed Skill does not (packaging layer)

- Root packaging: `README.md`, `LICENSE` (MIT), `.gitattributes`, `.gitignore`.
- `examples/bounded-autonomy-scaffold/` (25 files) — a snapshot of THIS
  repo's `proposals/bounded-scheduler-v0.1/impl`; under inclusion topology it
  should be regenerated from this repo, not treated as independent source.
- `theory/` (12 files).

## 3. theory/ is already almost fully in this repo

Hash-identical with this repo's root `theory/`: 10 of 12. Exceptions:
- `theory/无我.md` — formatting-only drift (public copy lacks `==` highlight
  markers present here; verified by full-text diff, no content difference).
- `theory/转向.md` — exists only in the public Skill repo; **missing from
  this repo**. Candidate single item to import during migration.

## 4. Baseline (packages/) confirmed as evidence-only

13/27 hash-identical with public repo, 14 drifted, 57 public-only — matches
FINDING.md. Keep frozen; do not use as payload source.

## Resulting migration payload recipe (for the future dual-sign proposal)

1. Runtime: live installed Skill tree minus `__pycache__`/`.pytest_cache`
   (49 real files) into a new distribution path in this repo.
2. Packaging: `LICENSE`, Skill `README.md`, dotfiles from public repo HEAD.
3. `theory/转向.md`: import into root `theory/`.
4. `examples/`: regenerate from this repo's impl, or drop with a pointer.
5. Content-equivalence check: every public-repo blob either present
   hash-identical in this repo, or accounted for as stale-superseded (list in
   §1) or regenerated (examples). Then and only then the standalone repo may
   go private (separate dual-sign, per control directive).

## Side discovery, already fixed this round

Public repo HEAD still carried the observer's surname (2 hits in the scaffold
example's pirate covenant snapshot), violating the 2026-07-14 08:59 owner
redaction directive. Fixed and pushed as `cc4ae8c` after scan-only gate v3
PASS (84 files / 3 patterns / 0 hits); remote HEAD re-verified 0 hits.
History blobs retain the old text, same accepted boundary as ef0b844.
