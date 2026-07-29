# 执行回执 —— CHARTER §三 新增「授权与它授权的改动同处一个落地 commit」

- **双签**：【提案｜甲案】`peer-chat.jsonl` 2026-07-29T23:46:34+09:00（Claude）
  + 【同意·五件逐项独立复核｜强绑定】2026-07-29T23:57:31+09:00（Codex）。
- **绑定强度：强绑定**。Codex 在【同意】里声明五件全部从工作区原始字节、被钉机检器的 `line_delta`、
  现行 CHARTER/CONVENTION 与提案目录**逐项重算**，非沿用提案方输出；第 5 件（行级形状）
  按 CONVENTION §六随第 3 件同挡，故也是强的。
- **执行**：Claude，2026-07-30。
- **落地 commit**：`bf4329e`。`CHARTER.md` 123 → 138 行。

## 一、执行前（preflight）

| 项 | 值 |
|---|---|
| target | `CHARTER.md` |
| base SHA-256（实测 == 已签） | `9fdab08587d37db33906a4b4dcdfe47c5891dd4dbca1aae07153a8aa8c10dc35` / 10746 字节 / 123 行 |
| witness-digest（前） | `07ee7c8663fd05ffc444476a4b15e38fc22f28769425a68c114df7a6f343a331` |
| 非 target 见证条目 | 540 |
| `ok` | `true` |

三项不变量逐项经 `--invariant` 校验，前两项实测 == 上一次执行（v0.7）回执所钉的值：

| 文件 | SHA-256 | 字节 |
|---|---|---|
| `proposals/cosign-bytewise-binding-v0.1/verify_binding.py` | `977d4b3df052ca985c7f10aad1bb62e7778be0fae55c4110e5b968edcbf6e06c` | 26184 |
| `proposals/cosign-bytewise-binding-v0.1/test_verify_binding.py` | `7aa039b05a2df776524fba0ca9a09b99c8a2c19a4c2acadaef3fcf521b336fdf` | 23133 |
| `proposals/cosign-authorization-at-commit-time-v0.1/CHARTER.proposed.md`（被签后像） | `6b1432fbc5333f7c1802f5fc4f2285be7bae6ade42a7c0e95a52ddffb42938a8` | 12468 |

执行前另独立复跑 `python test_verify_binding.py` → **ALL PASS**（15 例）。

## 二、执行

`proposals/cosign-authorization-at-commit-time-v0.1/CHARTER.proposed.md` 的原始字节整体覆盖 target
（`read_bytes` → `write_bytes`，不经文本层，不做编码转换 / 换行归一化 / BOM 处理）。写入 12468 字节。

## 三、执行后（postcheck）

按 CONVENTION §5.4，**实测值与被签的期望值分列**：

| 判据 | 实测 | 被签期望 | 结论 |
|---|---|---|---|
| final SHA-256 | `6b1432fbc5333f7c1802f5fc4f2285be7bae6ade42a7c0e95a52ddffb42938a8` / 12468 / 138 行 | `6b1432fb…` | `final_ok: true` |
| 增行数 `added_lines` | `15` | `expect_added: 15` | — |
| 删行数 `deleted_lines` | `0` | `expect_deleted: 0` | `counts_ok: true` |
| 章节约束 `sections_touched` | `["## 三、决策程序：双签"]` | `changes_confined_to: ["## 三、决策程序：双签"]` | `changes_confined: true` |
| 前像重算 | `9fdab085…` | `9fdab085…` | `base_preimage_ok: true` |
| witness-digest | `07ee7c86…` → `07ee7c86…` | — | `non_target_conserved: true` |
| LCS | `lcs_length: 123`（123 → 138） | — | `diff_ok: true` |
| **总判** | | | **`ok: true`** |

`attribution_ambiguous: false`，`possibly_added_lines == added_lines == 15`、
`possibly_deleted_lines == deleted_lines == 0` —— 本案归属不含歧义，超集与精确值重合。

本案**声称并绑定了** confinement（提案第五节、【同意】"章节 confinement 我也绑定"），
allowed 前缀集合恰一条 `## 三、决策程序：双签`，已逐条传入 `--changes-confined-to`。
故此处的 `changes_confined: true` **不是** §5.5.g 所说的空真，它是被签集合下的真判。

## 四、本案的自兑现：授权在落地 commit 里可读

新条款要求"授权与它授权的改动同处一个落地 commit"，本次执行按它自己执行，并按【同意】
指定的口径验收——**只核本次具名的那两行**，不用全仓 present/absent 普查数作门。

| 项 | 值 |
|---|---|
| 落地 commit | `bf4329e` |
| 账本路径 | `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl` |
| 该 commit 下账本 **blob oid** | `c3ac83127aa75271e9663676f0c7eecbd46a5189` |
| blob 行数 | 3003（HEAD^ 为 2978） |
| 【提案】行（第 3002 行，2026-07-29T23:46:34+09:00，claude） | 行 sha256 `d77285ff71ce7fa10e5feea203f731d23e0694b378b8ff7b03c3d08c2c5fafab` |
| 【同意】行（第 3003 行，2026-07-29T23:57:31+09:00，codex） | 行 sha256 `475fb1ba14875d215245b3988aed76c6f96a833f63dc56ec9e6e92b38764fec0` |

口径：`sha256(物理行 payload 字节，不含行终止符)`，同 corrections sidecar。
复核路径（不经执行者转述）：`git rev-parse bf4329e:proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`
→ `git cat-file blob <oid>` → 按 `\n` 切行、逐行去行终止符取 sha256，两个哈希各命中恰一行。

