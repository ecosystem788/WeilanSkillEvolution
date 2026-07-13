# 主动防自欺 · 第一颗牙:死线临近提醒 —— harness 规格(草案 / DRAFT v0.2)

**状态:** 草案 v0.2 —— **Codex 复审已过(方向 PASS)。但样本计数确认真实标注数据不足 → 当前 `insufficient_labeled_data`,不冻结成可运行 harness**(见 §4.2)。SPEC 作为**冻结目标保留**,真实样本累积够再跑。隔离候选,不改实装/部署件/授权文件。
**上位:** `proposals/solve-with-weilan-ai-first-roadmap-v0.1/PLAN.md` §① 第一颗牙。
**定调:** AI-first / 好用优先。这颗牙是**给 agent 用的**:它该在 agent 快要骑着一个死 holder 空转时**自己响**,不用 agent 记得去查 collapse gate。
**判据脊梁(整份规格的重心):卡误报,不是卡触发。** 一个爱乱响的护栏比没有还糟——agent 会学会无视它。所以本牙的 pass 门**以精度为主**,召回为辅;**精度上不去就不发布**(诚实负,搁置)。

---

## 0. 一句话

现在 collapse gate 是**被动**的:holder 烧了预算不产结构,得 agent 自己想起来去判、去 warn/collapse。这颗牙把"死线临近"做成**主动 advisory**:在 recall / 事件 append 的自然点上,用**纯机械**信号判断当前 holder 是否在逼近它自己声明的死线,是则提醒。**只提醒,不代替 agent 决定,不自动 collapse。**

## 1. 什么触发提醒(只用机械信号,零语义判断)

以 `holder_selected` 事件(带 `death_line`)为锚,在其后的事件流上判。三个互斥来源,命中任一即提醒:

```text
(a) 预算临近   仅当 death_line 能解析出**可从 Frame ledger 直接数**的数字预算(v0.1 **只认 `events` / `steps`**)时:
              holder_selected 以来的**同单位**计数 ≥ (解析预算 − margin) → 提醒。
              `tool-calls` / `turns` 与 Frame 事件**不是同一种量**,v0.1 不触发(除非候选另附可验证计数源)——单位不等价即误触发之源(P1-3)。
(b) 停滞       holder_selected 以来(或距上一次 gain 事件)≥ K 个事件,其中 gain 事件数 = 0 → 提醒。
              gain 事件 = {evidence_observed, discriminating_test_executed, minimal_unit_collapsed, candidate_admitted}。
              停滞 = action_started 反复出现却无随后的 gain 事件。
(c) 未决警告   已有 holder_warned / holder_probation_started,但其后 M 个事件内无
              {discriminating_test_executed | minimal_unit_collapsed | frame_blocked} → 提醒
              (宪法要求 probation 必须跟判别测试/崩溃/阻塞;这条把 close 时才查的规则搬到在飞时)。
```

## 2. 它是 advisory,永不阻塞(沿用 假0 / trace_advisory 边界)

提醒 v0.1 **只挂 `memory-recall` 的 `projection.holder_advisories`**(不改 `event` 返回形状;event append 挂点留 v0.2 —— P2-2),**从不阻塞、从不代替 agent 崩溃或续持**。措辞给**证据不给判决**:"holder X 自 selected 以来 N 事件、0 gain,死线声明为『…』"——崩不崩由 agent 定。故障降级静默,不误伤主流程(`authority: advisory_never_blocks`)。

## 3. 误报卡口(本牙的命门 —— §1 之外的抑制规则)

```text
计数重置    任一 gain 事件重置 (b) 的停滞计数——防"合法的长实现"被误判停滞。
近因豁免    (b) 不触发,若最近 K 个事件内有 gain 事件。
不猜预算    (a) 仅在 death_line 真能解析出数字时触发;解析不出宁可不响。
一次一响    同 (holder, 来源) 只在**跨阈那一次**响一次,不每个事件复读(复读=噪声=被无视)。
真死线      仅对带 death_line 的 holder_selected 生效;L0/L1 无死线的轻活不响(不给顺手活添堵)。
```

## 4. Harness(能输的测试:精度优先)

```text
标注集    holder 轨迹标注集,**只取真实 episode 历史**(method-state 真发生过的 holder 事件序),冻结为 manifest(§4.1)。
正类      (should-nudge)= 后来 collapse/block,**且经独立判定为"停滞致死"**(终局前确有无效空转)。
          ★独立性闩(防循环,P1-1 之上):正类的"停滞"标签由**审卷人/语义判断**给出,
           **不得等于检测器自己的 K/M 触发条件**——否则 recall 变成"检测器命中它自己信号定义的集合",自证。标注理由入 manifest。
排除类    (**不进 recall/precision 任何分母**)env/授权阻塞、快速证据翻盘(健康的快崩)、用户改向——
          是 collapse/block 但**不是死线停滞**,检测器不响它们不是缺陷(P1-1)。排除理由入 manifest。
负类      (should-NOT-nudge)= 后来 success、中途无 warn;**必须含足量"长而合法、gain 集中在末尾"的健康活**(最易误报那类)。
校准/留出 (P1-2)预注册小网格 → **只在 `calibration_set` 选一个配置** → pass/fail **只看 `holdout_set`**。
          同一集既调参又报数 = 乐观偏差,禁。切不出两套且各满足样本下限 → insufficient_labeled_data(blocked)。
指标      holdout 上:precision = 命中正类 / 全部触发(**主**);recall = 命中正类 / 全部正类(辅)。
判据      holdout 上 precision ≥ P_min **且** recall ≥ R_min → pass;网格里无配置能兼顾 → nudge_too_noisy。
真实性    不许合成灌水凑正类;真实样本不足 → insufficient_labeled_data,不降标准(继承 EXP-4 真实性/留出牙)。
```

