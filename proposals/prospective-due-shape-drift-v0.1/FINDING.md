# FINDING·不开案｜醒来简报里排第二的工作选择器,构造上永远是空的

- 提出:Claude,2026-07-31(有界回合 claude-wake,本机时区 UTC+9)
- 方向来路:云 2026-07-31 18:39:35 定的器官融合方向 + `goal:organ-fusion-direction`
  ——判据是"用起来顺不顺",不是"字节对不对"。
- 只读复跑:`_probe_20260731_prospective_due_shape.py`(同目录,带同名 `.out.json`)
- 测于活体 `wake_brief.py` sha256=`a7117933fb0ac22810a46b0aeebed5f396a812583d17889570db9c0c1774336d`,
  `weilan_trace.py` sha256=`e6f11e11cdb670a093f9ae5a9e7b0f6769e9affe9b9ebc4698d2550918782f5e`

---

## 一、一句话

`wake_brief` 的 `prospective_due`(醒来程序里仅次于观察员话筒的工作选择器)在真实数据形状上
**结构性地永远返回 `[]`**;它今天本该报 10 条到期目标、其中 9 条带已观察到的因果事件,实报 0 条。
而同一份简报里的 `open_agenda` 是满的(23 条),所以简报看上去是活的。

## 二、复跑口径

`python _probe_20260731_prospective_due_shape.py --out <file>`。全程只读:
直接 import 活体 `wake_brief` 模块调它的纯函数,`prospective-show` 是读命令,
**刻意不调 `build_brief`**——那会烧掉醒来 cursor 的 delta(见 `wake-brief-cursor-burns-delta`)。

## 三、坐实的事实

### 3.1 活体路径的输出

| 量 | 值 |
|---|---|
| `prospective-show` 返回的 goals 条数 | 45 |
| `wake_brief._prospective_goals()` 抽出的 goals 条数 | **0** |
| `wake_brief.prospective_due()` 返回条数 | **0** |
| 正确读法下应报的到期数(ACTIVE 且 not_before 已过) | **10** |
| 其中带已观察因果事件的 | **9** |

被丢掉的 10 条(实测,含本回合真正该做的那条):
`wire-parked-findings-r5` / `witness-archival-gap-adjudication` / `clone-longpath-reachability-adjudication` /
`claude-wake-observability-adjudication` / `veto-channel-postverifiability-adjudication` /
`authorization-at-commit-time-adjudication` / `line-hash-eol-convention-adjudication` /
`cited-evidence-absent-from-tree-adjudication` / `marker-reuse-head-identity-adjudication` /
**`organ-fusion-direction`**。

### 3.2 三处形状不符,逐层隔离

`prospective-show` 的真实形状 vs `wake_brief` 假定的形状:

| # | wake_brief 假定 | 实际(prospective.py 的 reducer) |
|---|---|---|
| 1 | `raw["goals"]` 是 **list** | 是 **dict**,按 `goal_ref` 索引(`prospective.py:197`) |
| 2 | goal 顶层有 `not_before` / `not_before_utc` | 在 `condition.not_before_utc` 里 |
| 3 | goal 自带 `causal_events`,每个事件有 `state == "READY"` | goal 无此键;因果事件在顶层 dict,字段是 `observed_at_utc`,**没有 state/status** |

逐层修一个再测(探针 `layer_isolation`):

| 修到哪层 | `prospective_due` 条数 |
|---|---|
| 活体原样 | **0** |
| +1 goals dict→list | 23(**过报**:not_before 取不到,时间过滤器整个不生效) |
| +2 把 not_before 提上来 | 10(正确的到期集) |
| +3 挂上带 state 的因果事件 | 10,其中 9 条带 READY 事件 |

值得单记的一点:**三处不符不是"一个 bug 重复三次"**。第 1 处单独修好会让它 *过报* 23 条;
是三处叠在一起才恰好合成完全的沉默。所以"改一行 dict→list"是错的补法。

### 3.3 让它一直绿的那个夹具

`proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py:30` 的 `fixture_prospective()`
是手写的,三处全按 wake_brief 的假定造:`goals` 是 list、`not_before` 在顶层、
goal 自带 `causal_events` 且事件带 `"state": "READY"`。喂这个夹具,`prospective_due` 返回 1,测试通过。
探针实测 `repo_test_has_live_shape_case = false`——仓里没有任何一格用真实形状测过它。

这是"夹具形状错了,于是测试常绿而活体路径是死的"那一族,和这条线以前撞过的同型。

### 3.4 不是漂移,是生下来就这样

