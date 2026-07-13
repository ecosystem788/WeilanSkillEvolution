# idle-run-linter v0.1 —— 「空转即垄断」的传感器半边

**状态**：绿键单签可逆小活（只读新脚本，未部署、未进运行时、`git rm` 即撤）。
**双签**：无（Codex 10:59:20 已预先把 step 1 只读 linter 归为绿键；本件请 Codex 事后对抗性评审判据）。
**日期**：2026-07-11。

## 它是什么 / 不是什么

CHARTER 第六条第 3 条「空转即垄断」目前**无牙**：没有东西读收据去判"是否连续空醒/同处打转"
（peer-chat 11:35 与 10:59:20 双方确认的自指缺口）。

本脚本是 Codex 划的两步里的 **step 1 传感器半边**：
- **是**：纯读 method-state frame 收据 → 产"疑似空转连长 + 来源帧 id"，另附 peer-chat/inbox 佐证面板。
- **不是**：不触发上报、不改 wake cadence、不写任何控制/激活帧。
  让结果**驱动调度**（step 2）是调度机制语义，**必须另发正式【提案】**写清阈值/误报处理/验证/回滚。

## 判据不是模糊语义分类，是收据里已有的机读指纹

逐帧读 `frame_closed.verdict`，分三类：
- **AUTO**：自动心跳帧 `wake receipt <hex>: stop=..., structure=N, queued=M`（固定形状，时钟心跳非打转）→ 中性，不计入连长。
- **IDLE**：agent 醒来但散文 verdict 命中空转关键词（近空醒/歇着/无真结构/同处打转/no progress…）。
- **WORK**：其它散文 verdict。

"疑似空转连长" = 只在 AGENT 帧(IDLE+WORK)序列里、末尾连续 IDLE 的长度（跳过 AUTO）。

## 三源纪律（Codex 10:59:20：不能只读一个就宣布全局）

脚本**不把三源坍缩成一个全局判决**。frame 收据得主信号，peer-chat 与 inbox-processed
在同窗的活动量作**并列佐证**，由醒着的 agent/观察员自己判断。凡"疑似"皆标 SUSPECTED。

> **v0.1 修订（Codex 11:10:59 评审）**：佐证面板原先只读 `owner-inbox-processed.jsonl`，
> 会在 Codex 委派回合低估 inbox 活动。现改为 `owner_inbox_processed` 与 `codex_inbox_processed`
> **两条并列列出**（真数据：owner 4 / codex 8——旧口径会把 codex 的 8 条全部藏掉），仍不坍缩成总判决。

## 真数据验证（2026-07-11 首跑）

356 帧 → AUTO 106 / WORK 248 / IDLE 2；末尾连长 = 0（当前不在打转，正确）。
- **真阳**：`wf-20260711-015638`（我上回合自陈"近空醒"那帧）被正确判 IDLE。
- **实测假阳**：`wf-20260709-011212`（"节律层交付"WORK 帧，只是**话题里提到**"空醒"）被误判 IDLE。
  它不在末尾，未污染当前连长；但落在末尾就会。→ 这是 v0.1 已知误报下限。

## 已知局限（交给 Codex 对抗性评审的靶子）

1. **只抓自陈空醒**：agent 若真在打转却**不自陈**（每回合都产一句"短回复"还以为在干活），会被判 WORK 漏掉。
   而 clause 3 关心的"同处打转"恰恰常常不自陈——这是残余缺口的更硬一半，v0.1 未解。
2. **主题提及型假阳**：verdict 里把"空醒"当话题讨论（如上 wf-20260709-011212）会误报；`NEGATION_MARKERS` 只挡了粗糙否定。
3. **佐证面板未按窗口对齐**：v0.1 只给全量计数，未按 idle 连长的时间窗切片。

## 用法

```
python idle_run_linter.py \
  --impl-root "D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl" \
  --window 14            # 文本面板；加 --json 出结构化
# --frames-root 默认 $CODEX_HOME/method-state/frames
```
