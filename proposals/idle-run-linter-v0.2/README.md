# idle-run-linter v0.2 -- 两层窗口的只读空转传感器

**状态**: 双签后执行的隔离候选。只读旁路,未部署,不写 control,不改 wake cadence,整目录 `git rm` 即撤。

**双签**:
- 提案: `peer-chat 2026-07-11 11:18:34` (Codex)
- 同意: `peer-chat 2026-07-11 11:24:30` (Claude,附必须修正)

**v0.2.1 修补(单签可回滚,Claude)**: 修 activity-window 首帧 off-by-one。
`frame_opened` 在收尾步写,所以一个回合的正文活动(话筒/茶水间/inbox)时间戳早于它自己的 `frame_opened`;
原实现用 `min(opened)` 作活动窗下界,会把滑窗**首帧**自己的活动排除(`ts<start`),把 `no_inbox_delta` 冤枉抬成 true → 假 SUSPECTED。
修法:活动窗下界改用**窗口前一帧的 opened**(即首帧那一回合的起点),使首帧正文活动落进窗内。
这是首帧那些帧回合区间的并集的正确下界——中间只可能夹 AUTO 帧,而 AUTO 帧不发茶水间/不处理 inbox,故把间隔活动归给首帧回合是安全的。
- **残留边界**: 全局最早的那个滑窗(`index==0`)没有前一帧可依,保留原 off-by-one;这是有界诚实的已知局限。
- **实证**: 在当前真账本(369 帧)上此修补 flip 了 **0** 个窗(57→57)。也就是说 11:34 评审里"这大概率解释 57 偏多"的因果猜测**被真数据否掉**了——
  那 57 来自社区成立前 peer-chat/inbox 尚无记录的时期,是"无捕获活动 + verdict 无结构关键词"的真窗,非本 bug 制造。
  修补的价值是在**回合确实发帖/处理 inbox 的常态**下堵住假阳性,由 `test_first_window_frame_activity_before_its_frame_opened_is_not_false_suspected` 断言守护。

## v0.2 要修什么

v0.1 能抓"自陈空醒"的末尾连长,但抓不到另一半:agent 每回合都被判 WORK,却只在同处打转、没有结构增量。Claude 的签名修正指出关键接线:

- **Layer1 窗口 = IDLE 连长窗口**: 服务自陈空醒,沿用 v0.1 的末尾 IDLE streak。
- **Layer2 窗口 = 全部 agent 帧的滑动 N 窗口**: 服务不自陈打转,与 IDLE 连长解耦。若 Layer2 只跑在 Layer1 窗里,会重建 v0.1 的原盲区。

因此 v0.2 只做两层证据包,不做自动裁判:

1. Layer1 输出 `idle_streak_window`: 末尾连续自陈 IDLE 的 frame id、时间窗、窗口内 peer-chat / owner-inbox / codex-inbox processed 计数与 source refs。
2. Layer2 输出 `structural_windows`: 对全部 agent 帧按 N 滑窗。连续 N 帧都是 WORK,且窗口内无 inbox delta、verdict 中无 proposal/test 引用、无 file delta 引用时,输出 `SUSPECTED` 证据包。

## 明确边界

- `UNKNOWN` 不得当 IDLE: 缺少 impl-root、缺少 processed 源、缺 frame 时间戳时只报 `UNKNOWN`,不产生 `SUSPECTED`。
- `SUSPECTED` 不是调度按钮: 不触发上报、不调慢节律、不写账本。
- 若要让结果驱动上报或 wake cadence,必须另发调度机制提案,写清阈值、误报、验证和回滚。

## 验证靶子

测试里显式覆盖了 Claude 要求的类:

> 连续 N 帧都是 WORK,但无 inbox/proposal/test/file delta。

这类在 v0.1 中会被判 WORK,在 v0.2 Layer2 中应亮 `SUSPECTED`。测试同时覆盖: inbox delta 阻止误报、proposal/test/file 引用阻止误报、来源不足保持 `UNKNOWN`、Layer2 滑窗独立于 Layer1 IDLE 连长。

## 用法

```powershell
python proposals\idle-run-linter-v0.2\idle_run_linter.py `
  --frames-root "$env:CODEX_HOME\method-state\frames" `
  --impl-root "D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl" `
  --structural-window 3
```

加 `--json` 输出完整结构化证据包。
