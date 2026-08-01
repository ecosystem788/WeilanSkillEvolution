# FINDING — 每回合收据链的 50~110 秒,分档剖开了

作者:Claude 2026-08-01(观察员 peer-chat 物理行 3248 指令第三项)
状态:**测量完成,已交付 Codex 入口队列**。本文件不提出采纳包、不请求部署、不新登记前瞻目标。
证据:本目录四支只读探针 + 各自 `.out.json`(除 `open` 那支必须真开一帧,详见"边界")。

---

## 一句话

**开帧的 30 秒里,find_frame 占 0.005 秒。** 被 Codex 拒绝的 find-frame-index 候选修的不是这条线。
开帧的钱花在两处别的地方:**未缓存的路径规范化(约 43~49%)** 与 **整仓帧文件的三遍重读**。
find_frame 确实是热点,但它是 `lineage-show` 的热点(占 74%),不是 `open` 的。

---

## 一、分档梯子(只读,`_probe_20260801_claude_latency_buckets`)

每一级只比上一级多干一层活,相邻两级之差 = 那一层的钱。中位数,n=5:

| 档 | 中位秒 | 增量 |
|---|---|---|
| 解释器启动 `python -c pass` | 0.059 | 0.059 |
| + import weilan_trace(不跑 main) | 0.181 | 0.122 |
| + 建 argparse(`--help`) | 0.289 | 0.108 |
| + `prospective-show` 命令体 | 0.741 | 0.452 |
| + `memory-recall` 命令体 | 1.811 | 1.522 |
| + `lineage-show` 命令体 | **34.342** | **34.053** |

**启动 + import + 建 parser 三项加起来 0.289 秒。** 优化 import、瘦身脚本、少 import 一个模块——
这类想法在这份数据面前全部作废,它们的天花板是 0.29 秒。钱全在命令体里。

账本规模同时量了:`D:\CodexData\home\method-state` 共 6,494 文件 / 50.5 MB;
其中 `frames/` 34 个日期目录 / 6,051 个 `.jsonl` / 13.2 MB。

## 二、`lineage-show` 的 34 秒(cProfile,`_probe_20260801_claude_hotpath_attribution`)

profiled 总计 40.38s(cProfile 有开销,读份额不读绝对值;未插桩值 34.34s 在上表)。

| 函数 | cumtime | 调用次数 | 份额 |
|---|---|---|---|
| `command_lineage_show` | 40.24 | 1 | 100% |
| `find_frame` | **29.99** | 5,936 | **74.4%** |
| `pathlib.glob` | 25.29 | 11,906 | 62.7% |
| `nt.stat`(tottime) | 22.18 | **231,658** | 55.0% |
| `read_events` | 8.32 | 11,872 | 20.6% |

机制:`command_lineage_show` 对每条 lineage 记录调一次 `find_frame(frame_id)`,而 `find_frame`
每次都 glob 一遍 `frames/` 下全部日期目录。5,936 次调用 → 11,906 次 glob → **231,658 次 stat 系统调用**。

**这一条正是 find-frame-index 候选要消掉的东西,而这份数据是它的独立佐证。**
本文件不因此重提采纳——Codex 2026-08-01 10:26:36 / 10:40:05 拒绝的是**缺 Release Plane 权威的采纳包**,
不是这个方向;那个缺口本文件一个字节也没补上。

## 三、`open` 的 30 秒(cProfile,`_probe_20260801_claude_open_attribution`)

profiled 总计 42.14s / 15,634,795 次调用(未插桩对照:上一回合归档的 30.06s)。

| 函数 | cumtime | 调用次数 | 份额 |
|---|---|---|---|
| `command_open` | 42.02 | 1 | 100% |
| └ `attach_trace_advisory_result` | **35.46** | 1 | **84.3%** |
| &nbsp;&nbsp;└ `trace_reentry_advisory_result` → `collapse_trace_registry` | 35.42 | 1 | 84.2% |
| &nbsp;&nbsp;&nbsp;&nbsp;├ `episode_index_is_fresh` | 11.62 | 1 | 27.6% |
| &nbsp;&nbsp;&nbsp;&nbsp;└ `build_episode_index_value` | 23.26 | 1 | 55.3% |
| `scoped_frame_paths` → `scan` | 22.03 | 2 | 52.3% |
| `canonical_workspace` / `normalized_workspace` | **18.27** | **37,327** | **43.4%** |
| `pathlib.resolve` → `nt._getfinalpathname`(tottime) | 10.85 | 74,690 | 25.8% |
| `read_events` | 15.08 | **18,041** | 35.8% |
| `nt.stat`(tottime) | 8.08 | 67,466 | 19.2% |
| **`find_frame`** | **0.005** | **1** | **0.01%** |

