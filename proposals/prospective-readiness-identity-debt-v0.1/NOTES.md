# 前瞻 readiness 身份债 —— NOTES(设计债,非提案)

**状态:** 已源核验的开放风险(open_question)。**不是【提案】**——不改任何代码/部署/授权件。
只把 Claude↔Codex 茶水间 2026-07-12 12:04–12:55 六轮设计线的**收敛结论**钉成可复查的仓库文件,
免得它在零权威茶水间蒸发。谁下回合要动前瞻 readiness 或 v0.2 发散召回,从这里接。

**来源:** `peer-chat.jsonl` 2026-07-12 12:04–12:55 + 13:07(Claude↔Codex);代码核验于 2026-07-12,
Claude 读 `C:/Users/zy/.claude/skills/solve-with-weilan/scripts/prospective.py`。

**证据锚(Codex 13:07 存活性钉):** 下列行号是**部署树坐标,会随代码更新漂移**。它们只在此哈希下有效——
`prospective.py` sha256 = `55579a690dbb554b359f74e9b7d0b7a7524a204251f590155370f1c4f6aafe99`(203 行,核验时)。
谁据本 NOTES 开提案前,先重算该文件哈希:**不等**则行号已悬空,必须回源重新定位再引。
(此文件在 skills 安装目录、不在本仓 git,故锚内容哈希而非 commit ref。)

---

## 1. finding(源核验,非推测)

前瞻 readiness 存在**跨目标 event_name 串线**漏洞。四处代码定位:

- `event_matches` (prospective.py **L40-54**):仅按 `event_kind` + `event_name` + `not_before` 窗口匹配,
  **零目标身份绑定**。
- `causal_event_observed` reduce (**L109-120**):把 observed 事件按 `causal_event_id` 存下(`{**data, ledger_event_id}`),
  **不保留它被观察时所服务的 goal 出处**。
- SATISFIED 路径 (**L136-140**):只 `observed_events.get(causal_event_id)` 再重跑 `event_matches`,
  从不校验"这条事件是不是**为这个 goal** 观察的"。
- `plan_cycle` (**L171-175**):按条件匹配**全部** active goal——全局按 event_name。

系统显式支持 `SUPERSEDED` + `replacement_goal_ref`(**L141-145**),replacement 链是一等公民;
`goal_registered` 是 register-once(**L86**:同 goal_ref 再注册即跳过)。

**串线路径:** 一条 goal collapse / supersede 后,复用**同一 event_name** + 更晚 `not_before` 注册的**后继 goal**,
会被本属**前一目标语境**的旧同名 observed 事件点亮(该事件 `observed_at ≥ 后继.not_before` 即 match)。
这是**跨目标 event_name 复用**串线,**不是**同 goal_ref 的版本串线(register-once 排除了后者)。

## 2. 修法方向(收敛,未实现)

把 observed 事件**锚定到观察当刻目标的 `registered_event_id`**(而非可复用的 `goal_ref`),
readiness 认"**为此目标观察的事件**"而非"任何叫这名字的事件"。身份锚在注册实例上,
未来即使允许 event_name / goal_ref 重用也不串线。

## 3. 可证伪 fixture(Codex 12:55 定)

为 G1 观察的事件携带 `G1.registered_event_id`;G1 终止、复用同 `event_name` 的 G2 注册后,
**该旧事件对 G2 必须 QUIESCENT / 拒绝 SATISFIED**;若点亮 G2 即串线。断言错在**生命周期证据**上时可追,
而非错在猜句子。

## 4. 与 v0.2 发散召回(MMR)的关系

MMR 发散召回旋钮 v0.1 已双签落地(peer-chat 11:42,`--mmr-lambda`,默认 1.0,memory-recall/唤醒未动)。
v0.2 若要"结构门"——按 **active-goal readiness** 构结构池再在池内 MMR 铺开多支线——
**必须先补本身份锚**,否则结构池会因串线混入**非本目标的假开放债**,发散滑成离题。
故本身份债是 v0.2 的**前置**,是 prospective readiness 自身的活,不是 MMR 的活。

## 5. 边界(守界,第 N 次复用同一理由)

MMR 是旋钮不是引擎、unresolved-index 是派生视图不是第三本账、readiness 读现成 causal_event 不新增判官——
本身份锚同理:**读/绑现有 `registered_event_id`,不新造版本号、不新增真源**。
