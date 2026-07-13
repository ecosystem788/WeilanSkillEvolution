# 降地板 · 第二颗牙(现为首建):conversation 结论 capture+promote 一步化 —— harness 规格(FROZEN v0.1a)

**状态:** FROZEN v0.1a —— 经 Codex 六轮复审与项目方授权冻结实现;实现复审后补明"复制 gate + drift-tested reject equivalence"。门矩阵/落账对现行**部署实装**逐条对齐(`D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py`,只读核对)。隔离候选实现,不改实装/部署件/授权文件。
**上位:** `proposals/solve-with-weilan-ai-first-roadmap-v0.1/PLAN.md` §③。
**为什么现在是它:** ①(死线牙)`insufficient_labeled_data`;③ 不吃历史标注,当场可跑。
**定调:** AI-first / 好用。把对话来的 sourced 结论从 capture→promote **两条命令降到一条**。**省往返,不省判断;§2 每一道门原样,一分不放宽。**
**收窄:** 只做 **conversation path**。file/frame-only、多源、displace/supersedes/conflicts-with —— v0.1 不支持(明确 unsupported,不算失败)。

---

## 0. 一句话

`memory-note` = `evidence-capture` + `evidence-promote` 融成一条,**原子、单 fence**执行(§1)。判断 flag 仍显式,§2 全门原样。非对话源走另一条 `memory-consolidate`,不在本牙。

## 1. 执行契约:原子 + 单 fence(定死 P2-1 + Codex 本轮 fence 要求)

```text
memory-note 在**同一个 contract_fence(state_root, workspace_key, scope_key)**内完成:
  预检全部 capture 门 + 全部 promote 门(§2)+ budget → 全过 → **append evidence + append semantic memory + append PROMOTED promotion audit**(三者同 fence);
  任一门不过 → **不写任何东西**(无悬空 candidate、无 audit、semantic_memory_written=false)。
```

**为什么单 fence:** 现行 `evidence-promote` 本身在 `contract_fence` 内(实装 command_evidence_promote)。若 memory-note 把预检和落账分开、或分两个 fence,budget / freshness 会 TOCTOU 漏穿(检查后被别的会话改掉)。**capture 预检 → promote 门 → budget → 三次 append(evidence + semantic entry + PROMOTED audit),必须在同一 fence 下一气呵成。**
**为什么原子:** 避免"先 capture 再 promote 被拒"留悬空 candidate + 重试造重复。这是相对手工两步的强化。
**实现口径:** 在"单 fence + 不动现有命令"约束下,v0.1 候选复制现有 capture/promote gate 检查到融合命令内,不是重构成单一共享 helper。复制带来的 drift 风险由 §4/§6 的全门 reject equivalence 持续测试约束;任一 gate 的 reason/category 漂移必须红。

## 2. 门矩阵(对现行实装逐条对齐;按阶段 + 精确 reason_code + 退出类别)

**category:** `usage` = 输入非法(现行 raise,视作用法错,error 退出);`policy` = 过了输入、被策略门拒(现行 JSON `decision:REJECTED`)。memory-note 对每门须产**同 reason_code + 同 category**。

```text
【CAPTURE 阶段】(现行 command_evidence_capture)
  门              触发                                   reason_code                                   category
  durable-signal  signal ∈ {casual_chat,                    non_durable_conversation_signal              policy
                  social_acknowledgement, transient_status}(非持久;枚举名以实装 PERSISTABLE 集为准)
  claim 非空      claim 为空                              "--claim cannot be empty"                     usage
  对话出处        无可解析 conversation:<t>#<turn>        "conversation evidence requires --source ..." usage
  claim ≤6 行     claim 超 6 行                           claim_exceeds_six_line_fragment_boundary      policy
  敏感(捕获域)  {claim, sources, tags} 含敏感材料       <sensitive_material_reason>                   policy
  turn 可解析     conversation turn 无法解析               "conversation turn provenance is not ..."     usage
  evidence ≤4096  编码后 evidence > 4096 bytes            evidence_fragment_exceeds_4096_bytes          policy

【PROMOTE 阶段】(现行 command_evidence_promote_fenced,fence 内;reasons 累积 → policy)
  判断门          缺 --stable                             stability_not_confirmed                       policy
                  缺 --reusable                           cross_task_reuse_not_confirmed                policy
                  缺 --privacy-reviewed                   privacy_review_not_confirmed                  policy
  kind-for-signal kind ∉ PROMOTABLE_KINDS_BY_SIGNAL[signal] semantic_kind_not_allowed_for_signal        policy
  summary 非空    summary 空                               semantic_summary_empty                        policy
  敏感(晋升域)  {summary, detail, tags, source} 含敏感   semantic_content_failed_sensitive_material_check policy
  grounding       claim/summary token 交集为空             semantic_summary_not_grounded_in_evidence_claim policy
  budget          语义预算耗尽(仅无其他 reason 时查)     semantic_budget_exhausted                     policy
  [freshness]     evidence_sources_stale —— **见 §2.1,融合路径 N/A**
```

### 2.1 融合路径 N/A-by-construction 的门(Claude freshness + Codex 本轮 evidence-lifecycle 补全)

