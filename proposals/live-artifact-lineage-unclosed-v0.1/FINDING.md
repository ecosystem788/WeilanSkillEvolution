# FINDING｜正在运行的这件工件,没有回执、没有快照、也不在 git 里

authority: none(只读测量 + 一次纯增量的字节抢救;未改 live、未改产品源、未改任何机制)
测于 2026-07-31,HEAD=6d2bf8e。三支只读探针可复跑,路径见第六节。

---

## 一、一句话

`deployments/` 里 13 份 DEPLOYMENT_RECEIPT 没有一份的 `after_artifact_hash` 等于今天 live 的
`5fd0a51d…`;仓内 57 份 solve-with-weilan 快照没有一份等于它;逐 blob 看,live 的 48 个文件里
**恰好 1 个不在任何 ref 的可达集里** —— `scripts/weilan_trace.py`(307,103 字节)。
**这台机器上,它只有一份拷贝,就是正在跑的那一份。**

## 二、不是谁失职:那次改动是签过的

live 与上一份回执的前像树逐字比对,差异只有一处代码 hunk(`_probe_..._live_drift_since_last_receipt.py`
的 `vs_rollback`),内容是并发回执写入口改用带偏移的宿主时钟并补 `time_authority` 字段:

```
-        "time": args.time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
+        "time": receipt_time,
+        "time_authority": time_authority,
```

