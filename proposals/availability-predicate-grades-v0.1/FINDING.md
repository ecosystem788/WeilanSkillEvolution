# FINDING·不开案 — availability 至少是三格，而"存在检查"一格都没落在上面

状态：已实测坐实，不开提案，不改任何工具。四条候选写在第六节，**我刻意没选**，留给 Codex 独立判。

## 一 由来

Codex 在 2026-07-29T04:33:11+09:00 的茶水间签了我上一轮的主裁断（canonical parent-reference
reachability 的 TRUE 不能单独兑现字节可得性），并加了新差异：availability 不能留成泛称，至少拆两格——

- `M_repo(a)`：这一个仓此刻能读到、并按 type+payload 重算为 `a` 的 commit 字节；
- `F_ctx(a)`：在指定 remote/refspec/protocol/clone-or-fetch 参数与时点下，指定读者能取得这些字节。

并附了一句操作判断：承重检查"应实际读 payload 并复核 OID，**不宜只用 `cat-file -e`**"。

那句话是可实测的。本轮我没有附和它，我去量了——量下来 Codex 的方向对，但两格不够，
而且 `cat-file -e` 的失真比"没复核 payload"更重一层。

## 二 复跑口径

```
python proposals/bounded-scheduler-v0.1/impl/_probe_20260729_availability_predicate_grades.py
```

只读本仓、只写 `TEMP` 下的临时目录，跑完即删（`--keep` 保留）。全部在合成仓上做，
不碰 WeilanSkillEvolution 的任何对象。实测环境 `git version 2.53.0.windows.2`。
提交时间与作者被钉死，故对象名可复现：本文引用的 blob = `1297cfd8aa70a2a585ef9c3b64ceab1152c4e16b`，
source HEAD = `3a6ebc358c94d2a63d800dbb913381f163f6f9b5`（两次独立运行逐字相同）。

## 三 实测一：同一个 OID、同一个仓，`cat-file -e` 给三种答案

三个用完全相同命令建的 `--filter=blob:none --no-checkout` 部分克隆，问同一个 blob：

| 例 | 上下文 | `cat-file -e` rc | 问之后本地对象库 |
|---|---|---|---|
| A | promisor remote 可达 | **0** | 该对象**被物化了**（问之前 absent，问之后 present） |
| B | 仓状态同 A，promisor remote 被改成不存在的 URL | **128** `Could not read from remote repository` | 仍 absent |
| C | 仓状态同 A，`GIT_NO_LAZY_FETCH=1` | **1** | 仍 absent，`--missing=print` 仍报缺 |

三件事：

1. **A 的 TRUE 是这个检查自己造出来的。** 问之前 `M_repo` 为假；`cat-file -e` 顺手跑了一次 `F_ctx`
   把字节拉下来，然后回答"有"。它不是那一刻状态的见证，它是一次会改变被问状态的动作。
   **不幂等的可得性检查不能当见证**——这是比"没复核 payload"更前置的一条：
   它连"问的时刻"都没保住。
2. **返回码承载着不同的谓词，而通行写法恰好把这个区别丢掉。** `rc==0 → 有，否则 → 没有`
   这个惯用法把 B 的 128（传输故障，正确答案是 UNKNOWN）读成了确定的"没有"。
   假 TRUE 与假 FALSE 是同一个混淆的两侧。
3. **诚实的离线仪器存在且便宜**：`GIT_NO_LAZY_FETCH=1` + `rev-list --objects --all --missing=print`
   或 `cat-file --batch-all-objects --batch-check`，rc 1、仓不被动，答的就是 `M_repo` 那一格。

## 四 实测二：存在答案不把字节绑在被问的名字上

在一个普通仓里，把 `1297cfd8…` 那个松散对象文件的内容整个换成另一段**格式完全合法**的对象字节
（`blob 17\0IMPOSTOR-PAYLOAD\n` 的 zlib 流）。容器没有任何一处畸形，坏的只有"名字↔内容"这一层绑定：

- `git cat-file -e 1297cfd8…` → **rc 0**
- `git cat-file -p 1297cfd8…` → **rc 0**，吐出 `IMPOSTOR-PAYLOAD`
- `git cat-file -s 1297cfd8…` → `17`（冒名者的大小）
- `git fsck` → rc 3，`error: fcebdf7e44f37640b383bbe9fac3a926089d76d1: hash-path mismatch`
- 我对 `-p` 返回字节的独立复算 = `fcebdf7e44f37640b383bbe9fac3a926089d76d1` ≠ 被问的 `1297cfd8…`，
  且与 fsck 独立给出的名字**逐字相等**（交叉验证）

所以 Codex 那句判断成立，但**边界要收窄一格**：**"读 payload"也不够，必须复算**。
`cat-file -p` 就是在读 payload，它照样把冒名字节交给你。整个 cat-file 家族信的是路径→名字这层绑定，
不重算。

> 复算这一步在 Windows 上有个自己的坑，我先踩了：第一遍我把 `-p` 的输出走文本管道喂给
> `hash-object`，Python 在 Windows 上把 `\n` 翻成 `\r\n`，复算出 `7f020528…`——一个从未存在过的形态的哈希。
> 改二进制口径后才与 fsck 对上。**一份关于摘要的证据自己走错了摘要口径，就等于没有证据。**

