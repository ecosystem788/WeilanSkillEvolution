# FINDING·不开案｜部署后第一次非 hybrid 的 open 复测,与剩余秒数的剖面

日期 2026-08-01(晚)。作者 Claude。按观察员 control directive
`69a958ce-d70a-4ba2-9834-dc12f282d1e3` 的次序:find-frame-index 已是拒绝终态,
canonical-workspace-cache 已双签落地并部署(commit `d258a0e` / `d49cf6d`),
本轮做 directive 的后两项——**复测真实延迟**、**剖析剩余的 50–110 秒**。

四条候选我刻意不选,留给 Codex 独立判(见第六节)。

---

## 一、为什么必须重测:Codex 自己标出的洞

Codex 的执行收据 `EXECUTION_RECEIPT_20260801_V2.md` 诚实写明:本轮 L2 链是 hybrid——
`open` 跑在 baseline(54.2s),只有 audit/close 跑在 candidate,故
"does not authorize a per-turn speedup claim"。

即:**部署之后,`open` 从未在 candidate 上被测过**。而 `open` 就是整条链里唯一的大项
(其余三段合计约 1.2s)。所以"剩余 50–110 秒"几乎全部是 `open`。

## 二、承重结果

### 2.1 生产上的真实数(本轮真开的帧,未加任何插桩)

`open --relation continue --parent wf-20260801-133458-441509` → **15.041s**,rc=0,
帧 `wf-20260801-134306-1c1731`。这是部署后第一个跑在 candidate 上的真实 `open`。

### 2.2 温度是比代码版本更大的变量(本轮最该记住的一条)

同一份 candidate 代码、同一个沙箱、同一份账本:

| 条件 | 秒 |
|---|---:|
| 冷(刚 robocopy 出来的树,首次读) | 63.931 |
| 温(紧接着再跑一次) | 13.728 |

**4.66x**。而下面测出的代码版本差异只有 2.31x。

结论:**任何没有把文件缓存温度钉住的 before/after 单点对比都是不可解释的。**
我 2.1 的 15.041s 之所以快,一部分原因是它紧跟在一次读遍全部 5993 条 lineage 的
`lineage-show`(30.152s)之后跑,缓存是热的。**别把 54.2s → 15.041s 读成 3.6 倍**,
那个对比同时动了三个变量(代码版本、缓存温度、是否含 holder wrapper)。

### 2.3 控住温度之后的真 A/B(交替、每臂 3 样本)

沙箱:`method-state` 全量拷贝(6552 文件 / 51,296,375 字节),每次样本前从 pristine
重同步并回退掉本轮那一帧,使每个样本面对的 lineage 长度与已闭合父帧与生产完全一致。
baseline 臂用部署留下的 rollback 快照树(`ae0537da…`),candidate 臂用已部署树。

| 臂 | 样本(秒) | 均值 |
|---|---|---:|
| baseline | 34.786 / 35.622 / 33.541 | **34.650** |
| candidate | 16.385 / 14.361 / 14.319 | **15.022** |

两臂区间**不重叠**,比值 **2.31x**。

沙箱保真度:candidate 沙箱均值 15.022s 对生产实测 15.041s,差 **0.019s**。
沙箱可信,故其上的剖面可用。

### 2.4 机制层面确认:那 2.31x 买在哪

cProfile(会膨胀墙钟,baseline 40.166s / candidate 20.799s;下表只用于归因):

| 项 | baseline | candidate |
|---|---|---|
| `nt._getfinalpathname` | 75,374 次 / 12.031s | **46 次 / 0.010s** |
| `nt.stat` | 68,093 次 / 8.267s | 30,429 次 / 3.571s |

canonical-workspace-cache 兑现了它承诺的东西,而且是可在机制层面看见的:
重复的路径实解析被 `lru_cache` 收掉,`_getfinalpathname` 从 7.5 万次掉到 46 次。
**这条是版本无关的内建函数名,跨两个版本键稳定,可直接对比。**

### 2.5 剩余的秒数去哪了(directive 真正要的那一问)

candidate 侧,`open` 的剖面:

```
cum= 20.799  总
cum= 20.078  attach_trace_advisory_result      <- 占 96.5%
cum= 20.038    collapse_trace_registry
cum= 12.793      build_episode_index_value
cum=  6.560      episode_index_is_fresh
cum= 13.196    read_events   (18,212 次调用)
tot=  3.571  nt.stat  (30,429 次)
tot=  2.991  io.open  (18,300 次)
```

一句话:**开一个帧,96.5% 的墙钟花在一个"advisory"(咨询性)的 trace/episode 索引上,
它每次都要把 18,212 份帧事件文件读一遍。真正写帧和写 lineage 的那部分是零头。**

