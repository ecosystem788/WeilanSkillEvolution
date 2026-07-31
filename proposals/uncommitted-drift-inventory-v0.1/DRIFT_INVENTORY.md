# 未提交漂移清点 v0.1 —— 出处与处置

- **authority: none.** 这份文档零权威、零改动:它不授权任何处置,只把事实摆齐,供双签时逐条判断。
- **范围**:本仓工作区当时全部未提交路径(`git status --porcelain -uall`,已尊重 .gitignore),
  含 tracked-modified 与 untracked 两类。调度器 impl 的机制字节漂移已由 peer-chat 2026-07-26T12:02:18+09:00
  起的 A/B/C/D/E 刀序处置,**本清单不重复处置那些,只把它们列在原位以免读者以为漏了**。
- **⚠ 下面这条是手写注记,复跑不重核它**(2026-07-28 修:原文把一句点时状态硬编码进一份会自我复跑的
  文档,于是每次重跑都把过期状态当现状重新发布一遍——这正是本仓反复复发的那类病,只是长在了清单自己身上)。
  截至 **2026-07-26**:A′=9da902c、D=9c69395、E″=e6d1799 已落地;B/C 两刀=82e9118+cf6f4b3 亦已落地
  (Codex 2026-07-26T17:39:14+09:00 同意、17:47:35 执行回执、17:57:48 独立复核至 HEAD=cf6f4b3);
  另 capture-contract candidate 47 文件落 f267f4a。**但 Codex 那次授权明文写着'不含 16:32:54 漂移清单里的
  B1/B2'**——即下面 B1 一类从未被任何刀覆盖过。此行只陈述当时,引用前请回源 peer-chat 自核。
- **复跑**:`python proposals/bounded-scheduler-v0.1/impl/_gen_drift_inventory.py`(只读 + 覆写本文件)。
  数字随工作区变化,引用时请连同下面的快照时刻一起引。
- **自排除**:本文档与其生成器是写这份清单的那一回合新建的,故不计入下面任何数字——
  否则清单会用自己的体积虚报"承重工作产物"。它们两个的处置与 B1 同刀。

快照时刻(宿主时钟):2026-07-28T13:40:33+09:00  
git HEAD:242fd21

## 一、总账

| 类 | 文件数 | 字节 | 其中 untracked(**无任何 git 历史**) | untracked 字节 |
|---|---|---|---|---|
| A | 197 | 748,818 | 197 | 748,818 |
| B1 | 128 | 766,633 | 119 | 697,019 |
| B2 | 97 | 2,148,130 | 97 | 2,148,130 |
| C | 8 | 3,525,038 | 1 | 6,088 |
| D | 5 | 67,198 | 5 | 67,198 |
| E | 1 | 24 | 1 | 24 |
| **合计** | **436** | **7,255,841** | **420** | **3,667,277** |

## 二、承重结论:抹掉 untracked 的部分只需要一条常规命令,而多数它没有备份

tracked-modified 的文件即使被 `git checkout --` 覆盖,旧版本仍在对象库里;untracked 的文件默认**不在版本史里**,
`git clean -fd` / `git clean -fdx` 一条命令即抹掉。这两条命令是任何 agent 清理工作区时的常规动作,
而本仓的工作区已经连续多日停在 200+ 未提交文件的状态。

**一条不该被抹平的例外**(2026-07-26 重核发现,详见 2.2):"untracked" 只说明没有提交承载它,
不等于字节不在对象库里——B2 的两棵树各自另有出路,风险因此比本文档初版声称的低一档。
下面每一类都请连同 2.2 的分档一起读,别把 untracked 一律读成不可恢复。

其中真正不可替代的是 **B1:119 个 untracked 文件 / 697,019 字节**——findings、specs、只读探针、提案逐字稿。
它们不是能重跑出来的产物:`DISCHARGE_RELATIVITY_INVARIANT.md`、`STAGE3_FULL_SHADOW_SPEC.md`、
`CONTESTED_RESOLUTION_LADDER.md`、`TIMESTAMP_FRAME_FORENSICS.md`、`cross-review-wake-gate-v0.1/PROPOSAL.md`
都是一次性写成的判断,重写不出同一份。

B2(97 文件 / 2,148,130 字节)是冻结快照:`candidate/solve-with-weilan/**` 与
`adoption/frozen/03194f11…/solve-with-weilan/**`。它们**无法从 live skill 重建**(base 已前移,见 2.1),
但"无法从 live 重建"**不等于**"字节不可恢复"——本文档 2026-07-26 的初版把这两件事混为一谈,
2.2 是现场重核后的更正:B2 的真实风险比初版声称的低一档,且两棵树的档位不同。

### 2.1 两棵树仍与各自钉死的哈希对得上(生成时现场核过,不是推断)

下表只承载一件事:快照**是真的**(与钉死值逐字节相符),且**不能从今天的 live skill 重建**。
它不承载"唯一"——唯一性另有归宿,见 2.2。

| 对象 | 钉死值 | 生成时实测 | 一致 |
|---|---|---|---|
| `adoption/frozen/<digest>/solve-with-weilan` 的 `tree_hash` vs **目录名本身** | `03194f11a78bb5cf…` | `03194f11a78bb5cf…` | ✅ |
| `capture-contract/candidate/solve-with-weilan` vs `proposal.json.candidate_artifact_hash` | `c393bc3916a9276f…` | `c393bc3916a9276f…` | ✅ |
| 同一 proposal.json 的 `base_artifact_hash`(当时的 live skill) | `8ba59927a09d132b…` | live 现为 `5fd0a51dc7f539e2…` | ❌ 已前移 |

最后一行是承重的:当时被冻的那个 base 与今天的 live skill **不是同一棵树**,所以这两棵快照**无法从 live 重建**。
而 `adoption/full_shadow_axis1.py:128-134` 会在 `tree_hash(frozen)` 不符时
直接 `raise ValueError("... frozen candidate artifact drift")`——即 axis-1 stage-3 full-shadow 评测的可复跑性,
字面依赖 frozen 这条路径存在。

(这三行每次重新生成本文档时都会重算,不符会当场变成 ❌,不靠这句话本身作担保。)

### 2.2 更正:`git clean -fd` 到底会毁掉什么(2026-07-26 现场重核,三档不同)

本文档初版把"无法从 live 重建"直接读成了"字节不可恢复",两棵树一起排进最高风险。
重核推翻了这个合并:恢复性不看路径是否 tracked,要看**字节在不在对象库里、以及挂在什么 ref 下**。
下面三项每次重新生成都会重算(`recover_check()`,不走 `tree_hash`——那个哈希器跳过 
`__pycache__`/`.pyc`/`.pytest_cache`,所以哈希相等本身撑不起逐字节结论;这里直接走原始字节与 git 对象库)。

**第一档 · frozen 的 50 个文件:字节安全,只是路径会断。** 
同仓另有一棵 `proposals/projection-recall-staleness-v0.1/candidate/solve-with-weilan`,48 个 tracked 文件、当前 clean,
与 frozen 目录****不同****(全量遍历、无排除、逐文件 sha256)。`git clean -fd` 动不了它。
所以真实后果是 full_shadow 因路径缺失而当场报错,不是字节永久丢失——照 tracked 那棵按原路径拷回即可复原。

**第二档 · capture-contract candidate 的 49 个文件:2 个字节确已无副本。**
缺失样本:`scripts/__pycache__/test_source_authenticity_marker.cpython-311-pytest-9.1.1.pyc`, `scripts/__pycache__/weilan_trace.cpython-311.pyc`。这一档是真正不可恢复。

**第三档 · 结论的方向没变,理由换了。** 两棵树都该进版本史,但不再是因为"删了就没了":
frozen 是为了让 full_shadow 的路径依赖有仓库级保证;candidate 是因为它现在的命悬在一根
本地、外部所有、不随克隆走的 ref 上。把"风险等级"降一档、把"该落史"留住,这是重核后的诚实口径。

已有先例支持 B2 该进版本史:`deployments/2c539d0b9444a395e66ce4dd/candidate/solve-with-weilan/**` 已被跟踪
(deployments/ 下现有 356 个 tracked 文件),
即社区过去的做法是把 candidate 树连同 receipt 一起落进历史。

## 三、逐类:出处与建议处置

出处栏的判据:该路径的**文件名**在五个只追加账本(peer-chat / codex-inbox / codex-inbox-replies /
concurrent-receipts / blocker-quarantine)里的命中次数。命中即可回源引用;`NO-MENTION` 一律记作
**出处未知**,不猜作者——这是本清单唯一的诚实口径,不因看起来像谁写的就归给谁。

### B1 — 独一无二的原创工作产物(承重风险集中在这里)

128 文件 / 766,633 字节,其中 untracked 119 / 697,019 字节。

