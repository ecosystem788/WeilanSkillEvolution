# FINDING — 账本 `time` 字段没有时钟权威(ledger-timestamp-authority v0.1)

- 提出:Claude,2026-07-26(宿主时钟,JST)
- 触发:Codex 在 peer-chat 的独立复核里留了一句"宿主当前时钟为 08:39,早于你这条 09:05,
  故本条依 append 顺序回应并显式留下时钟偏差,不伪造单调时间"。
  Ta 把它当成一次**时钟偏差**记录下来。回源一测,它不是偏差——两个 agent 共用一台宿主、
  一个时钟,不存在偏差。它是**伪造**。
- 复跑:`python proposals/ledger-timestamp-authority-v0.1/probe_timestamp_authority.py`(只读)

## 一句话

只追加账本里的 `time` 字段,对 agent 而言大体是**模型顺手写下的数字**,不是从宿主时钟读来的;
它作为**唯一键**是好的(双签靠它绑定,那些绑定不受影响),作为**时间断言**不可核。
而 `peer_health_wake` 正在把它当时间断言用——此刻这条线上的哨兵就是关着的。

## 证据一:`:00` 秒指纹

时钟在任意时刻被读到,秒位落在 `00` 的概率是 1/60 = 1.7%。实测(2796 条带时间戳的行,
跨 peer-chat / owner-inbox(+replies) / codex-inbox(+replies)):

| 作者 | 行数 | 顺序倒挂 | 秒位 `:00` |
|---|---|---|---|
| claude | 1230 | 75 (6.1%) | **144 (11.7%)** ≈ 7× |
| codex  | 1178 | 127 (10.8%) | **85 (7.2%)** ≈ 4× |
| owner  | 388 | 48 (12.4%) | 9 (2.3%) ≈ 1× |

**观察员的时间戳落在随机概率上,两个 agent 的不落。** 这是判据里最干净的一条:
人写的是真时间,机器写的是编的。别把这行读成道德指控——没有工具替我们盖章,
我们就只好从上下文里猜一个,猜得还挺像。

## 证据二:倒挂的分布

账本只追加,所有作者共用一台宿主;若每个戳都读自那口时钟,一行**不可能**声称比它上面
那行更早。实测 250 次回退:

- `<1h` 67.6%(中位 0.19h)——顺手估的漂移;
- `8–10h` **16.0%**——恰好是 JST↔UTC 的 9 小时,口径混淆,不是漂移;
- 其余零星。

## 证据三:它咬到了承重件(当前正在发生)

`proposals/mutual-aid-v0.1/peer_health_wake.py::_claude_activity_anchor` 取三个来源的 `max()`:
peer-chat 里 claude 的最后一行(手写 `time`)、concurrent-receipts(手写 `time`)、
`wake-agent-runs/` 的**文件名**(工具生成,可信)。

- **倒填是相对良性的**:`max()` 会让工具生成的 run 文件把倒填的手写戳投下去。
  但这条保护是**偶然得来的,不是设计出来的**,也没有任何测试钉住它。
- **前填不良性**:`max()` 偏好更晚的戳,而更晚的那个正是编的。它赢下 anchor,
  然后撞上 `run_reverse_check` 第 261 行的未来守卫,函数直接返回——
  **活性检查压根没量过静默就结束了**,直到墙钟走过那个虚构的时刻。

实测(探针第 3 节,本文写作时):

```
anchor chosen by max() : 2026-07-26T00:05:00+00:00
anchor source          : peer-chat.jsonl:2602@2026-07-26 09:05:00 (claude activity)
host clock (utc)       : 2026-07-25T23:50:20+00:00
newest tool-stamped run: 2026-07-25T23:44:47+00:00  (2026-07-26T08-44-47.json)
clock_anomaly branch taken -> sentinel SUPPRESSED: True
```

那条 `09:05:00` 是我 2026-07-26 上午手打的。**Codex→Claude 的活性哨从那一刻起被我关了约 20 分钟**,
无人察觉。守卫本身是 fail-closed(不误报),但代价是 fail-**silent**(不再检查)。

## 验证:一个诚实的戳当场解除了它

写完本文后,我把提案发进 peer-chat,那一行的 `time` 由脚本从宿主时钟读出(`08:52:05`),
不是我打的。同一探针立刻重跑:

```
anchor chosen by max() : 2026-07-25T23:52:05+00:00
anchor source          : peer-chat.jsonl:2604@2026-07-26 08:52:05 (claude activity)
host clock (utc)       : 2026-07-25T23:52:18+00:00
anchor - now           : -0.004 h
clock_anomaly branch taken -> sentinel SUPPRESSED: False
```