这些门守的风险在"同命令、单 fence、新建 evidence、不暴露 `--evidence-id`"的原子路径里**根本不存在**,故 harness 标 **N/A-by-construction**——不是跳过、不是覆盖缺口:

```text
evidence_sources_stale     capture 与 promote 同一瞬间同一 fence,无时间窗 → 快照必一致,恒真通过。
evidence 找不到/多条       同命令内新建恰一条 evidence,不接受 --evidence-id → 不可能 not-found/多条。
already promoted           新建 evidence → 不可能已 promoted。
非 CANDIDATE 状态          新建即 CANDIDATE。
```

但仍须断言:memory-note 在 capture 阶段做了**源可解析性**校验(对话出处门 + turn 可解析门),且新建 evidence 处于 CANDIDATE。"§2 全部门原样复用"这句因此没有审查口子——每一门要么进 harness、要么在此显式记 N/A + 理由。

## 3. 参数合同(冻结;`no_real_reduction` 机械判据)

```text
合法常见 path 允许且仅需:
  --signal --claim --source(conversation:) --kind --summary [--detail] [--tag ...] --stable --reusable --privacy-reviewed
若还要求调用者先查 evidence_id / 手动生成 source snapshot / 跑 promotion dry-run → no_real_reduction。
```

## 4. Harness(能输;无需历史标注集)

```text
步数测      合法结论:before(capture+promote=2 命令)vs after(memory-note=1)。after 必须 = 1。
门回归      §2 每一门喂对应非法输入,memory-note 必须拒,且与手工 capture/promote **同 reason_code + 同 category**(§4.1)。fixture 精度:
            · wrong-kind:用**合法 SEMANTIC_KIND 但不被该 signal 允许**——signal=verified_result + --kind decision
              (verified_result 只允许 {fact,lesson})→ semantic_kind_not_allowed_for_signal。**不得**用 banana(那是 argparse,测不到真门)。
            · 敏感两 fixture:{claim/source/tag} 含敏感 → capture 拒(policy);{summary/detail/tag} 含敏感 → promote 拒。
            · 非持久信号**三个都测**:casual_chat / social_acknowledgement / transient_status,均 → non_durable_conversation_signal
              (用实装 CLI 合法枚举名,喂简写会先死在 argparse、测不到真门)。
            · stale-source:N/A-by-construction(§2.1),不构造。
归一化等价  合法路径拆**两组**比(P1:gate_checks/reason_codes 在 promotion audit 记录里,**不在 semantic entry 上**):
            (a) semantic entry:{kind, summary, detail, tags, sources*, supersedes, conflicts_with,
                promotion.{evidence_id, promotion_id, schema_version}(id 归一)} 等价;排除 memory_id/timestamp/path/hash。
            (b) promotion audit 记录:{decision:PROMOTED, gate_checks, reason_codes, requested_kind, summary_hash,
                semantic_memory_id, evidence_id, promotion_id(id 归一)} 等价;排除 timestamp/path/hash。
                **audit 无 `signal` 字段**(现行 record 不存 signal);signal 一致性靠 audit.evidence_id → evidence record join 后比。
            *sources 归一化:`evidence:<uuid>` → `evidence:<normalized>` 再比;并单独断言 conversation source 逐字相同、
             evidence source 存在、promotion linkage(entry ↔ audit 的 promotion_id/evidence_id 对应)有效。
原子性      每个 policy 拒绝后:无悬空 candidate、semantic_memory_written=false、无 audit;重试(补齐)只产生一组 success 记录;全程单 fence(§1)。
不支持面    file/frame-only、多源、displace/supersedes/conflicts-with → 明确报 unsupported-in-v0.1(不算失败)。
```

### 4.1 "拒绝同构"的定义

```text
memory-note vs 手工,对同一非法输入,须一致:
  - failing_gate（同一道门）、reason_code（同一码）、category（usage/policy 同类）
  - semantic_memory_written = false
  - policy 拒绝:统一 JSON {decision:REJECTED, reason_codes:[...]};usage 错误:error 退出(同手工 capture 的 raise 类别)
副作用不要求逐字相同:memory-note 原子(policy 拒后不留 candidate),手工两步会留 candidate——memory-note 的强化,不算违约。
审计落账(P2,区分成功/拒绝):
  - success:**必须写 PROMOTED promotion audit**(gate_checks / reason_codes / decision:PROMOTED / semantic_memory_id),与手工同。
  - policy reject:memory-note **不写任何 audit**(原子强化);手工 promote reject 会写 REJECTED audit —— 这是 memory-note 的强化。
    但**不得**被实现者误读成"memory-note 完全不碰 promotion ledger":success 路径必须写 PROMOTED audit。
```

## 5. 退出码(预注册,互斥)

```text
floor_lowered            (pass)合法 2→1 + §2 全门同 reason_code/category + 归一化等价 + 原子单 fence(无悬空/无重复)+ 参数合同内
floor_lowered_but_leaky  (死)§2 任一门失守(对应非法输入溜进语义集,或 reason_code/category 错配)—— 降标准,回炉
no_real_reduction        需先查 id / 手动 snapshot / dry-run —— 白降,回炉
blocked_engineering      管道/隔离/fence 故障 —— 不产出裁决,修复重跑
```

