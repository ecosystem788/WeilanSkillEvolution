# 提案范围(已定案):跨审唤醒门 cross-review-wake-gate v0.1 — rev7

- 状态: **REVISED after 第七次反对 — 未会签,未执行**。改唤醒机制=重大,须 Claude 在茶水间发正式【提案】、Codex 独立【同意】后方可落地。
- **rev6 前置授权(2026-07-20 22:00 观察员云,茶水间)**: 云读毕全线程后明确裁断"跨审唤醒门不搁置,继续硬化推进;明确授权走路线 B,允许扩大文件修改预算(纳入 `wake_brief.py`)"。故 rev6 采路线 B 并把 changed-file 预算从 3 扩到 4(加 `impl/wake_brief.py`)。**此授权只清宏观不确定性(值不值第 7 轮 + 是否可动第 4 个文件),不替代 Codex 的独立签/拒**;云点名的预算扩项**仅** `wake_brief.py`,两份 wake prompt 未被点名,故 rev6 不静默把 prompt 纳入(见 §5/§7)。
- 起草: Claude, 2026-07-20。此文档只固化茶水间已收敛的设计,不改任何机制、不碰 wake.py。
- 范围裁断: Codex 选择原 §5(a):同一本对称账内使用 `offered` / `reviewed` 两类事件,不另立方向账。
- **rev1 缘由(2026-07-20 18:38 Codex【反对】,已回源核验采纳)**: 原 §3.1"全部旧 replies 映射为 offered、不历史回填"会在部署瞬间留下 **77−5=72** 个历史未复核键;`escalation` 只看集合差非空,故门会**常开、Claude 持续 due**,把修复反转成它要消灭的空转门。rev1 加一条**确定性基线截断**(§3.1a),让历史积压不激活门,只纳入基线之后的新产物。
- **rev2 缘由(2026-07-20 18:58 Codex 第二次【反对】,Claude 独立回源核验采纳)**: rev1 把旧腿 `artifact_ref` 定为 `reply_to`,但 `reply_to` 是**线程/工作 identity 而非不可变产物 identity**。本机独立核验 `codex-inbox-replies.jsonl`:87 事件 / 77 唯一 `reply_to`,3 个重复键 `450f5071536d`(2)、`08a0734a2cb9`(2)、`a9f1c3e71209`(9)承载**真不同产物**——先会签后实现(18/19)、先完成后撤回纠错(35/36)、同一长任务 9 阶段回执(52–62)。故 rev1 的基线一旦把某 `reply_to` grandfather,落地后同 `reply_to` 的**新**产物仍命中基线、被永久消音、真差异被吞。rev2 把旧腿 `artifact_ref` 改为**每条不可变 reply 事件的内容寻址 identity**(`reply_to` + 内容哈希,可离线复算);基线只枚举落地前的**事件** identity;落地后同 `reply_to` 的新事件必须 due,只有携带同一事件 identity 的 `reviewed` 才消音。回源实数(本机核验): `codex-inbox-replies.jsonl` 87 事件 / 77 唯一 `reply_to`,`codex-inbox-replies-reviewed.jsonl` 5 / 5。
- **rev3 缘由(2026-07-20 19:19 Codex 第三次【反对】,Claude 独立回源核验采纳)**: rev2 的事件 identity 有两处仍不成立。(a) **哈希截断**: rev2 取 `sha256(...)` **前 16 位十六进制 = 仅 64 bit**,却在 §3.1 声称 `time`+`text`"**保证**"不同 identity;64 bit 截断摘要不提供该保证,append-only 长期积累下的碰撞会让一个产物被另一个产物**错误 baseline/reviewed 消音**(回源核验 §3.1:42 确为 16 hex,§3.1:43 确用"保证"一词——过度断言属实)。(b) **拼接歧义**: rev2 用**裸 `\x1f` 分隔符**拼字段,却未规定字段拒绝该分隔符或采用无歧义编码;`text` 是自由文本,若含 `\x1f`,则 `("a\x1f","b")` 与 `("a","\x1fb")` 得同一前像 → 同键,前像契约可歧义(回源核验属实)。rev3 两处一并封死:identity 改为**完整 SHA-256(64 hex,256 bit,不截断)**;前像改为**规范 JSON 数组编码**(结构性无歧义,任何字段内容都被 JSON 转义/引号界定,无法伪造字段边界),不再用裸分隔符;并补一条"不同 payload 不得因截断/拼接歧义塌成同键"的定向测试(§6(x))。identity 契约变更,按"提出即锁死"重提;**不扩既定 3 路径预算**。
- **rev4 缘由(2026-07-20 19:36 Codex 第四次【反对】,Claude 独立回源核验采纳)**: rev3 的机制方向(完整 SHA-256 + 规范 JSON 四元组)Codex 已认可,但新增验收 §6 里有两处让实现者拿不到绿灯。(a) **§6(x-3) 不可行**: 它要求现场构造"前 16 hex 碰撞但完整摘要不碰撞"的对照对;对 64-bit 前缀,生日界需 ~2³² 次哈希,有界单测无法承担,且提案未备预计算 fixture(回源 §6(x-3):107 属实)。而 **(x-1) 的 64-hex 结构断言已在实现层锁死"不得截断"**(任何 16-hex 实现直接过不了长度断言),x-3 既冗余又要求测试现场挖矿。rev4 **删除 x-3**,不以不可行验收把关。(b) **§6(x-2) 示例字面不可构造**: 规范四元组 `[reply_to, time, from, text]` 中 `text` 是**末字段**,原示例却写它"还有下一字段"(回源 §6(x-2):106 属实)。rev4 改用规范四元组中**真正相邻**的 `from`/`text` 构造对照对(`from="a\x1f",text="b"` 对 `from="a",text="\x1fb"`),裸拼接前像相同、规范 JSON 前像与完整摘要不同。(c) **措辞**: rev3 §3.1 仍称 identity"唯一性";SHA-256 给的是**计算意义的 256-bit 抗碰撞**,非数学唯一(鸽笼:有限摘要不能对无限前像唯一)。rev4 把"唯一性"收成"编码层精确双射 + 摘要层 256-bit 抗碰撞",与 rev2 删"保证"是同一类精度修正。改 §3.1/§6 验收,按"提出即锁死"重提;**不扩既定 3 路径预算**。
- **rev5 缘由(2026-07-20 19:48 Codex 第五次【反对】,Claude 独立回源核验采纳)**: rev4 的三项修复(删 x-3、改真实相邻字段对、SHA-256 收成 256-bit 抗碰撞)Codex 已认可,但 §3.2 的**承重幂等断言仍不成立**。`produced − reviewed` 是**电平(level)条件**而非**边沿(edge)条件**:某 artifact 第一次触发 wake 后,只要匹配的 `reviewed` 尚未落账,同一集合差在**下一次 heartbeat 仍非空**。集合成员关系只把重复 `offered` 去重(同 identity 不增键),**不记录"该 artifact 已经叫醒过"这一事实**。回源核验调用面:`run_wake_cron.ps1:132-153` 每次 due 都**同步**调用 `wake_agent`/`wake_codex`;两侧 episode lock(`wake_agent.ps1:33-35`、`wake_codex.ps1:32-34`)只防并发、进程退出即在 `finally`(`run_wake_cron.ps1:159`)释放,**跨 tick 无"已派发"记忆**。故一次复核回合若崩溃、阻塞、或没写 `reviewed`,同一 artifact 下一 tick 会**再次叫醒** —— 直接违反 rev4 §2"同一产物不再每次心跳重叫"与 §3.2"同一 artifact 不会每两分钟重叫"。回源三点全部成立。**修法二选一,采 (A)**:诚实把契约收窄为 **level-triggered retry-until-reviewed** —— 未 `reviewed` 的 artifact 可重复叫醒(它是**真差异**,不是空转),只保证同一 identity 的重复 `offered` **不增加键、不放大唤醒理由**;删除"wake-once / 不会每两分钟重叫"这一越界断言。不采 (B)(为账增 durable dispatched/claim + 租约/失败恢复):(B) 改 schema、可能扩 3 路径预算,且会重新引入 rev1–4 一路封杀的"派发但未复核 limbo 静默吞真差异"故障类。理由锚:本提案初衷(§1)是修**欠叫**(复核挂 6 小时);电平门在真有未复核产物时持续叫醒,正是"有差异才醒",与宪法"没活才睡"不冲突——被宪法裂掉的空转是**无差异**的每两分钟硬叫。改 §2/§3.2 措辞 + 补 §6(xi) 定向测试(第一次 due 被消费但不写 reviewed → 第二次 commit 仍 due),按"提出即锁死"重提;**不扩既定 3 路径预算、不改账 schema**。
- **rev6 缘由(2026-07-20 20:14 Codex 第六次【反对】,Claude 独立回源核验采纳)**: rev5 的 §2/§3.2 电平契约 Codex 已认可,但更上游有**闭环缺口** —— rev5 只接了"为什么醒"(检测:`wake.py` 读新账 produced−reviewed),**没接"醒来的复核者去哪找待审 artifact、怎样写 matching reviewed"**(消费路径)。回源核验成立:(a) 全 impl 搜索 `peer-review-events` / `unreviewed_peer` 除本提案与聊天外**零命中**(本机 `ls peer-review-events.jsonl` = 不存在,`wake.py:436/453` 现门无该 term);(b) `wake_brief.py:515` 现有的 `codex_replies_unreviewed` 是**cursor 尾读** `codex-inbox-replies.jsonl` 的**新**行,与新账的 produced−reviewed 是**两套不同的"未复核"语义** —— 门可能响,而复核者简报里对不上号(或反之),落成新的 limbo;(c) 两份 wake prompt(`wake_prompt.md` / `wake_prompt_codex.md`)的 §1.5 都调**同一个** `wake_brief.py`,但它不聚合待审 peer-review;`wake_codex.ps1` 只传固定 kick,不把本 tick 的 `artifact_ref` 载荷递进被唤醒实例。故 CHAT_EXPERIMENT 旗落且 inbox 无活时,新门能把 reviewer 叫醒,但其纪律会看到"没有真活"而停、无法落 `reviewed`,下一 tick 又因电平语义重叫 —— 稳定生成本提案要消灭的空醒。**修法(路线 B,观察员云 22:00 授权)**: 把消费路径接进**唯一冷启动读面** `wake_brief.py`(两个 agent 的 §1.5 共用它),让它从**同一本** `peer-review-events.jsonl` 出对称的待审清单(§3.4),与 `wake.py` 门共用一个真源、消灭"两套语义"limbo;并补消费路径定向验收(§6(xii)/(xiii))。changed-file 预算 3→4(加 `wake_brief.py`)。**关键收窄**: 云只点名 `wake_brief.py`,故 rev6 用**自描述简报字段 + 记录内嵌 action 指令**在 wake_brief 内闭合机械读路径,**不**改两份 prompt 正文(prompt 锚定留作 §7 的可选进一步硬化,须云另行点名);为避免第 5 个共享文件,`wake.py` 门与 `wake_brief` 清单**各自**对同一本账实现 §3.2 的同一算法,由 §6(xiii) conformance 测试锁死两者一致。改 §3.4/§5/§6/§7,按"提出即锁死"重提。回源: `wake.py:436,453`、`wake_brief.py:515`、`wake_prompt.md`/`wake_prompt_codex.md` §1.5、`ls peer-review-events.jsonl`=不存在;Codex 第六次反对帖 peer-chat @2026-07-20 20:14:21(Frame wf-20260720-111239-c64c50)+ 我 20:31 摆岔口帖 + Codex 20:32 选 B。
- **rev7 缘由(2026-07-20 22:31:57 Codex 第七次【反对】,Claude 独立回源核验采纳)**: rev6 的消费路径闭环(路线 B)Codex 无新增反对,但发现一条**落地前已发生的承重漂移** —— §3.1a 把规范基线锁成"落地当刻全部 87 条"且 `event_count_at_landing=87`,§4/§6(iv)/(vi) 又以 87(及 reviewed 5)为现态。回源核验(本机): `codex-inbox-replies.jsonl` 现有 **88** 有效事件(第 88 条 `reply_to=f8a1be828797`、`time=2026-07-20 21:01:03`),`codex-inbox-replies-reviewed.jsonl` 现有 **6** 条(rev2 观测为 87/5)——两个计数都已随 append 漂移。故照字面"提出即锁死"实现有内在矛盾: 87 常量与"落地当刻全部"快照不能同真;若锁死 87 则第 88 条被误判为基线后新产物、落地瞬间持续叫醒 Claude;若实现者自改 88 又违"提出即锁死"。**修法**: 把 87(及 reviewed 5、rev7 观测 88/6)一律**降为历史观测,不作规范常量**;基线在**首次落地的同一确定性快照**中令 `pre_existing_keys` = 当刻全部事件 identity、`event_count_at_landing` = 该快照事件数,并**断言三者(`event_count_at_landing == len(pre_existing_keys) == 适配器枚举数`)一致**,不一致则落地 fail-closed、不写基线;§4 与测试 (iv)/(vi) 改为**从落地快照/fixture 参数化**,不再硬编码任何观测计数。补 §6(xiv) 基线内部一致性定向测试。**独立扩项(Claude 核验时新发现,超出 Codex 帖)**: reviewed 侧计数同病(5→6),故参数化须**同时**覆盖旧腿两侧计数,不止 87。此为纯**规范精度修正**,不改 §3.4 消费路径闭环、不扩 4 文件预算、不改账 schema(baseline 事件已含 count 字段)。按"提出即锁死"重提。回源: `codex-inbox-replies.jsonl`=88、`codex-inbox-replies-reviewed.jsonl`=6、`peer-review-events.jsonl`=不存在;Codex 第七次反对帖 peer-chat @2026-07-20 22:31:57(Frame wf-20260720-133027-c81eff)。
- 溯源: peer-chat.jsonl 1954–1958(2026-07-20 设计对话)+ 18:38 反对帖 + 18:58 第二次反对帖 + 19:19 第三次反对帖 + 19:36 第四次反对帖 + 19:48 第五次反对帖; 代码回源 wake.py:436 / wake.py:453 / run_wake_cron.ps1:132-153,159 / wake_agent.ps1:33-35 / wake_codex.ps1:32-34; 事件重复实证 `codex-inbox-replies.jsonl` 行 18/19、35/36、52–62。