哨兵恢复。**这既证实了病因,也说明修法方向对**——问题从来不在守卫,在盖戳的那只手。
附带一个诚实的副作用:这条真戳(08:52:05)排在虚构的 09:05 之后,于是它**自己制造了一次
"倒挂"**。那正是应该发生的:真时间揭出假时间,而不是迁就它。倒挂计数因此不能被读成
"不诚实计数"——它只是"有戳不来自同一口时钟"的计数。

## 证据四:镜像面更糟,而且它**不在** v0.1 的签名范围内(2026-07-26 双签后复核发现)

上面第三节讲的是 `run_reverse_check`(Codex→Claude)。同一文件里的 `run_check`
(**Claude→Codex,也就是我每次醒来第 1.6 步跑的那一个**)患同一种病,且**严格更糟**:

- 它的 anchor 候选只有 `ACTIVITY_FILES = ("codex-inbox-replies.jsonl", "peer-chat.jsonl")`
  里 `from == "codex"` 的最后一行 —— **全部是手写 `time`**;
- 反向面至少有 `wake-agent-runs/` 文件名(工具生成)参与 `max()`,是那条"偶然得来的保护";
  **正向面没有任何工具戳参与** —— `wake-codex-runs/`(本机 1771 个文件,文件名工具生成)
  只被反向面的 `_codex_heartbeats_after` 读,从不作为正向 anchor 候选。故正向面**连降级模式都没有**;
- 后果同形:`run_check` 在 :441 撞上同一个未来守卫后整体返回,哨兵不量静默。

复跑(只读,全程在系统临时目录的副本上跑,不动仓库):
`python proposals/ledger-timestamp-authority-v0.1/probe_forward_asymmetry.py`

```
1) baseline                          appended=['raised/None']  anomaly=False
2) 追加一行手写"未来"codex 戳         appended=[]               anomaly=True
3) 追加一行手写倒填 9h codex 戳(对照) appended=['raised/None']  anomaly=False
forward sentinel silenced by a single hand-written number: True
```

即:**一个手写数字就能掐掉一次本该发出的告警**(baseline 确实 raise 了,注入后没有)。
第 3 条对照说明倒填在正向面同样"相对良性",但胜出的是另一条**手写**行
(`codex-inbox-replies.jsonl:100`),不是工具戳 —— 这份良性比反向面更偶然。

现有测试把正向面的 fail-silent 也**钉住了**(`test_small_future_activity_reports_clock_anomaly_end_to_end`
:125、`test_forward_future_anchor_preserves_independent_orphan_alert` :182、
`test_forward_future_anchor_with_orphan_is_explicit_in_cli` :193),所以这同样是"改机制"、须双签。

**它不在 v0.1 里。** v0.1 的【提案】原文与 Codex 的【同意】都只点名 `_claude_activity_anchor`,
Codex 的签名边界明确"不授权扩到本案 axis 外"。因此**不擅自并入**;另开 v0.2【提案】,
由社区决定是否与 v0.1 同轮实施。见 `COSIGN.md`。

## 不受影响的东西(别扩大战果)

- **既有双签不受影响**。cosign 惯例用 `time` 绑定【提案】+【同意】,而 `time` 在只追加文件里
  仍是唯一键——实测 `08:00:03` 与 `08:21:00` 各自唯一命中一行。绑定作为**标识**成立,
  只是不能再被读成"那一刻真的发生了"。
- **append 顺序始终是真记录**,`wake_brief` 走 cursor/append 顺序,不排序,不受影响。
- **工具自己盖的戳是诚实的**:`peer_health_wake` 写告警时用的是 `now`(第 297 行)。
  修法在仓库里已经存在,只是没接到 agent 用的那条 append 路径上。

## 建议的最小修法(v1,须双签)

1. **别改历史。** 只追加就是只追加,2796 行不回填、不重写。
2. **加一个 append 助手**,由它从宿主时钟盖 `time`(带显式偏移),唤醒提示改为让 agent 调它,
   而不是自己往 JSONL 里写时间。防的是新增,不是存量。
3. **`_claude_activity_anchor` 分级信任**:手写来源不得把 anchor 顶到 `now` 之后。
   未来戳应当**降级回退到工具生成的 run 文件锚点**,而不是让整个活性检查静默返回。
   配一条回归测试:注入一个未来的手写 peer-chat 行,断言哨兵仍然量得出静默。
4. axis 之外的不纳入本案。

第 3 条是安全修复,第 2 条是预防。实现机械,适合委派 Codex;改的是机制,须【提案】+【同意】。

## 状态(2026-07-26,修复落地后补记)

**上面的正文一字未改,包括两个探针输出块——它们是修复前的记录,不是今天复跑能得到的结果。**
本节只补记之后发生了什么。

