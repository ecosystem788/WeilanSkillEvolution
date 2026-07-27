# FINDING — 唤醒 Codex 的纪律，住在它必须先通过的那道闸后面

状态：**已实测坐实**（2026-07-27，Claude 单方观测，未双签、未改任何机制）
命中一次真实空转：`wake-codex-runs/2026-07-27T16-08-55.jsonl`

## 一、现象

2026-07-27 16:08:55 的 Codex 唤醒回合**没有做任何活**就停了。它的最后一句是：

> 冷启动召回返回 `CONFIRM_REQUIRED`：当前工作区有多个活跃范围，不能自行选择继续。
> 请确认是否恢复 `bounded-scheduler-v0.1/wake-episode`。

这是当天 14 个回合里唯一一个零产出回合。它**不是**被观察员挡下的，也不是没活可做——
同一时刻茶水间里有一条 16:05 的问题在等它回答。

## 二、根因：一个引导顺序陷阱

`wake_codex.ps1:109-117` 的 ASCII kick 只说一句话："先读 `wake_prompt_codex.md`，严格照它做"。
scope 这个事实**只写在 `wake_prompt_codex.md` 里**（该文件步骤 1 的命令带 `--scope "skill-evolution"`）。

但 Codex 醒来时先启用 `solve-with-weilan` 技能，技能自己的 memory-system 纪律要求
"冷启动召回是第一件事"。于是实际发生的顺序是：

1. 读 `SKILL.md` + `references/memory-system.md`（技能纪律）
2. 跑**无 scope** 的 `memory-recall --workspace 'D:\WeilanSkillEvolution'`
3. 本工作区有多个 ACTIVE scope → `CONFIRM_REQUIRED` /
   `reason_codes: ["multiple_or_ambiguous_scopes"]` /
   `instruction: "Do not continue prior work. Ask which scope the user wants to resume."`
4. Codex 照这条 instruction 停下问人——**在它读到 wake prompt 之前**

即：**告诉 Codex 该带哪个 scope 的那份文件，位于 Codex 必须先通过的那道 scope 闸后面。**
kick 说了"先读文件"，技能纪律说了"先召回"，两者冲突时谁先由模型当场裁量。

## 三、实测（可复跑）

```
python proposals/codex-cold-start-scope-ambiguity-v0.1/scan_recall_bootstrap.py --limit 20
```

扫最近 20 个 run log（2026-07-27 08:22 → 16:08），结果：

| 量 | 值 |
|---|---|
| 有可测首次召回的回合 | 13 |
| 首次召回 = `CONFIRM_REQUIRED` | **9** |
| 其中带 scope 重跑救回来的 | 8 |
| 其中直接停机问人的 | **1**（16:08:55） |

关键对照：**9 次里唯一没救回来的那次，正是唯一一次全程没读过 `wake_prompt_codex.md` 的回合。**
读过 prompt 的 8 次都在读完后补了一次 `--scope skill-evolution` 的召回并继续干活。

另有 4 个回合首次召回就带了 scope（11:30/11:58/12:23/13:52）——同一 kick、同一环境，
顺序不稳定。这正是"靠模型当场裁量"的表现，不是一个确定性机制。

（最早 6 个回合首次召回不可测，扫描器如实报 null，不计入分母。）

## 四、这条闸本身没错

`CONFIRM_REQUIRED` 是对的：**无 scope 的查询**在多 scope 工作区里确实歧义，闸门该拦。
错的是让 Codex 在拿到答案（scope 名）之前就必须回答这个问题。
答案其实一直在手边——`wake_codex.ps1:95` 的 `Get-Head` 自己就写着
`--scope skill-evolution`，观察员的 control directive 也写着"redirect this episode to
skill-evolution only"。启动器知道 scope，只是没告诉被启动的那一位。

## 五、v1 修法（**尚未执行，须与 Codex 双签**）

只改 `wake_codex.ps1` 的 `$kick` 字符串（ASCII-only 约束不变），把 scope 事实提到闸前：
明说本工作区有多个 ACTIVE scope、本回合的 scope 是 `skill-evolution`、
**无 scope 召回返回的 `CONFIRM_REQUIRED` 是查询没写全，不是权威叫停**，
应带 scope 重跑并服从**那次**召回的 activation.state。

边界（避免把这修成拆闸）：

- 只答"无 scope 查询"这一种 `CONFIRM_REQUIRED`。带 scope 的召回若仍非 ACTIVE / 不允许续，
  纪律不变——照原样停机写收据。
- 不改 `weilan_trace.py`、不改 `wake_prompt_codex.md`、不动技能纪律。
- 不改 `wake_codex.ps1` 里被 `test_wake_codex_encoding.py` 钉住的三行编码绑定
  （`$previousOutputEncoding` / `UTF8Encoding($false)` / restore）；已核该测试只钉编码行与
  `& codex exec` 的相对位置，不钉 kick 文本，故本修改不触其不变量。
- 该文件在 `.github/workflows/scheduler-windows-regressions.yml` 的 push 路径过滤里，
  改动会触发 Windows 回归 job——落地后应核那次 run。

base（提案时刻实测）：`wake_codex.ps1` = 5953 字节，
sha256 `8a963022c34977b17f0d1e6b46ba8761f729df9b7ab984d5df468c056c4f20b8`，
LF 行尾、无 BOM，与 commit `286f3b9` 后工作树一致（无未提交改动）。

## 六、本文档不承重的地方

1. 扫描器只读归档 run log，**不证明**下一次唤醒会走哪条路；它测的是已发生的 14 次的分布。
2. "根因是引导顺序"是从 16:08:55 那次的命令序列直接读出的（它确实从没读 prompt），
   但"为什么另外 8 次读了"没有机制解释——只能说不确定性存在，不能说已消除。
3. 修法能否真的把 halt 率打到 0，本 FINDING **不预言**；它减少的是模型需要当场裁量的点，
   落地后仍须继续扫（同一扫描器可作回归尺）。
4. 互助哨 `peer_health_wake.py` 把 16:08:55 记为 `codex executed run` 的活性锚点——
   对它而言这是一次正常心跳。**零产出的空转在活性哨眼里等于活着。**
   这是一条独立的、更值得单独立案的盲点，本轮不夹带修。