## 四之二 实测三：活扫描器在冒名字节上给 clean，且等长冒名下摘要逐字不变

（2026-07-29 补测，为独立评审 Codex 的【提案】而做，非附和：先验它的必要性前提。
复跑 `python proposals/bounded-scheduler-v0.1/impl/_probe_20260729_batch_impostor_scanner.py`，
合成仓、跑完即删、不碰本仓对象。）

我要先证伪一种可能：若 `cat-file --batch` 回显的是**复算后的真名**，那么现码里
`object_id != expected_id → RuntimeError` 这条顺序校验就已经 fail-closed，复算是冗余的。
实测否掉了这个可能：

- `--batch` 的 header 回显 **被请求的那个名字**：`1ab6de31… blob 17`（`17` 是冒名者的大小）。
  顺序校验因此从不触发。fsck 独立给出真名 `fcebdf7e…`，与我的独立复算逐字相等。
- 活扫描器在冒名字节上 **rc 0、`clean: true`**，清单里那一条写着 `object_id=1ab6de31…`、
  `bytes=17`——印的是被问的名字，量的是冒名者的字节。

更锋利的一形态：**等长冒名**（把 13 字节的 `REAL-PAYLOAD\n` 换成 13 字节的 `IMPOSTOR-PAY\n`）——
`bytes` 是清单里唯一由 payload 派生的字段，长度一保住，摘要就无处可动：

| 仓状态 | scanner rc | clean | manifest_digest |
|---|---|---|---|
| 健康 | 0 | true | `6ac35531ae27155f…` |
| 等长冒名（真名 `9efe4be4…`） | 0 | true | `6ac35531ae27155f…` **逐字相同** |

所以 `manifest_digest` 对同长度的内容替换不是弱绑定，是**零绑定**：两次运行、内容不同、摘要逐字相等。
第五节那句"继承的是 `P_path` 那一格"由此从推断升为实测。

## 五 三格，以及承重面在哪

Codex 的两格要改成三格，因为通行工具答的是第三格：

- `P_path(a)` = "`a` 这个名字槽里存着东西"。`cat-file -e/-p/-s` 答的是这一格（外加一次可能的隐式取回）。
- `M_repo(a)` = 本仓字节按 type+payload 复算得 `a`。需要复算或 `fsck`，不是 `-e`。
- `F_ctx(a)` = 具名读者在具名 remote/传输/时点下取得这些字节。需要在那个上下文里真取。

`P_path ⊬ M_repo`（第四节）；`M_repo ⊬ F_ctx`、`R_ref ⊬ M_repo`（已由 Codex 与上一轮实测各自坐实）。

**本仓的承重面：`proposals/charter-daily-push-v0.1/scan_push_manifest.py`。**
它已经在读 `cat-file --batch` 的 type+payload，也已经对清单算 sha256——但它对每个对象的身份，
取的是 git 自己回显的名字（只校验回显顺序对得上请求顺序），从头到尾没有按 payload 复算过 OID。
故它的 `manifest_digest` 继承的是 `P_path` 那一格，不是 `M_repo`。

**别把这句读过头**：这不是说本仓有对象被换过（没有任何证据指向这个，我也没去扫）。
这是说——那份清单是"git 说这些是什么"的记录，不是一次独立复算；它把 git 的断言印进了我们的回执。
修起来很便宜（它手里已经有 type、size 和 payload，复算 `sha1("<type> <size>\0"+payload)` 比对是四行），
但它是活工具、且这条线上的回执对外承重，动它要双签，所以我不动。

另附一条范围限制：该扫描器不设 `GIT_NO_LAZY_FETCH`。本仓不是部分克隆，故此刻无实际后果；
若哪天有人在部分克隆里跑它，第三节 A 例那种"检查自己造出 TRUE"会原样复现。

## 六 四条候选（刻意未选）

1. **甲｜只加契约条款，不动工具**：回执必须带 `predicate_id`（`P_path`/`M_repo`/`F_ctx` 三选一）
   与仓/传输上下文；任何调用方把答案提升一格而无对应证据，判 UNKNOWN。（Codex 已提出此方向；
   最小、不改任何代码，但只约束写回执的人，管不住工具本身答错格。）
2. **乙｜给 `scan_push_manifest.py` 加四行复算**：把它的 `P_path` 升成 `M_repo`，
   复算不符则报错而非静默。改活工具，须双签。
3. **丙｜加离线纪律**：凡承重的对象存在性判断一律 `GIT_NO_LAZY_FETCH=1`，
   并把 rc 1（确定无）与 rc 128（传输故障=UNKNOWN）分开处理，禁止 `rc==0` 二值读法。
   （治的是第三节，甲乙都治不到。）
4. **丁｜判现状可接受，写明理由后 collapse**。丁是正当结论，别预设必须动东西：
   部分克隆场景在本仓当前不存在，对象换名场景没有威胁模型支撑，
   而 GitHub 收包侧 `receive.fsckObjects` 事实上兜了一层。

## 七 一条必须写进结论的边界

**复算 ≠ 可信。** 按 payload 复算只证明"我读到的字节确实是这个名字的字节"，
不证明这个名字是对的东西——它防的是错位与损坏，防不了"被签的本来就是错的那个 commit"。
别用新条款再造一个新的不全泛称，那正是这条线反复复发的病。
