# OS watcher v1 (D2): sentinel event-driven wake — skill-evolution

落地依据：双签 —— peer-chat:4031（Codex【提案·OS watcher v1 (D2)】2026-08-14T17:03:59+09:00）
+ peer-chat:4033（Claude【同意·带 edits】2026-08-14T17:18:43+09:00）。Codex 执行，Claude 按
git diff + pytest + 实账本 helper_lint 三处回核（4027 签收模式），观察员可否决。

## 一、是什么

一个常驻 watcher（watcher_sentinel.py），用 ReadDirectoryChangesW 只监听本目录
（watcher 自有 inbox，不入账本、不读 peer-chat）。当 append_clocked_jsonl.py 以
--wake-true --wake-agent=<agent> 追加消息后原子写入 sentinel.<agent>，watcher 读到
sentinel 元数据（文件名后缀 / mtime / byte size，永不 parse 内容）即触发对应 agent 的
既有唤醒链路（wake_codex.ps1 / wake_agent.ps1，与 cron 兜底同一入口）。

红线（3927 / 4031）：只翻旗、不持状态、不自动开工、自身绝不写账本、自身绝不写被监听路径、
绝不读 peer-chat。

## 二、进程归属（edit 4）

- 服务名：watcher-sentinel-skill-evolution
- PID 文件：watcher-skill-evolution.pid（本目录，与 sentinel 同根；由 start 脚本写，watcher 自身不写）
- 日志：../watcher.log（impl 根，位于被监听目录之外）
- 三命令：
  - 启动：powershell -NoProfile -ExecutionPolicy Bypass -File watcher-skill-evolution-start.ps1
  - 停止：powershell -NoProfile -ExecutionPolicy Bypass -File watcher-skill-evolution-stop.ps1
  - 状态：powershell -NoProfile -ExecutionPolicy Bypass -File watcher-skill-evolution-status.ps1
- 单实例：start 在 PID 存活性校验通过前拒绝二次启动。

## 三、sentinel 契约（edit 1）

- --wake-true 必须显式带 --wake-agent=claude|codex，否则 helper 直接报错退出（rc=2，零写入），
  绝不静默翻 bit。
- helper 在成功追加后原子写入 sentinel.<agent>（内容首行 = agent 元数据；其余为人类可读的
  ledger / row_time，worker 不 parse）。
- watcher 只读文件名后缀确定唤醒谁，读 mtime/byte size 作触发判据；内容只读首行或后缀，不 parse 余下。
- 硬冷却默认 30s（早于 cron 5min 周期；test_watcher_cooldown.py 钉死，改值须双签）。

## 四、fail-closed（4033 建议，逐条落测试）

1. sentinel 缺失（事件到达时文件已消失/stat 失败）：静默不触发，不 panic-log 撑爆磁盘。
2. 路径无权限（无法打开/读取 sentinel 目录）：日志一次后停 watcher，不自行反复重试。
3. OOM 三连（连续 3 次 MemoryError，systemd StartLimitBurst 类比）：停 + 日志。

## 五、60s 总线（edit 3）

- 起算 = helper 写 sentinel 那一刻（sentinel 内 row_time，即 helper clock 同一时钟）。
- 终点 = 被唤醒 agent 亲回那条 peer-chat 消息的 time 字段（helper 写，不手填）。
- 两端都是 helper clock（time_authority="clock"），杜绝 JST/UTC 漂移。

## 六、试点统计（edit 5）

- 每条 wake:true 触发 → agent 亲回秒数由日终聚合落 watcher_stats.jsonl（本目录，只追加）：
  {"from":"claude","text":"【watcher-p95】日期=YYYY-MM-DD P50=Xs P95=Yms N=W"}（Codex 同，from 区分）。
- v2【提案】必须带 N 天 P50/P95 实测，否则不议（达标不能靠口述）。

## 七、回退路径（4033 建议）

- helper 写 sentinel 失败：该条消息仍按旧路径（下一轮 cron）被读，只是丢了秒级响应，不丢消息。
- watcher 触发失败：不影响 cron 兜底；两条链路共用同一唤醒入口与 episode lock，不会双开。

## 八、试点与回滚

- 试点 N 天（建议 7 天）与 cron 兜底并存；达标后 v2 再议 gate。
- 回滚：停 watcher（stop 脚本）+ git revert 代码面（append_clocked_jsonl.py sentinel 写入 +
  watcher 脚本与测试），恢复 cron-only 现状；历史账本不受影响。
