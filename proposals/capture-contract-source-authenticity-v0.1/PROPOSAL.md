# source-authenticity-marker v0.1 rev2 — 正式范围提案

状态：**FORMAL PROPOSAL rev2 / v0.1 已被 Claude 反对且失效；rev2 待 Claude 独立签或拒；未授权实现、采纳或部署。**

提案来源：owner 于 `peer-chat.jsonl:owner@2026-07-20 07:58:21` 明示“可以提案推进”，并由
`skill-evolution` control `edad4a66-2061-4e35-a41c-c20fbbd9493b` 限定为“先形成有界 proposal scope，
再谈实现”。本案只推进 `FINDING.md` 的来源真实性轴；`projection-recall-staleness-v0.1` 保持独立后案，
不把 freshness / adjudication / branch selection 混入本案。

## 改什么

在一个尚未构造、尚未冻结的候选 Skill 中，为新产生的 evidence promotion 增加一个**来源真实性解释标记**。
rev2 不再把记录互斥地二分成 testimonial / observational；它只陈述当前 provenance 与入口契约能够直接证明的
**来源构成事实**：

- `testimonial_attestation.present=true`：provenance 中存在已通过既有 locator/resolution 检查的 conversation source；
  它只表示记录含证言来源、需要在场审查，**不**表示证言真实或为 claim 充分作证。
- `non_testimonial_anchors`：逐项列出 provenance 中可识别的 file/frame/evidence 等非 conversation source；
  它只表示这些锚随记录存在，**不**把“可定位的 artifact”冒充成“机器已执行观察检查”。
- `observational_derivation.present=false` 且 `reason=current_capture_contract_has_no_machine-check-proof`：当前两个法定入口
  没有承载“哪项机器检查被执行、输入/边界/结果为何”的证明通道，故不得从 source shape 猜出观察推导。
- `conclusion=no_authenticity_conclusion`：无论纯 conversation 还是 conversation + file/frame 混合来源，机器均不输出真值结论。

上述字段由可验证 provenance 与固定入口能力派生，不允许调用者自填 classification、basis 或权威类别。不得出现
`authentic=true`、truth score 或自动真值裁断。未来若要让 `observational_derivation.present=true` 可达，必须另行提案一个
可验证、不可由调用者自证的 machine-check proof 契约；不得在本案实现中暗加参数或凭 file/frame ref 猜测。
它是解释标记，**不是 promotion 的真实性闸门**：不能因为机器无法证真就拒绝一条原本满足既有 promotion 契约的记录。

新写入须经两个公开入口得到同一契约：

1. `memory-note` 的 capture+promote 原子路径；
2. `evidence-capture` 后的 `evidence-promote` 路径。

读取旧记录时保持兼容：无标记的历史 promotion 显示为 `unclassified / legacy / no_authenticity_conclusion`，
不回填、不改写历史；形状非法、provenance 缺失或摘要绑定被篡改的标记只能降为 `untrusted`，不能升级为真值结论。

## 为什么

当前机器能验证 source ref 可解析、promotion 的 stable/reusable/privacy 等条件，却不能证明来源确实为 claim 作证。
“可定位”与“真实作证”是两个契约。把二者拍平会让可解析的假证言获得耐久化后的过强读法；反过来，
把“无法证真”做成拒绝闸门又会伪装机器拥有不存在的裁断能力。本案只让这个边界在记录与读取时可见。

rev2 回源确认两个公开 promotion 入口都无法产生“纯 observational”记录：`memory-note` 只接受恰好一个 conversation source，
`evidence-capture` 也强制至少一个 conversation source。因此 v0.1 按“是否含 conversation”派生互斥类别时，
`observational_derivation` 永不可达；若仅因混合记录另带 file/frame source 就判为 observational，又会把 locator 当 proof。
rev2 采用非互斥来源构成，诚实保留这个能力缺口，不为满足测试而制造一条未获授权的新入口。

## 有界候选范围

双签后才可开始候选构造；future candidate changed-path budget **最多 3 个路径**：

1. `candidate/solve-with-weilan/scripts/weilan_trace.py`
2. `candidate/solve-with-weilan/references/memory-system.md`
3. `candidate/solve-with-weilan/scripts/test_source_authenticity_marker.py`

不得改 `packages/solve-with-weilan` frozen baseline、`D:\CodexData\skills\solve-with-weilan` deployed Skill、
`ARCHITECTURE.md`、`ROADMAP.md`、`EVALUATION_POLICY.md`、`evals/`、`tools/`、adoption/deployment authority。
CLI 参数保持兼容；本案不增加自动 rebuild、不改变 activation/control、不改变 semantic budget。

当前未跟踪的 `candidate/` 目录是**会签前原型证据，不是已获授权候选**。若本案双签，它必须从签署时核验过的
deployed base 重新形成干净候选；排除 `__pycache__`、`.pytest_cache` 等运行产物，并以外部 Evolution Plane
生成 base/candidate artifact hash 与可验证 `proposal.json`。不得把原型的额外行为静默带入。

## 怎么验证

定向验收必须覆盖：

1. 两个 promotion 入口对同一证言来源写出同型 `testimonial_attestation.present=true`，且无 `authentic` 字段；
2. 一条同时含 conversation 与 file/frame source 的 promotion 必须确定性地同时得到 testimonial attestation 与
   `non_testimonial_anchors`，但 `observational_derivation.present` 仍为 `false`，不得静默二选一或把 locator 冒充机器检查；
3. 一条只有 conversation source 的 promotion 得到空 `non_testimonial_anchors`；两个公开入口均不得构造
   `observational_derivation.present=true`，并明示 `current_capture_contract_has_no_machine-check-proof`；
4. 标记由 evidence provenance 与固定入口能力派生，调用者不能自填 classification/basis；
5. legacy 记录保持可读且不回填；缺失、非法或篡改标记降为 `untrusted`；
6. 一条满足旧 promotion 契约的记录，不因来源构成解释而被拒；
7. 既有 conversation evidence、evidence lifecycle、semantic memory 回归不破。

候选构造后先运行定向测试与相关回归，再由 `tools/evolution_cli.py proposal-validate` 验证内容寻址提案；
baseline 与 candidate 只能使用同一 frozen manifest、相同 cases 和 budgets。验证结果只是证据，不构成采纳。

## 怎么回滚

本轮仅新增本提案文档和茶水间提案，回滚就是撤回提案并保留历史留痕；不会触碰运行时。
若未来候选构造失败，丢弃未采纳候选即可。若未来另经独立 adoption/deployment 决策后上线，回滚必须恢复
部署收据中记录的、此前已验证的 content-addressed predecessor；不得重写历史 evidence。

## 双签边界

本提案若获 Claude【同意】，只授权按上述 3 路径预算构造干净候选、补齐 artifact hashes、运行定向/等价评测并出收据。
**不授权 adoption、deployment、修改评测标准，也不授权顺手实施 projection freshness 姊妹线。**

v0.1 提案：`peer-chat.jsonl@2026-07-20 19:37:00`。
Claude 反对：`peer-chat.jsonl@2026-07-20 19:48:00`——两个法定入口 conversation source 恒在，原互斥二分使
observational 分支不可达，混合来源缺少确定规则。**rev2 已独立回源核验并采纳。**

溯源：`FINDING.md`；`projection-recall-staleness-v0.1/FINDING.md`；v0.1 Frame
`wf-20260720-102738-14b23e`；rev2 Frame `wf-20260720-112148-5e9354`。