## 6. 杀死测试

```text
漏门牙 ★     §2 每门喂对应非法输入,必拒且与手工路径同 reason_code+category(§4.1)。任一溜进或等价漂移 = leaky 死。
不代填牙 ★    缺 stable/reusable/privacy-reviewed 时必拒,不得自动补 true。补 = leaky 死。
原子/fence 牙 ★ policy 拒后无悬空 candidate、重试不重复;capture 预检+promote 门+budget+三 append 全在同一 fence(TOCTOU)。
归一化等价牙  合法路径 semantic entry 与 PROMOTED audit **两组均等价**(§4;sources 按 §4 归一)。
参数合同牙    超出 §3 合同的额外前置 = no_real_reduction。
回落牙        需人工审阅原文/多段 transcript/敏感上下文判定的情形回落手工;普通已隐私确认的常见路径仍一步。
边界牙        只加融合命令;不改 gate/consolidate、不动 budget/displacement、不动其他命令。
```

## 7. 边界与非目标

```text
- 只做 conversation path;file/frame 走 memory-consolidate(已一步);多源/displace/supersedes/conflicts-with v0.1 不支持。
- 不改门标准:§2 全部门复制到融合命令并用全门 reject equivalence 防漂移;不动现有命令。
- 省往返不省判断:三个判断 flag 仍显式。
- 隔离候选 + harness + 收据;采纳/部署仍是项目方不可逆动作。
```

## 8. 待冻结 / 待定(Codex 复审 + 项目方定)

```text
① 命令名(memory-note?)
② unsupported 报错口径("v0.1 conversation-only;file/frame 用 memory-consolidate;多源/displace 走手工")
③ --kind 必须显式(倾向:是)
④ §2 门矩阵 = 冻结时对**候选基座**的 weilan_trace.py 再逐条核一遍(本表对齐的是 D:\CodexData 部署件当前态;
   候选若 fork 自别的基座,以基座为准);sensitive_material_reason 的具体码随实装。
```

## 9. 更正记录

```text
FROZEN v0.1 → FROZEN v0.1a(实现复审后修正):
  明确实现是复制 gate 而非共享 helper;把 "复用" 改为 "复制 + 全门 reject equivalence 防漂移"。
  harness 要覆盖 §2 每个 reject gate:stable/reusable/privacy-reviewed、grounding、empty claim、>6 lines、>4096 bytes、empty summary、retry-no-dup 等。
v0.7 → FROZEN v0.1(项目方授权冻结实现):
  状态改为冻结;修 §6 残留 "两 append" 为三 append。
v0.6 → v0.7(Codex 第六轮复审,字段对齐 → 冻结候选):
  P1 audit 去掉 `signal`(现行 promotion record 无此字段;有 requested_kind/summary_hash);signal 一致性靠 audit.evidence_id join evidence。
  P2 §1 "两次 append" → 三次(evidence+entry+audit);§6 归一化等价牙加"含 PROMOTED audit 两组"。
v0.5 → v0.6(Codex 第五轮复审):
  P1 成功路径补 append PROMOTED promotion audit —— gate_checks/reason_codes/decision/semantic_memory_id 在此 audit,不在 entry;同 fence。
  归一化等价拆两组(§4):semantic entry 字段 + promotion audit 字段;修正 gate_checks/reason_codes 落位。
  P2 §4.1 明确:policy reject 不写 audit(原子强化),success 必写 PROMOTED audit —— 别误读成完全不碰 promotion ledger。
v0.4 → v0.5(Codex 第四轮复审,收敛):
  P1 social_ack → social_acknowledgement(用实装 CLI 合法枚举名,否则死在 argparse、测不到真门)。
  P2 evidence-lifecycle 三门(找不到/多条、already promoted、非 CANDIDATE)并入 §2.1 N/A-by-construction —— 补上"全门复用"最后一个审查口子。
v0.3 → v0.4(Codex 第三轮复审,对现行实装逐条核):
  P1 capture 门补全:加 claim 非空/≤6 行/敏感(捕获域)/turn 可解析/≤4096 bytes,精确 reason_code + 阶段(§2)。
  P1 wrong-kind 口径钉死:合法 SEMANTIC_KIND 但不被 signal 允许(verified_result+decision),非 argparse 的 banana(§4)。
  P1 敏感门拆两 fixture:capture 扫 {claim,source,tag} / promote 扫 {summary,detail,tag,source}(§2、§4)。
  P2 原子写进单 contract_fence(TOCTOU;§1)。
  P2 非持久信号三个都测,"无transfer" 并入 non_durable_conversation_signal,不再单列(§2、§4)。
  ★Claude 查出:freshness 门在原子融合路径 N/A-by-construction(无 capture→promote 时间窗),标 N/A 非缺口(§2.1)。
  退出类别 usage/policy 明确,拒绝同构含 category(§4.1)。
v0.2→v0.3、v0.1→v0.2:见 git 历史/前版(收窄 conversation-only、显式 flag、归一化等价、参数合同、2→1 更正)。
```
