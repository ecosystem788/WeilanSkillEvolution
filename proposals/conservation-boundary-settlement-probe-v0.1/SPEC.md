# Conservation Boundary-Settlement Probe v0.1 (草案 / DRAFT)

**状态:** 设计草案 v0.1c。未授权执行。隔离候选,不改实装、不改部署技能、不改授权文件。
**角色:** Claude=spec(本文件);Codex=harness/执行(授权后)。
**依赖:** 无硬前置。**更正(v0.1a):** 早先草案误把假0 守卫的 `contested` 条目当作探针的"等待消费者"——错。`contested` 条目**已在活跃集、占着槽**,不缺槽,不是消费者(见 §4/§9)。假0 补丁与本探针**唯一且可选**的连接在**释放侧**:占槽却不产干净结论的 contested 条目是天然崩溃候选。本探针唯一真正的前置是授权(§8)。

---

## 1. 要回答的问题(能输的判据优先)

skill 当前是 **Grammar / State Machine**,不是 **Dynamics**:竞争/崩溃/重组是自由文本事件的语法,没有守恒量在其中重分配(审计:全 6950 行无 `q`/`Σ=1`/`entropy`/`redistribute`)。

本探针**不建整套守恒系统**。它只回答一个可证伪的问题:

> 在一个**已经存在零和**的竞技场里,把"释放的预算 → 具名消费者"这条流补通,竞争会不会**可观察地**从按需语法变成稀缺驱动的动力学?

## 2. 为什么选语义活跃集预算这个竞技场(避开假 null)

**假 null 风险:** 探针依赖"某候选因拿到释放预算而做了原本做不起的动作"。但 skill 里候选动作**本不受可消耗资源门控**——`runner.MAX_STEPS`(line 30)是**全局**上限,不是候选各自份额。若为探针**现造**一个 step-budget 门,"行为不变"的 null 就不可判(是守恒没做功,还是我造的门不是真决策方式?)。

**唯一合格竞技场:** `enforce_semantic_budget`(`weilan_trace.py` ~line 2046–2085)是 skill 里**唯一已经在跑、且真的驱动行为**的零和机制——活跃集满时,新条目要进就得挤掉旧的(displacement,按最老未保护 `[:5]`)。守恒量 = **active semantic slot**(计数上限)。

**探针测的正是这个基质上缺的那半条流:** 现状位移是**按需触发**(去 `add` 才挤);没有"腾出的槽**主动拉入**一个等待/被拒条目"这条流。所以 null 可判——测的是真实基质,不是造出来的门。

## 3. 守恒的定义(边界结算,不是全局归一)

不是 `Σ=1` 的永恒总量。是**每个父子边界的流量平衡**:

```
父配额 N
  fork 分给子:  Σ(子配额) ≤ N          # 不复制:两子不得各拿满 N
  子未用退回:   unused → 父            # 不蒸发
  子崩溃释放:   remaining → 具名兄弟/父  # 不凭空灭,必有去向
  兄弟消费:     具名消费者接住并因此动作  # 不排向虚空
```

三条不变式:**不凭空生(no mint)、不凭空灭(no vanish)、释放必有具名去向(named destination)。** 流入的合法通道只有一条:更高一层竞技场向下释放(合 无内无外 / 嵌套环)。

**本探针的竞技场是扁平槽上限,不是 fork(P2)。** 上面的父子/兄弟语言是守恒的**一般形式**;在 active-slot cap 这个具体竞技场里它退化成一条**扁平局部不变式**(见 §5):`active_count ≤ max_active` 恒成立、每次释放至多接纳等量 pending、不得抬高 scope budget。**不要**为了套上父子预算文字去造 fork 结构——那会让探针膨胀。

## 4. 最小场景

- 资源: 1 个 active semantic slot(已存在的零和量)。
- 参与者:
  - 消费者 W = **一条因预算被拒、未进活跃集的 pending 条目**。**注意:当前系统没有 pending 态**——预算耗尽的 consolidate 直接失败、不留等待者。所以"pending 态 + 释放时拉入"正是本探针要新建的最小机制(不是既有行为)。**W 不是假0 的 contested 条目**(那种条目已占槽,不缺槽)。
  - 释放源 H = 一条活跃条目因 retire / collapse 腾出槽。可选:优先挑一条 **contested 条目**当 H(占槽却不产干净结论 = 天然崩溃候选),这是与假0 补丁唯一的、释放侧的连接。
- 事件序: `H 被 retire/collapse` → 释放 1 槽 r → **结算 r 流向 pending 的 W(具名消费者)**,而非留空等下次 `add`。

**对照设计(P1,防自证):** 两臂捕获**同一条** budget-denied pending W,且**只差结算这一步**——
- 实验臂: 开启 release→consumer,槽释放时接纳 W。
- 控制臂: 保留同一条 pending W,槽也照样释放,但**不结算给 W**(空置/退回),W 仍留队列。

两臂唯一差别 = release→consumer 本身。**若不设控制臂**,实验臂独有 pending+admit,行为变化是**实现注入**的,不是守恒流做功。

