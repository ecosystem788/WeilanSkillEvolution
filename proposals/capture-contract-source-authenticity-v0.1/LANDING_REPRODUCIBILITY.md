# Capture-candidate landing reproducibility

Commit `f267f4a85d786f7cc83f3945c0b2ae549640894c` made the candidate at
`proposals/capture-contract-source-authenticity-v0.1/candidate/solve-with-weilan`
clone-stable. Its fixed parent is `cf6f4b3767b07fe004bbaac73c381f5ebac52dc7`.

The durable object-level invariants are:

- the commit has exactly 47 changed entries, all additions under the target;
- the target subtree is `c91ff506e3a0995205ba662750f1f5322a7602af`;
- the target contains 47 blobs and 903,000 raw bytes;
- 46 target entries were reachable from the fixed parent and one was not;
- the one formerly orphaned blob is
  `64bf3ab7eb719817c8b1895e40f164c782a32d07`;
- the manifest is
  `d5789a6e35348b51391ca9f8e72c308788b3a66858363d7014e00c12043e6286`.

The manifest is self-contained: sort entries by relative path, append
`relpath + NUL + sha256(raw blob bytes) + LF` for each entry, then take the
SHA-256 of the concatenation. It preserves the 47 path-to-blob relationships
without depending on a repository hashing implementation.

Run the verifier from the repository root:

```powershell
python proposals/capture-contract-source-authenticity-v0.1/verify_landing.py
```

`LANDING_DRIFT` means a fixed commit, parent, path, blob, subtree, or manifest
invariant changed or became unavailable. `HASHER_DRIFT` means those primary
invariants still hold but the secondary `tools.evolution_core.tree_hash`
bridge changed or could not run. The verifier prints the blob ID of the
`tools/evolution_core.py` bytes it actually invoked.

## Secondary `tree_hash` bridge

The expected bridge value is
`c393bc3916a9276f2dddfda6973790d3738acd0bd756ec8259f4d87463c60d6c`.
It was independently reproduced with both of these
`tools/evolution_core.py` variants:

- committed `HEAD` blob:
  `bd416521e8b6260c5e42680bd645cb20833d8b8b`;
- observed working-tree blob:
  `69b1cd4cd3890e9562a9428096091d23709d2a72`.

Both variants produced the same value because this candidate contains no path
excluded by either variant. The blob IDs identify the measuring rule; they are
not additional landing invariants.

## Byte-faithful extraction

Object storage is exact; a materialized working tree depends on checkout and
archive configuration.

For exact verification, prefer `git ls-tree` plus `git cat-file blob`, as
`verify_landing.py` does. A root-commit archive with the target pathspec also
retains the repository-root attributes:

```powershell
git archive f267f4a85d786f7cc83f3945c0b2ae549640894c proposals/capture-contract-source-authenticity-v0.1/candidate/solve-with-weilan
```

A bare subtree archive does not carry the root `.gitattributes`. On a machine
with `core.autocrlf=true`, it can materialize CRLF bytes and produce a different
`tree_hash`. Use an explicit byte-preserving policy if a subtree archive is
required:

```powershell
git -c core.autocrlf=false archive f267f4a85d786f7cc83f3945c0b2ae549640894c:proposals/capture-contract-source-authenticity-v0.1/candidate/solve-with-weilan
```

Therefore the bounded claim is: object-level bytes are exact; working-tree
bytes depend on the materialization configuration.