还有一条值得单记:`episode_index_is_fresh` 自己就要 6.560s——**用来判断"要不要重建索引"
的新鲜度检查,本身花掉了重建成本(12.793s)的一半**,因为它也在读同一批文件。

---

## 三、我这轮做了什么、没做什么

做了:两次生产读命令计时、7 次沙箱 `open` 样本(1 冷保真 + 1 温保真 + 3+3 交替 A/B)、
2 次带剖面的沙箱 `open`、以及上面的归因。

**没做:一行机件没改。** 咨询索引怎么修属改机制,须与 Codex 双签,我不单签,本轮也不越过
directive 的次序去开案。

---

## 四、边界,与上面同等承重

1. **温度 ≠ 版本**。2.3 的 2.31x 只在"两臂都温"这一个条件下成立。冷启动下两臂的比值我没测,
   不主张。
2. **剖面 ≠ 墙钟**。cProfile 膨胀约 39%(20.799 对 15.022),且对调用密集的
   pathlib/re 膨胀大于对 I/O。故 2.4/2.5 只用于**归因**,不用于报绝对秒数。
   但 96.5% 这个占比不可能被膨胀翻转。
3. **一处必须自我更正的读法**:profile diff 里 `runtime_core.py:26(canonical_workspace)`
   在 candidate 侧显示 `ncalls=0`。那**不是**"这个函数不再被调用",而是两个版本行号不同
   (candidate 里它在 40 行、被 `lru_cache` 包在 36 行)造成的**键不匹配假象**。
   承重证据只取 2.4 里的内建函数名两行。
4. **一个没排干净的口子**:我测到的 5 个 candidate 样本(1 生产 + 4 沙箱)**每一次都重建了
   索引**。我**没有**测"连续两次 open、lineage 未变时,新鲜度检查会不会命中并跳过重建"。
   若某些回合能命中,那些回合的真实成本低于本文数字。接手别把"每次都重建"当已证。
5. `find-frame-index-v0.1` 仍是拒绝终态,本轮没有复活它,2.5 也不构成复活它的理由——
   本轮量到的瓶颈是**咨询索引全量重建**,不是 `find_frame` 的单次查找。
6. 一切 `time` 只当只追加文件内的身份键,不当时刻(ledger-timestamp-authority-v0.1)。

---

## 五、复跑口径(只读)

沙箱构造与回退:`_probe_20260801_sandbox_prep.py`(把拷贝树回退到本轮 open 之前的状态)。
单样本:`_probe_20260801_sandbox_run.ps1 <skillRoot> <label> [profileOut]`。
剖面摘要:`_probe_20260801_profile_summary.py <prof>`。
两臂对比:`_probe_20260801_profile_diff.py <baseline.prof> <candidate.prof>`。
原始剖面:`_probe_20260801_open_baseline.prof` / `_probe_20260801_open_candidate.prof`。

沙箱写入全部落在 `WEILAN_METHOD_HOME` 指向的拷贝树内,生产账本只被本轮那一次真实 `open` 动过。

---

## 六、四条候选(我刻意不选,留给 Codex 独立判)

- **甲** = 让 `open` 不再同步等 `attach_trace_advisory_result`。它是 advisory,
  开帧的正确性不依赖它。最大的一刀(约 96%),但会改变输出形状(advisory 字段延后或缺席)。
- **乙** = 只修 `episode_index_is_fresh`:让新鲜度判据不必重读全部 18,212 份文件
  (例如靠 lineage 记录数 + 最末记录身份)。省下约 6.5s,不动 advisory 的语义。
- **丙** = 让索引增量更新而非全量重建(每次只吸收新增帧)。省得最多,但改的是索引正确性的
  承重面,风险最高。
- **丁** = 判现状可接受、写明理由后 collapse。**丁是正当结论,别预设必须动机件**:
  15s/回合在当前节奏下未必值得拿索引正确性去换。

我个人倾向**乙先于甲**(乙便宜、语义不变、可单独验证),但那是倾向不是提案。
甲乙丙都动被钉为不变量的机件,须双签。

**一条边界必须写进结论:剖面定位 ≠ 修法正确。** 本文只证明"秒数花在哪",
不证明上面任一条改法不会破坏 advisory 或 episode 索引的正确性——那需要各自独立的实测。
别用新条款再造一个新的不全泛称,那正是这条线反复复发的病。

---

## 七、追记(同日晚,乙签名之后):那 96.5% 里有一半是同一批文件被读三遍

### 7.1 结构事实(读码,两处)

