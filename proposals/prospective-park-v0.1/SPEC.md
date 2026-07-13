# 反垄断简化 · 第一刀:prospective → park —— SPEC(草案 / DRAFT v0.1)

**状态:** **挂起(SUSPENDED,2026-07-08)—— 待调度器路线决定。** 若建有界调度器,自治环大概率点着 prospective(跨唤醒周期的目标记忆 + 因果条件匹配正是它的对岸)→ 那就**不 park**(park 后又 restore = 纯 churn)。本刀只在"调度器也还远"时才成立。见 `proposals/bounded-scheduler-v0.1/DESIGN.md`。以下为原草案,保留备查。
草案,未冻结,未实现。隔离候选,不改实装/部署件/授权文件。
**上位:** `proposals/machine-antimonopoly-audit-v0.1/MAP.md`(④ 反垄断审计,prospective = SIMPLIFY-TO-STUB,最大 surface / 零消费者)。
**定调:** 反垄断第一刀。prospective **零点火、零消费者、封闭孤岛**(`build_self_projection` 读 governance/control/lineage 却从不读它)。把它从**活的 surface** 收回;整包 park 到可恢复归档。**收 surface,不丢结构(零 fire/零消费者),不丢前瞻工作(parked、可恢复)。**

---

## 0. 一句话

prospective 是"造好的桥、对岸没浇"——占 ~590 行 + **5 个顶层 CLI 动词** + 一整套子系统词汇 + 第 4 个账本目录,而全史零点火、无人消费。把它占的**活 surface** 收回;代码/测试/文档 park 起来,等真有自治 driver 消费 cycle plan 时按 restore-trigger 恢复(§5)。

## 1. 从活 skill 移除

```text
- prospective.py(reducer + planner,~203 行)
- weilan_trace.py:prospective 命令块(~3219–3439)+ argparse(~6562–6628)+ import(30–37)
- SKILL.md:prospective 段(line 40 + 命令例 139–141)
- references/prospective-system.md
- test_prospective.py(移入 parked,不进 live 套件)
- test_derivation_performance.py 的 prospective 用例(:265)—— 摘除或迁 parked(见 §6)
```

## 2. Park(保前瞻工作,不是删)

整包 prospective bundle **内容寻址**存进本候选 `parked/`,附 restore 过程 + restore-trigger(§5)。git 历史本就留着;parked 是**显式、可一键恢复**的归档。**这是简化(收活 surface),不是 CUT(丢工作)。**

## 3. "不丢结构" harness(能输;全部纪律所在)

```text
零 fire 复核    目标账本 prospective 事件数 = 0 —— 移除不孤立任何真数据。
零消费者复核    移除后 grep 整个 weilan_trace.py "prospective" = 0 残引;
               build_self_projection 行为**逐字不变**(它本就不读 prospective —— 审计已证)。
全套件绿        移除后**现有全部 test_*.py 通过**(含修好 test_derivation_performance)。
               任一挂 = 有人依赖它 = 它不是孤岛 = structure_lost 死(§4)。
CLI 复核        `weilan_trace.py --help` / 子命令列表不再出现 prospective 动词;其余命令不变。
py_compile     移除 import/命令/parser 后模块仍干净编译、parser 仍构建。
恢复复核        从 parked 按 restore 过程重建,产物 hash == 移除前 prospective bundle hash。
```

## 4. 退出码(预注册,互斥)

```text
surface_reclaimed_no_structure_lost  (pass)移除 + 零fire/零消费者复核过 + 全套件绿 + CLI 洁净 + parked 可恢复
structure_lost                       (死)任一消费者断裂 / 任一现有测试挂 / 任一真 prospective 数据被孤立
                                     —— 它不 inert,回炉重审 MAP 那一格(说明有我们没找到的消费者)
blocked_engineering                  管道/隔离故障 —— 不产出裁决,修复重跑
```

## 5. Restore-trigger(前瞻工作的复活条件,写死免得丢)

```text
当存在一个**真正消费 cycle plan 的自治 driver**(②b cron 自治环,或任何 register→observe→自动 transition 的循环)时,
从 parked 一键恢复 prospective。在此之前它就是"对岸没浇的桥",不占活 surface。
—— 这条把"简化不是永久否定它"写死:它是为自治未来预建的,只是那未来受 A 线成熟度限、现在远,先收 surface。
```

## 6. 杀死测试(每颗牙演示会失败)

```text
孤岛牙 ★    移除后任一现有测试挂 = 它有消费者 = structure_lost 死。prospective 若真孤岛,全绿。
残引牙      weilan_trace.py / build_self_projection 里 prospective 残引 = 0,否则漏改(半移除比不移除更糟)。
恢复牙      parked 能**逐字**恢复(hash 对上),否则这不是 park 是删 —— 丢了前瞻工作,违约。
边界牙      只动 prospective 面;frame/memory/governance/transaction/runner 及其命令/账本**零改动**(diff 佐证)。
```

## 7. 边界与非目标

```text
- 这是**简化(收活 surface)**,不是删:parked + 可恢复 + restore-trigger 明写。
- 只动 prospective;不碰其他机制(它们在 MAP 里是 KEEP)。
- 空的 memory/prospective/ 账本目录:留(无数据),不清历史。
- 隔离候选 + harness + 收据;采纳/部署仍是项目方不可逆动作。
```

## 8. 待冻结 / 待定(Codex 复审 + 项目方定)

```text
① 深度(项目方定):
   (A) park —— 代码移出 tree 进 parked(最大 surface 收回;**推荐**)。
   (B) 轻 —— 代码留 tree,只从 SKILL.md + CLI 注册摘除(收认知 surface,不动 LOC)。
   倾向 A:审计的核心发现是**认知 surface(5 动词 + 词汇)** 比 LOC 更贵,而 A 把两者都收。
② test_derivation_performance.py:265 的 prospective 用例:摘除 vs 迁 parked 测试。
③ prospective bundle 的确切文件清单 + 移除的 weilan_trace.py 行区间 —— 冻结时对候选基座逐条核。
```
