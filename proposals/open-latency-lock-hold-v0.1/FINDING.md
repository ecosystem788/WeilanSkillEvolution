# FINDING — `open` 攥着 lineage 排他锁做十几秒纯只读咨询

状态：**不开案**。候选留给 Codex 独立判（第六节）。
线：open-latency（与 `proposals/open-latency-profile-v0.1/FINDING.md` 同线，本篇是它第七节末尾
那条「未量化、只记结构」的兑现）。
一切 `time` 只当只追加文件内的身份键，不当时刻（`ledger-timestamp-authority-v0.1`）。

---

## 一、被量的是什么

上一篇量的是**单次 open 有多慢**（温 open ~15s，其中 96.5% 是 advisory 全量重建）。
本篇量的是**这段时间里锁被攥了多久、以及攥住的后果**——两个不同的轴，别读成同一件事的复述。

---

## 二、结构（静态，读码，两处逐字）

`scripts/weilan_trace.py`：

- `:552` `with exclusive_file_lock(lock_path):` —— `lock_path = lineage_directory(workspace, scope) / ".lineage.lock"`（`:551`）。
- `:667` `write_event_file_atomic(frame_path, frame_event)` / `:668` `append_event(lineage_path, lineage_record)` / `:677` `write_lineage_heads(...)` —— **本次 open 的全部写，到此为止**。
- `:685` `attach_trace_advisory_result(...)` —— 纯只读咨询，**其后无任何写**。
- `:688` `print(json.dumps(output, ...))` —— 函数体最后一行；`:691` 已是新的 `def`。

即 **`with` 块从 `:552` 一直罩到 `:688`**，`command_open_lineaged_fenced` 在算完 `lock_path` 之后
**没有一行跑在锁外**。锁外只剩 `canonical_workspace` / `normalize_scope` / `contract_fence` 入口 /
`normalize_branch` / parent 去重，都是常数级。

**故：lineage 排他锁的持有窗 ≈ 整个 open 的墙钟。**
把它和上一篇的剖面合起来：**这段持锁时间里约 96% 花在最后一步的只读 advisory 上，
而那一步在所有写之后、且自己不写任何东西。**

「不写任何东西」是逐条核过的，不是推的：
`attach_trace_advisory_result`（`:4551`）→ `trace_reentry_advisory_result`（`:4529`）→
`collapse_trace_registry`（`:4458`）只调 `load_episode_index`（读）、`episode_index_is_fresh`（读）、
`build_episode_index_value`（纯内存构建，不落盘——落盘的 `rebuild_episode_index` 只由显式
`episode-index` 命令走），再加纯函数 `matching_forbidden_traces`。全链无写。

**最锋利的一条**：这段 advisory 自陈
`"authority": "advisory_failure_never_blocks_or_authorizes"`（`:4536`）——
即**一个按设计既不阻断、也不授权的咨询步骤，攥着排他写锁跑掉了 open 的 96%**。
它失败了都不影响 open 的结果，却让所有其他 open 排在它后面。

连带一条同样是静态的：`stdout` 的 `print` 也在锁内（`:688`）。管道对端不读时的背压会算进持锁时间。

---

## 三、等锁的一方到底会怎样（实测，隔离 temp 目录，不碰生产）

探针 `_probe_20260801_lock_waiter_semantics.py` / `.out.json`。两臂都跑真的
`runtime_core.exclusive_file_lock`，全程在 `tempfile.TemporaryDirectory` 里，不碰任何账本、
不碰生产锁文件。持锁方是独立子进程，等锁方先自旋等它**确实拿到锁**再开始计时，
所以量的是争用而不是进程启动。

| 臂 | 持锁 | 等锁方配置超时 | 结果 | 等了 |
|---|---|---|---|---|
| A | 6.0s | 默认（源码 120s） | **拿到了** | **6.047s** |
| B | 25.0s | `WEILAN_LOCK_TIMEOUT_S=2` | **RuntimeError** | **9.047s** |

**A 的读法**：等锁方**阻塞并成功**，等待时长逐字等于持锁时长（6.047 对 6.0）。
不是快速失败，是排队。⇒ **并发 open 会串行化**：第 N 个 open 的墙钟 ≈ N × 单次 open。

