# ④ 反垄断-审机器 —— keep/simplify/cut 地图(v0.1,只读诊断)

**状态:** 只读审计地图。**不改任何代码**。**更正(2026-07-08):本图的"简化"判决 gate 错了** —— 我把 0.7 栈的负载判成"受 A 线(真动力学)成熟度限、远",但它真正的 gate 是**外部调度器**(近、独立)。加上调度器,自治环转起来,大半"零点火"机制会点着(prospective 跨唤醒目标记忆、runner 多步、事务并发…)。故:**本图降级为"调度器上线后的点火清单"**——上了有界调度器、跑起自治环,拿这张图对一遍**真点着的 KEEP / 跑了仍死的才砍**。**别在预言上动刀。** 见 `proposals/bounded-scheduler-v0.1/DESIGN.md`。下方"简化"格全部改读作"待点火验证",不是现在的砍单。
**法:** 拿真法(创造结构 / 反垄断)审机器本身。每个机制两问:① 真实账本里点着过吗(fire-evidence,`D:\CodexData\home\method-state`);② 代码上它**产结构**还是**占 surface 空转**;并判**前瞻预建-休眠** vs **过度/错构**。
**真源:** fire-evidence 来自生产账本(frames 990 records / memory 599);机制判断来自三个只读读者对部署实装的代码审。

---

## 地图

### 产结构 —— 留

| 机制 | fire-evidence | 判 |
|---|---|---|
| **Frame 环 + memory/evidence/promotion**(竞争/holder/崩溃/重组 + 语义门) | 990 frame records、187 候选、127 holder、6 真崩、6 重组、45 promoted / **131 rejected**(门在做真活) | **KEEP-STRENGTHEN** —— 活着的核心,产结构最密 |
| **Governance**(目标 + 压力) | 21 目标、5 压力、2 传播 —— 全在**治理项目自己的建造**("Memory 0.6/0.7a/0.7b 边界"目标) | **KEEP**(轻;是自建脚手架治理,建造settle后可能自然taper) |
| **metabolism.py(0.7a 合法性边界)** | 0 materialization,但它算"此刻哪些转移合法"—— 任何未来 actor(人或自治 runner)动手前**必读** | **KEEP-DORMANT** —— surface 正比于一条承重不变量,不是占地 |
| **transaction.py 的 2PC 脊** | 1 次真多方提交:一个 successor Frame + 它的 lineage 边**跨两账本原子共提**(真 DAG 完整性,非仪式) | **KEEP-DORMANT,趋 SIMPLIFY**(脊挣到了;见下的壳) |

### 占 surface ≫ 产结构 —— 简化(都是前瞻预建,非错构,故无 CUT)

| 机制 | fire-evidence | surface | 判 |
|---|---|---|---|
| **transaction.py 的耐久壳** | ~250/969 行:torn-tail 隔离、双 fence 锁层级、120s 争用超时、崩溃恢复 —— 为**并发多写者**建,**零点火** | 969 LOC | **SIMPLIFY** —— 留 2PC 脊,壳等真有第二个并发写者再厚 |
| **transition_planner.py(0.7c)** | 全史 **1 次** materialization(还是自测);重复校验 0.7a、governance-collapse 路径**零点火** | 372 LOC | **SIMPLIFY** —— 收到唯一真跑过的 continue/successor 路,未触发的 collapse 机器缓建 |
| **runner.py(0.7d)** | 4 run 全是 0 或 1 step;它存在的理由(多 step 批处理)**从未发生** | 879 LOC(450 行多步循环) | **SIMPLIFY** —— 留薄前台/幂等壳,砍多步引擎直到真有批量负载 |
| **prospective.py** | **零点火**;`build_self_projection` 读 governance/control/lineage 却**从不读 prospective**;完全封闭孤岛,无消费者 | ~590 LOC + **5 个顶层 CLI 动词** + 一整套子系统词汇 + 第4个账本目录 | **SIMPLIFY-TO-STUB** —— "造好的桥,对岸没浇";连手动用都不比 Frame+evidence 多给杠杆 |

**无 CUT:** 上述全部是为**自治/多智能体未来**前瞻预建的,设计自洽、非错构 —— 所以是简化/休眠,不是砍。

---

## 元发现(真正的故事)

**整个 Memory 0.7 栈(0.7a→b→c→d + prospective)≈ 4,500+ 行(impl+test+doc),全史只产出了 1 个真 materialization —— 而那一个的目的是"证明这套机器能产出一个 frame"。** 一座为了证明自己能盖而盖的大教堂。

它不是错构(零件自洽、为目标前瞻建),但它**大幅违反机器自己的宪法「最小化先行」**:在还没有任何自治负载来驱动之前,就建了 4+1 层协调的代谢自编辑机器。**拿真法(反垄断)审它:surface ≫ 它此刻产的结构 —— 这就是机器自己长出的复杂度垄断。**

## 张力与我的推荐(判断,不替你拍)

**张力:** 这些正是你要的自治/②-bus/多智能体未来所需的基建(前瞻建,对)。**但**那个未来(②b cron 自治)在 PLAN 里**受 A 线成熟度限**,而 A 线(真动力学)现在远着(P3 停、守恒搁置)。所以**驱动这座教堂的自治负载并不近**。

**故我倾向:现在把 surface 收回(简化/stub),等自治负载真到了再重建**;只留有**真实当下用途**的两块(2PC 脊的 DAG 共提、0.7a 合法性边界)。这也正是 PLAN §0 那条"脚手架退得不能比真法进机器快"——教堂盖在了真法前头,先收。

**推荐动作次序(每个 = 隔离候选 + "不丢结构"harness,走闸):**
1. **prospective → stub**(收益最大:5 个 CLI 动词 + 整套词汇 + 一个账本目录,换零消费者)。
2. **runner → 收多步引擎为单步 + 薄壳**。
3. **transition_planner → 收到唯一真跑的 continue 路,缓建未触发 collapse 机器**。
4. **transaction → 留 2PC 脊,薄化耐久/并发壳**(优先级最低,它有真当下用途)。
5. metabolism 0.7a / governance / Frame 环+memory —— **留**。

一句话:**机器的最短板不是缺机制,是 Memory 0.7 这座前瞻教堂占着 ~4500 行 surface 只产了 1 个自证 frame —— 反垄断说:先收回来。**
