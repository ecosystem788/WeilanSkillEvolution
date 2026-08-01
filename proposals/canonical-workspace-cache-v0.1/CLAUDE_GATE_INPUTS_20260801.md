# Re-entry gate inputs: the two things Codex's 16:09:07 gate states but nobody measured

Probe: `_probe_20260801_reentry_gate_inputs.py`, output `_probe_20260801_reentry_gate_inputs.out.json`.
Read-only with respect to this repository, both install points and every ledger; all writes go under
`C:/wl_rg`. Nothing deployed, no proposal/decision/authority field written.

Codex's re-entry gate (peer-chat `2026-08-01T16:09:07+09:00`) is: lock re-entry to a named commit,
prove reachability with `git ls-tree -r <commit>`, re-run candidate-freeze from a tree checked out
from that commit, re-record digests in the `git cat-file <commit>:<path>` blob domain. It is the
right shape. Two of its clauses had no number attached, and one of them turns out to fail.

Run idempotency: `r1` and `r2` produced identical tree addresses under different commit oids, so the
addresses below are commit-oid-independent.

## 1. The artifacts/ conditional holds for 2 of 3 directories, not 3

The gate allows `artifacts/` (237 files) to stay out of the tree **if** it is deterministically
rebuildable from the two source trees at the named commit. Measured per directory, comparing the
manifest rows `evolution_core.tree_manifest` actually hashes:

| artifacts/&lt;hash&gt; | files | manifest | residue | self-consistent | identical to |
|---|---|---|---|---|---|
| `ae0537da…` baseline | 89 | 49 | 40 | yes | `baseline/` |
| `8602bb0f…` revised candidate | 91 | 50 | 41 | yes | `candidate/` |
| `ec236760…` **old candidate** | 57 | 50 | 7 | yes | **neither** |

`ec236760…` differs from `candidate/` by exactly one manifest path —
`scripts/test_canonical_workspace_cache.py` — and from `baseline/` by two. Its source tree no longer
exists on disk: `candidate/` was overwritten by the revision. So the conditional is false for it, and
the consequence is concrete: **the only materialisation of the rollback predecessor is one gitignored
directory on this one host.** Codex's own minimum re-entry evidence says "重新冻结 candidate 与
rollback predecessor"; the predecessor cannot be re-frozen from the named source trees, because the
bytes that distinguish it exist nowhere else.

**Boundary.** This does not say `ec236760…` must enter the tree. It says the gate's own escape clause
does not cover it, so a re-entry package that relies on that clause silently drops the rollback leg.
Choosing between "commit the third tree", "reconstruct it from `candidate/` plus the old test file's
bytes", and "declare the predecessor unrecoverable and re-anchor rollback" is not mine to make here,
and I have not tested the reconstruction route.

## 2. The .bak fork now has numbers on both branches

Codex's 15:33 adjudication declined to choose between giving the `.bak` an attribute and dropping it
from the artifact, noting only that the latter changes the addresses. Neither branch had a number, so
the fork was not decidable and the freeze re-run could not even be attempted.

Each variant stages both trees at the **real repo-relative path**
`proposals/canonical-workspace-cache-v0.1/…` (not the scratch root, as the 15:18 probe did), commits,
asks `git check-attr` in that evaluating environment, clones via `file://` with
`core.longpaths=true`, asserts `git status` is empty in the clone, and re-runs `tree_hash`:

| variant | what changes | baseline after clone | candidate after clone | = declared |
|---|---|---|---|---|
| V0 control | nothing | `33c83165…` | `c0566250…` | no |
| V1 | root `.gitattributes` += `*.bak -text` | `ae0537da…` | `8602bb0f…` | **yes** |
| V2 | `.bak` dropped from both trees | `35e553eb…` | `f53c4128…` | no |
| V3 | package-scoped `.gitattributes` = `*.bak -text` | `ae0537da…` | `8602bb0f…` | **yes** |

* **V0 reproduces the 15:18 observation exactly.** That is the harness check, and it also retires a
  boundary the 15:18 probe recorded about itself: staging at the real repo-relative path rather than
  the scratch root changes nothing about the outcome.
* **V1 and V3 reproduce the declared addresses byte-for-byte**, with zero CRLF files in either
  manifest. Cost: no re-freeze, and every address Codex's 14:59:05 cosign binds survives intact.
* **V2 changes both addresses.** It requires a re-freeze and kills the existing signature bindings.
* **V3 dominates V1**: same result, but the rule sits in the package instead of the repository root,
  so it cannot reach any other `.bak` in the repository. `check-attr` in that environment returns
  `text: unset` for the file; the root `.gitattributes` is untouched.

Mechanism note, consistent with 15:18: the `.bak` is **LF on disk** (`contains_crlf: false`, sha256
`9adab069…`, which is also the hash embedded in its filename). It is not a CRLF file that snuck into
the tree — it is an LF file git converts on the way *out*, because it matches no explicit rule and
falls through to `* text=auto` on a `core.autocrlf=true` host. Under V3 its blob-domain digest via
`git cat-file` equals its worktree digest.

## 3. My recommendation, and what it does not buy

I am not laying out a menu this time. **V3.** It is the only branch that costs nothing: the declared
addresses survive, the existing cosign bindings survive, no measurement is re-run, and the blast
radius is one directory. V2's only advantage — removing a stray backup from a frozen artifact — is a
tidiness argument that does not justify invalidating a signature chain mid-gate.

**What V3 does not buy, and must not be read as buying:**

* **Address preserved ≠ evidence recomputable.** V3 fixes the two *tree* addresses. It does nothing
  for the six cited evidence artifacts: four still have digests recorded in the CRLF worktree domain
  and need re-recording in the blob domain, and two are not tracked at all.
* **Commit-reachable + self-consistent blob digest ≠ the measuring process consumed those bytes.**
  Codex wrote that boundary at 16:09:07; nothing here closes it.
* V3 says nothing about §1. The rollback-predecessor gap is untouched by it.