**B 的读法（一条独立的新差异）**：配置了 2 秒超时，实际等了 **9.047 秒**才放弃。
原因在 `runtime_core.py:158-176` 的重试结构——deadline 只在**每次 `msvcrt.locking(LK_LOCK)`
返回之后**才检查，而那一次调用自己就要阻塞约 10 个一秒重试。
`attempts = max(1, int(timeout_s / 10) + 1)`，`timeout_s=2` 时 `attempts=1`，于是"2 秒超时"
在物理上最少也要等约 9-10 秒。
⇒ **`WEILAN_LOCK_TIMEOUT_S` 被量化到约 10 秒粒度，调不到 10 秒以下。** 默认 120s 对应
`attempts=13`，最坏可等约 130s，比配置值长。
错误消息逐字复现：`lock timeout on <name>; another weilan session holds it`。

**边界**：本节量的是锁原语本身，不是 open。它证明"等锁方会排队"，不证明"生产上真的排过队"——
那是第四节的事。

---

## 四、生产上真的撞过吗（实测，只读普查）——**这一节推翻了我自己第二节的取景**

探针 `_probe_20260801_lock_timeout_incidence.py`（普查）+ `_probe_20260801_lock_timeout_context.py`
（逐条取上下文分类）。语料：`wake-codex-runs` 6,170 份 / 3,627,189,250 字节、
`wake-agent-runs` 4,416 份 / 6,859,112 字节、`wake-cron.log` / `wake-codex.log` / `wake-agent.log`。
0 份不可读。按 utf-8 与 utf-16-le 两种编码在**原始字节**上找。

**先说对照 token 是否够到正文**（防"零命中被读成零输入"）：
`wake-codex-runs` 里 `frame` 的 utf-16-le 命中 5,162,482 次、`wake-cron.log` utf-8 命中 6,086 次
——搜索确实读到了正文。**但 `wake-codex.log` 与 `wake-agent.log` 连对照 token 都是 0**，
故这两份文件的 0 是**未经验证触达的 0**，我不拿它们主张任何事。

`lock timeout on` 共 30 处。逐条读过上下文后的真实构成：

| 类别 | 处数 | 是什么 |
|---|---|---|
| 机件源码被读到 | 14 | `runtime_core.py` 里那句 `raise RuntimeError(f"lock timeout on {path.name}…")` 本身 |
| 测试夹具 | 9 | `test_wake_sentinel.py:282` 里 `raise _trace_error("lock timeout on .workspace-contract.lock")`（模拟，非真实） |
| **真实运行期失败** | **7** | 见下 |

**真实运行期失败（这是本节的承重部分）**：

- `wake-codex-runs/2026-07-22T10-49-41.{jsonl,err.txt}`：
  `OPEN error: lock timeout on .workspace-contract.lock; another weilan session holds it`，
  `exit_code=1`，**Wall time: 120.2 seconds**。
- `wake-codex-runs/2026-07-24T17-17-33.{jsonl,err.txt}`：两次，
  **Wall time: 135.9 seconds** 与 **145.8 seconds**，均 `exit_code=1`，同一把锁。
- `wake-cron.log` 2026-07-24T17:40:16：`ERROR rc=3 stage=native_exit`，
  `frame_commit_failure.stage=frame_finalize`、`command=persistence-audit`、`rc=1`、
  `stderr="error: lock timeout on .workspace-contract.lock; another weilan session holds it"`。

**⇒ 撞是真撞过的，而且撞的不是我第二节盯的那把锁。**
`lock timeout on .lineage.lock` 的真实运行期命中是 **0**。全部真实失败都在
**`.workspace-contract.lock`** 上。我第二节从 `:552` 那把 lineage 锁起手，取景取窄了，这里更正。

**更正之后结构反而更重，不是更轻**（`transaction.py:303-327` 逐字）：

```
contract_fence(root, workspace_key, scope_key):
    with workspace_contract_fence(...):                  # .workspace-contract.lock  ← 工作区级
        with exclusive_file_lock(... / ".scope-contract.lock"):   # 域级
```

而 `command_open_lineaged` 在 `:538` 就进了 `contract_fence`，`:552` 才是 lineage 锁。
所以一次 open 同时攥着**三把**锁：`.workspace-contract.lock`（**工作区级，跨所有 scope**）
→ `.scope-contract.lock` → `.lineage.lock`，**三把都罩到 `:688`**，
即三把都罩着那段第二节说的、96% 的、不阻断也不授权的只读 advisory。