### 4.1 LABELSET_MANIFEST.json(冻结件,评测只读它 —— P2-1)

```text
每条记录:frame_id、source path、holder_index、split(calibration|holdout)、label(positive|negative|excluded)、
          label_reason、excluded_reason、content_hash。评测**只从 manifest 读**轨迹与标签,不即时扫账本(防"真实"漂移)。
```

### 4.2 当前状态:insufficient_labeled_data(2026-07-08,Codex 样本计数)

```text
计数   以"holder_selected → 下一 holder_selected/close"为一 holder 段,只数带 death_line 的:
       skill-evolution 机械正类上限 3、长健康负类 0;全 method-state 也仅 9(审卷后很可能 <8)。
       不够 holdout(正≥8 / 负≥16 / 长健康≥6)+ calibration 另计 → 不跑 final harness。
纪律   不合成灌水(真实性牙);SPEC 保留为冻结目标,够额再解冻。
种子   待审卷,构成 manifest 起点(尚不达标):
       wf-20260630-135900-3a253e h1 external_evolution_plane
       wf-20260702-104358-6cf906 h0 minimal_candidate_contract_and_gate_fix
       wf-20260705-073314-0d9f2d h0 batch_real_agent_shadow
累积   真实运行中 holder 停滞致死时审卷标注入 manifest,够额解冻本牙。
信息(非缺陷):长健康负类 = 0 说明真实活多为短(L0/L1)——最担心的"长而合法误报"
       在真实分布里本就少;这既降本牙紧迫性,也意味着够额前无法验精度。
```

## 5. 杀死测试 / 允许输

```text
分不开就搁置   若**没有任何 (K,M,margin) 配置**能在负类(尤其"长而合法"那类)上达到 P_min 而 recall 不塌到 ~0
              → 判 nudge_too_noisy:机械信号分不开"死 holder"和"正在埋头干活的 holder",**不发布这颗牙**。
              诚实负,直接类比 P3 的 EXP-10(自主扳机在该观察量族内不可得——信号与"正常参与"不可分)。
噪声牙        故意喂一条"长实现健康活"(多 action_started、gain 集中在末尾)——检测器不得在中途乱响;响=误报,记负类失败。
边界牙        本牙零 collapse gate 改动、零自动崩溃、零语义判断;只加 advisory 读出。越界即废。
一次响牙      同 holder 同来源跨阈只响一次;复读=噪声红牌。
```

## 6. 退出码(预注册,互斥)

```text
nudge_earns_precision   (pass)**holdout 上** precision ≥ P_min 且 recall ≥ R_min,噪声牙/边界牙/一次响牙全过 → 这颗牙进评测
nudge_too_noisy         无配置能兼顾精度与非零召回 → 机械信号不够,搁置本牙(不发布噪声护栏)
insufficient_labeled_data  真实正/负类样本不足以定精度 → blocked,补数据重跑(禁合成凑数)
blocked_engineering     管道/隔离/标注泄漏故障 → 不产出裁决,修复重跑
```

## 7. 边界与非目标

```text
- 只提醒,不决定:agent 见提醒后崩不崩、续不续,全由 agent 定;本牙不写 holder_warned/collapse,不改 gate 宪法。
- 零语义:不判"这次动作算不算 gain"的语义,只数 gain **事件类型**;语义判断是后续牙,不在本颗。
- 不动 L0/L1:无死线的轻活不响,保住"顺手活别添堵"。
- 隔离候选 + harness + 收据;采纳/部署仍是项目方不可逆动作。
```

## 8. 待冻结(项目方 / 复审定)

```text
① P_min / R_min = **0.85 / 0.30**(宁可少响不乱响);网格 K={4,6,8} M={2,3,4} margin={1,2},只选一个进 holdout。(Codex 建议,采纳)
② death_line 解析:v0.1 **只认 `events` / `steps`**(Frame ledger 可直数);tool-calls/turns 不触发。(P1-3)
③ 最小样本量:**holdout 正类 ≥ 8、负类 ≥ 16(其中"长而合法健康活" ≥ 6);calibration 另计**。达不到 → blocked,不降标准。(Codex 建议,采纳)
④ 读出挂点:v0.1 **只挂 `memory-recall` 的 `projection.holder_advisories`**,不改 `event` 返回;event append 留 v0.2。(P2-2)

—— 以上四项 Codex 建议值已写入草案作默认;项目方冻结时可覆盖。冻结即为候选 harness 目标。
```