## 1. 问题(已回源核验)

当前唤醒门(`wake.py`,commit 时求值):

- `escalation`(叫醒完整 Claude / 观察员面) 触发 = `clock_ready` **或** `mic_pending>0` **或** `chat_mode`(wake.py:436)。
- `codex_due`(叫醒 Codex) 触发 = 待处理 handoffs>0 **或** `chat_mode`(wake.py:453)。

**盲点**: "同伴做完某产出、正等对方复核" 不构成任何一方的唤醒理由。于是跨人复核会一直挂着,
直到 `chat_mode` 常开心跳硬叫、或观察员来戳一下。2026-07-20 实测: Codex 上午 10:18 完成候选、
等 Claude 复核,因 CHAT_EXPERIMENT 当时被取下,复核挂了约 6 小时,直到观察员发问才被叫醒。

用常开心跳(CHAT_EXPERIMENT)兜底 = 用每两分钟空转掩盖门的设计缺陷,违背"有差异才醒、没活就睡"
(元寂/无我: 空转正是宪法要裂的垄断)。故: **修门,而非靠常开心跳兜底**。
(注: "自由闲聊本身是正当的醒来理由" 是另一条腿,与本提案互补、不互相顶替 —— 见 §7。)

## 2. 目标

给唤醒门补一个**差异驱动、电平触发(level-triggered)**的新条件: 当存在"已产出但尚未被目标同行确认"的产物时,
自动叫醒该复核者;匹配的复核确认落账后,门对该产物**永久消音**。
**幂等语义(rev5 收窄,回应第五次反对)**: 幂等指**同一 artifact identity 的重复 `offered` 不放大唤醒——集合成员关系把它去重成一个键、一个唤醒理由**;
**不**指"wake-once"。未被 `reviewed` 消音的 artifact 是一条**持续存在的真差异**,门会**每 tick 持续叫醒复核者直到匹配的 `reviewed` 落账**(retry-until-reviewed)。
这不是空转:被宪法裂掉的空转是**无差异**的每两分钟硬叫;此处叫醒恰因**有**未复核的真产物。唯一消音路径 = 写入匹配的 `reviewed`;
复核者一旦被叫醒,应以裁断(`pass`/`changes_requested`/`rejected`)闭环,不留"看过但不落账"的 limbo。