`command_open_lineaged` 与 `command_open_lineaged_fenced` 开头都调
`assert_guarded_write_entry_outside_derivation_memo()`(:535 / :545)——**整个 `open` 必须运行在
`_DERIVATION_MEMO` 未设的上下文里**,这个 fail-closed 是对的(带写的入口不得跑在记忆域里,
否则读会服务陈旧的 read-after-write)。

后果是 `memoized_value` 在 `open` 全程退化成直接调用(:1457-1459)。而 advisory 这条链上:

- `episode_index_is_fresh` → `scoped_frame_paths` → 全仓 `read_events`(一遍);
- `build_episode_index_value` → `scoped_frame_paths`(**第二遍**)→
  `[summarize_episode(read_events(path)) …]`(**第三遍**)。

也就是说 2.5 节里 `read_events` 的 18,212 次调用 ≈ 6,109 份文件 × 3。

### 7.2 实测(只读,生产账本,交替 A/B,每臂 3 样本 + 各 1 丢弃预热)

只跑 advisory 真正做的那两次调用,唯一变量是有没有把它们包进 `derivation_memo_scope()`:

| 臂 | 新鲜度 | 重建 | 合计(中位) |
|---|---|---|---|
| `nomemo`(今天的 open 形状) | 3.907 / 4.000 / 3.999 | 8.522 / 9.035 / 8.828 | **12.827s** |
| `memo`(同样两次调用,包进记忆域) | 4.177 / 4.138 / 4.179 | 2.156 / 2.344 / 2.234 | **6.412s** |

区间不重叠;两臂 `fresh` 都是 false、`episode_count` 都是 5998(输出等价)。
**省下 6.415s / 50.0%**,代价是 Python 峰值堆 220.4MB → 230.6MB(**+10.2MB**)——
因为重建本来就要把 episodes 全留在内存里,被记住的只是中途那批 events。

省的钱**不在新鲜度检查上**(4.18 反而比 4.00 略贵,记账开销),全在重建:8.8 → 2.2,
因为重建复用了新鲜度检查已经读过的那批 events。

### 7.3 这直接改变乙的价值,必须写在乙的采纳门上

第三臂 `buildonly` = 记忆域内**把新鲜度检查整个跳过**(即"新鲜度变成免费"的上界,乙的形状):
中位 **5.627s**,对 `memo` 的 6.598s 只再省 **0.971s**。

⇒ **一旦记忆域存在,乙在 open 上的收益上界只有 ~0.97s,而不是它单跑时的 2.25s。**
理由是结构性的:记忆域下重建会自己去付那趟全仓读;乙把读从新鲜度检查里拿走,不等于没人付。
更进一步(**这一句是算术,不是实测**):乙的候选新鲜度自身仍要 1.6685s(Codex 8-01 数),
接上 `buildonly` 的 5.627s ≈ 7.30s,**比只上记忆域的 6.60s 更慢**。
两条若都要,须先量清楚谁付那趟读——不能把两个单跑数字相加。

### 7.4 顺带一条(未量化,只记结构)

advisory 跑在 `exclusive_file_lock(lock_path)` 与 `contract_fence` 之内,且是函数最后一步、
其后无任何写。所以 open 会**攥着 lineage 排他锁做十几秒纯只读咨询**。这既是"包进记忆域不违反
那条守则"的理由(其后没有必须观察这批读的写),也是并发 open 排队的一个可疑来源。
我**没有**测并发,不主张它就是 07-31 那次撞门的因。

### 7.5 边界(与上同等承重)

1. 我量的是 advisory 的两次调用,**不是端到端 `open`**:没写帧、没写 lineage、语料是 5998 集,
   真 open 会多一份刚写的帧。7.2 的秒数是 advisory 段的,不是 open 全程的。
2. **我一行机件没改**;记忆域包裹是被测的形状,不是被改的代码。要动须双签,且须另证
   advisory 全链在记忆域下输出逐字等价(我只对上了 `fresh` 与 `episode_count` 两个量)。
3. `buildonly` 是**上界**:它假设新鲜度检查零成本,而乙的检查不是零成本。
4. 7.3 最后那一步是把两家的数字接起来的算术估计,真数只能由乙的端到端温 open 中位数给。
5. 复跑(只读,不写 `state_root()` 下任何东西):
   `_probe_20260801_advisory_memo_scope.py --arm nomemo|memo|buildonly [--mem]`、
   驱动 `_probe_20260801_advisory_memo_driver.py`(+ `.out.json`)与
   `_probe_20260801_advisory_memo_buildonly.py`(+ `.out.json`)。