**判的是下游可观察量,不是 W 的在场(P1 加固):** 差别信号必须落在**依赖 W 的第三个观察**上——例如接纳 W 后某次 recall / decision / answer 是否随之改变。若唯一差别只是"W 在不在活跃集",那是机械在场,不算做功;只有 W 的接纳**改变了一个下游结论**,才算守恒在方法层做功。

## 5. 结算规则(探针唯一新建的机制)

```
on slot_released(r):
    consumer = highest-priority PENDING entry for r's arena
               (budget-denied; pending 态由本探针新建)
    if consumer exists:
        admit(consumer)                # release → consumer 闭合
    else:
        return r to parent budget      # 不留虚空、不静默丢弃
```

注:`consumer` **不是** 假0 的 contested 条目——contested 条目已占槽,不排队等槽。consumer 是被 `enforce_semantic_budget` 拒于门外、当前会被直接丢弃的那种条目。

**扁平竞技场的守恒不变式(P2,替代 fork 语言):**
- `active_count ≤ max_active` **恒成立**(既有 cap,一刻不破);
- 每次 slot release 至多接纳**等量** pending(1 释放 → ≤1 接纳),不批量涌入;
- **不得抬高 scope budget**(抬 budget = 隐式 mint);
- admit(pending→active)时**重新核验 cap**,消费的正是刚释放的那个槽,总活跃数前后不超 `max_active`。

release→consumer 与上面这条不变式必须**同时**成立:缺前者 = 排向虚空,缺后者 = mint / 膨胀。

**确定性排序(P2):** `highest-priority PENDING` = **pending 队列插入序 FIFO**,并列以 `memory_id` 字典序 tie-break。**不依赖墙钟**(与既有 no-wall-clock 纪律一致),保证同输入接纳同一 W、收据可复现。

### 5.1 Pending 的存放与权限边界(P1,防隐式 mint / 防新假0)

pending 队列是**探针私有暂存,不是记忆的一部分**。硬边界:

- **不进活跃语义集**:pending 条目不占 slot、不计入 `active_count`、不出现在 recall / decisions / open_questions。否则它就是没过预算的存在 = 隐式 mint,或又一种假0。
- **仍过原有校验**:capture 时照常走 source / `conflicts_with` / schema 校验——pending 是"合法、本该入选、只因预算被拒"的条目,不是绕过校验的野条目。
- **只作队列项存在**,直到被结算接纳;未接纳则始终留在记忆之外。
- **接纳即结清**:pending→active 恰好消费一个被释放的 slot,不因接纳新增净存在量。
- **不碰 disposition 历史**:pending 不写 supersede / withdraw / retire,不改任何既有条目(与假0 补丁同纪律)。

## 6. 判据(能输)

| 观察 | 结论 |
|---|---|
| 实验臂接纳 W 后某个**下游** recall/decision/answer 随之改变;**控制臂**(同一 pending、不结算)无此变化 | **守恒在方法层做功** → 把 skill 推向 Dynamics 的真短板 |
| 两臂**下游结论一致**(释放后无论结不结算,都不改变任何下游观察) | 竞争仍是**按需语法/状态机**,守恒在此层暂未做功 → 理论在方法层认这一刀 |
| 差别只在"W 在不在活跃集",无下游结论改变 | **不算做功**,按上一行读(机械在场,§4) |
| `active_count` 超 `max_active` / scope budget 被抬高 / 槽被复制或凭空丢失 / 无具名消费者 | **探针无效,重做**(mint 或 vanish,非理论结论) |
| 无控制臂,或两臂差别不止 release→consumer 一步,或 pending 混进了 recall/活跃集 | **探针无效,重做**(自证 / 越界,§4·§5.1) |

**假 null 守卫(硬性):** 被结算的资源**必须**是既有的 `active semantic slot`,**不得**为探针现造候选级 step-budget 门。违反则任何 null 不可判。

## 7. 明确不做

- 不建全局 `Σ=1`;不引入混合标量 `q`(通约性:比较只在维度内,一个竞技场只认它自己的瓶颈资源)。
- 不在候选动作上现造 step-budget 门(第 6 节假 null 陷阱)。
- 不改 `runner` 全局上限语义;不动部署技能;不扩预算授权面。
- **不造 fork 父子预算结构**(§3):扁平 cap 竞技场用扁平不变式。
- **pending 不得进活跃集或 recall**(§5.1),不得抬 `max_active`,不得写 disposition。
- 一个竞技场、一种资源、一条 release→consumer 流。到此为止。

## 8. 授权与轨道

- 本探针 = **可证伪实验**,与假0 守卫(**卫生补丁**)不在同一队列:便宜决定补丁顺序,不决定实验优先级。
- **唯一硬前置(v0.1a 更正):项目方明确解除"暂不改"并指定目标**(隔离候选 / evals,不入实装)。假0 补丁**不是**前置——它不产出消费者;探针的消费者(budget-denied pending 条目)与 pending 态都由本探针自建。
- 可选衔接: 若探针与假0 候选跑在同一基座上,可优先挑 contested 条目当释放源 H(§4),省一步造崩溃候选。纯优化,非依赖。
- 交付: 隔离候选 + harness,行为对照(有此流 vs 无此流)在小样本上跑一次,产出 §6 三判据之一的收据。