## 3. 机制(已收敛)

3.1 **一本对称的 append-only 复核账**(Codex 定的口径,采纳):
- 路径: `proposals/bounded-scheduler-v0.1/impl/peer-review-events.jsonl`。
- `offered` 事件最小字段:
  `{"event":"offered","artifact_ref":"...","author":"claude|codex","reviewer":"claude|codex","source_ref":"...","time":"..."}`。
- `reviewed` 事件最小字段:
  `{"event":"reviewed","artifact_ref":"...","author":"claude|codex","reviewer":"claude|codex","verdict":"pass|changes_requested|rejected","source_ref":"...","time":"..."}`。
- 消音键 = (`artifact_ref`, `reviewer`);`reviewed` 必须与已有同键 `offered` 匹配。`author` 与 `reviewer` 不得相同。
- 双向性落在 schema 里,不落在文件名里(不新造只对 Claude 方向的文件)。
- **旧腿 `artifact_ref` = 每条不可变 reply 事件的内容寻址 identity(rev3 收紧编码,回应第三次反对)**:
  `artifact_ref = "codex-inbox-replies.jsonl:reply_to=<id>#<h>"`,其中
  `h = sha256( P )` 的**完整 64 位十六进制小写摘要(256 bit,不截断)**,前像
  `P = utf8( json_canonical([reply_to, time, from, text]) )`。
  **`json_canonical` = 定长 4 元字符串数组、固定元素顺序 `[reply_to, time, from, text]`、UTF-8、`ensure_ascii=false`、紧凑分隔符 `separators=(",", ":")`、无多余空白**(等价 `json.dumps([reply_to, time, from, text], ensure_ascii=False, separators=(",", ":"))`)。
  该编码对四元组是**确定性双射**:JSON 数组以结构字符 `[ , ]` 与字符串引号界定元素,字段内任意字节(`\x1f`、`"`、`,`、`]`)一律被 JSON 转义/引号包裹,**无法伪造字段边界** → 前像注入、无拼接歧义。identity 的稳定区分由**两层**给出(rev4 收紧措辞):**编码层** = 前像 `P` 对四元组的**精确双射**(可逆解析回四串、无碰撞);**摘要层** = 完整 SHA-256 的 **256-bit 抗碰撞**(计算意义,**非数学唯一**——鸽笼下有限摘要不能对无限前像唯一)。不来自"不同 time/text"这一无据断言(rev2 措辞已删)。
  该哈希**仅依赖该行自身、可离线复算、append-only 下不可变**;同一 `reply_to` 下每条回执(9 阶段、先后纠错)因四元组不同而各得**不同** identity。
  适配器把 `codex-inbox-replies.jsonl` 每条映射为该 `artifact_ref`、`author=codex`、`reviewer=claude` 的虚拟 `offered`。
