# 宿主感知权威管线草图 v0.1

> **性质：设计草图，非提案，零行动权威。** 本文只封存一段已经收敛的茶水间判断，
> 不授权实现、接线、部署、规则注册、能力授予或调度变更。任何工程动作仍须按 `CHARTER.md`
> 判断权限；其中规则授权与能力表写入属于承重决定，须具名双签或观察员授权。

## 要解决的边界

宿主状态（CPU、磁盘、网络、持续效果等）是活体、非确定、不可由 reducer 重算的事实。
目标不是把它伪装成确定性账本态，而是保存“当时看见了什么”，再让已经获授权的确定性规则
在严格范围内裁出承重结果。事实、证据与权威必须分层，任何一层都不能自产下一层的资格。

## 四层管线

```text
capture（边界采样）
  -> sealed evidence（封存证据）
  -> rule adjudication（版本化规则裁断）
  -> capability table（探针×覆盖契约资格根）
```

这里的箭头表示依赖，不表示自动授权；实际信任方向由最顶层的具名签名向下约束。

### 1. Capture：非确定量只在 harness 边界铸造

- 探针在真实时间与宿主状态入场的边界采样；reducer/recall 核内不得读取 live host state、`now` 或重新采样。
- 瞬时观测可丢，不进入既有 `site_fingerprint` 或确定性 reducer。
- 采样输出至少带探针身份、参数、声明覆盖域、采样结果与外部注入的采样时刻。

### 2. Sealed evidence：可重放原样，不自动承权

- 封存项保存 `sampled_at`、来源、误差界与内容 hash；重放的是原证据，不是假装重新观测宿主。
- 裁断/执行时由 harness 再封存 `evaluated_at`；纯核只读这两枚时间。
- 规则同时检查采样窗口、执行窗口与 `evaluated_at - sampled_at` 新鲜度容差。过期或超差样本退回重采，不能承重。
- 既有持续效果若进入组合判断，也必须来自新鲜封存 envelope；live 读取不能偷渡进确定性 join。

### 3. Rule adjudication：规则的授权范围锁死后果

- `sealed -> eligible` 可由版本化纯规则确定性重算。
- `eligible -> 承重` 只有在规则的作用域、阈值、有效期与可触发后果已获具名双签/观察员授权时才可自动完成；否则只是一张候选票。
- 每次升权收据钉住 envelope hash、rule version、授权 ref 与执行 harness。
- 后果按效果格检查 join：本批拟执行效果与已封存的持续效果合并后，若超过任一授权 envelope 的后果上限，则退回在场签名。
- 撤销只关闭未来评估/执行门，不回写历史收据；持续动作的下一步仍属未来执行，撤销后必须停止。

### 4. Capability table：覆盖声明的资格根

`complete` 不是裸布尔，而是获准探针对版本化 coverage contract 的具名证明。封存项至少绑定：

```text
probe_id
coverage_contract / version
declared_scope
acquisition_result = complete | partial | failed
```

规则只在 `required_scope` 被一份新鲜、`complete`、契约版本匹配的证明覆盖时继续。
未知探针、错版契约、`partial`、`failed` 或过期证明一律落 `unknown` 并锁死，绝不按零效果放行。
完整性只相对于规则声明的 `required_scope`，不要求不可实现的“整机全闭合”。

能力表决定哪个探针有资格为哪个 scope 声称完整，是整条管线的信任根。因此：

- 每一行注册都是授予“一类宿主事实未来可自动升权”的能力，必须由双签或观察员具名授权；
- 能力表不得通过它自己授权的自动通道扩张自己；
- 能力撤销只影响未来的门，不追溯抹除已封存证据与历史升权收据；
- join 收据除 envelope hash 外，还须钉住 `probe_id + coverage contract/version + capability-row ref`。

## 闭合的不变量

1. 宿主事实不能自产权威：capture 只产观测，sealed 只产可引用证据。
2. 规则不能扩张自己的后果域：单规则与组合效果都受预签上限约束。
3. 探针不能自封完整性资格：coverage claim 的资格来自预签能力表。
4. 能力表不能自举：它的注册权落回具名双签或观察员授权。
5. 不完整、过期或错版信息保持 `unknown`；沉默永不默认成“已停止”或“完整覆盖”。
6. 历史留痕与未来效力分离：撤销停未来门，不篡改过去账。

## 与现有笔记的关系

- `NOTE.md` 记录自危类故障、状态惯性、跨故障域见证与双源归因；本文不改写这些约束。
- `../situational-awareness-v0.1/NOTE.md` 的内容/时点/观测者/覆盖四轴仍是 envelope 的基础；
  本文进一步收窄“覆盖声明由谁有资格作出、怎样进入承重规则”。
- 本文没有选实现、schema 或接线路径；这些仍是未来正规提案要验证的开放项。
- 若未来从 `../projection-recall-staleness-v0.1/FINDING.md` 的 axis-1 发起宿主感知接线提案，
  提案须回引本文作为 schema 选择的设计前件；这条互指只防止设计输入成为孤儿，不预先授权接线。

## 溯源

承重判断回源到 `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`：

- `2026-07-22 18:50:43` 至 `19:28:53`：观测/封存/承重三态、时间铸造点、双封时间、
  新鲜度、效果 join、撤销不对称与持续效果 envelope；
- `2026-07-22 19:31:18` 至 `19:41:33`：相对 required scope 的覆盖闭合、受信 coverage claim、
  版本化 contract 与 probe×contract 能力表；
- `2026-07-22 19:44:36`：能力表不得自举、每行注册须落回具名双签/观察员授权。

茶水间发言是具名证据与判断，不自动授权行动；本文同样只保留证据，不改变该权威等级。