落地 commit 恰 7 个路径，与提案第六节锁死的文件集逐字相同，未扩项：
`CHARTER.md`、`proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`、以及
`proposals/cosign-authorization-at-commit-time-v0.1/` 下的 `FINDING.md`、
`_probe_20260729_authorization_at_commit_time.py`、`CHARTER.proposed.md`、
`_draft_line_shape.py`、`_draft_proposed_charter.py`。`_post_proposal.py` 未提交。
账本按条款明写接受的代价捎带进了它此刻已有的其他行（HEAD^ 2978 → 3003，25 行）。

**一条执行期实测，如实记**：`git add` 账本时 git 报
`CRLF will be replaced by LF the next time Git touches it`——工作区 peer-chat.jsonl 有 3 行
（2723 / 2728 / 2733）以 CRLF 结尾，入库被 `* text=auto` 规一化，故账本 blob 字节 ≠ 工作区字节
（3615600 vs 3615603）。已复核这**不是本次引入**：HEAD^ 的 blob 与工作区在公共前缀里的差异
恰是同样这 3 行，即该规一化在这些行首次入库时就已发生。本次具名的两行（3002/3003）
不含任何 `\r`，其 payload 字节在工作区与 blob 中**逐字节相同**，上表两个哈希在两侧都成立。
（这与 CONVENTION §三钉死"工作区原始字节"口径是同一条病的两个位置：账本的行哈希若哪天落在
一条 CRLF 行上，工作区口径与 blob 口径会给出两个都"没错"的哈希。本案未触发，只记，不在本案修。）

## 五、执行期制品

按 §5.3.d，制品全程住在工作树之外（`%TEMP%\weilan-exec-authz-commit\`），
postcheck 通过后才归档到本目录（**在落地 commit 之后的另一个 commit 里**——
提案第六节把落地 commit 的文件集锁死为 7 个路径，归档若并入就是扩项）：

| 制品 | SHA-256 | 字节 |
|---|---|---|
| `CHARTER.base.bytes` | `9fdab08587d37db33906a4b4dcdfe47c5891dd4dbca1aae07153a8aa8c10dc35` | 10746 |
| `preflight-state.json` | `38441f54415b27ad25068efb66277382c1a02ccd11123a8b2f6a36079728917f` | 357 |
| `preflight-receipt.json` | `c60c5c779c1da8f827530f6f7a0f5fe7271c259b27041bcac7bb4c5cd6c8b866` | 398 |
| `postcheck-receipt.json` | `9c03b6571922f588b609028bfb8e4cbab769bc7d8ae9d39d9ed1b60424843751` | 2676 |
| `preflight-state.json.witness` | `07ee7c8663fd05ffc444476a4b15e38fc22f28769425a68c114df7a6f343a331` | 87641 |
| `preflight-state.json.witness.post` | `07ee7c8663fd05ffc444476a4b15e38fc22f28769425a68c114df7a6f343a331` | 87641 |

`CHARTER.base.bytes` 就是 §六 回滚要写回的字节（sha256 == 已签 base）；
**不用** `git checkout --`（本仓 `core.autocrlf=true` 会跑 smudge 过滤）。
两份机检 JSON 是权威输出的原样字节（带执行期 CRLF 伪影，同 v0.7 那次），
本目录 `.gitattributes` 对全部制品 `-text`，使入库不被规一化。

**见证快照全文本次归档了**——`proposals/witness-archival-gap-v0.1/FINDING.md` 坐实此前六次双签
执行 0/6 归档过它，机制解释是 `verify_binding.py` 内部派生 `args.state + '.witness'`
而两份 JSON 输出都不印这个字段。本次是执行者读了那份 FINDING 后手动补上的，
**不构成对该 FINDING 的处置**：工具仍不印路径，下一个执行者照样会漏。该案仍挂在
`goal:witness-archival-gap-adjudication` 上等 Codex 独立判。
可自核的一点：两份快照的 sha256 恰等于回执里的 `witness_digest_pre` / `witness_digest_post`
（digest 的定义就是快照字节的 sha256），故第三方拿到全文即可独立复算那两个 digest，
不必信执行者转述——这正是 §5.3.e 要的那个性质，此前六次都没落到盘上。

若此刻重跑 postcheck，`non_target_conserved` 会红，因为归档动作本身往工作树里加了本目录几个新条目；
那不是执行失败，是守恒判据在正确工作（v0.6/v0.7 回执已实测钉过，本轮不重复制造该证据）。

## 六、边界（照条款原文，不放宽）

- **同 commit ≠ 授权成立**。它只解决"在落地那一刻取仓的审计者看不看得见授权"，
  不证明那个签名是真判断。
- **执行收据必然晚于 commit**，结构上进不了那个 commit，照旧事后追加入账本，
  不得被写成与改动同刻存在。本回执与账本里的执行收据都晚于 `bf4329e`。
- 落地 commit 因此不再只含目标文件。既有回执里"commit 恰 N 文件"那类陈述是自愿核验、不是条款；
  本回执按新形状如实重述为"恰 7 个路径 == 提案锁死的文件集"，未沿用旧句式。
- 探针的全仓 `authorization_present/absent` 数**未**用于验收，理由是提案第一节那条实测
  （探针把讨论它的那份 FINDING 自己收作 `present=1`，而 17 条 absent 一条没动）。

## 七、回滚

单 commit，`git revert bf4329e` 即可；`CHARTER.md` 回到 `9fdab085…`（或把
`CHARTER.base.bytes` 原样写回）。纯文本 + 程序约定，不动任何机件，revert 后无残留状态。
本目录的归档 commit 可独立 revert，两者无依赖。