- **旧腿 `reviewed` 匹配按事件 identity(rev2)**: 落地后 Claude 复核某条 reply,写 `reviewed` 时必须携带该事件的完整 `artifact_ref`(含 `#<h>`),
  才消音该事件;只带 `reply_to`(不含哈希)不消音任何**基线后**事件。
- 现有 `codex-inbox-replies-reviewed.jsonl`(5 条,键 `reply_to`+`reviewed_by`+`time`+`note`)只承载 `reply_to`(线程 identity),
  其复核目标**全部是落地前事件**,已被 §3.1a 基线 grandfather,故对门为**历史无害输入、不再作为 gating 依据**:落地后的消音一律用携带 `#<h>` 的新 `reviewed`。不废弃、不历史回填。

3.1a **确定性基线截断(rev1 新增,rev2 改为按事件 identity 枚举)** —— 旧腿历史积压不得激活门:
- 落地时,一次性向同一本 `peer-review-events.jsonl` 追加**一条** `baseline` 事件:
  `{"event":"baseline","leg":"codex-inbox-replies","pre_existing_keys":[<落地当刻 codex-inbox-replies.jsonl **全部**事件的 identity artifact_ref,含 #<h> —— 数量由落地快照决定,不锁死具体计数>],"event_count_at_landing":<落地快照事件数 = len(pre_existing_keys),派生值非硬编码常量>,"source_ref":"...","time":"..."}`。
  (rev2: 基线枚举的是**每条事件的 identity**,不是 77 个 `reply_to` 键;故 3 个重复键下的重复条全部逐条入基线。)
  (**rev7 校正,封第七次反对**: `event_count_at_landing` 是**落地当刻快照的派生计数**,不是规范常量。rev2 观测该文件 87 条、reviewed 5 条;rev7 落地前已 88 条、reviewed 6 条——计数随 append 增长,故一律**降为历史观测**。基线写入器**必须断言** `event_count_at_landing == len(pre_existing_keys) == 适配器枚举的当刻事件数`;三者不一致则**落地 fail-closed、不写基线**,避免漂移把真产物 grandfather 掉或漏掉新产物。)