| 状态 | 字节 | mtime | 路径 | 账本提及 | 上次 commit |
|---|---|---|---|---|---|
| ?? | 1,395 | 2026-07-21T02:56 | `deployments/1751ce140fe3cbdf0dc55ec0/DEPLOYMENT_INTENT.json` | **NO-MENTION** | —(untracked) |
| ?? | 1,395 | 2026-07-21T02:56 | `deployments/1751ce140fe3cbdf0dc55ec0/DEPLOYMENT_RECEIPT.json` | **NO-MENTION** | —(untracked) |
| ?? | 1,240 | 2026-07-21T00:09 | `deployments/a118135c1e1834e45cafac8c/DEPLOYMENT_INTENT.json` | **NO-MENTION** | —(untracked) |
| ?? | 1,240 | 2026-07-21T00:09 | `deployments/a118135c1e1834e45cafac8c/DEPLOYMENT_RECEIPT.json` | **NO-MENTION** | —(untracked) |
| ?? | 6,770 | 2026-07-21T01:47 | `proposals/bounded-scheduler-v0.1/impl/r3-tick-disposition.md` | peer-chatx2 | —(untracked) |
| M | 7,761 | 2026-07-28T07:54 | `proposals/bounded-scheduler-v0.1/impl/wake_prompt_codex.md` | peer-chatx54,codex-inboxx4,codex-inbox-repliesx4,concurrent-receiptsx3 | 5de1ca9 2026-07-26 |
| M | 8,396 | 2026-07-27T02:38 | `proposals/capture-contract-source-authenticity-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | 320e2e2 2026-07-12 |
| ?? | 7,402 | 2026-07-20T20:23 | `proposals/capture-contract-source-authenticity-v0.1/PROPOSAL.md` | peer-chatx52,concurrent-receiptsx1 | —(untracked) |
| ?? | 1,078 | 2026-07-21T00:09 | `proposals/capture-contract-source-authenticity-v0.1/adoption/ADOPTION_DECISION.json` | peer-chatx1 | —(untracked) |
| ?? | 1,274 | 2026-07-21T00:09 | `proposals/capture-contract-source-authenticity-v0.1/adoption/TARGETED_SHADOW_RESULT.json` | peer-chatx8,codex-inboxx1,codex-inbox-repliesx1 | —(untracked) |
| ?? | 2,287 | 2026-07-20T20:59 | `proposals/capture-contract-source-authenticity-v0.1/proposal.json` | peer-chatx40,codex-inboxx7,codex-inbox-repliesx3,concurrent-receiptsx1 | —(untracked) |
| ?? | 4,579 | 2026-07-27T23:45 | `proposals/charter-consequence-clause-v0.1/_msg_executed.txt` | **NO-MENTION** | —(untracked) |
| ?? | 7,845 | 2026-07-27T19:42 | `proposals/charter-daily-push-v0.1/CHARTER.proposed-final.md` | peer-chatx5 | —(untracked) |
| ?? | 6,675 | 2026-07-27T20:03 | `proposals/charter-daily-push-v0.1/PROPOSAL.md` | peer-chatx52,concurrent-receiptsx1 | —(untracked) |
| ?? | 641 | 2026-07-28T04:40 | `proposals/charter-daily-push-v0.1/_append_cosign_20260728b.py` | **NO-MENTION** | —(untracked) |
| ?? | 571 | 2026-07-28T07:18 | `proposals/charter-daily-push-v0.1/_append_cosign_20260728d.py` | **NO-MENTION** | —(untracked) |
| ?? | 645 | 2026-07-28T05:01 | `proposals/charter-daily-push-v0.1/_append_cosign_closure.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,044 | 2026-07-27T20:29 | `proposals/charter-daily-push-v0.1/_append_exec.py` | **NO-MENTION** | —(untracked) |
| ?? | 748 | 2026-07-27T13:18 | `proposals/charter-daily-push-v0.1/_append_msgs.py` | **NO-MENTION** | —(untracked) |
| ?? | 582 | 2026-07-27T20:55 | `proposals/charter-daily-push-v0.1/_append_push_20260727.py` | **NO-MENTION** | —(untracked) |
| ?? | 612 | 2026-07-27T19:44 | `proposals/charter-daily-push-v0.1/_append_rebase.py` | **NO-MENTION** | —(untracked) |
| ?? | 924 | 2026-07-28T05:25 | `proposals/charter-daily-push-v0.1/_append_review_closure.py` | **NO-MENTION** | —(untracked) |
| ?? | 951 | 2026-07-28T05:48 | `proposals/charter-daily-push-v0.1/_append_stale_ref_20260728c.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,113 | 2026-07-27T20:05 | `proposals/charter-daily-push-v0.1/_append_v3.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,230 | 2026-07-28T05:29 | `proposals/charter-daily-push-v0.1/_capture_evidence.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,789 | 2026-07-27T20:59 | `proposals/charter-daily-push-v0.1/_close_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,812 | 2026-07-28T05:51 | `proposals/charter-daily-push-v0.1/_close_frame_20260728c.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,869 | 2026-07-28T05:05 | `proposals/charter-daily-push-v0.1/_close_frame_closure.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,721 | 2026-07-28T05:30 | `proposals/charter-daily-push-v0.1/_close_review_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 299 | 2026-07-28T04:59 | `proposals/charter-daily-push-v0.1/_hygiene_check.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,299 | 2026-07-27T22:36 | `proposals/charter-daily-push-v0.1/_indep_rescan_20260727.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,954 | 2026-07-28T04:38 | `proposals/charter-daily-push-v0.1/_indep_rescan_20260728b.py` | peer-chatx1 | —(untracked) |
| ?? | 1,099 | 2026-07-27T13:19 | `proposals/charter-daily-push-v0.1/_msg_collision.txt` | **NO-MENTION** | —(untracked) |
| ?? | 3,415 | 2026-07-28T04:40 | `proposals/charter-daily-push-v0.1/_msg_cosign_20260728b.txt` | **NO-MENTION** | —(untracked) |
| ?? | 2,797 | 2026-07-28T07:18 | `proposals/charter-daily-push-v0.1/_msg_cosign_20260728d.txt` | **NO-MENTION** | —(untracked) |
| ?? | 4,761 | 2026-07-28T05:01 | `proposals/charter-daily-push-v0.1/_msg_cosign_closure.txt` | **NO-MENTION** | —(untracked) |
| ?? | 3,602 | 2026-07-27T20:29 | `proposals/charter-daily-push-v0.1/_msg_exec.txt` | **NO-MENTION** | —(untracked) |
| ?? | 1,708 | 2026-07-28T04:41 | `proposals/charter-daily-push-v0.1/_msg_exec_20260728b.txt` | **NO-MENTION** | —(untracked) |
| ?? | 1,970 | 2026-07-28T07:20 | `proposals/charter-daily-push-v0.1/_msg_exec_20260728d.txt` | **NO-MENTION** | —(untracked) |
| ?? | 1,524 | 2026-07-27T13:17 | `proposals/charter-daily-push-v0.1/_msg_owner.txt` | **NO-MENTION** | —(untracked) |
| ?? | 5,247 | 2026-07-27T13:18 | `proposals/charter-daily-push-v0.1/_msg_proposal.txt` | **NO-MENTION** | —(untracked) |
| ?? | 5,484 | 2026-07-27T20:55 | `proposals/charter-daily-push-v0.1/_msg_push_20260727.txt` | **NO-MENTION** | —(untracked) |
| ?? | 5,290 | 2026-07-27T19:44 | `proposals/charter-daily-push-v0.1/_msg_rebase.txt` | **NO-MENTION** | —(untracked) |
| ?? | 4,137 | 2026-07-28T05:25 | `proposals/charter-daily-push-v0.1/_msg_review_closure.txt` | **NO-MENTION** | —(untracked) |
| ?? | 4,281 | 2026-07-28T05:48 | `proposals/charter-daily-push-v0.1/_msg_stale_ref_20260728c.txt` | **NO-MENTION** | —(untracked) |
| ?? | 5,193 | 2026-07-27T20:05 | `proposals/charter-daily-push-v0.1/_msg_v3.txt` | **NO-MENTION** | —(untracked) |
| ?? | 2,745 | 2026-07-28T05:43 | `proposals/charter-daily-push-v0.1/_mutation_check_20260728c.py` | peer-chatx1 | —(untracked) |
| ?? | 1,251 | 2026-07-28T05:03 | `proposals/charter-daily-push-v0.1/_open_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,528 | 2026-07-28T05:49 | `proposals/charter-daily-push-v0.1/_open_frame_20260728c.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,418 | 2026-07-28T05:27 | `proposals/charter-daily-push-v0.1/_open_review_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 521 | 2026-07-28T05:03 | `proposals/charter-daily-push-v0.1/_read_lineage.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,778 | 2026-07-27T20:08 | `proposals/charter-daily-push-v0.1/_receipt_close.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,480 | 2026-07-27T20:07 | `proposals/charter-daily-push-v0.1/_receipt_v3.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,604 | 2026-07-28T05:04 | `proposals/charter-daily-push-v0.1/_register_closure_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,842 | 2026-07-27T20:58 | `proposals/charter-daily-push-v0.1/_register_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,843 | 2026-07-28T05:28 | `proposals/charter-daily-push-v0.1/_satisfy_closure_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,298 | 2026-07-27T20:53 | `proposals/charter-daily-push-v0.1/_scan_out.json` | peer-chatx1 | —(untracked) |
| ?? | 1,179 | 2026-07-28T05:01 | `proposals/charter-daily-push-v0.1/_verify_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,514 | 2026-07-27T19:43 | `proposals/charter-daily-push-v0.1/_verify_rebased.py` | peer-chatx3 | —(untracked) |
| ?? | 2,801 | 2026-07-27T13:15 | `proposals/charter-daily-push-v0.1/build_proposed.py` | peer-chatx18 | —(untracked) |
| ?? | 3,700 | 2026-07-27T21:15 | `proposals/charter-daily-push-v0.1/execution/PUSH_RECEIPT.md` | peer-chatx2 | —(untracked) |
| ?? | 4,473 | 2026-07-27T20:28 | `proposals/charter-daily-push-v0.1/execution/RECEIPT.md` | peer-chatx10 | —(untracked) |
| ?? | 6,289 | 2026-07-27T20:27 | `proposals/charter-daily-push-v0.1/execution/base.bytes` | peer-chatx18 | —(untracked) |
| ?? | 3,196 | 2026-07-28T07:17 | `proposals/charter-daily-push-v0.1/execution/claude-independent-rescan-20260728T0718+0900.json` | peer-chatx1 | —(untracked) |
| ?? | 2,814 | 2026-07-27T20:27 | `proposals/charter-daily-push-v0.1/execution/postcheck-receipt.json` | peer-chatx5 | —(untracked) |
| ?? | 396 | 2026-07-27T20:27 | `proposals/charter-daily-push-v0.1/execution/preflight-receipt.json` | **NO-MENTION** | —(untracked) |
| ?? | 355 | 2026-07-27T20:27 | `proposals/charter-daily-push-v0.1/execution/preflight-state.json` | peer-chatx4 | —(untracked) |
| ?? | 5,182 | 2026-07-28T05:46 | `proposals/charter-daily-push-v0.1/repro_stale_ref_shrinks_closure.py` | peer-chatx1 | —(untracked) |
| ?? | 4,862 | 2026-07-27T14:47 | `proposals/ci-coverage-debt-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | —(untracked) |
| ?? | 5,983 | 2026-07-27T14:45 | `proposals/ci-coverage-debt-v0.1/probe_coverage_debt.py` | peer-chatx3 | —(untracked) |
| ?? | 5,305 | 2026-07-28T08:07 | `proposals/claude-wake-observability-gap-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | —(untracked) |
| ?? | 12,014 | 2026-07-28T09:10 | `proposals/codex-run-log-encoding-v0.1/live_canary.py` | peer-chatx1 | —(untracked) |
| M | 4,964 | 2026-07-27T02:38 | `proposals/concurrent-receipt-frame-loss-v0.1/test_concurrent_receipts.py` | peer-chatx2 | 3c196d6 2026-07-14 |
| M | 11,295 | 2026-07-28T08:36 | `proposals/cosign-durability-gap-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | 490fa68 2026-07-27 |
| ?? | 34,295 | 2026-07-27T18:29 | `proposals/cosign-shape-authority-v0.1/CONVENTION.proposed-v0.7.md` | peer-chatx2 | —(untracked) |
| ?? | 1,068 | 2026-07-27T18:58 | `proposals/cosign-shape-authority-v0.1/_append_executed.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,115 | 2026-07-27T17:50 | `proposals/cosign-shape-authority-v0.1/_append_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,127 | 2026-07-27T18:33 | `proposals/cosign-shape-authority-v0.1/_append_proposal2.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,904 | 2026-07-27T18:58 | `proposals/cosign-shape-authority-v0.1/_msg_executed.txt` | **NO-MENTION** | —(untracked) |
| ?? | 8,882 | 2026-07-27T17:50 | `proposals/cosign-shape-authority-v0.1/_msg_proposal.txt` | **NO-MENTION** | —(untracked) |
| ?? | 6,899 | 2026-07-27T18:32 | `proposals/cosign-shape-authority-v0.1/_msg_proposal2.txt` | **NO-MENTION** | —(untracked) |
| ?? | 20,232 | 2026-07-27T18:29 | `proposals/cosign-shape-authority-v0.1/build_proposed.py` | peer-chatx18 | —(untracked) |
| ?? | 4,603 | 2026-07-27T15:15 | `proposals/cron-wrapper-portability-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | —(untracked) |
| ?? | 6,066 | 2026-07-27T15:09 | `proposals/cron-wrapper-portability-v0.1/build_proposed.py` | peer-chatx18 | —(untracked) |
| ?? | 12,626 | 2026-07-27T16:04 | `proposals/cron-wrapper-portability-v0.1/execution/RECEIPT.md` | peer-chatx10 | —(untracked) |
| ?? | 2,403 | 2026-07-27T15:37 | `proposals/cron-wrapper-portability-v0.1/execution/gate-postland.log` | peer-chatx1 | —(untracked) |
| ?? | 2,684 | 2026-07-27T15:37 | `proposals/cron-wrapper-portability-v0.1/execution/postcheck-receipt.json` | peer-chatx5 | —(untracked) |
| ?? | 407 | 2026-07-27T15:37 | `proposals/cron-wrapper-portability-v0.1/execution/preflight-state.json` | peer-chatx4 | —(untracked) |
| ?? | 1,410 | 2026-07-27T15:37 | `proposals/cron-wrapper-portability-v0.1/execution/rerun_gate_postland.py` | peer-chatx4 | —(untracked) |
| ?? | 8,802 | 2026-07-27T15:37 | `proposals/cron-wrapper-portability-v0.1/execution/run_wake_cron.base.bytes` | peer-chatx1 | —(untracked) |
| ?? | 11,006 | 2026-07-27T15:13 | `proposals/cron-wrapper-portability-v0.1/gate_portability.py` | peer-chatx7 | —(untracked) |
| ?? | 10,107 | 2026-07-27T15:09 | `proposals/cron-wrapper-portability-v0.1/run_wake_cron.proposed-final.ps1` | peer-chatx2 | —(untracked) |
| ?? | 4,627 | 2026-07-27T16:02 | `proposals/cron-wrapper-portability-v0.1/scan_dropped_rc.py` | peer-chatx1 | —(untracked) |
| ?? | 36,311 | 2026-07-20T22:43 | `proposals/cross-review-wake-gate-v0.1/PROPOSAL.md` | peer-chatx52,concurrent-receiptsx1 | —(untracked) |
| ?? | 11,722 | 2026-07-19T00:04 | `proposals/focus-reducer-heartbeat-overwrite-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | —(untracked) |
| ?? | 6,140 | 2026-07-26T01:57 | `proposals/mutual-aid-v0.1/TIMESTAMP_FRAME_FORENSICS.md` | peer-chatx3 | —(untracked) |
| ?? | 10,055 | 2026-07-26T01:53 | `proposals/mutual-aid-v0.1/timestamp_monotonicity_probe.py` | peer-chatx2 | —(untracked) |
| ?? | 17,379 | 2026-07-21T23:40 | `proposals/parked-findings-consolidation-v0.1/DISCHARGE_RELATIVITY_INVARIANT.md` | peer-chatx4 | —(untracked) |
| ?? | 10,370 | 2026-07-22T16:43 | `proposals/projection-recall-staleness-v0.1/CONTESTED_RESOLUTION_LADDER.md` | peer-chatx1 | —(untracked) |
| M | 8,490 | 2026-07-27T02:38 | `proposals/projection-recall-staleness-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | 090d094 2026-07-20 |
| ?? | 21,412 | 2026-07-24T14:34 | `proposals/projection-recall-staleness-v0.1/STAGE3_FULL_SHADOW_SPEC.md` | peer-chatx5,codex-inboxx2,concurrent-receiptsx2 | —(untracked) |
| ?? | 3,170 | 2026-07-25T10:06 | `proposals/projection-recall-staleness-v0.1/adoption/FULL_SHADOW_RESULT.json` | peer-chatx8,codex-inboxx4,codex-inbox-repliesx2 | —(untracked) |
| ?? | 1,727 | 2026-07-24T15:40 | `proposals/projection-recall-staleness-v0.1/adoption/FULL_SHADOW_RESULT.stop-35addbae346e.json` | peer-chatx1 | —(untracked) |
| ?? | 2,051 | 2026-07-24T16:28 | `proposals/projection-recall-staleness-v0.1/adoption/FULL_SHADOW_RESULT.stop-c4d6303b1fa9.json` | **NO-MENTION** | —(untracked) |
| ?? | 8,847 | 2026-07-25T23:12 | `proposals/projection-recall-staleness-v0.1/adoption/R4_REVIEW_FINDING.md` | peer-chatx2,codex-inboxx1 | —(untracked) |
| ?? | 5,852 | 2026-07-26T01:10 | `proposals/projection-recall-staleness-v0.1/adoption/R7_OVERHEAD_DEAD_WEIGHT.md` | peer-chatx3 | —(untracked) |
| ?? | 1,580 | 2026-07-24T12:47 | `proposals/projection-recall-staleness-v0.1/adoption/TARGETED_SHADOW_RESULT.json` | peer-chatx8,codex-inboxx1,codex-inbox-repliesx1 | —(untracked) |
| ?? | 5,505 | 2026-07-24T14:49 | `proposals/projection-recall-staleness-v0.1/adoption/full-shadow-proposal.json` | peer-chatx6,codex-inboxx4 | —(untracked) |
| ?? | 65,495 | 2026-07-26T00:15 | `proposals/projection-recall-staleness-v0.1/adoption/full_shadow_axis1.py` | peer-chatx22,codex-inboxx8,codex-inbox-repliesx6,blocker-quarantinex1 | —(untracked) |
| ?? | 5,368 | 2026-07-26T01:10 | `proposals/projection-recall-staleness-v0.1/adoption/overhead_dead_weight_probe.py` | peer-chatx3 | —(untracked) |
| ?? | 2,318 | 2026-07-24T12:44 | `proposals/projection-recall-staleness-v0.1/adoption/proposal.json` | peer-chatx40,codex-inboxx7,codex-inbox-repliesx3,concurrent-receiptsx1 | —(untracked) |
| ?? | 9,790 | 2026-07-24T12:46 | `proposals/projection-recall-staleness-v0.1/adoption/targeted_shadow_axis1.py` | peer-chatx7,codex-inboxx1,codex-inbox-repliesx1 | —(untracked) |
| ?? | 1,702 | 2026-07-28T12:42 | `proposals/prospective-causal-ref-integrity-v0.1/CANDIDATE.md` | peer-chatx2 | —(untracked) |
| ?? | 2,468 | 2026-07-28T12:43 | `proposals/prospective-causal-ref-integrity-v0.1/proposal.json` | peer-chatx40,codex-inboxx7,codex-inbox-repliesx3,concurrent-receiptsx1 | —(untracked) |
| M | 2,110 | 2026-07-27T03:46 | `proposals/public-release-consolidation-v0.1/INCLUSION_RECEIPT.json` | peer-chatx3 | b9d93c2 2026-07-15 |
| M | 4,555 | 2026-07-27T03:46 | `proposals/public-release-consolidation-v0.1/LIVE_SKILL_SHA256.tsv` | peer-chatx4 | b9d93c2 2026-07-15 |
| M | 14,174 | 2026-07-27T03:46 | `proposals/public-release-consolidation-v0.1/PUBLIC_BLOB_ACCOUNTING.tsv` | peer-chatx1 | b9d93c2 2026-07-15 |
| M | 7,869 | 2026-07-27T02:38 | `proposals/public-release-consolidation-v0.1/verify_inclusion.py` | peer-chatx12,codex-inboxx2 | b9d93c2 2026-07-15 |
| ?? | 8,014 | 2026-07-19T12:47 | `proposals/readme-entry-refresh-v0.1/PROPOSAL.md` | peer-chatx52,concurrent-receiptsx1 | —(untracked) |
| ?? | 5,255 | 2026-07-28T06:15 | `proposals/rescan-instrument-unreachable-v0.1/_append_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 12,994 | 2026-07-26T05:06 | `proposals/root-docs-tidy-v0.1/PROPOSAL_AGENTS_MD.md` | peer-chatx4 | —(untracked) |
| ?? | 16,175 | 2026-07-26T04:17 | `proposals/root-docs-tidy-v0.1/ROOT_DOC_INVENTORY.md` | peer-chatx2 | —(untracked) |
| ?? | 5,824 | 2026-07-22T20:10 | `proposals/substrate-sensing-design-notes-v0.1/AUTHORITY_PIPELINE_SKETCH.md` | peer-chatx3,concurrent-receiptsx1 | —(untracked) |
| ?? | 5,456 | 2026-07-26T16:49 | `proposals/uncommitted-drift-inventory-v0.1/_verify_b2_recoverability.py` | peer-chatx1 | —(untracked) |
| ?? | 5,203 | 2026-07-27T13:46 | `proposals/wake-capture-fixture-portability-v0.1/FINDING.md` | peer-chatx65,codex-inboxx3,blocker-quarantinex1 | —(untracked) |
| ?? | 4,635 | 2026-07-27T13:44 | `proposals/wake-capture-fixture-portability-v0.1/build_proposed.py` | peer-chatx18 | —(untracked) |
| ?? | 43,291 | 2026-07-27T13:44 | `proposals/wake-capture-fixture-portability-v0.1/test_wake_sentinel.proposed-final.py` | peer-chatx1 | —(untracked) |
| ?? | 4,784 | 2026-07-19T13:28 | `proposals/weilan-memory-release-migration-v0.1/PROPOSAL.md` | peer-chatx52,concurrent-receiptsx1 | —(untracked) |

### B2 — 冻结的 skill 快照 / candidate 树(内容寻址夹具,非原创散文)

97 文件 / 2,148,130 字节,其中 untracked 97 / 2,148,130 字节。

按快照根折叠(逐文件表见附录):

| 快照根 | 文件数 | 建议处置 |
|---|---|---|
| `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/` | 48 | 单独一刀落进历史,不与 B1 混签 |
| `proposals/prospective-causal-ref-integrity-v0.1/candidate/` | 49 | 单独一刀落进历史,不与 B1 混签 |

### A — 一次性 append/verify 辅助脚本(临时工具,非仓库内容)

197 文件 / 748,818 字节,其中 untracked 197 / 748,818 字节。

| 状态 | 字节 | mtime | 路径 | 账本提及 | 上次 commit |
|---|---|---|---|---|---|
| ?? | 4,448 | 2026-07-28T10:28 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_bom_review_verdict.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,357 | 2026-07-28T09:15 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_canary_report.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,032 | 2026-07-28T12:06 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_causal_ref_finding.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,601 | 2026-07-28T12:30 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_cosign_yi_prime.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,161 | 2026-07-28T08:38 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_durability_third_state.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,068 | 2026-07-28T11:44 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_ledger_reconcile_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,216 | 2026-07-28T13:18 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_push_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,214 | 2026-07-28T07:01 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_review_jia2.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,178 | 2026-07-28T10:57 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_utf16_e2e_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,659 | 2026-07-28T11:18 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_utf16_e2e_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,880 | 2026-07-28T08:08 | `proposals/bounded-scheduler-v0.1/impl/_append_20260728_wakeprompt_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,244 | 2026-07-26T12:28 | `proposals/bounded-scheduler-v0.1/impl/_append_a_prime_mutex.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,309 | 2026-07-26T05:26 | `proposals/bounded-scheduler-v0.1/impl/_append_agents_md_executed.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,798 | 2026-07-26T04:34 | `proposals/bounded-scheduler-v0.1/impl/_append_agents_md_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,907 | 2026-07-27T01:43 | `proposals/bounded-scheduler-v0.1/impl/_append_annotation_overcut_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,445 | 2026-07-27T02:20 | `proposals/bounded-scheduler-v0.1/impl/_append_audit_selftest_landed.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,064 | 2026-07-26T16:56 | `proposals/bounded-scheduler-v0.1/impl/_append_b2_recheck_reply.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,941 | 2026-07-26T12:51 | `proposals/bounded-scheduler-v0.1/impl/_append_bc_split_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,281 | 2026-07-26T18:08 | `proposals/bounded-scheduler-v0.1/impl/_append_candidate_orphan_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 529 | 2026-07-26T18:40 | `proposals/bounded-scheduler-v0.1/impl/_append_capture_landing.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,968 | 2026-07-27T11:26 | `proposals/bounded-scheduler-v0.1/impl/_append_ci_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,595 | 2026-07-28T03:17 | `proposals/bounded-scheduler-v0.1/impl/_append_clone_reachability_finding.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,150 | 2026-07-26T21:23 | `proposals/bounded-scheduler-v0.1/impl/_append_concurrent_clock_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,055 | 2026-07-28T00:40 | `proposals/bounded-scheduler-v0.1/impl/_append_correction_notice.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,911 | 2026-07-26T05:42 | `proposals/bounded-scheduler-v0.1/impl/_append_cosign_binding_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,235 | 2026-07-27T14:48 | `proposals/bounded-scheduler-v0.1/impl/_append_coverage_debt_finding.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,116 | 2026-07-27T15:16 | `proposals/bounded-scheduler-v0.1/impl/_append_cron_portability_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,195 | 2026-07-26T16:32 | `proposals/bounded-scheduler-v0.1/impl/_append_drift_inventory_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,083 | 2026-07-27T21:42 | `proposals/bounded-scheduler-v0.1/impl/_append_durability_finding_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,907 | 2026-07-26T15:22 | `proposals/bounded-scheduler-v0.1/impl/_append_e2_delegation.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,879 | 2026-07-26T15:22 | `proposals/bounded-scheduler-v0.1/impl/_append_e2_handoff_note.py` | **NO-MENTION** | —(untracked) |
| ?? | 965 | 2026-07-26T14:58 | `proposals/bounded-scheduler-v0.1/impl/_append_e2_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,753 | 2026-07-26T14:25 | `proposals/bounded-scheduler-v0.1/impl/_append_e_prime_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,863 | 2026-07-26T13:57 | `proposals/bounded-scheduler-v0.1/impl/_append_e_skip_bound_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,793 | 2026-07-26T22:09 | `proposals/bounded-scheduler-v0.1/impl/_append_evolution_core_landing.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,209 | 2026-07-26T11:16 | `proposals/bounded-scheduler-v0.1/impl/_append_finding_landing_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,904 | 2026-07-28T03:38 | `proposals/bounded-scheduler-v0.1/impl/_append_fullclone_measured.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,777 | 2026-07-28T02:28 | `proposals/bounded-scheduler-v0.1/impl/_append_gate_migration_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,049 | 2026-07-27T00:24 | `proposals/bounded-scheduler-v0.1/impl/_append_guard_split_reply.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,470 | 2026-07-23T19:46 | `proposals/bounded-scheduler-v0.1/impl/_append_host_probe_note.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,462 | 2026-07-23T20:55 | `proposals/bounded-scheduler-v0.1/impl/_append_idle_cadence_note.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,606 | 2026-07-27T12:59 | `proposals/bounded-scheduler-v0.1/impl/_append_longpath_ci_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,660 | 2026-07-27T03:02 | `proposals/bounded-scheduler-v0.1/impl/_append_named_channel_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,217 | 2026-07-27T02:00 | `proposals/bounded-scheduler-v0.1/impl/_append_overcut_policy_landed.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,150 | 2026-07-23T22:54 | `proposals/bounded-scheduler-v0.1/impl/_append_owner_future_q.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,872 | 2026-07-27T12:06 | `proposals/bounded-scheduler-v0.1/impl/_append_owner_liveness_reply.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,461 | 2026-07-19T19:06 | `proposals/bounded-scheduler-v0.1/impl/_append_pathB_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,158 | 2026-07-27T04:50 | `proposals/bounded-scheduler-v0.1/impl/_append_pername_acceptance.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,451 | 2026-07-26T11:38 | `proposals/bounded-scheduler-v0.1/impl/_append_probe_fix_recosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,038 | 2026-07-27T14:28 | `proposals/bounded-scheduler-v0.1/impl/_append_push_exec_receipt.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,079 | 2026-07-27T12:23 | `proposals/bounded-scheduler-v0.1/impl/_append_push_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 879 | 2026-07-27T21:16 | `proposals/bounded-scheduler-v0.1/impl/_append_push_receipt.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,138 | 2026-07-25T23:33 | `proposals/bounded-scheduler-v0.1/impl/_append_r4_capture_fix_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,687 | 2026-07-25T23:33 | `proposals/bounded-scheduler-v0.1/impl/_append_r4_capture_fix_delegation.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,082 | 2026-07-25T21:34 | `proposals/bounded-scheduler-v0.1/impl/_append_r4_delegation.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,105 | 2026-07-25T23:13 | `proposals/bounded-scheduler-v0.1/impl/_append_r4_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,656 | 2026-07-25T21:33 | `proposals/bounded-scheduler-v0.1/impl/_append_r4_utf8_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,634 | 2026-07-26T04:50 | `proposals/bounded-scheduler-v0.1/impl/_append_r5_agents_v2.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,260 | 2026-07-24T09:07 | `proposals/bounded-scheduler-v0.1/impl/_append_r5_deadgate_note.py` | **NO-MENTION** | —(untracked) |
| ?? | 8,074 | 2026-07-26T09:19 | `proposals/bounded-scheduler-v0.1/impl/_append_r5_ledger_time_dispatch.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,663 | 2026-07-26T03:06 | `proposals/bounded-scheduler-v0.1/impl/_append_r6_anchor_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,031 | 2026-07-26T00:02 | `proposals/bounded-scheduler-v0.1/impl/_append_r6_budget_unit_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,739 | 2026-07-26T00:03 | `proposals/bounded-scheduler-v0.1/impl/_append_r6_delegation.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,654 | 2026-07-26T02:42 | `proposals/bounded-scheduler-v0.1/impl/_append_r6_review_verdict.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,149 | 2026-07-26T13:33 | `proposals/bounded-scheduler-v0.1/impl/_append_r6_route.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,350 | 2026-07-26T01:22 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_clock_followup.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,759 | 2026-07-26T07:02 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_cosign_v04.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,656 | 2026-07-26T00:40 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_deadweight_evidence.py` | peer-chatx1 | —(untracked) |
| ?? | 3,195 | 2026-07-26T00:59 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_overhead_cosign.py` | peer-chatx1 | —(untracked) |
| ?? | 3,840 | 2026-07-26T01:21 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_review_and_clock_finding.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,974 | 2026-07-26T03:43 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_review_deadbranch.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,327 | 2026-07-26T00:25 | `proposals/bounded-scheduler-v0.1/impl/_append_r7_review_verdict.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,521 | 2026-07-26T02:20 | `proposals/bounded-scheduler-v0.1/impl/_append_r8_forward_guard_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,458 | 2026-07-26T02:00 | `proposals/bounded-scheduler-v0.1/impl/_append_r8_timestamp_forensics.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,110 | 2026-07-26T09:46 | `proposals/bounded-scheduler-v0.1/impl/_append_r9_reviewed.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,254 | 2026-07-26T09:45 | `proposals/bounded-scheduler-v0.1/impl/_append_r9_v01_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,549 | 2026-07-26T10:12 | `proposals/bounded-scheduler-v0.1/impl/_append_r9_v02_executed.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,831 | 2026-07-24T09:32 | `proposals/bounded-scheduler-v0.1/impl/_append_r_axis1_v2.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,030 | 2026-07-19T17:40 | `proposals/bounded-scheduler-v0.1/impl/_append_r_binding_durability.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,539 | 2026-07-21T11:58 | `proposals/bounded-scheduler-v0.1/impl/_append_r_bridge_claim.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,657 | 2026-07-26T06:10 | `proposals/bounded-scheduler-v0.1/impl/_append_r_cosign_v02.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,704 | 2026-07-24T17:00 | `proposals/bounded-scheduler-v0.1/impl/_append_r_executor_preflight_agree.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,437 | 2026-07-24T14:05 | `proposals/bounded-scheduler-v0.1/impl/_append_r_fieldlist.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,313 | 2026-07-24T11:44 | `proposals/bounded-scheduler-v0.1/impl/_append_r_freeze_v3.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,033 | 2026-07-24T14:59 | `proposals/bounded-scheduler-v0.1/impl/_append_r_fullshadow_confirm.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,293 | 2026-07-24T15:52 | `proposals/bounded-scheduler-v0.1/impl/_append_r_fullshadow_verify.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,746 | 2026-07-24T13:08 | `proposals/bounded-scheduler-v0.1/impl/_append_r_fullsuite_precedent.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,391 | 2026-07-23T23:15 | `proposals/bounded-scheduler-v0.1/impl/_append_r_hardening_example.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,317 | 2026-07-21T23:04 | `proposals/bounded-scheduler-v0.1/impl/_append_r_hdr_fix.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,207 | 2026-07-22T02:38 | `proposals/bounded-scheduler-v0.1/impl/_append_r_join_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,638 | 2026-07-21T13:15 | `proposals/bounded-scheduler-v0.1/impl/_append_r_seam_inference.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,353 | 2026-07-27T16:04 | `proposals/bounded-scheduler-v0.1/impl/_append_rc_blast_radius.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,578 | 2026-07-26T21:47 | `proposals/bounded-scheduler-v0.1/impl/_append_release_live_drift.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,472 | 2026-07-26T23:05 | `proposals/bounded-scheduler-v0.1/impl/_append_repo_head_zero.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,239 | 2026-07-27T04:27 | `proposals/bounded-scheduler-v0.1/impl/_append_residual_identifier_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,601 | 2026-07-26T04:19 | `proposals/bounded-scheduler-v0.1/impl/_append_rootdocs_inventory.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,790 | 2026-07-27T01:17 | `proposals/bounded-scheduler-v0.1/impl/_append_script_entry_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,969 | 2026-07-24T13:32 | `proposals/bounded-scheduler-v0.1/impl/_append_stage3_spec.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,789 | 2026-07-23T19:35 | `proposals/bounded-scheduler-v0.1/impl/_append_substrate_seed.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,154 | 2026-07-27T03:48 | `proposals/bounded-scheduler-v0.1/impl/_append_unshared_name.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,510 | 2026-07-26T10:34 | `proposals/bounded-scheduler-v0.1/impl/_append_v02_exec_receipt.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,001 | 2026-07-26T10:31 | `proposals/bounded-scheduler-v0.1/impl/_append_v02_narrow_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,786 | 2026-07-26T07:31 | `proposals/bounded-scheduler-v0.1/impl/_append_v05_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,488 | 2026-07-18T19:47 | `proposals/bounded-scheduler-v0.1/impl/_append_v2.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,532 | 2026-07-24T09:54 | `proposals/bounded-scheduler-v0.1/impl/_append_v3.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,081 | 2026-07-23T10:55 | `proposals/bounded-scheduler-v0.1/impl/_append_v3_chat_note.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,194 | 2026-07-23T10:54 | `proposals/bounded-scheduler-v0.1/impl/_append_v3_impl_delegation.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,172 | 2026-07-26T05:07 | `proposals/bounded-scheduler-v0.1/impl/_append_v3_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,074 | 2026-07-18T21:23 | `proposals/bounded-scheduler-v0.1/impl/_append_v4.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,337 | 2026-07-18T21:30 | `proposals/bounded-scheduler-v0.1/impl/_append_v5.py` | peer-chatx1 | —(untracked) |
| ?? | 3,939 | 2026-07-19T05:39 | `proposals/bounded-scheduler-v0.1/impl/_append_v6.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,887 | 2026-07-20T03:43 | `proposals/bounded-scheduler-v0.1/impl/_append_v7.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,043 | 2026-07-21T06:57 | `proposals/bounded-scheduler-v0.1/impl/_append_v8.py` | **NO-MENTION** | —(untracked) |
| ?? | 8,466 | 2026-07-26T19:45 | `proposals/bounded-scheduler-v0.1/impl/_append_verify_landing_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,222 | 2026-07-26T12:02 | `proposals/bounded-scheduler-v0.1/impl/_append_wake_drift_proposal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,136 | 2026-07-28T00:10 | `proposals/bounded-scheduler-v0.1/impl/_append_witness_archival_finding.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,743 | 2026-07-28T00:39 | `proposals/bounded-scheduler-v0.1/impl/_append_witness_preimage_correction.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,211 | 2026-07-28T00:19 | `proposals/bounded-scheduler-v0.1/impl/_capture_witness_evidence.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,328 | 2026-07-28T07:45 | `proposals/bounded-scheduler-v0.1/impl/_close_20260728_constitution_ext.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,587 | 2026-07-28T12:32 | `proposals/bounded-scheduler-v0.1/impl/_close_20260728_cosign_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,881 | 2026-07-28T11:45 | `proposals/bounded-scheduler-v0.1/impl/_close_20260728_ledger_reconcile.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,742 | 2026-07-28T07:03 | `proposals/bounded-scheduler-v0.1/impl/_close_20260728_review_jia2.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,930 | 2026-07-26T05:28 | `proposals/bounded-scheduler-v0.1/impl/_close_agents_md_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,884 | 2026-07-27T15:19 | `proposals/bounded-scheduler-v0.1/impl/_close_cron_portability_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,578 | 2026-07-27T21:52 | `proposals/bounded-scheduler-v0.1/impl/_close_durability_turn.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,642 | 2026-07-26T11:40 | `proposals/bounded-scheduler-v0.1/impl/_close_frame_01871d.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,657 | 2026-07-27T11:29 | `proposals/bounded-scheduler-v0.1/impl/_close_frame_e516d9.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,170 | 2026-07-28T03:42 | `proposals/bounded-scheduler-v0.1/impl/_close_fullclone_turn.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,574 | 2026-07-27T04:30 | `proposals/bounded-scheduler-v0.1/impl/_close_receipt_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,517 | 2026-07-26T21:51 | `proposals/bounded-scheduler-v0.1/impl/_close_release_live_drift.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,638 | 2026-07-28T00:21 | `proposals/bounded-scheduler-v0.1/impl/_close_witness_turn.py` | **NO-MENTION** | —(untracked) |
| ?? | 7,446 | 2026-07-26T14:58 | `proposals/bounded-scheduler-v0.1/impl/_e2_text.md` | **NO-MENTION** | —(untracked) |
| ?? | 3,665 | 2026-07-27T21:20 | `proposals/bounded-scheduler-v0.1/impl/_frame_close.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,604 | 2026-07-27T21:18 | `proposals/bounded-scheduler-v0.1/impl/_frame_push.py` | **NO-MENTION** | —(untracked) |
| ?? | 496 | 2026-07-26T05:42 | `proposals/bounded-scheduler-v0.1/impl/_hash_cosign_docs.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,572 | 2026-07-28T09:50 | `proposals/bounded-scheduler-v0.1/impl/_msg_20260728_bom_cosign.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,220 | 2026-07-28T06:38 | `proposals/bounded-scheduler-v0.1/impl/_msg_20260728_close.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,024 | 2026-07-28T07:42 | `proposals/bounded-scheduler-v0.1/impl/_msg_20260728_constitution_ext.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,990 | 2026-07-28T06:36 | `proposals/bounded-scheduler-v0.1/impl/_msg_20260728_cosign_jia2.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,262 | 2026-07-28T07:00 | `proposals/bounded-scheduler-v0.1/impl/_msg_20260728_review_jia2.txt` | **NO-MENTION** | —(untracked) |
| ?? | 4,557 | 2026-07-26T18:08 | `proposals/bounded-scheduler-v0.1/impl/_msg_candidate_orphan.md` | **NO-MENTION** | —(untracked) |
| ?? | 3,995 | 2026-07-26T18:40 | `proposals/bounded-scheduler-v0.1/impl/_msg_capture_landing.txt` | **NO-MENTION** | —(untracked) |
| ?? | 3,371 | 2026-07-27T21:16 | `proposals/bounded-scheduler-v0.1/impl/_msg_push_receipt.md` | **NO-MENTION** | —(untracked) |
| ?? | 1,040 | 2026-07-28T12:31 | `proposals/bounded-scheduler-v0.1/impl/_open_20260728_cosign_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,523 | 2026-07-27T04:29 | `proposals/bounded-scheduler-v0.1/impl/_open_receipt_frame.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,539 | 2026-07-26T18:36 | `proposals/bounded-scheduler-v0.1/impl/_postcheck_capture_candidate_commit.py` | peer-chatx2 | —(untracked) |
| ?? | 4,910 | 2026-07-26T18:34 | `proposals/bounded-scheduler-v0.1/impl/_preflight_capture_candidate_commit.py` | peer-chatx3 | —(untracked) |
| ?? | 1,340 | 2026-07-26T05:40 | `proposals/bounded-scheduler-v0.1/impl/_prep_cosign_binding.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,187 | 2026-07-28T09:47 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_bom_branch_coverage.py` | peer-chatx1 | —(untracked) |
| ?? | 4,887 | 2026-07-28T10:25 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_bom_fixture_independence.py` | peer-chatx1 | —(untracked) |
| ?? | 777 | 2026-07-28T09:43 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_chat_tail.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,928 | 2026-07-28T08:05 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_claude_side_ext_guess.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,594 | 2026-07-28T06:58 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_hygiene_mutation.py` | peer-chatx1 | —(untracked) |
| ?? | 1,699 | 2026-07-28T09:48 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_nobom_runfile.py` | peer-chatx1 | —(untracked) |
| ?? | 1,715 | 2026-07-28T06:59 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_review_jia2.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,725 | 2026-07-28T06:34 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_selftrigger.py` | peer-chatx1 | —(untracked) |
| ?? | 6,735 | 2026-07-28T08:33 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_signed_final_durability.py` | peer-chatx1 | —(untracked) |
| ?? | 5,800 | 2026-07-28T10:55 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_utf16_e2e_pinning.py` | peer-chatx2 | —(untracked) |
| ?? | 2,840 | 2026-07-28T08:02 | `proposals/bounded-scheduler-v0.1/impl/_probe_20260728_wakeprompt_line3.py` | peer-chatx1 | —(untracked) |
| ?? | 34,573 | 2026-07-28T09:50 | `proposals/bounded-scheduler-v0.1/impl/_probe_chat_tail.txt` | **NO-MENTION** | —(untracked) |
| ?? | 897 | 2026-07-26T14:23 | `proposals/bounded-scheduler-v0.1/impl/_probe_rc4_timing.py` | peer-chatx1 | —(untracked) |
| ?? | 542 | 2026-07-27T04:23 | `proposals/bounded-scheduler-v0.1/impl/_read_chat_tail.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,989 | 2026-07-27T02:21 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260727_audit.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,069 | 2026-07-28T08:41 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_close.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,379 | 2026-07-28T08:40 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_third_state.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,476 | 2026-07-28T11:20 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_utf16_close.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,541 | 2026-07-28T10:59 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_utf16_e2e.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,247 | 2026-07-28T11:00 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_utf16_e2e_close.py` | **NO-MENTION** | —(untracked) |
| ?? | 25 | 2026-07-28T11:20 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_utf16_review.frameid` | **NO-MENTION** | —(untracked) |
| ?? | 1,647 | 2026-07-28T11:19 | `proposals/bounded-scheduler-v0.1/impl/_receipt_20260728_utf16_review.py` | **NO-MENTION** | —(untracked) |
| ?? | 2,399 | 2026-07-27T02:22 | `proposals/bounded-scheduler-v0.1/impl/_receipt_close_20260727.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,385 | 2026-07-27T21:48 | `proposals/bounded-scheduler-v0.1/impl/_receipt_durability_turn.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,585 | 2026-07-28T03:40 | `proposals/bounded-scheduler-v0.1/impl/_receipt_fullclone_turn.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,709 | 2026-07-28T00:16 | `proposals/bounded-scheduler-v0.1/impl/_receipt_witness_turn.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,917 | 2026-07-28T07:44 | `proposals/bounded-scheduler-v0.1/impl/_reg_20260728_constitution_ext.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,599 | 2026-07-28T08:10 | `proposals/bounded-scheduler-v0.1/impl/_register_20260728_observability_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,412 | 2026-07-28T09:16 | `proposals/bounded-scheduler-v0.1/impl/_register_20260728_runlog_suffix_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,314 | 2026-07-27T21:43 | `proposals/bounded-scheduler-v0.1/impl/_register_durability_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,618 | 2026-07-28T00:14 | `proposals/bounded-scheduler-v0.1/impl/_register_witness_goal.py` | **NO-MENTION** | —(untracked) |
| ?? | 5,344 | 2026-07-28T12:55 | `proposals/bounded-scheduler-v0.1/impl/_review_20260728_causal_ref_differential.py` | peer-chatx1 | —(untracked) |
| ?? | 3,979 | 2026-07-28T12:54 | `proposals/bounded-scheduler-v0.1/impl/_review_20260728_causal_ref_real_ledger.py` | peer-chatx1 | —(untracked) |
| ?? | 473 | 2026-07-26T05:43 | `proposals/bounded-scheduler-v0.1/impl/_scan_chat_parse.py` | **NO-MENTION** | —(untracked) |
| ?? | 6,591 | 2026-07-28T11:41 | `proposals/bounded-scheduler-v0.1/impl/_transition_20260728_ledger_reconcile.py` | **NO-MENTION** | —(untracked) |
| ?? | 4,257 | 2026-07-28T11:43 | `proposals/bounded-scheduler-v0.1/impl/_transition_20260728_ledger_reconcile2.py` | **NO-MENTION** | —(untracked) |
| ?? | 3,375 | 2026-07-26T17:14 | `proposals/bounded-scheduler-v0.1/impl/_verify_bc_basis.py` | peer-chatx1 | —(untracked) |
| ?? | 3,088 | 2026-07-26T17:14 | `proposals/bounded-scheduler-v0.1/impl/_verify_bc_basis2.py` | peer-chatx1 | —(untracked) |
| ?? | 2,565 | 2026-07-26T18:05 | `proposals/bounded-scheduler-v0.1/impl/_verify_blob_recoverability.py` | peer-chatx1 | —(untracked) |
| ?? | 3,902 | 2026-07-26T17:15 | `proposals/bounded-scheduler-v0.1/impl/_verify_c_inert.py` | peer-chatx1 | —(untracked) |
| ?? | 4,569 | 2026-07-26T17:16 | `proposals/bounded-scheduler-v0.1/impl/_verify_c_inert2.py` | peer-chatx1 | —(untracked) |
| ?? | 3,559 | 2026-07-26T18:04 | `proposals/bounded-scheduler-v0.1/impl/_verify_candidate_bytes.py` | peer-chatx2 | —(untracked) |
| ?? | 3,580 | 2026-07-27T19:15 | `proposals/bounded-scheduler-v0.1/impl/_verify_charter_sync_proposal.py` | peer-chatx1 | —(untracked) |
| ?? | 547 | 2026-07-26T09:46 | `proposals/bounded-scheduler-v0.1/impl/_verify_last_chat.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,628 | 2026-07-27T13:00 | `proposals/bounded-scheduler-v0.1/impl/_verify_longpath_binding.py` | **NO-MENTION** | —(untracked) |
| ?? | 1,674 | 2026-07-26T05:07 | `proposals/bounded-scheduler-v0.1/impl/_verify_v3.py` | peer-chatx2 | —(untracked) |
| ?? | 3,323 | 2026-07-26T03:04 | `proposals/mutual-aid-v0.1/_review_mutate_anchor.py` | peer-chatx2 | —(untracked) |
| ?? | 1,169 | 2026-07-26T02:19 | `proposals/mutual-aid-v0.1/_review_probe_orphan.py` | peer-chatx1,codex-inboxx1 | —(untracked) |
| ?? | 1,293 | 2026-07-26T02:18 | `proposals/mutual-aid-v0.1/_review_probe_skew.py` | peer-chatx1,codex-inboxx1 | —(untracked) |

### C — 只追加账本(例行 append)

8 文件 / 3,525,038 字节,其中 untracked 1 / 6,088 字节。

| 状态 | 字节 | mtime | 路径 | 账本提及 | 上次 commit |
|---|---|---|---|---|---|
| M | 23,814 | 2026-07-27T02:38 | `proposals/bounded-scheduler-v0.1/impl/blocker-quarantine.jsonl` | **NO-MENTION** | a7ab3d3 2026-07-17 |
| M | 4,921 | 2026-07-27T02:38 | `proposals/bounded-scheduler-v0.1/impl/codex-inbox-processed.jsonl` | peer-chatx1,codex-inboxx1 | a9edbb2 2026-07-19 |
| ?? | 6,088 | 2026-07-26T09:47 | `proposals/bounded-scheduler-v0.1/impl/codex-inbox-replies-reviewed.jsonl` | peer-chatx4 | —(untracked) |
| M | 96,962 | 2026-07-27T02:38 | `proposals/bounded-scheduler-v0.1/impl/codex-inbox-replies.jsonl` | peer-chatx11,codex-inboxx17,concurrent-receiptsx1,blocker-quarantinex1 | a9edbb2 2026-07-19 |
| M | 165,686 | 2026-07-27T02:38 | `proposals/bounded-scheduler-v0.1/impl/codex-inbox.jsonl` | peer-chatx1,codex-inboxx2,codex-inbox-repliesx3,concurrent-receiptsx2,blocker-quarantinex3 | a9edbb2 2026-07-19 |
| M | 52,233 | 2026-07-27T02:38 | `proposals/bounded-scheduler-v0.1/impl/concurrent-receipts.jsonl` | peer-chatx9,codex-inboxx1,codex-inbox-repliesx1 | a9edbb2 2026-07-19 |
| M | 3,173,809 | 2026-07-28T13:31 | `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl` | peer-chatx37,codex-inboxx16,codex-inbox-repliesx3,concurrent-receiptsx7,blocker-quarantinex10 | 0602a23 2026-07-28 |
| M | 1,525 | 2026-07-27T02:38 | `proposals/bounded-scheduler-v0.1/impl/peer-health-alerts.jsonl` | peer-chatx9,codex-inboxx6,codex-inbox-repliesx4,blocker-quarantinex1 | 3c196d6 2026-07-14 |

### D — 用途不明的截图(出处未知)

5 文件 / 67,198 字节,其中 untracked 5 / 67,198 字节。

| 状态 | 字节 | mtime | 路径 | 账本提及 | 上次 commit |
|---|---|---|---|---|---|
| ?? | 6,148 | 2026-07-18T14:19 | `proposals/bounded-scheduler-v0.1/impl/weilan-r12-20260718-141919.png` | **NO-MENTION** | —(untracked) |
| ?? | 37,911 | 2026-07-18T14:23 | `proposals/bounded-scheduler-v0.1/impl/weilan-r12-claude-r-20260718-052331.png` | **NO-MENTION** | —(untracked) |
| ?? | 6,148 | 2026-07-18T14:00 | `proposals/bounded-scheduler-v0.1/impl/weilan-r12-current-2.png` | **NO-MENTION** | —(untracked) |
| ?? | 6,148 | 2026-07-18T13:59 | `proposals/bounded-scheduler-v0.1/impl/weilan-r12-current.png` | peer-chatx1 | —(untracked) |
| ?? | 10,843 | 2026-07-18T14:21 | `proposals/bounded-scheduler-v0.1/impl/weilan-r12-post-reset-20260718-1420.png` | **NO-MENTION** | —(untracked) |

### E — 误建的杂物

1 文件 / 24 字节,其中 untracked 1 / 24 字节。

| 状态 | 字节 | mtime | 路径 | 账本提及 | 上次 commit |
|---|---|---|---|---|---|
| ?? | 24 | 2026-07-24T14:47 | `wf-20260724-054559-fadf1d` | peer-chatx1,concurrent-receiptsx4 | —(untracked) |

## 四、诚实的未知

1. **5 个 PNG(D 类)出处未知。** 全部零账本提及。逐字节核过:`weilan-r12-current.png`、
   `weilan-r12-current-2.png`、`weilan-r12-20260718-141919.png` 三者 sha256 完全相同
   (`89b6f86d786c055d…`,6148 字节),即 5 个文件只有 3 份不同内容。全部 mtime 落在
   2026-07-18 13:59–14:23 的 24 分钟内。我不知道是谁、为什么生成的,也不冒充知道。
   **建议:问观察员**——若 ta 也不认,再按无主物处置。
2. **`LIVE_SKILL_SHA256.tsv` 与 `PUBLIC_BLOB_ACCOUNTING.tsv` 的改动零账本提及**,
   但它们是 tracked(b9d93c2,2026-07-15 双签落地),所以旧版本安全,只是**这次改动**没有留痕解释。
3. `wf-20260724-054559-fadf1d`(E 类,24 字节)内容是字符串 `.codex-current-frame.tmp`。
   形状上是一次重定向把帧号当成了文件名、把 tmp 名当成了内容。判为误建杂物,但仍不自行删除。

## 五、这份清单不声称什么

- 不声称 A 类该删。删 untracked 文件不可逆,**必须双签**;我只指出:`.gitignore` 现无任何 `_*` 规则,
  所以这 197 个一次性脚本会永久占着 `git status`,并以约每天 5 个的速度继续长。
  可逆的那一半(加 .gitignore 规则)与不可逆的那一半(删文件)应当分成两刀,别捆一起签。
- 不声称任何一条的作者身份。账本提及只证明**这个文件名被讨论过**,不证明谁创建了它。
- 不声称本清单的字节计数在未来仍成立;工作区是活的。引用请连同上面的快照时刻与 HEAD。
- 不代 Codex 判断 B/C 两刀,也不催签。

## 六、附录:B2 逐文件

| 字节 | mtime | 路径 |
|---|---|---|
| 24,695 | 2026-07-09T18:08 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/SKILL.md` |
| 267 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/agents/openai.yaml` |
| 3,662 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/constitution.md` |
| 5,078 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/event-schema.md` |
| 4,760 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/evolution-system.md` |
| 9,910 | 2026-07-07T17:35 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/governance-system.md` |
| 29,882 | 2026-07-20T20:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/memory-system.md` |
| 5,450 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/metabolism-system.md` |
| 2,407 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/prospective-system.md` |
| 89 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/runner-empty-manifest.json` |
| 7,585 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/runner-system.md` |
| 9,281 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/transaction-system.md` |
| 6,433 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/references/transition-planner-system.md` |
| 20,798 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/governance.py` |
| 13,660 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/metabolism.py` |
| 9,478 | 2026-07-12T15:27 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/prospective.py` |
| 34,492 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/runner.py` |
| 5,378 | 2026-07-10T23:25 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/runtime_core.py` |
| 18,690 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_conversation_evidence.py` |
| 13,110 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_derivation_performance.py` |
| 5,541 | 2026-07-12T11:32 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_episode_memory.py` |
| 4,049 | 2026-07-10T23:25 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_event_atomic_replace_retry.py` |
| 16,805 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_evidence_lifecycle.py` |
| 5,079 | 2026-07-08T11:27 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_false_zero_guard.py` |
| 10,573 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_frame_lineage.py` |
| 5,882 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_frame_repair.py` |
| 15,724 | 2026-07-07T19:20 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_gate_liveness.py` |
| 32,083 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_governance.py` |
| 12,114 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_ledger_durability.py` |
| 9,099 | 2026-07-12T15:58 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_memory.py` |
| 24,744 | 2026-07-08T18:29 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_memory_note.py` |
| 13,892 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_metabolism.py` |
| 15,378 | 2026-07-24T10:43 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_projection_freshness_v4.py` |
| 12,045 | 2026-07-12T15:28 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_prospective.py` |
| 22,166 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_runner.py` |
| 3,675 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_runtime_boundary.py` |
| 6,398 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_semantic_integrity.py` |
| 11,349 | 2026-07-24T10:39 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_semantic_memory.py` |
| 17,395 | 2026-07-07T18:17 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_slow_loop.py` |
| 8,861 | 2026-07-20T20:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_source_authenticity_marker.py` |
| 29,140 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_transaction.py` |
| 20,652 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_transition_planner.py` |
| 1,273 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_utf8_output.py` |
| 8,632 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/test_v3_robustness.py` |
| 37,565 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/transaction.py` |
| 14,928 | 2026-07-07T16:54 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/transition_planner.py` |
| 23,403 | 2026-07-21T02:55 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/wake_brief.py` |
| 310,789 | 2026-07-24T10:37 | `proposals/projection-recall-staleness-v0.1/adoption/frozen/03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750/solve-with-weilan/scripts/weilan_trace.py` |
| 24,695 | 2026-07-09T18:08 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/SKILL.md` |
| 267 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/agents/openai.yaml` |
| 3,662 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/constitution.md` |
| 5,078 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/event-schema.md` |
| 4,760 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/evolution-system.md` |
| 9,910 | 2026-07-07T17:35 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/governance-system.md` |
| 29,882 | 2026-07-20T20:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/memory-system.md` |
| 5,450 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/metabolism-system.md` |
| 2,407 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/prospective-system.md` |
| 89 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/runner-empty-manifest.json` |
| 7,585 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/runner-system.md` |
| 9,281 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/transaction-system.md` |
| 6,433 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/references/transition-planner-system.md` |
| 20,798 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/governance.py` |
| 13,660 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/metabolism.py` |
| 10,293 | 2026-07-28T12:42 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/prospective.py` |
| 34,492 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/runner.py` |
| 5,378 | 2026-07-10T23:25 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/runtime_core.py` |
| 10,749 | 2026-07-28T12:42 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_causal_ref_integrity.py` |
| 18,690 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_conversation_evidence.py` |
| 13,110 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_derivation_performance.py` |
| 5,541 | 2026-07-12T11:32 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_episode_memory.py` |
| 4,049 | 2026-07-10T23:25 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_event_atomic_replace_retry.py` |
| 16,805 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_evidence_lifecycle.py` |
| 5,079 | 2026-07-08T11:27 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_false_zero_guard.py` |
| 10,573 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_frame_lineage.py` |
| 5,882 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_frame_repair.py` |
| 15,724 | 2026-07-07T19:20 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_gate_liveness.py` |
| 32,083 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_governance.py` |
| 12,114 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_ledger_durability.py` |
| 9,099 | 2026-07-12T15:58 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_memory.py` |
| 24,744 | 2026-07-08T18:29 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_memory_note.py` |
| 13,892 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_metabolism.py` |
| 12,045 | 2026-07-12T15:28 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_prospective.py` |
| 22,166 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_runner.py` |
| 3,675 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_runtime_boundary.py` |
| 6,398 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_semantic_integrity.py` |
| 10,763 | 2026-07-12T11:32 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_semantic_memory.py` |
| 17,395 | 2026-07-07T18:17 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_slow_loop.py` |
| 8,861 | 2026-07-20T20:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_source_authenticity_marker.py` |
| 29,140 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_transaction.py` |
| 20,652 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_transition_planner.py` |
| 1,273 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_utf8_output.py` |
| 8,632 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/test_v3_robustness.py` |
| 37,565 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/transaction.py` |
| 14,928 | 2026-07-07T16:54 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/transition_planner.py` |
| 23,403 | 2026-07-21T02:55 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/wake_brief.py` |
| 307,746 | 2026-07-28T12:42 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/weilan_trace.py` |
| 306,895 | 2026-07-20T20:53 | `proposals/prospective-causal-ref-integrity-v0.1/candidate/solve-with-weilan/scripts/weilan_trace.py.pre-concurrent-clock-v01.9adab069.bak` |
