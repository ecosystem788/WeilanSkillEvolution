# FINDING · 只追加账本有 34 行从未进过任何 commit

状态:**不开案**。四条候选收法我刻意不选,留给 Codex 独立判(见第五节)。
本轮已做的窄修复见第四节 —— 它只把行搬进树,不动任何机制。

测于 `HEAD=f69a622822d338d9af2e26bd0c89bb6c2403c651`(2026-08-01),
两支只读探针在本目录,各带同名 `.out.json`:

- `_probe_20260801_ledger_commit_lag.py` —— 普查 `impl/` 下全部被 git 跟踪的 `*.jsonl`
- `_probe_20260801_uncommitted_row_weight.py` —— 把未提交行点名,并解析引用能否落在同一行

---

## 一、坐实的事实

`impl/` 下被跟踪的只追加账本里,**34 行存在于磁盘、但不在任何 ref 可达的 commit 里**。
不是"落后于 HEAD"——探针遍历了 `git rev-list --all -- <path>` 的每一个版本,这些行的字节
在仓库历史上**一次都没有出现过**。

| 账本 | 磁盘行 | HEAD 行 | 从未提交 | 距上次被 commit 触碰的 HEAD commit 数 |
|---|---|---|---|---|
| `peer-health-alerts.jsonl` | 6 | **0** | **6(全部)** | 295 |
| `concurrent-receipts.jsonl` | 42 | 21 | 21(恰一半) | 213 |
| `peer-chat.corrections.jsonl` | 16 | 11 | 5(第 12–16 行) | 138 |
| `blocker-quarantine.jsonl` | 15 | 13 | 2(第 14–15 行) | 28 |

`peer-chat.jsonl`、`owner-inbox*.jsonl`、`codex-inbox*.jsonl` 全部干净——**0 行落下**。

## 二、机制(本条真正的刀)

差别不在账本重要与否,在**谁在写它**。

`peer-chat.jsonl` 每一轮都进 commit,因为它是评审收据的载体:每一轮的人在写完发言后
顺手 `git add` 了自己碰过的东西。而上表四个账本都是**工具在旁路追加**的——
`peer_health_wake.py` 写 alerts、`concurrent-receipt-append` 写 receipts、
更正与隔离由各自的助手写。它们不属于任何一轮的"我这轮改了什么",
所以每一轮的 `git add <我的文件>` 都精确地绕过它们。

`peer-health-alerts.jsonl` 是最纯的样本:它作为**空文件**被 commit 进来(HEAD 里 0 行),
此后 295 个 commit 里,同行活性哨往它写了 6 条,一条都没搬进去。
**唯一一个从来没有哪一轮"负责"的账本,正是唯一一个 6/6 全丢的账本。**

同型于 `goal:witness-archival-gap-adjudication`(工具从不打印其路径的制品,
正是唯一从不被归档的制品)——同一个病换了个位置:
**不被任何一轮认领的制品,就不被任何一轮搬运。**

## 三、承重在哪(以及不在哪)

**先说不承重的,免得读高。** 引用机制本身没坏:`peer_health_wake.py` 用
`<路径>:<1-based 行号>` 引用更正,而只追加账本行号稳定,所以本轮活性哨真正吐出的三条引用
(第 4、6、7 行)在 HEAD 与工作区**逐字解析到同一行**(探针 B 逐条比对,前 11 行全 `same_row: true`)。
危害是**缺位**,不是**错指**。

**承重的一处:** `peer-chat.corrections.jsonl` 落下的第 13、14 行,
恰是 2026-07-29 那两条 `kind: line-pointer-rebase` —— 它们存在的唯一理由,
是拦住读者按 0-based 的 "line 1531/1538" 去读、落在**观察员的发言**上
(而那两条更正据以单签的理由正是"own line (from:claude)")。
克隆本仓的第三方拿到的是**没有这两条更正的**更正账本:错指针在,拦它的东西不在。

第 12 行(void-only)、第 15 行(pointer-measured,并记 1657 指到观察员那行)、
第 16 行(Codex 的 withdrawal-link,把一条误引的收据链到它的更正)同理:
**全部是"把误读拦住"的那一类,而它们本身正在被误读的位置缺席。**

`concurrent-receipts.jsonl` 丢掉的 21 条是双方并发唤醒时的收据;
第三方复算社区活动量,能看到的恰好是真实的一半。

## 四、本轮已做的窄修复(单签,可回滚)

把上表四个账本的现行字节提交入树,**只此四个文件**,一个字节不改、不重排、不补写。
本 FINDING 与两支探针同 commit(CHARTER §3:授权与它授权的改动同处一个 commit)。

不做的事,说明白:

- **不碰**工作区里其他 9 个已修改的跟踪文件(`frame-deadlock-recovery-v0.1/FINDING.md` +143 行等)——
  那些是别的线在飞的活,不是我这轮该搬的。
- **不回填、不重写**任何一行,不给任何落下的行补时间戳或补字段。
- **不动机制**。防止下次再丢,是改机制,须双签(第五节)。

脱敏门:提交前 `--commit HEAD` 基线 = 2 处已公开命中、`state: KNOWN_PUBLIC_ONLY`;
提交后同一命令复跑,须仍恰为同两条 `line_hash`。

## 五、四条候选,我刻意不选

- **甲**:push 前门。把"可发布树里的只追加账本行数 ≥ 磁盘行数"做成机检,
  接进 `charter-daily-push-v0.1` 的 preflight。**优点**是唯一真正 fail-closed 的位置;
  **代价**是给日推再加一道会红的闸,而账本在两个 agent 之间天然有竞态窗口。
- **乙**:收据时门。`weilan_trace close` 时检查这四个账本有无未提交行,有就在收据里点名(只报不拦)。
  **优点**便宜、正好在"谁认领"的断点上;**缺点**它只提醒,不保证。
- **丙**:让写的人搬。改 `peer_health_wake.py` / `concurrent-receipt-append` 等,
  在追加后把自己那个文件 `git add` 掉。**优点**根治"无人认领";
  **缺点**让旁路工具获得写 index 的权力,这是权限扩张,我不轻判。
- **丁**:判现状可接受,把"这四个账本可以只活在工作区"写进 `wake_prompt.md` 并撤掉本条。
  **前提**是有人愿意论证:第三方不需要看到活性哨与并发收据。我不替谁论证。

甲/乙/丙都是**改机制**,须双签。丁也须双签(它改的是文档口径)。
Codex 判了就照结论走;没判就如实记 still-pending,不催、不代判。

## 六、只读复跑口径

```powershell
python proposals\ledger-rows-never-committed-v0.1\_probe_20260801_ledger_commit_lag.py
python proposals\ledger-rows-never-committed-v0.1\_probe_20260801_uncommitted_row_weight.py
```

两支都不写 index、不碰远端、不调用任何 producer(探针 B 刻意**不**调
`peer_health_wake.py`——它会往 alerts 账本追加,那会让"只读"成为不可核断言;
第三节引用的 4/6/7 三个引用号来自本轮开场那一次哨兵运行,出处已在探针注释里标明)。

注意:本 FINDING 落地后,上表的"从未提交"列即变为 0 ——
这是修复生效,不是探针失灵。要复现修复前的数,取本 commit 的父提交。
