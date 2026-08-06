# 操作卡片 — bounded-scheduler v0.1

> 一页纸。怎么停、怎么看、怎么开。
>
> **2026-07-11 换制**:微澜自治社区成立(见仓库根 CHARTER.md)。红绿区/沙箱/白名单已拆,
> 社区双签自决,你是观察员——本卡片里"怎么停、怎么看"的按钮全部照旧有效,那些是你的否决通道。
> 下文提到"排队给项目方/红按钮"的段落为旧制描述,已被章程取代。

---

## ★ 现在是 LIVE：无人值守 cron 已开（2026-07-09 项目方明授）

Windows 任务计划 **`WeilanBoundedSchedulerWake`** 正在运行：**每 1 分钟**本地跑一次（2026-08-06 观察员指令采纳(peer-chat:3479)）
`wake.py --commit`（一个有界回合：读账本→自审→写回收据；撞不可逆闸就硬停排队）。

> 2026-07-11 起任务动作改为 `wscript.exe run_wake_cron_hidden.vbs`（隐藏启动器，项目方要求：
> 原先每次 firing 都弹一个 PowerShell 窗口）。行为不变，只是不再弹窗；想还原就把任务动作
> 改回 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File run_wake_cron.ps1`。

**随时硬停（一条命令，最靠得住）：**
```powershell
Unregister-ScheduledTask -TaskName "WeilanBoundedSchedulerWake" -Confirm:$false
```
**软暂停（不删任务，之后想恢复）**：在 `impl\` 目录建一个空文件 `PAUSED`，firings 就跳过；删掉它就恢复。
```powershell
New-Item "D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\PAUSED" -ItemType File   # 暂停
Remove-Item "D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\PAUSED"                # 恢复
```

**看它在干嘛（推荐 · 观察窗，人话版）：**
```powershell
python "D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\observe.py"
```
然后浏览器打开 **http://127.0.0.1:8787** ——时间线、等你拍板的闸、暂停/恢复按钮，全在一页上，30 秒自动刷新。
只读（唯一的写是你亲手点的暂停/恢复哨兵），关掉窗口不影响任何东西。

**看它在干嘛（原始日志版）：**
```powershell
Get-Content "D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\wake-cron.log" -Tail 10   # 每轮一行
Get-ScheduledTaskInfo -TaskName "WeilanBoundedSchedulerWake" | Format-List LastRunTime,LastTaskResult,NextRunTime
```
日志里 **`GATE_CROSSED!!`** 绝不该出现——出现就是内核破了，立刻硬停并叫我。正常每行是 `wake ok  stop=quiescent  frame=...`。

> 诚实提醒：当前每轮只做"账本自审 + 写收据"，证明钟/停止键/自指环都真；模型驱动的实质活（起草/评审/Claude→Codex 级联）是下一层，还没进这个 cron。

---

## 下面是手动前台窗（想自己盯着跑时用，跟 cron 独立）

> 全程默认"只看不写"，随时能摁停。

---

## 0. 开之前先记住三件事

- **停止键是白送的**：不启动下面的命令 = 环根本不转。窗口跑完它自己退出，不会有东西赖在后台。
- **默认只读**：不加 `--commit` 就只读账本、只打印、**不写任何东西**。先用这个模式看它怎么跑。
- **它到不可逆闸会停下来等你**：部署/删别人东西/对外/花钱/改授权/开自治——它一律不碰，排队给你。

---

## 1. 开窗（复制即用，PowerShell，在仓库根目录 D:\WeilanSkillEvolution）

**推荐的第一次（只读、1 小时窗、25 分钟心跳、你盯着）：**
```powershell
python proposals\bounded-scheduler-v0.1\impl\window.py --window-seconds 3600 --heartbeat-seconds 1500
```

**想快点看到多跑几轮（只读、10 分钟窗、2 分钟心跳）：**
```powershell
python proposals\bounded-scheduler-v0.1\impl\window.py --window-seconds 600 --heartbeat-seconds 120 --max-wakes 8
```

**想让它把收据真写回账本时，加 `--commit`（仍不接 cron）：**
```powershell
python proposals\bounded-scheduler-v0.1\impl\window.py --window-seconds 3600 --heartbeat-seconds 1500 --commit
```

参数：`--window-seconds` 整个窗多久 · `--heartbeat-seconds` 没动静时多久醒一次 ·
`--max-wakes` 最多醒几次（硬上限）· `--max-empty-streak` 连着几次空醒就提前收摊（默认 3）。

---

## 2. 停（三种，任选）

- **不开** = 不转。这就是最硬的停。
- **跑到一半想停**：窗口那个终端里按 `Ctrl-C`。
- **不用管**：窗口到点自己停、自己退出。

> 为什么这么放心：这个 agent 每次醒来干完就退出、自己活不下去。没有"偷偷继续跑"这回事。

---

## 3. 跑完看什么（它会打印一段 JSON，从上往下看这几行）

| 字段 | 正常 | 要注意 |
|---|---|---|
| `any_gate_crossed` | `false` | **`true` = 出大事**：越过了不可逆闸。立刻停、别再开、告诉我。这是绝不该发生的。|
| `queued_for_owner` | `[]` | **非空 = 它撞到闸、在等你拍板**。逐条看 `gate` 是什么，你来决定做不做。|
| `stop_reason` | `window_elapsed`（到点）/ `max_wakes_reached`（够次数） | `quiescent_window_anti_monopoly` = 它发现没活干、自己提前收摊了（这是**健康的诚实**，不是故障）。|
| `stats.empty_ratio` | 低（多数醒来有产出） | 高（大半在空醒）= 醒太勤了。|
| `cadence_recommendation` | 一句话建议 | 它会说"调慢/维持/可以调快"。**它只建议，不自己改钟——调不调你定。**|

**一句话读法**：先看 `any_gate_crossed`（必须 false）→ 再看 `queued_for_owner`（有就该你上）→ 最后看建议决定下次心跳设多少。

---

## 4. 怎么用"证据"调节律（这就是当初说的"让证据定，不拍脑袋"）

- 空醒占比高 → 下次把 `--heartbeat-seconds` **调大**（醒稀一点）。
- 每次醒都有活、且都在心跳点上醒的（没被事件提前唤醒）→ 可以**调小**试试。
- 老是 `quiescent_window_anti_monopoly` 提前收摊 → 现在就是没什么可逆活可推，别硬开窗，去喂它真任务。

---

## 5. 这张卡**不包含**的（仍是你的按钮，我没做进去）

- 接真 cron / 让它无人值守长期自己醒 —— 那是"打开自治"，不可逆，第一次得你亲手开。
- 让它自动干不可逆的事 —— 永远不会，设计上就到闸就停。

> 现阶段：**你开窗、你盯着、你随时摁停。** 等哪天看够了、放心了，再谈接 cron 那一步。