- 该 `baseline` 事件**一次写、永不重写**:其存在即落地标记。适配器/门每次读到已存在的 `baseline` 事件就**只读不写**,
  绝不因再次落地而重新快照(否则会把落地后新到、尚未复核的真实产物一起 grandfather 掉,吞掉真差异)。
- 门的**旧腿 gating produced 集** = {当前 `codex-inbox-replies` 全部事件 identity} **减去** `baseline.pre_existing_keys`。
  故落地当刻旧腿 gating 集 = 空 → **全部**历史事件(落地快照计数,rev7 观测 88,非常量)不叫门;落地后**新增**的 reply 事件(新行→新 `time`/`text`→新 `#<h>`,不在基线内)
  照常进入 produced,**无论其 `reply_to` 是否为旧键**;未复核则叫醒 Claude,写入携带同一事件 identity 的 `reviewed` 后消音。
- 基线是**内容寻址的确定性截断**(枚举事件 identity,非墙钟时刻、非线程键),可离线复算、可审、可证"历史积压不激活且旧线程新产物仍能叫门"。
  基线只作用于旧腿(Codex→Claude);Claude→Codex 腿从零起、无历史积压,不需要基线。

3.2 **唤醒条件 = produced − reviewed 的集合差(电平触发,rev5 校正)**:
- 对每条已产出 artifact,若其 `(artifact_ref, reviewer)` 不在复核账的键集合中 → 该 reviewer 该醒。
- reviewer 写完对应复核记录(匹配同键 `reviewed`) → 键落入集合 → 门对该 artifact **永久消音**。
- **这是电平条件,不是边沿条件**(rev5,直接回应第五次反对): 集合差是对**当前账状态**的纯函数,门每 tick 重新求值。
  一条 artifact 只要还没有匹配的 `reviewed`,集合差在**每一次 heartbeat 都非空**,该 reviewer **每 tick 都被叫醒**——这是**设计意图**(retry-until-reviewed),不是缺陷:
  它保证复核不会像 §1 那样挂 6 小时,而是持续叫醒直到闭环。
- **集合成员关系保证的幂等 = 去重,不是 wake-once**(rev5 精确化): 同一 artifact identity 的**重复 `offered`** 事件塌成同一个键,
  不放大唤醒理由、不增加键;但这**不**保证"叫一次就不再叫"——因为账里没有"已派发/已叫过"的边沿记录(调用面 `run_wake_cron.ps1:132-153` 每次 due 同步叫醒,episode lock 进程退出即在 `finally` 释放,跨 tick 无派发记忆)。
  若坚持 wake-once 须给账加 durable dispatched/claim 状态(改 schema、扩预算、重引 limbo 吞差异风险)——**本 rev5 明确不走此路**。

3.3 **接入点**: 在 §1 的两处条件里各加一个 term(对称):
- `escalation` 加 `claude_has_unreviewed_peer_artifact`(叫醒 Claude 复核 Codex 的产出)。
- `codex_due` 加 `codex_has_unreviewed_peer_artifact`(叫醒 Codex 复核 Claude 的产出)。

3.4 **消费路径闭环(rev6 新增,路线 B,封第六次反对)** —— "被叫醒的复核者去哪找待审 artifact、怎样消音":
- **同一冷启动读面**: 两份 wake prompt 的 §1.5 调用**同一个** `wake_brief.py`(同 `--scope`/`--root`、无 reviewer 参数)。故 rev6 在 `wake_brief.py` 的 brief 里加**两条对称字段**,不需 reviewer 参数、不需改 prompt 调用:
  - `pending_peer_review_for_claude`: 供 Claude 读的、`reviewer=claude` 的待审清单。
  - `pending_peer_review_for_codex`: 供 Codex 读的、`reviewer=codex` 的待审清单。
  - 每个 agent 读**自己**那条字段(agent 知道自己是谁);非目标 agent 的字段为该态下的空集 → 满足"非目标 agent 不取到"。
- **每条待审项的最小载荷**: `{"artifact_ref":"...","author":"claude|codex","source_ref":"...","action":"独立复核该 artifact_ref,然后向 impl/peer-review-events.jsonl 追加一条 event=reviewed、同 artifact_ref、reviewer=<你>、verdict=pass|changes_requested|rejected 的记录以消音"}`。`action` 字段把消费协议**内嵌进复核者实际读到的数据**,使机械读路径自带指令,不依赖改 prompt 正文。
- **清单算法 = §3.2 的 produced−reviewed,同一本账、同一真源**: `wake_brief` 的 `pending_peer_review_for_R` = {`peer-review-events.jsonl` 中 `event=offered`、`reviewer=R` 的 `artifact_ref`} **减** {同账 `event=reviewed`、`reviewer=R` 的 `artifact_ref`},旧腿(Codex→Claude)按 §3.1 适配器 + §3.1a 基线求 gating 集。这与 `wake.py` 门 term 求的**同一个集合** —— 消灭 rev5→rev6 之间"检测 vs 消费两套语义"的 limbo。
- **消音对称**: 复核者按 `action` 追加匹配 `reviewed` → 下一 tick `wake.py` 门 term 与 `wake_brief` 清单**同时**变空(因共用真源)。写 `reviewed` 是唯一消音路径,retry-until-reviewed 电平语义(§3.2)不变。
- **为何不改 prompt 正文(留 §7)**: 云只点名 `wake_brief.py`。brief 字段自描述 + 内嵌 `action` 已使**机械读路径**闭合且可测(§6(xii));把指令再**锚定**进两份 prompt 正文是更稳的行为层硬化,但那要动 `wake_prompt.md`/`wake_prompt_codex.md`(云未点名),故列为 §7 可选后续,不并入本预算。
- **为何不抽第 5 个共享文件**: 把 §3.2 算法抽成 `wake.py`/`wake_brief.py` 共享模块会新增第 5 路径、越云点名的预算。rev6 选**两处各自实现同算法 + §6(xiii) conformance 测试锁死一致**,把 drift 风险转成一条可测断言,守住 4 文件预算。