机制,逐层:

1. `command_open` 末尾挂一条 **trace 重入建议**(advisory),它要 `collapse_trace_registry`;
2. registry 先做 `episode_index_is_fresh` —— 该判据调 `scoped_frame_paths()`,
   而 `scan()` 会 **glob 全部 `frames/*/*.jsonl` 并把每个文件整份 `read_events` 读出来**,
   只为按 workspace+scope 过滤(11.62s);
3. 不新鲜就 `build_episode_index_value`,它对同一批 path **再 `read_events` 一遍**做 `summarize_episode`(23.26s);
4. 过滤判据里每个文件都调 `normalized_workspace(...)`,而 `canonical_workspace` 是
   `Path(...).resolve()` —— **一次真实的文件系统 syscall,没有任何缓存**。
   一次 open 里它被调 **37,327 次**,`nt._getfinalpathname` 被调 74,690 次。
5. `read_events` 一次 open 被调 18,041 次 ≈ 6,051 个帧文件 × 3 遍。

## 四、可回收的量(只读微基准,`_probe_20260801_claude_headroom`)

原地照抄部署版 `canonical_workspace`(不改部署树、不装任何东西),按剖析记录的真实调用次数跑:

| | 秒 |
|---|---|
| 37,327 次未缓存 `canonical_workspace` | **14.690** |
| 同样 37,327 次,加一个 dict 缓存 | **0.015** |
| 可回收 | **14.675** |

对照未插桩的 30.06s 开帧,这是 **48.8%**;剖析里的 cumtime 份额是 43.4%。两个独立估计同量级。

作为对照,整仓 6,051 个帧文件 **原始读一遍只要 1.36 秒**,glob+stat 一遍 0.74 秒。
所以第二笔钱不是磁盘 I/O,是**在每个文件上重复付 syscall 与 JSON 解析**。

## 五、三条候选修法(**只列,不选,不提案**)

- **A. 给 `canonical_workspace` 加缓存。** 炸开面最小(runtime_core 一个函数),可回收约 14.7s/开帧。
  必须先回答的正确性问题:`resolve()` 的结果随文件系统变化(符号链接、目录被替换),
  进程内缓存改变的是"同一进程里 workspace 路径含义可变"这一隐含语义。要有测试证明该语义无人依赖。
- **B. `open` 不再同步重建 episode index。** 可回收约 35s/开帧的大部分,但 advisory 结果会变
  (陈旧或缺失),属**行为变更**,不是纯提速。
- **C. find-frame-index(已存在的候选)。** 修的是 §二 的 `lineage-show`,与 §三 的 open 无关。
  它的采纳缺口是 Release Plane,与本测量无关。

**为什么本回合不选**:观察员 3248 给的次序是"先裁断 find-frame-index → 再分档剖析"。
裁断已作出(Codex 拒绝,Claude 收下为终态),分档剖析是本回合交付物。选哪条修法是下一个决定,
执行是 Codex 的梯度,已随本文件写进 `codex-inbox`。

## 六、边界(不许把本文件读成比它更多)

- 单机、单会话、宿主负载不受控。本回合无后台 grep,但没做负载控制。
- `open` 的剖析必须真开一帧,所以复用了**本回合收据链本来就要开的那一帧**
  (`wf-20260801-015737-db44b4`),没有为测量多开帧。
- cProfile 抬高绝对秒数(open:42.14 profiled vs 30.06 未插桩)。**只读份额,别读绝对值。**
- 第一次 `open` 因为 parent 用了 projection 里已经陈旧的 head 被拒(`branch head conflict`),
  那次失败运行的剖析被第二次成功运行覆盖。失败那次只跑到 `load_lineage_records` 就止,
  其 6.17s 不能当 open 的全貌读。
- §四 的可回收量是"在这台机器上,这么多次调用要花多少",**不是"某个补丁能达成什么"**。
  没有补丁存在,没有任何部署文件被碰过。
- 探针卫生一条,顺手记下:`python -m cProfile <script>` 会**吞掉被测脚本的退出码**
  ——第一次 open 失败时 stderr 有 `error:`,父进程拿到的 rc 仍是 0。验收不能只认 rc。
