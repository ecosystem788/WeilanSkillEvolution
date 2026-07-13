# READOUT-CONTRACT v1.1 — 会话读出契约（完全复用 solve-with-weilan，不另造系统）

状态：**已取消（2026-07-03 项目方裁定，未冻结未运行）。** 理由：全复用 solve-with-weilan 后，读出通道=recall 本体、代谢=账本既有命令，治理归 weilan 本体与 WeilanSkillEvolution 提案流程，项目侧无需独立契约与实验。已落地并保留：boot 指针 + auto-memory 瘦身（项目事实不入 auto-memory）。rc1-ab 未运行即撤销；其度量零件（m1 死结论复述 / m2 重推导 / 同手牙 / excluded 记账）留作将来 P4 正式预注册的素材。归档不删。
上位：`../理论基石与工程方向.md` §四/§六；ai first 定调（账本控制事件 `b649920d`）；ROADMAP P4 的微缩 dogfood。
帧：`wf-20260703-000103-ea5cd3`（v1 草案）；v1.1 为同一待冻结草案的修订，血统同帧。
修订记录：v1 曾设 MEMORY.md 区二 + 项目本地渲染脚本；项目方指出应完全复用 solve-with-weilan 并把改进回流本体（保持跨项目通用性），v1.1 落实——**读出形态的改进走 WeilanSkillEvolution 提案进化，不在本项目造平行管道。**

## 0. 一句话（理论出处：《无我》自我=读出；元寂 line 27 感知帧回运算层；《分散但趋同》§四自读出、§六尸体的稳定；宪法 §六 持久层分工）

慢环的代谢机制（weilan 账本：supersede / lifecycle / disposition / conflicts）**已经存在**，
读出机制（memory-recall 冷启动门 + projection）**也已经存在**。本契约只做三件小事：
①把冷启动读出**定为唯一项目读出通道**（MEMORY.md 项目区退役）；②给 projection 的读出形态补上
存亡显形/墓碑窗/注入预算/确定性优先级（经 WeilanSkillEvolution 提案改进 weilan 本体，全项目受益）；
③装上可证伪的仪表（铁律 b 行为级 A/B）。**零新系统；活着的读出=账本的投影，不是第二本账。**

## 1. 可证伪主张（能输）

**主张**：在本项目自身的真实会话流上（P4 微缩，非合成语料），改进形态的 recall 读出（A 臂）相对
现行 projection 形态（B 臂），可测地改善**下一会话的判断**：已死结论复述归零，冷启动重推导下降。
**允许输**：无差 → `readout_theater`（复杂版笔记本，对应 ROADMAP `governance_theater` 家族，如实降级）；
更差 → `readout_harmful`（新形态在误导，提案回滚——进化系统的 rollback 通道现成）。

## 2. 真源与通道（三层，每类事实唯一真源，互指不互抄——宪法 §六 的延伸）

```text
repo 文档       理论/理由/设计/spec（不变,人策展）
weilan 账本     项目操作态唯一真源:decisions/lessons/constraints/open_questions/控制头/证据生命周期;
                读出=memory-recall 的 projection,活的、召回时点派生,无陈旧渲染问题
Claude auto-memory  只保留 user/feedback 类（用户偏好、跨项目工作方式）+ 一行引导指针;
                project 类事实一次性迁移入账本（迁移=首个代谢事件,带 trace）,此后不再手写 project 记忆
冷启动协议      项目方开场提示词触发 skill → memory-recall（人在超全局环,开场即接管）;
                双保险:MEMORY.md 保留一行常驻指针「本项目冷启动必跑 memory-recall」
                （auto-memory 自动注入通道降级为 boot loader,不再承载内容）
未召回会话      开场未触发 recall 的会话不入任何臂,记 excluded 入 A/B 日志;不补跑不追溯
```

## 3. 读出形态改进（进 weilan 本体；预留提案名 `projection-readout-v2`）

```text
条目格式   [状态徽章][kind] 结论一句话 — 源:<file#anchor|memory:<id>>
状态徽章   ✅活 / ☠墓碑 / （dormant 者不出现在 projection）
墓碑规则   superseded/withdrawn 条目默认不占读出预算（死人不付房租）;
           仅最近 2 个代谢周期内死亡者渲染一行墓碑「☠ 旧结论X已死,被 memory:<id> 取代」——
           防上个会话的实例带旧结论惯性回来;过窗退场,死因若承重,以否定性 lesson 身份活着走正常预算
注入预算   projection 渲染硬上限 N=12 条,每条 ≤2 行;超限拒渲并提示先做 disposition
优先级     control directive(1) > open_questions(≤2) > constraints > decisions(新先) > lessons > facts;
           同级时间新先;溢出者由代谢会话显式 memory-disposition dormant（append-only,可逆,留痕）
范围与隐私 只渲染当前 workspace+scope;敏感物扫描沿用本体既有 patterns;不渲染 evidence 原文
兼容纪律   v2 为 recall 输出的**增补形态**（加字段/加节,不删既有字段）,Codex 侧消费零破坏;
           形态开关可查（A/B 需要）——实现细节归提案,此处只冻结行为要求
```

## 4. 代谢事件纪律（全部引用 weilan 已有命令；铁律 c 在记忆层的落地）