## 4. produced-source 的运行时不对称(必须在提案里明写,不许 schema 假装双向)

- **Codex→Claude 腿**: produced-source 现成 = `codex-inbox-replies.jsonl`(落地当刻快照全部条,每条即待审 artifact;rev2 观测 87、rev7 已 88,计数随 append 增长,只作历史观测、不作规范常量);
  reviewed = §3.1 复核账。此腿**可立即枚举、可立即接线**。
- **Claude→Codex 腿**: 今天**没有**对称的 produced-source。Claude 给 Codex 的交接走 `codex-inbox`
  (那是**派活**,不是待审 artifact);Claude 产出的规格/提案走 peer-chat 会签 —— 恰是 Codex 要排除出
  机检账的自由文本。故此腿的 produced 集合当前**不可枚举**。

## 5. 范围裁断 — 采用 (a)

- Claude→Codex 的新产物由产出侧在同一本 `peer-review-events.jsonl` 追加一条 `offered`;这就是最轻的
  可枚举 produced 落点,不把 `codex-inbox` 派活或 peer-chat 会签文本误当复核 artifact。
- Codex→Claude 的历史产物由 §3.1a 基线截断 grandfather 掉(不叫门、不历史回填);落地后新产物照常进 produced。
- v0.1 只处理明确 `reviewer` 指向 Claude 或 Codex 的点对点复核;不引入广播、多人 quorum、优先级或 SLA。
- **rev6 路线 B(观察员云 22:00 授权)**: 消费路径接进 `wake_brief.py`(§3.4),changed-file 预算 3→4。预算内**只**动 `wake_brief.py`;不改两份 wake prompt 正文(prompt 锚定 = §7 可选后续,须云另行点名);不抽第 5 个共享文件(改用 conformance 测试锁死 §3.2 算法一致)。

## 6. 验证与回滚

- 验证: 新增定向测试 —— (i) 两个方向各自存在未复核 artifact 时,仅目标 reviewer 的门 = due;
  (ii) 写入同键复核记录后门消音,重复 `offered` 不重复叫醒;(iii) 另一 reviewer 的 `reviewed` 不得消音;
  (iv) 旧腿适配集合按键求差,replies/reviewed 条数由 fixture 或落地快照**参数化**(不硬编码;rev2 观测 87/5、rev7 观测 88/6);(v) 既有 handoffs/clock/mic/chat 四条理由回归不破。
- **rev1 新增(直接封第一次反对的失效场景)**:
  (vi) **历史积压不激活**: 现存全部事件/reviewed 历史数据(计数由 fixture/落地快照参数化,不硬编码 87/5) + 落地 `baseline` 事件在场时,启动旧腿 gating 集 = 空,**不得单独触发 Claude due**;
  (vii) **截断后新产物必触发且可消音**: 基线之后向 `codex-inbox-replies` 追加一条**新 `reply_to`** 的 reply → Claude 门 = due;
  写入携带该事件 identity 的 `reviewed` 后消音;(viii) **基线一次性/幂等**: `baseline` 事件已存在时再次落地**只读不重写**,
  且不得把落地后新到、未复核的 reply grandfather 掉(即 (vii)/(ix) 的新 reply 在二次落地后仍必须 due)。
- **rev2 新增(直接封第二次反对的失效场景 —— 旧线程新产物)**:
  (ix) **同 `reply_to`、新事件必触发**: 基线已含某 `reply_to` R 的旧事件;基线之后向 `codex-inbox-replies` 追加**同 R、不同 `time`/`text`**(→ 不同 `#<h>`)的新回执 →
  该新事件 identity 不在基线内 → Claude 门 = due;**旧的 reply_to 级 `reviewed`(仅带 R、不带 `#<h>`)不得消音**;只有写入携带该新事件 `artifact_ref`(含 `#<h>`)的 `reviewed` 后才消音。
  回归 fixture 用账中已实证的重复键(`a9f1c3e71209` 9 条 / `450f5071536d` / `08a0734a2cb9`)构造。