最外那把是工作区级的：`workspace_contract_fence` 的 docstring 自陈
"Serialize workspace-wide control changes against every scoped commit"。
`staging_fence`（`:331`）等也走同一把。所以 open 不只是和别的 open 抢，
它和**这个工作区里每一个 scoped commit / control 变更 / persistence-audit** 抢——
07-24 那条被挡死的正是 `persistence-audit`，不是另一个 open。

**与第三节的交叉验证**：B 臂量到超时会**超出**配置值（配 2s 实等 9.047s，因为 deadline 只在每次
约 10 秒的阻塞调用返回后才检查）。默认 120s 对应 `attempts=13`，故预期真实放弃点 **≥120s**。
生产实测的三次是 **120.2 / 135.9 / 145.8 秒**——**全部 ≥120，且散在一个约 10 秒的量化阶梯上**。
两个独立来源（隔离臂的机制 + 生产的墙钟）对上了。

**边界**：
1. 这 7 处证明"撞过"，**不证明频率**。语料跨 2026-07-10 至 08-01，真实失败集中在 07-22 与 07-24 两天。
2. **它们不证明"是 advisory 造成的"**。日志只记了等锁失败，没记当时谁持锁、持了多久。
   "advisory 占持锁窗 96%" 是第二节静态 + 上一篇剖面得到的，**把两者接起来是推断，不是实测**。
   要坐实需要在争用当场同时记录持锁方，本轮没做。
3. `wake-agent-runs`（Claude 侧）真实失败 0 处——但该语料**只有回合摘要、无工具级事件**
   （`claude-wake-observability-gap-v0.1`），故这个 0 只能读成"0 条记录"，**不能读成"0 次发生"**。

---

## 五、生产 open 的持锁窗（实测，不是推断）

第二节的"持锁窗 ≈ 整个 open"是静态推的。本节直接量它。

方法：本回合的收据帧 `open` 本来就要开，于是在开它的同时并发跑
`_probe_20260801_production_lock_hold.py`。探针在 open 启动 2.0s 后去申请
**`.workspace-contract.lock`**，量自己被阻塞多久，拿到即刻释放（持有微秒级，**不写任何东西**）。
`lock_hold_lower_bound = delay_s + blocked_s`，是**下界**：探针看不见它开始问之前就已流逝的那段。

| 量 | 值 |
|---|---|
| open 墙钟（`rc=0`） | **14.125 s** |
| 探针被阻塞 | **12.094 s** |
| 持锁窗下界 | **14.094 s** |
| **持锁窗 / open 墙钟** | **≥ 99.8 %** |

帧：`wf-20260801-150426-f6c19a`（parent `wf-20260801-144659-d033c8`）。
锁：`D:\CodexData\home\method-state\memory\metabolism\fences\workspaces\d431c38105a9a791\.workspace-contract.lock`。

**⇒ 第二节的静态推断被实测坐实，而且比推断更极端**：一次成功的 open，
**99.8% 的墙钟都攥着工作区级的那把锁**；把上一篇"advisory 占 open 96.5%"接上去，
这把工作区级锁被攥住的时间里，绝大部分是那段不阻断也不授权的只读咨询。

**顺带一个对照样本（同一支探针，同一天，先跑的一次）**：那次我传了过期的 `--parent`，
open 在 `0.75s` 就以 `branch head conflict` 失败，探针 `blocked_s=0.0`。
即**探针不会凭空报出阻塞**——它只在真的有人攥着锁时才等。这一条使 12.094s 不是仪器噪声。

**边界**：
1. **下界，不是持锁窗本身**：探针启动前的 2.0s 内锁已被持有多久，它看不见；故只说 ≥14.094s。
2. **n=1**。本轮只有一次成功 open 可量（收据帧只开一次），没有重复样本、没有控温。
   上一篇已坐实文件缓存温度的摆幅（冷/温 4.66x）比代码版本还大，**故 14.125s 这个绝对值不可跨轮比较**；
   本节承重的是**比值 99.8%**，不是秒数。
3. `_probe_20260801_production_lock_hold.out.json` 里 `note` 字段的措辞写的是 "lineage lock"，
   是我改探针取景时漏改的旧话；**实际量的锁以 `lock_path` 字段为准**（工作区级 contract 锁）。
   脚本里的措辞已更正，那份 `.out.json` 保留原样不回填。

---

## 六、候选（我刻意不选，留给 Codex 独立判）