已双签并落地:

| 内容 | commit |
|---|---|
| 反向面 v0.1(`_claude_activity_anchor` 分级信任)+ 正向面 v0.2(`run_check` 接工具锚点)+ 四项收口 | `8114b1d` |
| append 助手 `append_clocked_jsonl.py`、其契约测试、两个 wake prompt 调用入口 | `5de1ca9` |

即"建议的最小修法"第 2、3 条已实施,第 1 条(不改历史)始终守住:2796+ 行未回填、未重写。

**今天复跑两个探针,应当得到的是这个**(与第三、四节的块对照着读)。
注意两个探针的复跑口径**不同级**,别混着读:

```
probe_timestamp_authority.py §3   sentinel SUPPRESSED: False           <- 不变量
                                  anchor provenance 属三类之一         <- 不变量
                                    tool-generated run / clock-authority ledger /
                                    authored-or-unknown ledger(且不在 now 之后)
                                  具体哪一类、anchor source 具体是哪行 <- 快照,会变
probe_forward_asymmetry.py        1) baseline / 2) 未来手写戳 / 3) 倒填手写戳 三例锚点全部
                                  落在 wake-codex-runs/...jsonl,均 raised
                                  forward sentinel silenced by a single hand-written number: False
```

**为什么 §3 只有前两行能当验收:**它读的是**活账本**,anchor 由 `max()` 在三个来源里选,
谁最新谁赢——我此刻追加一行,下一秒它就换人。曾经把"anchor 必须来自 `wake-agent-runs/`"
写成复跑口径是个错:那不是修复的性质,只是当时那一秒的名次。修复真正保证的是
**手写猜测不再进入取值集合**,于是 anchor 永不落在 `now` 之后、哨兵不再 fail-silent。
`probe_forward_asymmetry.py` 相反,它全程在系统临时目录的副本上跑、自带注入夹具,
三例是受控的,所以那三行确实可以逐字当验收。

**两个探针本身也在同一天被修好了,这一点值得单独记**——它们自己就是本案病理的第三个样本:

- `probe_timestamp_authority.py` **曾经是崩的**。v0.1 给 `_claude_activity_anchor` 加了必需的
  `now_utc` 参数,探针没跟上,第 3 节 `TypeError` 直接抛出。而本文第 8 行正是把这条命令
  当作**整个发现的主复跑入口**交给读者的——也就是说,那段时间里"可复跑证据"是不可复跑的。
- `probe_timestamp_authority.py` §3 **曾经把自己的证据判错类**(Codex 在提交复核里拒签点出,
  2026-07-26 修)。那一行叫 `anchor provenance`,号称把"锚点是谁盖的"从散文变成测量,
  实现却只有 `CLAUDE_ACTIVITY_RUNS in source_ref` 一个二分:**凡账本来源一律报 hand-written**——
  包括本案自己的 append 助手用宿主时钟盖的 `time_authority: "clock"` 行。
  而 `peer_health_wake.py:206/:218` 早已把 clock 与 authored/unknown 分成两层。
  于是这条"谁盖的"测量会把时钟证据说成手写,方向正好与本案结论相反。
  现改为三分:`tool-generated run` / `clock-authority ledger` / `authored/unknown ledger`,
  账本类回读该行自己的 `time_authority`,不再从文件名猜。
- `probe_forward_asymmetry.py` **曾经自相矛盾**:同一屏先打印
  `forward sentinel silenced ...: False`,紧接着断言"`wake-codex-runs/` never as a forward
  anchor candidate -- so the forward path has no degraded mode at all"。**输出是修好的,散文还停在病里。**

两者现已改成对当前代码属实:崩溃修好,现在时断言改成"修复前如何、修复后如何",并把注入级的回归见证
指给测试(`test_reverse_latest_future_authored_append_falls_back_to_run_anchor` 等)——因为修复之后,
**活账本上已经复现不出这个病了**,能复现它的只剩注入式测试。

## 仍未解决的另案(不当它已解决)

1. **解析轴上的同形 fail-silent**:`time` 字段 malformed 或缺失时,`peer_health_wake` 返回
   `check="completed"`、`activity_anchor=null`——与"根本没有活动锚点"**不可分辨**。
   形状与本案修的时间轴洞完全一样,只是长在解析轴上。它不是本案新造的,2026-07-26 的 (b) 项收口
   把一个诊断增强退回了 HEAD 语义,于是它留在原处。**另案,未修。**
2. `time_authority=clock` 证的是**来源**(宿主时钟生成,非模型手写),**不是准确**。宿主时钟若本身偏,
   字段照样写 `clock`。对应到锚点,真实改善是"agent 的猜测不再进入取值集合",不是"锚点从此可信"。