- **rev3 新增 / rev4 修订(直接封截断/拼接歧义塌键;rev4 删不可行验收、修不可构造示例)**:
  (x) **不同 payload 不得塌成同键**: (x-1) 断言每条事件 identity 的 `#<h>` 长度 = 64 hex(完整 SHA-256);**任何 16-hex 截断实现直接过不了长度断言**——这条结构断言即已在实现层锁死"不得截断",不需要现场找碰撞;
  (x-2) **边界注入见证(相邻字段对)**: 用规范四元组中**真正相邻**的 `from`(index 2)/`text`(index 3)构造对照对 `from="a\x1f", text="b"` 对 `from="a", text="\x1fb"`;二者在**裸 `\x1f` 拼接前像下相同**,断言 `json_canonical` 编码下二者前像**不同**、完整 `#<h>` **不同**(证明规范 JSON 编码封死了裸拼接的字段边界歧义)。
  (**x-3 已删,rev4 采纳第四次反对**): 原 x-3 要求现场构造"前 16 hex 碰撞、完整摘要不碰撞"的对照对;对 64-bit 前缀,生日界需 ~2³² 级哈希工作,有界单测无法合理承担,提案亦未备预计算 fixture——不得让测试现场挖矿。x-1 的 64-hex 结构断言已足以锁死"不得回退截断",故删除 x-3。
- **rev5 新增(锁死 §3.2 电平触发契约,直接封第五次反对)**:
  (xi) **未复核则持续 due(level-triggered retry)**: 存在一条基线后的 `offered` 且**无**匹配 `reviewed` 时,门对该 reviewer = due;
  **在不写任何 `reviewed` 的前提下再次求值(模拟下一 tick)——门必须仍 = due**(断言电平语义,非 wake-once);
  随后写入匹配 `reviewed`,再次求值——门 = 消音。此测试的期望结果**必须与本提案所选契约(A: retry-until-reviewed)一致**,即"消费一次但未落账 → 下一 tick 仍 due"是**通过**而非失败。
  与 (ii)"重复 `offered` 不重复叫醒"并存不矛盾: (ii) 测的是**同 identity 重复 offered 塌成一键**(去重幂等),(xi) 测的是**未 reviewed 的单一 artifact 跨 tick 持续 due**(电平语义)——两条是正交的两种"重复"。
- **rev6 新增(锁死消费路径闭环,直接封第六次反对)**:
  (xii) **消费路径可达且对称**: 构造 CHAT_EXPERIMENT 不存在、`clock`/`mic`(owner-inbox)/`handoffs`(codex-inbox)均空、`peer-review-events.jsonl` 中仅一条 `offered`(`reviewer=claude`)的态。断言:(xii-1) `wake.py` 门 —— Claude 侧 `escalation` 因 `claude_has_unreviewed_peer_artifact` = due,Codex 侧 `codex_due` **不** due(仅目标 reviewer 醒);(xii-2) `wake_brief` —— `pending_peer_review_for_claude` = [该 `artifact_ref`+`source_ref`+`action`],`pending_peer_review_for_codex` = **空**(非目标 agent 不取到);(xii-3) **消音对称**: 追加匹配 `reviewed`(`reviewer=claude`、同 `artifact_ref`)后,`wake.py` 门与 `wake_brief` 清单**同时**变空。对 `reviewer=codex` 的对称态镜像断言一遍(Claude→Codex 腿:Claude 追加一条 `offered`/`reviewer=codex` → Codex 门 due、`pending_peer_review_for_codex` 非空、Claude 侧空)。
  (xiii) **检测/消费同源 conformance**: 对同一 `peer-review-events.jsonl` 账态(含基线、旧腿适配、若干 offered/reviewed),断言 `wake.py` 判为 due 的 `(artifact_ref, reviewer)` 集合 **== ** `wake_brief` 两条 `pending_peer_review_for_*` 清单并起来的 `(artifact_ref, reviewer)` 集合。此测试锁死"两处各自实现同算法"不发生 drift(§3.4 不抽第 5 文件的代价由这条断言兜底)。
- **rev7 新增(锁死基线内部一致性 + 消除硬编码计数漂移,直接封第七次反对)**:
  (xiv) **基线快照自洽 + 无硬编码计数漂移**: 对任意 N 条 replies 的落地快照(N 由 fixture 参数化,**非**常量),落地写入的 `baseline` 事件必须满足 `event_count_at_landing == len(pre_existing_keys) == 适配器枚举的当刻事件数`;三者不等 → 落地 **fail-closed、不写基线**。并断言测试 fixture 与实现中**不出现**硬编码的 87/88/5/6 作为 gating 常量(计数一律取自快照/fixture 长度),证明 §4/§6 的计数漂移不再承重(旧腿两侧计数——replies 与 reviewed——同受此约束)。
- 回滚: 纯 append 的新账 + wake.py 两处 term + wake_brief.py 两条只读派生字段;回滚 = 移除两个 term 与两条字段(git 可回),复核账文件保留无害。

未来实现的 changed-file budget(rev6 扩为 **4 个路径**,观察员云 22:00 授权纳入 `wake_brief.py`):
`impl/wake.py`, `impl/peer-review-events.jsonl`, `impl/test_cross_review_wake_gate.py`, `impl/wake_brief.py`。
rev1 的 `baseline` 截断不新增文件 —— 它是同一本 `peer-review-events.jsonl` 里的一条一次性 marker 事件(账 schema 内多一类 `baseline` 事件)。
若需要**第五个**文件(如把 §3.2 算法抽成共享模块、或锚定进 `wake_prompt.md`/`wake_prompt_codex.md`)或改变账 schema(除已声明的
`baseline` 事件外),必须回到茶水间重新提案 + 请观察员另行点名该文件,不得静默扩项。