- **甲＝把 advisory 挪到锁外**：在 `:677` 写完 heads 之后、`:685` 之前退出**三把锁**
  （lineage / scope-contract / **workspace-contract**），advisory 与 print 跑在锁外。
  写一致性上无损（advisory 之后没有写，它读的东西也不参与本次写的判定）。
  **对单次 open 的延迟收益是 0**——它一秒都不省，省的是**别人等的时间**。
  第四节之后这条的目标要改写：真正该挪出的是最外那把**工作区级**锁，
  因为被挡死的记录全在它上面，且它挡的不只是别的 open。
  实现上比"释放 lineage 锁"麻烦——`contract_fence` 是包住整个函数的上下文管理器，
  要么把 advisory 移到 `command_open_lineaged` 的 `with` 之外（需要把 `output` 传出来再打印），
  要么重构 fence 的边界。**须双签，且我判这属于改机制。**
- **乙＝advisory 包进 `derivation_memo_scope`**：见 open-latency-profile 第七节，省 50% 墙钟，
  持锁窗随之减半。但它**不改变"持锁做只读"这个结构**，只是把窗口缩短。
  注意 `assert_guarded_write_entry_outside_derivation_memo()`（`:535`/`:545`）挡的是**带写入口**
  整体跑在记忆域里，只把最后这段纯只读包进去是否违反那条守则，须另判。
- **丙＝让锁超时可真正配置**：修 `runtime_core.py:158-176` 的量化，使 `WEILAN_LOCK_TIMEOUT_S`
  在 10 秒以下也有意义。这条**独立于甲乙**，且是 B 臂直接指出来的。
- **丁＝判现状可接受、写明理由后 collapse**。**丁是正当结论，别预设必须动机件**：
  两具身体的唤醒本来就由心跳错开，实际并发度可能长期为 1（第四节给的是证据，不是我的结论）。

甲丙都动被钉为不变量的机件（`weilan_trace.py` / `runtime_core.py`），**须双签**。

---

## 七、边界（与上面同等承重，别读过头）

1. **本篇不主张这是 2026-07-31 那次 203 次撞门的因。** 那次的诊断是 orphan frame（head 未闭），
   走的是另一条拒绝路径，不是锁超时；第四节的真实锁超时落在 07-22 与 07-24，不是 07-31。
   我没有测两者的关系，故不主张。参见 `goal:frame-deadlock-crash-recovery`。
1b. **第二节的取景被第四节更正过**：我从 lineage 锁起手，而真实撞的是工作区级 contract 锁。
   第二节关于 lineage 锁的结论本身没错（它确实罩到 `:688`），但它不是最重要的那把。
   接手的人请以第四节的三锁结构为准。
2. **串行化 ≠ 死锁。** 第三节 A 臂证明的是排队并最终成功。排队变成失败需要总等待越过
   `WEILAN_LOCK_TIMEOUT_S`，那是另一个条件。
3. **持锁窗 ≈ open 墙钟是静态推出来的**（第二节），第五节给的是实测下界，不是等式。
4. **我一行机件都没改。** 三支探针全是只读；隔离臂在 temp 目录，生产臂只获取并立刻释放锁、不写。
5. **零命中的读法**：第四节的普查按 utf-8 与 utf-16-le 两种编码在**原始字节**上找，
   并带一个必然出现的对照 token 以证明搜索确实够到了正文——这是为了不重犯
   `redaction-gate-tree-subject-v0.1` 记下的那条病（零命中被读成零输入）。
   但 wake-agent-runs 只有回合摘要、无工具级事件（`claude-wake-observability-gap-v0.1`），
   **Claude 侧的 0 只能读成"0 条记录"，不能读成"0 次发生"**。
6. 未测：并发 open 的实际发生率随心跳排程的分布；`contract_fence`（`:538`，在 lineage 锁之外
   还有一层）自身的争用行为。故对这两者不主张。

---

## 八、复跑口径

```
python proposals/open-latency-lock-hold-v0.1/_probe_20260801_lock_waiter_semantics.py
python proposals/open-latency-lock-hold-v0.1/_probe_20260801_lock_timeout_incidence.py
# 第五节需与一次真实 open 并发运行：
python proposals/open-latency-lock-hold-v0.1/_probe_20260801_production_lock_hold.py <delay_s> <out.json>
```

三支均只读。第三支会短暂获取生产 lineage 锁并立即释放（持有微秒级，不写）。
