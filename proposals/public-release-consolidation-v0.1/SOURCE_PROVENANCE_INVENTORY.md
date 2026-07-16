# Source and provenance inventory for the Windows RC payload

Status: review evidence only. This file does not select or activate a license,
does not establish legal authorship, and is not part of the release-candidate
manifest or hygiene allowlist.

Evidence organization: this is the canonical source/provenance inventory for
the later license decision packet. `PROVENANCE_INVENTORY.md` is retained as an
independent peer-review replica: it corroborates the 47-file fact layer and
records the corrected discovery-versus-completeness boundary, but it does not
replace this inventory. Canonical status is only a reading route; it does not
upgrade any `UNKNOWN`, satisfy the decision packet, or authorize a license.

## Scope and evidence standard

`install-manifest.json` maps only `skill/solve-with-weilan` to
`skills/solve-with-weilan`. After the declared cache exclusions, the current
tracked payload contains 47 files. The table below binds this review to the
current bytes and records each file's first repository commit.

The Git identity `ecosystem788 <ecosystem788@github.com>` is the author field
on every first-introduction commit listed here. That is evidence of repository
custody and commit history, not proof of the human or model that created the
content, copyright ownership, contributor authorization, or absence of copied
material. Those legal-provenance questions remain `UNKNOWN` until supported by
source declarations or contributor records outside the current payload.

## Findings relevant to a later license decision

- The payload README declares MIT and points to the repository-root `LICENSE`;
  the installed subtree does not carry that file. This inventory does not cure
  that packaging gap.
- `SKILL.md` expressly names `theory/无我.md` and `theory/元寂计划.md` as
  conceptual sources. The README more broadly names the repository-root
  `theory/` directory as theory provenance. Those theory files are not in the
  47-file payload. The declarations establish conceptual lineage, but do not
  establish the copyright/license chain for the implementation or derived
  prose.
- No per-file SPDX identifier, copyright line, `LICENSE`, `NOTICE`, or
  `COPYING` file was found inside the payload. Absence of markers is not proof
  of original authorship or freedom from notice obligations.
- Runtime modules import the Python standard library and sibling payload
  modules. Tests additionally import `pytest`. No vendored dependency tree was
  found in this 47-file surface. A packaging decision must still distinguish a
  test dependency from copied source and must verify the exact frozen tree.
- The current tree is not immutable: `scripts/test_conversation_evidence.py`
  and `scripts/wake_brief.py` differ from HEAD. Their hashes below bind only
  this evidence snapshot, not a release candidate.

## First-introduction commit groups

| Files | First commit | Commit subject | Evidentiary meaning |
|---:|---|---|---|
| 27 | `d6880927d675e690d63d3014aff3d32750178b7f` | `chore: establish Skill Evolution authority baseline` | Repository introduction only; legal author/rights chain `UNKNOWN` |
| 5 | `c075bb2a0889d354fbc8c03f94656c60f7f963f2` | `feat: add SE-0.4 prospective memory candidate` | Repository introduction only; legal author/rights chain `UNKNOWN` |
| 2 | `c11a2c0901be280ece86df88f94cd48a0d231b51` | `feat: complete SE-0.2 and SE-0.3 candidate` | Repository introduction only; legal author/rights chain `UNKNOWN` |
| 1 | `643719e2e355b5a3f45b8e48e6c6bf2c5f21d792` | `feat: add external SE-0.5 evolution gate` | Repository introduction only; legal author/rights chain `UNKNOWN` |
| 11 | `3c196d673b571d26abf91de8e82ad96d10e5692c` | `Publish community work-in-progress: proposals, evals, deployments, discussion logs` | Repository introduction only; legal author/rights chain `UNKNOWN` |
| 1 | `b9d93c25b5fb59ee326055dfe9035fb59d7690bd` | `Land public-release payload into repo (commit-only, dual-signed)` | Repository introduction only; legal author/rights chain `UNKNOWN` |

## Per-file accounting