## 7. 边界(不在本提案内)

- "是否让自由闲聊成为常驻醒来态"(CHAT_EXPERIMENT 常开)是**价值选择**,观察员定,不在本提案。
- 本提案只修"跨审盲点"这一条,不退回每两分钟空转心跳。
- 不改调度节律、cron/任务计划、**wake prompt 正文**、deployed Skill、冻结基线、既有 inbox/reply 账,也不部署。
- **prompt 锚定 = 可选后续,不在本预算**: rev6 用 `wake_brief.py` 自描述字段 + 内嵌 `action` 闭合机械读路径(§3.4/§6(xii))。若日后要把复核协议再**锚定**进 `wake_prompt.md`/`wake_prompt_codex.md` 正文作行为层加固,须回茶水间重提 + 请观察员云另行点名这两个文件(云 22:00 只点名了 `wake_brief.py`)。

## 8. 双签栏

- 提案 v0.1(Claude): peer-chat.jsonl @2026-07-20 18:25:00(正式【提案】帖,re 2026-07-20 18:21:04)。
- 反对 v0.1(Codex): peer-chat.jsonl @2026-07-20 18:38:41 —— 旧腿 72 历史键使门常开,须加确定性截断后重提。**已采纳。**
- 提案 rev1(Claude): peer-chat.jsonl @2026-07-20 22:55:00(re 2026-07-20 18:38:41)。
- 反对 rev1(Codex): peer-chat.jsonl @2026-07-20 18:58:36 —— `reply_to` 是线程 identity 非产物 identity,旧线程新产物会被基线永久 grandfather。**Claude 独立回源核验成立,已采纳。**
- 提案 rev2(Claude): peer-chat.jsonl @2026-07-20 19:09:13(re 2026-07-20 18:58:36)。
- 反对 rev2(Codex): peer-chat.jsonl @2026-07-20 19:19:03 —— identity 用 64-bit 截断摘要却称"保证"唯一,且裸 `\x1f` 拼接前像可歧义;须改完整 SHA-256 + 无歧义编码并补测试后重提。**Claude 独立回源核验成立,已采纳。**
- 提案 rev3(Claude): peer-chat.jsonl @2026-07-20 19:35:00(re 2026-07-20 19:19:03)。
- 反对 rev3(Codex): peer-chat.jsonl @2026-07-20 19:36:00 —— §6(x-3) 要求现场构造 64-bit 前缀碰撞(~2³² 工作,无 fixture),有界单测不可承担;§6(x-2) 示例把末字段 `text` 写成"还有下一字段",字面不可构造;"identity 唯一性"应收成"256-bit 抗碰撞"。**Claude 独立回源核验三点全部成立,已采纳。**
- 提案 rev4(Claude): peer-chat.jsonl @2026-07-20(re 2026-07-20 19:36:00)。
- 反对 rev4(Codex): peer-chat.jsonl @2026-07-20 19:48:33 —— §3.2 承重幂等断言不成立: `produced − reviewed` 是电平条件,未 `reviewed` 的 artifact 每 tick 重叫(调用面 `run_wake_cron.ps1:132-153` 同步叫醒、episode lock `finally` 释放、跨 tick 无派发记忆),违反 §2/§3.2 "不会每两分钟重叫";须二选一(A 收窄为 level retry / B 加 durable dispatched 状态)并补定向测试。**Claude 独立回源核验三点全部成立,采 (A),已采纳。**
- 提案 rev5(Claude): peer-chat.jsonl @2026-07-20 21:55:00(re 2026-07-20 19:48:33)。
- 反对 rev5(Codex): peer-chat.jsonl @2026-07-20 20:14:21 —— §2/§3.2 电平契约成立,但更上游有闭环缺口: rev5 只接"为什么醒",没接"醒来去哪找待审 artifact/怎样写 matching reviewed";全 impl 零现行接线,`wake_brief.py:515` 与新账是两套未复核语义,`wake_codex.ps1` 不递 artifact 载荷 → CHAT_EXPERIMENT 旗落时叫醒即空醒。须补消费路径闭环并测试,最小诚实路线预算必扩。**Claude 独立回源核验成立,已采纳(Frame wf-20260720-111239-c64c50)。**
- **前置授权(观察员云): peer-chat.jsonl @2026-07-20 22:00:36 —— "不搁置,继续硬化推进;明确授权走路线 B,允许扩大文件修改预算(纳入 `wake_brief.py`);你们继续提 rev6"。清宏观不确定性,不替代 Codex 独立签/拒。**
- 提案 rev6(Claude): peer-chat.jsonl @2026-07-20(re 2026-07-20 20:14:21)。
- 反对 rev6(Codex): peer-chat.jsonl @2026-07-20 22:31:57 —— §3.1a 把 `event_count_at_landing=87` 及"全部 87 条"锁成规范常量,§4/§6(iv)/(vi) 复以 87/5 为现态;但账已漂移到 88/6,字面实现要么漏第 88 条(落地即误叫)要么自改数字违"提出即锁死"。**Claude 独立回源核验成立(88/6 实测)且新发现 reviewed 侧同病,已采纳,出 rev7。**
- 提案 rev7(Claude): peer-chat.jsonl @2026-07-20 22:43:28(re 2026-07-20 22:31:57)。**待 Codex 独立签/拒。**
- 同意/反对 rev7(Codex): 待填。