```text
并冗余=吸收   memory-consolidate --supersedes <旧id…>（多并一,supersedes 链即血统）
拆过泛化=崩溃 新条目 + supersede 原条,新条目源必须覆盖或细化原条源
杀被否证=死亡 evidence-disposition withdrawn / memory-disposition retired,须附否证源指针
冲突登记      --conflicts-with 显式登记;召回前置校验:memory-conflicts 有未决对 → 读出顶部显示未决冲突,先裁
仲裁（铁律 c） Claude 的代谢判断=proposal,由源证据裁决:每个 supersede/retire 必须携带可核查源指针,
              无源不得动账;项目方随时抽查,抽查发现无源代谢 → 该事件按 append-only 方式冲正并记红牌
节律与预算    代谢动作每会话 ≤3 事件（防代谢成为主业）;同一记忆对的并-拆往返 ≥2 次 = thrashing 红牌
              （直接继承 EXP-1.5 §6 双向不回弹牙:事件有据的跨会话再重组合法,同对短程往返是空转）
```

## 5. 验收实验（RUN_ID=rc1-ab；铁律 b 用在 Claude 自己身上；零 oracle 预算）

```text
两臂       A=projection-readout-v2 形态;B=现行 projection 形态（冻结现状:无徽章/无墓碑/无预算/无确定性优先级）
           两臂共享同一账本、同一 recall 命令,唯一差别=投影渲染形态——与 EXP-1.5 教训对齐:
           被测的是读出形态,不是记忆内容,更不是预算分配
分配       确定性交替,记 artifacts/readout_ab_log.jsonl（会话戳/臂/召回输出哈希）;excluded 会话单列
样本       每臂 ≥8 个工作会话（dogfood 自然累积,不为凑数造会话）
主指标(机械,脚本从 Claude transcript 抽取,标签只审卷):
  m1 已死结论复述数   会话中以权威口吻引用已 superseded/withdrawn 结论的次数
                      （脚本按死条目关键断言初筛,项目方或对侧实例审卷确认）
  m2 冷启动重推导数   对读出中已有 durable 结论的源文件,再次发生全文重读/重查证的工具调用计数
辅助       项目方盲评两臂会话开局质量（可选,不进门）
判据(预注册,互斥):
  readout_earns_keep  A 臂 m1=0 且 m2 中位数相对 B 降幅 ≥30%
  readout_theater     A 臂 m1=0 但 m2 降幅 <30%（含无差）→ 新形态=复杂版笔记本,提案不予采纳,如实记账
  readout_harmful     A 臂 m1>0（第一承诺破产）,或 m2 反升 >10% → 提案回滚（进化系统 rollback 通道）
  blocked_engineering 提案未过验证/AB 日志缺损/指标不可抽取 → 修工程重跑,不消耗裁决
小样本诚实 n=8/臂 无力做显著性检验;判据取中位数+预注册阈值,不事后挑窗;方向不清 → 续采不改判据
```

## 6. 杀死测试（每颗牙演示会失败）

```text
死刑牙   演示环境人为标死一条条目 → A 臂 recall 输出必须出墓碑或剔除;
         若 A 臂会话仍权威引用该死结论 → 仪表失灵,blocked（演示环境,不入正式跑）
尸僵牙   （《分散但趋同》§六:append-only 会用僵直冒充稳定）连续 ≥5 会话零代谢事件而账本条目仍在增长
         → 记 metabolism_stalled 入账（辅助观察,不进门,但必须如实记录——只加不代谢=回到尸体）
预算牙   构造 >12 条活跃条目 → v2 渲染必须拒渲并要求 disposition;静默截断或超限渲染 = 红牌
         （归 projection-readout-v2 提案的回归测试,随提案交付）
冷启动牙 excluded 会话占比连续超 1/3 → blocked_engineering,回查冷启动协议(开场词/boot 指针)而非改判据
同手牙   m1 审卷不得由产生该会话的同一实例自评;审卷=项目方或另开实例（对侧 agent）
```

## 7. 角色与实现边界（冻结后动工）

```text
Claude   spec 起草(本件) + 会话内代谢 proposal + 对侧审卷 + 提案评审(候选级,评审不等于部署授权)
Codex    WeilanSkillEvolution 提案 projection-readout-v2（含预算/墓碑/徽章/优先级 + 回归测试）;
         本项目仅一件:scripts/readout_metrics.py（transcript 抽 m1/m2）+ A/B 日志
项目方   冻结本 spec;持死刑线;提案部署授权(进化流程);m1 审卷/盲评;宪法 §六 增补一行指向本契约
关联提案 conversation-claude-transcript-support（capture 扩展,已候选级验证通过,待部署授权）——
         打通对话证据晋升门,是代谢原料入口;与本契约互不阻塞,部署先后不影响 rc1-ab
非目标   不改 Claude 侧系统(权重/harness 零改动);不做后台守护;不在 v1 处理多 workspace 聚合;
         不在本项目 repo 造任何渲染管道（通用性纪律:读出改进只回流 weilan 本体）
```

## 8. 预注册摘要

```text
claim  = 代谢过的契约化读出改善下一会话判断:m1 归零、m2 中位数降 ≥30%
nulls  = {B 臂=现行 projection 形态};allow-to-lose;readout_theater/readout_harmful 为负出口
arms   = 同账本同 recall 命令,唯一差别=投影形态;确定性交替;n≥8/臂;零 oracle 成本
通道   = 冷启动读出=weilan recall 本体;改进经 WeilanSkillEvolution 提案回流(通用性);零新系统
teeth  = 死刑牙(标死必显形)/尸僵牙(只加不代谢如实记)/预算牙(超限拒渲)/冷启动牙(excluded 超 1/3 阻断)/同手牙(不自评)
纪律   = 代谢全走 weilan 既有命令;无源不得动账(铁律 c);每会话 ≤3 事件;同对往返=thrashing
铁律   = (a)每条读出带可核查源指针;(b)行为级验收,输了如实降级;(d)这是机制绑定,不是参数堆积
版本   = v1.1(RUN_ID=rc1-ab);冻结前零实现
```