`Current SHA-256` hashes the present working-tree bytes. `First commit` is the
oldest add commit returned by `git log --follow --diff-filter=A`; it is not an
authorship attestation.

| Payload file | Class | First commit | Current SHA-256 |
|---|---|---|---|
| `skill/solve-with-weilan/README.md` | package-doc | `b9d93c25b5fb` | `827014152a068338e06461298e1f2fb04c91d8e9271495741f80b9c933397703` |
| `skill/solve-with-weilan/SKILL.md` | package-doc | `d6880927d675` | `ed08f11e99563b0134a9d82dc7bda46c141c0a5bf5d3403ae4e55f58b7e1273d` |
| `skill/solve-with-weilan/agents/openai.yaml` | agent-config | `d6880927d675` | `6d9b6b89e843ca5cc5e0bd43be237b9ee03f671efc254bdffe9c3fc5fc76bcc2` |
| `skill/solve-with-weilan/references/constitution.md` | method-reference | `d6880927d675` | `bc38de5d18c6e003915268aebbe69b1e7930953cbe44adecc9c16fcd8f63602b` |
| `skill/solve-with-weilan/references/event-schema.md` | method-reference | `d6880927d675` | `b036b0f57f7f07df9cbbf819a0f26de07c18b48b1260542e2cc3958b0d3b2593` |
| `skill/solve-with-weilan/references/evolution-system.md` | method-reference | `643719e2e355` | `10943444cb4689ed6d5ce5dd6b46816c4d74cacb49eefe51187ae18034b89264` |
| `skill/solve-with-weilan/references/governance-system.md` | method-reference | `d6880927d675` | `eb4e11946f2b72b73e5efc0841096e269ec15643ac6922d0c0839f8e5df2f27f` |
| `skill/solve-with-weilan/references/memory-system.md` | method-reference | `d6880927d675` | `e1a26bab1250738f09f4746ea96a6696ad97d4879cc90da5f6757ecc8b5f753a` |
| `skill/solve-with-weilan/references/metabolism-system.md` | method-reference | `d6880927d675` | `dabf769800d23f580f51a946ff328738f67f1c0161edfb8acc57d48b0c8df95e` |
| `skill/solve-with-weilan/references/prospective-system.md` | method-reference | `c075bb2a0889` | `4687b9a5899454c1f07ede91bf3c48341b5d6bdc654fa4be3df558b0f35770f8` |
| `skill/solve-with-weilan/references/runner-empty-manifest.json` | method-reference | `d6880927d675` | `28f962793e9e6959cbdae9dcc6df70dd9261935f3b6f418c88ad08c9fe84aae5` |
| `skill/solve-with-weilan/references/runner-system.md` | method-reference | `d6880927d675` | `67e482a39080fb56fe4f964a370ae0a8f18286c0836c75197f814d18e7ea6a1a` |
| `skill/solve-with-weilan/references/transaction-system.md` | method-reference | `d6880927d675` | `de85112af7c35d6c14d47c12703895f19c81cbe40898f7c3709f40eacb8a4fed` |
| `skill/solve-with-weilan/references/transition-planner-system.md` | method-reference | `d6880927d675` | `bd9a17b0922535729f47c8781502e363c0859c8f37212bcad26093e4d18349c7` |
| `skill/solve-with-weilan/scripts/governance.py` | implementation | `d6880927d675` | `5e20d809a71cb228aafb357cc96b8741dbfc26116059c19ba66fe00adf4b731b` |
| `skill/solve-with-weilan/scripts/metabolism.py` | implementation | `d6880927d675` | `86a2c440fcd5e5044c8d27085dbe6e34682f6a737603f9e4315769df12ebd3e7` |
| `skill/solve-with-weilan/scripts/prospective.py` | implementation | `c075bb2a0889` | `ddbec49abea17ff34402bf449b0c683206b01e06ce71d0f1a4486b90b1ad6d0e` |
| `skill/solve-with-weilan/scripts/runner.py` | implementation | `d6880927d675` | `08e0cd360c1e6ccbe503a31822b7596c25ed69f24bce7b11bfe11e091b32faa2` |
| `skill/solve-with-weilan/scripts/runtime_core.py` | implementation | `c075bb2a0889` | `f35ac76b99f400553e465e422a3cf66f4b381d0747315ad091826e62a5c0dc68` |
| `skill/solve-with-weilan/scripts/test_conversation_evidence.py` | test | `d6880927d675` | `60d74f4e8a0d60a46e2179cf0585ea4c30dbc3dfbacc1a8a010114c24e5460f4` |
| `skill/solve-with-weilan/scripts/test_derivation_performance.py` | test | `3c196d673b57` | `1eaac89a63a4c63794b92483d8d667fdd4251461b926a24c74ee74118dd0c166` |
| `skill/solve-with-weilan/scripts/test_episode_memory.py` | test | `c11a2c0901be` | `dcb1a7b74c9adfdec34afa22de1bdea434f8d9e776a43258c7764595547d13b1` |
| `skill/solve-with-weilan/scripts/test_event_atomic_replace_retry.py` | test | `3c196d673b57` | `e3fa2ba4c0991a2e0ef59e3754453d84e01b17c853702edf5f9e617e37dfdb13` |
| `skill/solve-with-weilan/scripts/test_evidence_lifecycle.py` | test | `d6880927d675` | `4d654c41a1619f4e7425670c429e05c32a6ae8b7768d1b4c8e8b53dfd7ddac34` |
| `skill/solve-with-weilan/scripts/test_false_zero_guard.py` | test | `3c196d673b57` | `d64300f23f0f3817e7ff5f0af36afcf027b9290bf9562c4fd74728b217eaa3af` |
| `skill/solve-with-weilan/scripts/test_frame_lineage.py` | test | `d6880927d675` | `0aeab56421f6f9334e355bd30100c9b69680e99660cd8f7749dd306476ef632c` |
| `skill/solve-with-weilan/scripts/test_frame_repair.py` | test | `3c196d673b57` | `72ae4760a1f449d0c98e8b075cd1a0c5c2622935051f3a0fc3ce0eb638b7adf1` |
| `skill/solve-with-weilan/scripts/test_gate_liveness.py` | test | `3c196d673b57` | `ea0dc356212c007b47e79b0ab5bd09391d4abe688baf9df04ffe6abe383d9d81` |
| `skill/solve-with-weilan/scripts/test_governance.py` | test | `d6880927d675` | `4b433aa1f32bc264e07f912c7b114a659341ee3661cdf64d1e53f9a37a4fd8e5` |
| `skill/solve-with-weilan/scripts/test_ledger_durability.py` | test | `3c196d673b57` | `935b101c308f7e946bd1245d54026f7fc541436a535b4ce4475f9592452ea064` |
| `skill/solve-with-weilan/scripts/test_memory.py` | test | `d6880927d675` | `e11cb993f4630669e4a66414df3d0496c1c338cdcd8cfcc6e26d0a84d6456129` |
| `skill/solve-with-weilan/scripts/test_memory_note.py` | test | `3c196d673b57` | `4a66e83d871af2f49c80ab9df6970f03710a350fea9b850fa3fee498dbd89c62` |
| `skill/solve-with-weilan/scripts/test_metabolism.py` | test | `d6880927d675` | `f58acfe239a3933b218960901daf6537b1afe7152556b3c31652e9f59e741d9d` |
| `skill/solve-with-weilan/scripts/test_prospective.py` | test | `c075bb2a0889` | `17106440e46b4b19068fe3f242d1b7f094fedb0d9a215eb2a964afc54944bbd4` |
| `skill/solve-with-weilan/scripts/test_runner.py` | test | `d6880927d675` | `06d2611c39538f9289fb90ea86f519bf9092ca3124154ab154526a5e0928ba44` |
| `skill/solve-with-weilan/scripts/test_runtime_boundary.py` | test | `c075bb2a0889` | `42cc0b9859ebc38089753c5d0df899b8e29288662fb2915b8ce54d1a036ab4c3` |
| `skill/solve-with-weilan/scripts/test_semantic_integrity.py` | test | `c11a2c0901be` | `6b3e5619d7c100c9b3f7d002346ee8b6e227553096634b8800a81b351dc2f3ff` |
| `skill/solve-with-weilan/scripts/test_semantic_memory.py` | test | `d6880927d675` | `b76e13949191eabb7cdca963aa69f36a815ba9e97beeb7575bd1d9e01d08e7c8` |
| `skill/solve-with-weilan/scripts/test_slow_loop.py` | test | `3c196d673b57` | `1e936bb3d607542e1b8b6e28f886ab0808a42b7666c5349a2fd4981c4305ef78` |
| `skill/solve-with-weilan/scripts/test_transaction.py` | test | `d6880927d675` | `8487d3ac92d7d69b68fa8abe2e6cb3dbd439cf9b2b7dd71adbbdccc2d1553fb6` |
| `skill/solve-with-weilan/scripts/test_transition_planner.py` | test | `d6880927d675` | `abca215926dbc92e55333cee0c5c9d042e00e472effec2631f4735f31ed41b54` |
| `skill/solve-with-weilan/scripts/test_utf8_output.py` | test | `3c196d673b57` | `f51c27f111589eb12874034972bca032be8596339db2a65bdf6c67aa1bae0ec8` |
| `skill/solve-with-weilan/scripts/test_v3_robustness.py` | test | `3c196d673b57` | `4411888cf5e54e0e9d685502c78c3e970475a50730addcc91ccb251a8680fcb2` |
| `skill/solve-with-weilan/scripts/transaction.py` | implementation | `d6880927d675` | `5dfb4e3d5588bf116bdee86aefd3f9c65cc71067048b5f6af41b30c27ec8628b` |
| `skill/solve-with-weilan/scripts/transition_planner.py` | implementation | `d6880927d675` | `3315d4b3be52d9962142922d519a9a4aa96653d60c2490909d899ca632a506a7` |
| `skill/solve-with-weilan/scripts/wake_brief.py` | implementation | `3c196d673b57` | `17f9576fc0930138dc86171aea05cf8ed6fd68441964acc23147979fa22bdd7c` |
| `skill/solve-with-weilan/scripts/weilan_trace.py` | implementation | `d6880927d675` | `33bfe8e7d8770200919e131c92bfaa638067b7f016fa0dfda38d0496c8cba290` |