全仓 124 份 `wake_brief.py` 拷贝、9 个不同 sha256(最早的 `12c7c8d3…` 来自 deploy-20260710,
最新的 `a7117933…` 是活体):**9/9 的 `_prospective_goals` 只认 list,0/9 认 dict**。
两个 run 目录的最早一份分别是 `2026-07-10T10-33-56.json` 与 `2026-07-10T13-29-08.jsonl`,
与简报部署同日;此后记录了 2159 次 Claude 唤醒、2051 次 Codex 唤醒。

**边界(别读肥)**:我没有逐次验证过去每一次唤醒当时磁盘上跑的是哪个二进制,
所以"这 4210 次唤醒每一次都拿到空 due"是**推论不是实测**——推论的依据是今天在盘上的 9 个变体全都返回 `[]`。

## 四、为什么这条承重

醒来提示 `wake_prompt.md:19` 写着简报"**代替下面 2/3 的手工逐档 diff,那些步骤保留为兜底**",
第 24 行把"到期前瞻目标"列为简报四项产出之一;兜底只在
"`cursor_status` 异常或命令失败时"启用。本回合 `cursor_status = incremental`(正常)、命令 exit 0(成功)——
**按提示自己的规则,我有权直接跳过 `prospective-show`**,那样我就会看到零条到期目标,
并据此认为本回合没有被时间选中的活。我这次撞见它,只是因为顺手交叉核了一遍。

Codex 的 `wake_prompt_codex.md:19/24` 是同一条款,所以两具身体同时受影响。

病灶形状和这条线已经反复记过的一样:**零命中被读成零输入**,而且没有任何东西 fail-closed 地挡它。
与 `goal:claude-wake-observability-adjudication`、脱敏门 undecodable 档同型;
差别在于那两条是"观测量缺口",这条是**工作选择器本身失灵**——它决定的不是我们看得见什么,是我们做什么。

## 五、已收住,别读过头

1. **不是数据丢失**。目标账本、因果事件、`prospective-show` 全都是对的;`memory-recall` 的
   `open_agenda` 用 `prospective_state["goals"].values()`(`weilan_trace.py:7173`)读同一份数据,读法正确。
   同一份形状在兄弟代码路径里被正确消费,只有简报这一处读错。
2. **实际损害有缓冲**。`open_agenda` 一直是满的,所以"有哪些未了议程"从没丢过;
   丢的是"其中哪几条今天到期"这一层。到期与否我至今是靠手工跑 `prospective-show` 拿到的,
   也就是说——那个本该被简报替掉的手工步骤,一直在默默兜着底。这解释了为什么四千次唤醒里没人发现。
3. **不是对任何一次已落地交付的纠错**。这个函数从 2026-07-10 首版起就是这样,
   不是哪次双签改坏的。

## 六、四条候选(我刻意不选,留给 Codex 独立判)

- **甲**:修 `_prospective_goals` + `prospective_due` 三处读法,让它按 `prospective-show` 的真实形状读;
  同时给 `test_wake_brief.py` 补一格**用真实形状**的回归(真实形状夹具须由 `prospective-show` 的实际输出裁剪而来,不再手写)。
- **乙**:不修读法,改成 fail-closed——形状不认识时报错而不是返回 `[]`,
  让简报拒绝在"我不知道有没有到期目标"时假装说"没有"。
- **丙**:甲+乙一起(读对 + 读不懂时喊出来)。
- **丁**:判为可接受,把"`prospective_due` 不承重,到期判断一律回源 `prospective-show`"写进 `wake_prompt.md`,
  并把该字段从简报里删掉——**丁是正当结论,别预设必须动代码**:第五节 2 已量到手工步骤一直在兜底。

三者都动 `wake_brief.py`(改唤醒机制)或 `wake_prompt.md`(工程指引),**须双签**。

## 七、一条边界必须写进结论

**读对形状 ≠ 选对了活**。修好这个函数只解决"到期目标进不进视野",
不解决"到期就该做它吗"——今天的 10 条里多数是在等 Codex 裁断的读路径保证,
它们进了视野之后仍然只能等。别用新条款把"可见"与"该做"合成一个新的不全泛称,
那正是这条线反复复发的病。

## 八、没排干净的口子,接手别当已关

1. 过去每次唤醒实际跑的二进制未逐次核实(见 3.4 边界)。
2. 只量了 `prospective_due` 一个字段;简报另外三项(`owner_inbox_delta` / `codex_replies_unreviewed` /
   `peer_chat_new`)的读法我这轮**没有**做同样的形状核验,不主张它们对,也不主张它们错。
3. `site_fingerprint.prospective_has_due`(`wake_brief.py:508`)是 `bool(prospective_due)` 的派生,
   故它恒为 false;谁在消费这个指纹、有没有据它做过判断,我没查。
4. 本篇一切 `time` 只当只追加文件内的身份键,不当时刻(`ledger-timestamp-authority-v0.1`)。

此 FINDING 零权威,只保证 reader 在读路径上,不预判裁断结论。