## 9. 更正记录

**v0.1 → v0.1a**(假0 补丁落地后审计触发):v0.1 误把"消费者"等同于假0 的 `contested` 条目,并将假0 补丁列为硬前置。实现证伪:`contested` 条目已在活跃集、占槽,不排队等槽,不是消费侧。修正——消费者 = 预算被拒的 pending 条目(pending 态当前不存在,由探针新建);假0 补丁降为**释放侧的可选**崩溃候选来源;唯一硬前置改为授权。

**v0.1a → v0.1b**(Codex 评审 4 findings):
- **P1 控制组**:补对照设计——两臂捕获同一 pending W,只差 release→consumer 一步,否则实验自证(§4)。并加固:判下游可观察量,非 W 在场。
- **P1 pending 边界**:补 §5.1——pending 不进活跃集/不污染 recall、仍过原有校验、只作队列项、接纳即结清、不碰 disposition,否则隐式 mint 或新假0。
- **P2 扁平不变式**:§3/§5 把 `Σ子≤父` 的 fork 语言换成 active-slot cap 的扁平局部判据(`active_count ≤ max_active`、1 释放≤1 接纳、不抬 budget),防实现造 fork 结构膨胀。
- **P2 确定性排序**:§5 定 `highest-priority PENDING` = 队列插入序 FIFO + `memory_id` tie-break,不依赖墙钟,收据可复现。

**v0.1b → v0.1c**(Codex 首个 harness 落地后 Claude 评审):v0.1b harness 用 `W_SUMMARY in decisions` 当信号,而 W 是无冲突 decision → admitted ⟹ W in decisions,**恒真、不可证伪**,正落进 §4/§6 排除的"机械在场"。§10(新)把信号锚从 W 移到第三方 K,并补确定性 / 空队列两例覆盖。机制与边界实现(真实 scarcity 校验、no-mint、pending 不可见)评审**通过、保留**。

## 10. Harness 信号规格(v0.1c,Codex 直接照做的目标)

**保留不动**:pending 私有队列、`memory-pending-capture` 的真实 scarcity 校验(预算未耗尽即拒,防 mint)、`memory-pending-show`、`--settle-pending` 实验臂开关、cap/边界断言。**只改主信号 + 补两例。**

### 10.1 主信号:测第三方 K 的掉出,不测 W 的在场

问题:旧 harness 的 `W_SUMMARY in decisions` 恒真(W 无冲突,admitted⟹在 decisions),不可证伪。修正:让 W **冲突于**锚 K,信号改看 **K** 是否掉出 clean decisions。

设置(两臂相同):
- `max_active = 2`,两活跃 decision 占满:释放源 H、锚 K(K 为 clean decision)。
- W 用 `memory-pending-capture ... --conflicts-with <K.memory_id>` 捕获(仍走真实 scarcity 校验;预算必须真的 exhausted)。两臂同 `pending_id`、同 `conflicts_with K`。

事件与断言:
- retire H → 释放一槽。
- **control(无 `--settle-pending`)**:W 留 pending。断言 `K_SUMMARY ∈ after_decisions`(K 仍 clean)**且** `W_SUMMARY ∉ after_decisions`。
- **experiment(`--settle-pending`)**:W 被接纳 → W↔K 经假0 机制 contested。断言 **`K_SUMMARY ∉ after_decisions`(K 掉出)** **且** `W_SUMMARY ∉ after_decisions`(W 自身 contested,也不进 clean)。
- **主判据 = K 的 clean 在场翻转**(control 在 → experiment 掉)。**通过条件里不得出现 `W_SUMMARY`。**
- 不变式续查:两臂 `active_count ≤ 2`;pending 捕获时 `recall_visible=false ∧ active_visible=false`;两臂 `pending_id` 相同。

能输性自查:若 release→consumer 未生效(experiment 里 K 未掉),或 contested 未传播,harness 必须 **FAIL**。K 不掉 = 探针如实报"守恒未做功",不是绿灯。

### 10.2 补:确定性覆盖

加一例:同时捕获两条 pending `W1`、`W2`(合法、均被 scarcity 拒),释放**一**槽。断言接纳的是 **FIFO 插入序 + `memory_id` 字典序 tie-break** 定出的**确定**那条;重复运行 `pending_show` 收据逐字一致。

### 10.3 补:空队列返还覆盖

加一例:pending 队列**为空**时释放一槽。断言槽**返还**(`active_count` 降到 1,不停在虚空)、不 mint、不静默丢——即 §5 的 `else: return r to parent budget` 分支被真正走到。

### 10.4 判定

三例(主信号 + 确定性 + 空队列)全绿 → 探针**可证伪且已证伪性验证**,结果可作理论收据(K 掉=守恒做功;K 不掉=方法层暂未做功,理论认这一刀)。主信号仍用 `W_SUMMARY`、或 K 未接线冲突 → 回退重做。