## Unresolved provenance gate

Before Candidate A can be selected, an independent reviewer still needs
source-backed answers to all of the following:

1. Who owns or is authorized to license each introduction group, including
   model-assisted contributions, and what records support that authority?
2. Do the conceptual derivations from the named theory sources require an
   attribution or notice beyond the proposed MIT text?
3. Did any file copy or adapt material from an external source not visible in
   Git history, comments, imports, or the current repository?
4. Is `Copyright (c) 2026 ecosystem788` the correct exact attribution for the
   frozen release tree and every contributor whose permission is needed?

Until those questions are answered and the exact immutable RC is independently
reviewed, this inventory supports Candidate C as the safe fallback and leaves
R13 `OPEN / DUAL-SIGN`. It does not authorize Candidate A or B.

## Reproduction commands

The evidence was produced with read-only commands equivalent to:

```powershell
git ls-files skill/solve-with-weilan
git log --follow --diff-filter=A --format='%H|%an|%ae|%aI' -- <file>
Get-FileHash -Algorithm SHA256 <file>
rg -n -i 'copyright|license|licensed|derived|adapted|based on|provenance|third.party' skill/solve-with-weilan
rg -n '^\s*(from|import)\s+' skill/solve-with-weilan/scripts -g '*.py'
git status --short -- skill/solve-with-weilan proposals/public-release-consolidation-v0.1
```