这正是 Codex 2026-07-26T09:04:29+09:00【同意・带边界】里点名要的那条("helper 写
`time_authority:"clock"`;存量缺字段只解释为 authored/unknown,不回填"),授权记录在
`proposals/ledger-timestamp-authority-v0.1/COSIGN.md`。**改动本身双签齐全、内容正当。**
病在它落到 live 之后,既没生成部署回执,也没入仓。**这条 finding 不指控任何人的行为,它说的是谱系断了。**

## 三、坐实的测量

| 量 | 值 |
|---|---|
| live tree_hash(`D:\CodexData\skills\solve-with-weilan`) | `5fd0a51d…`,48 文件 |
| `C:\Users\zy\.claude\skills` | 同一目录的 junction(非第二份拷贝),见 correction-view-unwired §10.3 |
| 磁盘 + git 历史里的 DEPLOYMENT_RECEIPT | 13 份,history-only 0 份 |
| 其中 `after == 5fd0a51d…` 的 | **0 份** |
| 最新回执 `1751ce14…`(07-21)声明的 after | `9872361c…` ≠ live |
| 仓内 solve-with-weilan 目录快照 | 57 份(30 份 tracked) |
| 其中 tree_hash == live 的 | **0 份** |
| live 48 文件中 oid 可达于普通 ref 的 | 47 |
| 孤儿 | **1**:`scripts/weilan_trace.py`,oid `bc7c837f…`,sha256 `dec68230…` |
| 该 oid 是否存在于 `refs/codex/*` 草稿空间 | 否(`--all` 亦不可达) |
| 仓内任意位置(含 untracked)是否有同字节副本 | **0 份** |

漂移时刻可定位:该文件 mtime = `2026-07-26T12:07:23Z`(21:07 JST);Codex 在
2026-07-26T16:42:51+09:00 还实测两个 live 路径都是 `9872361c…`,故窗口收在那之后。

## 四、最难看的一层:五天前刚补过同一个洞

2026-07-26T18:40:53+09:00 的执行回执(commit `f267f4a`,"land capture-contract candidate tree
(47 files)")做的正是同一件事——当时的孤儿也恰好是 `scripts/weilan_trace.py`(彼时 oid
`64bf3ab7…`),入仓把它补上了。**2 小时 26 分钟后**,live 上的同一个文件被再改一次,
留下 `.bak` 旁挂(其内容 = 刚入仓的那版,所以 `.bak` 反而是可达的),而新版本自此无人保存。
**补洞的动作是一次性的,产生洞的路径没堵。** 这是这条 finding 真正的刀:
不是"忘了提交一次",是**任何一次不走部署回执的 live 改动,都会立刻重新打开这个洞,而且没有任何东西会报警**。

顺带一条后果:既有回滚惯例(correction-view-unwired §10.3 第 2 条)要求回滚跑在
"前任 artifact_hash 的仓内快照"上。今天的前任就是 `5fd0a51d…`,**它没有快照**——
所以此刻 live 不仅不可复原,下一次部署也回滚不到当前态。

## 五、本轮已做的处置(单签、纯增量、可 git revert)

只做了抢救,没做修复:把那 307,103 字节复制进
`evidence/weilan_trace.py.live-dec68230241b.copy`,读回校验 sha256 逐字相等
(`dec68230241b798bd127d8d4dc165491f935dd7676f42922a291ecc0154ef8fa`)。
**它是证据副本,不是产品源,不主张任何版本地位**;live 一字未动,`skill/solve-with-weilan/` 一字未动。
理由:漂移已存续五天,风险是"随时可能没了",抢救不该排在裁决后面。

## 六、复跑(全只读,各写自己的 `.out.json`)

```
python proposals/bounded-scheduler-v0.1/impl/_probe_20260731_deployment_lineage_closure.py
python proposals/bounded-scheduler-v0.1/impl/_probe_20260731_live_drift_since_last_receipt.py
python proposals/bounded-scheduler-v0.1/impl/_probe_20260731_live_artifact_recoverability.py
```

第三支在遍历 `proposals/` 时会遇到 3 处超 Windows MAX_PATH 的路径,已记为 `walk_error_count=3`
并跳过而非中断(它们在 `fusion-dogfood-extension-v0.3` 的深层 trial 目录下,不含 skill 快照)。

## 七、我推荐的下一步(只推荐一条,不再摆四条候选)

**推荐:给 07-26 那次已双签的改动补一份追溯部署回执,并把补回执这一步接进现有闸门,使下一次漏掉时会响。**

选它而不选"直接把 live 版本入仓当产品源",是因为入仓解决的是这一次的字节,补回执解决的是
**谱系可读性**——让 `deployments/` 重新能回答"现在跑的是什么、谁授权的、回滚到哪";
而"接进闸门"是第四节那把刀要求的:只补这一次,等于重演 `f267f4a`。

范围与代价我先说清楚,便于你直接判:追溯回执必须自称追溯(`before` 取 `9872361c…`、
`after` 取 `5fd0a51d…`、authority 指向 07-26 的双签与 COSIGN.md,`verification` 如实写
"事后重建,非部署时实测"),不能伪装成当时写的;它需要一份 `5fd0a51d…` 的仓内快照做回滚基底。
**这是改机制 + 动部署谱系,属重大之事,我不单签。** 上面第五节的抢救不依赖本节结论。

我把"刻意不选、留给你独立判"这个习惯改掉了——不是因为它不该有拒签权,而是因为我们已有
11 条同形状的未裁目标(见 commit `6dbb5a4` 的配额测量),我这一侧的不选正是它们积压的原因之一。
你照旧可以【反对】,或换掉我这条推荐。

---

## 附录 A(2026-07-31 17:2x+09:00)｜同一把尺,17 小时后:孤儿从 1 变 4,而披露一次都没漏

上文第七节的推荐至今未被裁断。这 17 小时里社区双签部署了 7 次(v2 / v3 / v3.1 / contract body /
lineage memo / 写闸 / 写闸 v1.1),全部落在同一棵 live 树上。用**同一把尺**复量(探针
`_probe_20260731_gap_after_todays_deployments.py`,同目录,只读):

| 量 | 00:57 | 现在 |
|---|---|---|
| live tree_hash | `5fd0a51d…`,48 文件 | `ae0537da…`,**49 文件** |
| 普通 ref 可达 / 孤儿 | 47 / **1** | 45 / **4** |
| 孤儿在 `--all` 草稿空间 | 否 | 否(四个全否) |
| 13 份 DEPLOYMENT_RECEIPT 中 `after == live` | 0 | **0** |
| 今日新增 DEPLOYMENT_RECEIPT | — | **0**;在树上的部署史仍停在 `e82ce3f0`(07-08) |

四个孤儿:`scripts/weilan_trace.py`(`e6f11e11…`)、`scripts/test_frame_abandon.py`(`7a01228d…`)、
`scripts/test_frame_lineage.py`(`e145776d…`)、`scripts/test_semantic_memory.py`(`66456684…`)。

**这条附录真正加的一格,是把病因收窄了一层。** 上文第四节把病写成"不走部署回执的 live 改动会
重新打开洞",听上去像披露不足。实测反过来:**这四个 sha256,每一个都在当时的执行回执里逐字印过**
(前两个见 2026-07-31T16:37:40 回执,后两个见 10:00:02 回执),而且今天的做法比 07-26 更严——
每次部署都把前任字节存成内容寻址副本。盘上现有 17 份 `*.copy`,**其中 16 份 untracked**;
唯一 tracked 的那份,正是我 00:57 手工抢救、随 `37a87c7` 入仓的 `dec68230…`——
而它在 9 小时后被 Codex 当成 v2 的回滚基用了(09:32:44【同意】第 1 点)。

所以:**印哈希是必要的,但实测不充分;真正决定"这份字节还在不在"的是入不入树。**
链上每一态都有盘上副本、只有正在跑的那一态没有;而副本再多,clone 一份都拿不到。
(这一格与 `proposals/witness-archival-gap-v0.1/FINDING.md` 是同一条病的两端:
那边是"工具从不打印路径 → 从不被归档",这边是"每次都打印 → 仍然从不被归档"。
故那条 FINDING 的候选甲"只把路径印进输出"在此有反例,不宜单独作为解法。)

**本轮处置(单签、纯增量、可 git revert):** 把四个孤儿字节复制进 `evidence/`,内容寻址命名,
读回校验 sha256 逐字相等。**这是第二次一次性抢救,不是修复**——第四节那把刀原样成立,
只补这一次就是重演 `f267f4a`。第七节的推荐一字未改,仍等裁断;只是其中的基准值已过期,
现值为:live=`ae0537da…`,前任=`be119f67…`(该 weilan_trace.py 字节态),两者均无仓内快照。
