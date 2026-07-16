# R2 independent candidate payload review — 2026-07-16 (Claude wake)

Status: read-only review evidence for gate R2 of `RELEASE_ACCEPTANCE_MATRIX.md`.
Authorizes nothing. The payload fix identified below and any matrix update go
through the normal fix + re-review loop.

Reviewer: Claude, independent of the payload author (Codex). Review target is
the exact current candidate: the `install-manifest.json` payload root
`skill/solve-with-weilan` (cache-excluded) plus the 14 allowlisted proposal
files, exactly as enumerated by `release_candidate_hygiene.py`.

## Method and reproduced evidence

1. **File-level accounting** against the adopted live Skill tree (the
   `WEILAN_LIVE_SKILL_PATHS` axis; see `FINDING.md` / `INCLUSION_MANIFEST.md`),
   per-file SHA-256 with manifest exclusions applied: candidate 47 files =
   live 46 files + `README.md` (packaging layer). Nothing missing from the
   candidate; nothing live-only. Content differs in exactly two files —
   matching the two-file delta declared in matrix row R2.
2. **Declared diff, `scripts/test_conversation_evidence.py`**: the negative
   credential fixture is now assembled at runtime by string concatenation, so
   the test source no longer carries token-shaped bytes while the test still
   requires capture rejection with `credential_like_material`. Semantics
   preserved; scanner rule `known_token_format` no longer matches source
   bytes. **Reviewed: PASS.**
3. **Declared diff, `scripts/wake_brief.py`**: the portable `_trace_script`
   default (sibling `weilan_trace.py`, `WEILAN_TRACE_SCRIPT` override
   retained) is correct for a fresh install. **Reviewed: PASS in isolation —
   but the file-level delta is larger than declared; see finding F1.**
4. **Test reproduction** (this review, 2026-07-16): `test_release_installer.py`
   + `test_release_candidate_hygiene.py` + `test_clean_home_rehearsal.py` →
   26 passed, 9 subtests passed, exit 0.
5. **Hygiene reproduction** (this review): `release_candidate_hygiene.py` →
   verdict `PASS`, 61 files, 0 findings, 0 missing, tree_sha256
   `b56794c40ea94aa49605e539d093d69a46e1f1b1a996d017ef229cfceaea6fd0`.
6. **Contract-test scope check**: `proposals/parse-diagnostic-contract-v0.1/
   test_parse_diagnostic_contract.py` passes (4 tests), but it imports
   `wake_brief` from `proposals/bounded-scheduler-v0.1/impl`, not from the
   candidate payload. Its pass is evidence about the impl copy only and says
   nothing about the candidate.

## Finding F1 — blocking for R2 closure

Candidate `skill/solve-with-weilan/scripts/wake_brief.py` (sha256
`17f9576fc0930138dc86171aea05cf8ed6fd68441964acc23147979fa22bdd7c`) omits the
dual-signed parse-diagnostic contract v0.3 implementation
(`proposals/parse-diagnostic-contract-v0.1/SPEC.md`, dual-signed 2026-07-15)
that is present and byte-identical in both the adopted live Skill tree and the
bounded-scheduler impl copy (both sha256
`958a6a02e4f0dd17d3097cad10d4088a758f78d9110af42a11f6914d1d3b065c`).

The candidate still carries exactly the pre-contract shapes the SPEC
deprecates: `{"parse_error", "source": "path:line", "raw"}` diagnostic rows,
`str.splitlines` record splitting in `_jsonl_from_bytes`, and
`_line_count = len(data.splitlines())` instead of the required
`data.count(b"\n")`.

Matrix row R2 declares the wake_brief delta as "portable default" only; the
actual live→candidate delta is 45 insertions / 121 deletions (the contract
machinery: `parse_diagnostic`, `_physical_records`, byte-offset threading,
`decode_failure` handling). The undeclared portion appears to be an omission
in sequencing — the candidate landed before the 2026-07-15 contract
deployment and only the portable-default fix was back-ported on 2026-07-16 —
not a reviewed decision.

Consequence: adopting the current candidate byte-for-byte would ship a runtime
that violates a contract this community already dual-signed and deployed.

## Required fix (mechanical, then single-file re-review)

Set candidate `wake_brief.py` := the contract implementation (sha256
`958a6a02…`) with the portable `_trace_script` default as the **only** delta;
rerun the candidate suite and hygiene scan; update matrix rows R2/R14
evidence; then re-review the single merged file and recompute inclusion
hashes at RC freeze.

## Verdict (initial review)

`R2 NOT CLOSEABLE` on the current candidate solely due to F1. All other
reviewed axes are consistent with their declared evidence, and both declared
payload fixes are individually sound.

## F1 re-review — 2026-07-16 (Claude wake, post-fix)

Target: the exact merged candidate `skill/solve-with-weilan/scripts/
wake_brief.py`, sha256
`b765d34abd282f6a0376c3c873ef0f6522e5566f7d958848484d2c1b2e491d36`, after
Codex's mechanical fix (codex-inbox-replies.jsonl reply_to `aa2d0e1d3a2f`,
2026-07-16 21:10:02).

1. **Hash verification**: candidate sha256 `b765d34a…d36`, impl copy sha256
   `958a6a02…65c` — both match the values Codex reported.
2. **Exact diff, impl → candidate**: a single hunk in `_trace_script` —
   hard-coded `D:\CodexData\…\weilan_trace.py` default replaced by
   `Path(__file__).with_name("weilan_trace.py")` with the
   `WEILAN_TRACE_SCRIPT` override retained. `from pathlib import Path` is
   already imported at line 16. No other byte differs; the F1 remediation
   spec ("contract implementation with the portable default as the only
   delta") is met exactly.
3. **Contract compliance, tested against the candidate itself** (closes the
   scope gap in method item 6 above): loading the candidate copy into
   `sys.modules` first and running `proposals/parse-diagnostic-contract-v0.1/
   test_parse_diagnostic_contract.py` → 4 passed, with
   `wake_brief.__file__` confirmed as the candidate path. The v0.3 machinery
   (`parse_diagnostic`, `_physical_records`, `data.count(b"\n")` line
   counting) is present and exercised in the candidate bytes.
4. **Candidate suite reproduction**: 26 passed, 9 subtests passed, exit 0.
5. **Hygiene reproduction**: verdict `PASS`, 61 files, 0 missing, 0
   findings, tree_sha256
   `f33c94c5432a8259cb9d9d3d5fb8dcde408e5d6f5d826ec9bd9457be26fca626`;
   per-file hash for the candidate `wake_brief.py` matches `b765d34a…d36`.

**Re-review verdict: F1 RESOLVED — R2 closeable for the current candidate.**
Inclusion hashes must still be recomputed at RC freeze; the old live-tree
anchor stays untouched. No push occurs in this episode (owner directive
2026-07-16 20:04:36).
