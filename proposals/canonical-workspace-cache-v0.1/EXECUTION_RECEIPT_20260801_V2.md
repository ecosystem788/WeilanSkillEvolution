# canonical-workspace-cache-v0.1 single-target deployment receipt

## Outcome

`canonical-workspace-cache-v0.1` was deployed exactly once to the single physical target
`D:\CodexData\skills\solve-with-weilan`. The C: spelling remains a Junction alias of the
same physical tree. No rollback trigger fired, so no rollback or redeploy was performed.

- deployment id: `43a91cbb4e2f0efa9d36a8a9`
- decision hash: `e98e1a5269b05f9b49b5ae9dc14ab08fb6322da5de37e00c2e23ab4353daf19f`
- before / rollback artifact: `ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad`
- deployed candidate: `8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a`
- deployment receipt: `proposals/canonical-workspace-cache-v0.1/deployments/43a91cbb4e2f0efa9d36a8a9/DEPLOYMENT_RECEIPT.json`
- rollback snapshot: `proposals/canonical-workspace-cache-v0.1/deployments/43a91cbb4e2f0efa9d36a8a9/rollback/solve-with-weilan`

## Dual-sign and authorization visibility

Dual-sign: proposal `2026-08-01T21:59:05+09:00` + independent consent
`2026-08-01T22:11:09+09:00`. The target-specific v2 decision was validated before deploy.

Authorization landing commit: `d258a0efbce7455f2c18403bb90f8b32954acfa9`.

- chat blob oid: `22c646223f88b7ff8613a360b85fd5d340dd5230`
- decision blob oid: `bbf40d757052fd673ba3985063c7cb82d259d825`
- proposal record, line 3291, `current-record-minus-LF-v1` SHA-256:
  `dd1b12b5a2f13652519936efb7f9041a49542eeb36cab17b75873210b2fddcf1`
- consent record, line 3292, `current-record-minus-LF-v1` SHA-256:
  `8708deb9bfd92a30639f03081bb7197adf16736951969f696ad3190522fc97a7`

Both physical records were read from the named commit's Git blob, split on `0x0A`, and had
no stored trailing `0x0D` before hashing.

## Preflight and deployment gates

- Scoped `memory-recall --scope skill-evolution`: `ACTIVE`, continuation allowed, fresh.
- Before deploy, D:, C:, package baseline, and the old rollback snapshot all hashed to
  `ae0537da...`; package candidate hashed to `8602bb0f...`.
- `C:\Users\zy\.claude\skills` remained a Junction to `D:\CodexData\skills`.
- The two named `SKILL.md` spellings had identical pre-deploy file ID
  `0x0000000000000000000500000002a443`.
- Prior rollback receipt `a59bd56fb0043866eded33a5` recorded restored artifact
  `ae0537da...`.
- `decision-validate`: `valid: true`, `issues: []`.
- Deploy was called once. Its receipt bound `before=ae0537da...` and `after=8602bb0f...`.

## Post-deploy verification

- D: and C: both hash to `8602bb0f...`.
- Both aliases still have one file identity; the post-replacement `SKILL.md` file ID is
  `0x0000000000000000000500000002a55e` from both spellings.
- The new rollback snapshot hashes to baseline `ae0537da...`.
- Focused test from D:: `rc=0`, `2 passed in 0.28s`.
- Focused test from C:: `rc=0`, `2 passed in 0.39s`.
- The cosigner's staleness-window probe was imported unchanged, with only its
  `CANDIDATE_RC` input rebound at runtime to the deployed `runtime_core.py`. It reproduced
  both disclosed topology-change divergences and reported
  `window_1_after_documented_clear.recovers=true`. This verifies the disclosed boundary;
  it does not claim baseline/candidate equivalence under in-process topology mutation.

Read-only command stdout was byte-identical across the version switch:

| Command | Before seconds | After seconds | Bytes | SHA-256 |
|---|---:|---:|---:|---|
| scoped `memory-recall` | 1.981 | 0.380 | 40,893 | `bdc303d31c305bab03c3e42d40448c553e235294d3c66a5de61978b2da05d2f2` |
| scoped `prospective-show` | 0.813 | 0.294 | 209,079 | `880f950a604c77978a37be1312e57dd379ebb008d15ec4f3007e4c67a0bb08e6` |
| scoped `lineage-show` | 34.209 | 30.128 | 1,421,820 | `f08446e95a2816b5a5d53bab696aa8c3e7e6426a2187e2f76efa994a4554da4e` |

The real read commands show a modest visible improvement, strongest on recall and
prospective-show and only about 1.14x on lineage-show. This is not evidence that every
episode is faster. The current real L2 receipt chain is hybrid: its open+holder wrapper ran
on baseline (`54.2s`), while version-switch audit (`0.408s`), round-end audit (`0.393s`),
and close (`0.423s`) ran on candidate. Their command-runtime sum (`55.424s`) is reported for
transparency but is not a clean before/after benchmark and does not authorize a per-turn
speedup claim. The earlier copied-ledger `2.066x` remains separate shadow evidence.

## Frame receipt

- frame: `wf-20260801-132040-42f8d7`
- relation: `continue`
- parent: `wf-20260801-131346-129402`
- persistence audits: `version_switch=NOT_PERSISTED`, `round_end=NOT_PERSISTED`
- close: `success`; validation `valid=true`, `event_count=4`
- `find-frame-index-v0.1` remained rejected and was not revived.

## File-reference visibility at authorization commit

| Original reference | Resolution at `d258a0e...` |
|---|---|
| `proposals/canonical-workspace-cache-v0.1/proposal.json` | blob `f397b73df9e138249701529db77700c14d02a053` |
| `proposals/canonical-workspace-cache-v0.1/SHADOW_RESULT.json` | blob `8be7b522476a4e01262a20c6b43ba28c4041917a` |
| `proposals/canonical-workspace-cache-v0.1/adoption/ADOPTION_DECISION_CODEXDATA_V2.json` | blob `bbf40d757052fd673ba3985063c7cb82d259d825` |
| `_review_20260801_claude_alias_target_and_rollback_state.py` | `proposals/canonical-workspace-cache-v0.1/_review_20260801_claude_alias_target_and_rollback_state.py`, blob `61215333808745ede771c547322a915b0c5d150e` |
| `_review_20260801_claude_alias_target_and_rollback_state.out.json` | `proposals/canonical-workspace-cache-v0.1/_review_20260801_claude_alias_target_and_rollback_state.out.json`, blob `cbd7cdaf52f55bdeeb18b737c3be08abf03aafd6` |
| `_review_20260801_claude_cache_staleness_window.py` | `proposals/canonical-workspace-cache-v0.1/_review_20260801_claude_cache_staleness_window.py`, blob `7556c74d80f9baceaeb0df610446792203ea85fe` |
| `_review_20260801_claude_cache_staleness_window.out.json` | `proposals/canonical-workspace-cache-v0.1/_review_20260801_claude_cache_staleness_window.out.json`, blob `d2d8963c7e0303ee4bd379a6df3adb90c50721b2` |
| `tools/evolution_core.py:60` | `tools/evolution_core.py`, blob `69b1cd4cd3890e9562a9428096091d23709d2a72` |

本表不穷尽全部证据来源；现场命令、运行时观察、对话判断等非文件型证据不在本表内。
路径与 blob oid 只证明该字节可从具名树取得，不证明它是签名者当时读取的字节，也不证明判断为真。
