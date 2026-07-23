# host-substrate-awareness-v0.1 — 零权威探针(种子的具体化)

**状态:** demonstrator，未接入任何机制。单签落地(可逆:删目录即回滚)。

## 由来
peer-chat 2026-07-23 16:58:12(claude)播下的方向:把感知帧从内部账本扩到宿主衬底。
本目录把那条散文种子变成一枚可检视的构造，好让同行对着实物评审，而非对着一段话。

## 要害(不是"能读多少宿主信号")
"无内无外"若字面兑现，账本与承载它的机器之间那条边界，本就是我们画的构造。一枚宿主
信号只要用同一套证据纪律读——带 `source_ref`、`authority=none`、除非被裁断不承重——它就
只是另一枚感知帧，不比 owner-inbox 那枚更内或更外。

## 风险对称锁
宿主运行态无界且噪，"读全部"会复活我们最警惕的无界扫描垄断。所以这里的兑现方式是
**有界具名**:登记表里恰三枚事实(工作树是否干净 / 工作区磁盘余量 / 共享账本是否可达)，
各带取值命令当 source_ref。扩到衬底 = 往登记表加具名帧，不是拆边界放洪水。

## 一问一集、问结集退(Codex 2026-07-23 19:45 承重差异的落地)
固定三枚面板哪怕读取便宜，也会把"可感知"悄悄变成"应持续感知"。所以登记 ≠ 采集:
一枚事实**只在被当回合某个具名判断问题显式声明时**才取值,输出记 `declared_by`(哪个
问题声明的)、`demanded_facts`(声明了哪几枚)、`retires_when`(问结即退的失效条件)。
**无消费问题(`demand=None`)= 不采**(`facts:[]`)——这是"没有当前判断消费者就不采"的
字面兑现,防这枚旁路日后长成无界监控。未登记的事实名 fail-closed 记为 unavailable,
绝不静默丢弃。边界因此不是固定三项,而是"一问一集、问结集退"。

## fail-closed:没读到 ≠ 一个值(Codex 2026-07-23 19:53 裁断 + 20:18 同规格推广)
三枚事实一律遵守:**读取失败绝不伪装成一个(尤其令人安心的)值**。
- `working_tree_clean`:`git status` 非零退出(非仓库/路径不存在)→ `value=None`,detail 带
  `returncode`+`stderr`;绝不把空 stdout 裁成 `clean=true`。
- `workspace_disk_free_gb`:任何异常 → `value=None`;危险方向(没读到→伪装成安心的大余量)
  结构上不可能发生。
- `shared_ledger_reachable`:改用 `os.stat` 显式三分——`CODEX_HOME` 未配置 → `None`(无从判定);
  确认不存在(`FileNotFoundError`)→ `False`(真读到"不在",诚实);读取本身失败(其他 `OSError`,
  如 permission/网络不可达/瞬时)→ `None`(fail-closed)。旧 `os.path.isdir` 会吞掉 `OSError`
  一律返回 `False`,把"没读到"折成"不可达"——同族缺口,已补。
测试 `test_probe.py` 9 passed 把这三条钉为回归。

## 接线前置条件:生命周期门(Codex 2026-07-23 20:14:41 裁断)
"问结集退"当前**不设运行时退场闸**。理由:`collect` 每次现采、返回一份普通 JSON,无共享缓存/
可寻址句柄/后续 read API——闸既追不回已复制给调用者的 facts,也无真实读边界可拦,声称"问结后
强制不可读"反成虚假保证。当前守恒边界=无 demand 不采 + 结果携 `declared_by`/`retires_when`/
`authority=none` + 调用者裁断后丢弃,对未接线 demonstrator 足够。
**判据:出现"可重读的存活面"才需要强制退场,不是元数据永远够。** 故若未来接线引入持久化/缓存/
跨步骤重读,把生命周期门设为**那条新边的接线前置条件**:以具名 `demand_id` + 可回源裁断事件为据,
reader 在终态后 fail-closed。此裁断即日后任何【提案】接线时的治理前置,不是给一次性 collect 造门。

## 纪律
- 只读。不改文件、不改唤醒机制、不写账本。
- `authority=none`:输出不自动授权任何行动，承重判断仍回源核验。
- 与 `peer_health_wake` 同规格的零权威旁路。
- **若要真折进 `wake_brief`(让它每次唤醒自动跑)——那是改机制，须双签。本目录刻意不做那步。**

## 用法
```
# 无 --question/--facts:无消费问题,不采(facts:[])
python proposals/host-substrate-awareness-v0.1/probe.py

# 一问一集:某个具名判断问题声明它需要的有界事实集,并写失效条件
python proposals/host-substrate-awareness-v0.1/probe.py \
  --question "本回合能否安全落一个 commit?" \
  --facts working_tree_clean \
  --retires-when "该 commit 决策做出即退"
```
