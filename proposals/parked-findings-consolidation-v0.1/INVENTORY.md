# parked-findings-consolidation-v0.1 — 收拢盘点（一张表，不是第五轴）

状态：**INVENTORY / MAP，零权威，未双签，未接线。** 本文件**不新增任何论点、不新造轴**，
只把已存在的四份 parked FINDING + 一份 FIXTURE_DESIGN 交叉映射成一张表，供观察员云决断方向、
供未来正规【提案】辨清重叠、避免"把同一契约固化在多个权威落点"。单签可逆（一份 doc，git 可撤）。

缘起：茶水间 `peer-chat.jsonl` 2026-07-20 21:55（Claude 向云抛三选一：继续挂旗攒 / 落旗接线 / 先收拢盘点）
→ 03:20（Codex 独立判断：倾向先盘点，最小产物是"共享不变量 / 正交验收 / 候选接线点"表，不新造第五轴）。
本文件即该表。云尚未裁断方向；本表是**决策支持**，对三个选项都有用，不预判、不接线。

## 一、四轴一夹具的映射表

| # | 文件 | "一条载体替两份契约站台"的本轴切面 | 正交验收：闭合语义（各轴不同型，防固化在同一落点） | 触及机器 / 候选接线点 | v1 建议范围（草案自陈） |
|---|---|---|---|---|---|
| 轴1 | `projection-recall-staleness-v0.1/FINDING.md` | 一条 freshness 断言替"无漂移"和"无写"两份契约站台 | **可闭合**：scope-semantic 层 stale 可确定性重算、安全自动刷；contested 属 adjudication 轴、rebuild 消不掉、须 surface 不选边 | reducer/读路径 freshness 判定；freshness token = scope-semantic 依赖向量的规范哈希（非单一 head） | 只改 freshness 判定 + 回归测试，自动 rebuild 另案 |
| 轴2 | `capture-contract-source-authenticity-v0.1/FINDING.md` | `evidence` 门把"可解析"当成"为该 claim 作证" | **对证言源永不可闭合**：Popper-负向，标记单调 append-only，绝不收敛成 `authentic=true`；observational 可记证伪日志 | `evidence-capture` provenance 门 / `evidence-promote` 闸（`weilan_trace.py:2519/2632/2660-2674`） | `evidence-promote` 加**标记非闸门**：testimonial_attestation vs observational_derivation |
| 轴3 | `decision-provenance-authority-class-v0.1/FINDING.md` | reducer 拍平语义记忆进 `decisions[]`，一行文本替"双签授权"和"零权威闲聊"两份契约站台 | **可正向机械闭合**：判的是 provenance 类型身份（溯到双签 receipt 还是 chat 载体），是可核事实；唯 `unclassified` 一侧不许猜 | reducer `weilan_trace.py:6273-6277`（decisions 拍平）、`6308`（顶层泛化 authority），读 `2175-2189`（入库即带项级 authority/source_snapshots） | `decisions[]` 项 `str`→`{text, source_refs, authority_class}`，authority_class 由 reducer 派生；不碰写路径与授权语义 |
| 轴4 | `coverage-ladder-derivation-v0.1/FINDING.md` | **元轴**：阶梯状态标签自己会成第四个替契约站台的载体 | **有界闭合到内容寻址根**：三态派生谓词各带 as_of；证据链有限步落到 git/账本内容哈希，落不到则 `ambiguous` 停、不向上猜 | 非独立代码面——是**任何上述接线【提案】都须满足的横切验收方法**（如何求值"覆盖态"） | 三态由谓词现算、带 as_of、wired 穿更正视图、ambiguous 一等输出（见其第四节验收清单） |
| 夹具 | `projection-recall-staleness-v0.1/FIXTURE_DESIGN.md` | —（服务轴1） | 锚定当前无状态重算行为；若将来走强制重建【提案】，此测应故意绊红 | 轴1 的 freshness 可逆性 characterization 夹具（隔离铁律、no-write 探针卡身份不卡拼写） | 随轴1 接线时作为验收锚 |

## 二、共享不变量（四轴同族——接线时勿在多个落点各造一份）

1. **病灶同型**："一条载体替两份契约站台，读者无法从投影/文本分辨。"每轴是它的一个实例。
2. **机器记可验、判断留在场**：机器只记可核事实，最终判断交在场治理。
3. **派生非存储**：类别/状态必须从可验 provenance 现场派生，绝不信写入者自填的标签（轴3 authority_class、轴4 阶梯谓词）。
4. **禁止某态被机械假装消解**：轴1 contested 在 rebuild 下幂等；轴2 append-only 永不 authentic=true；轴3 unclassified 不许猜成 authorized；轴4 ambiguous 不许猜成乐观值。
5. **诚实的未定 = 一等输出**：contested / ∞ / unclassified / ambiguous 各是本轴合法终点，不许藏成好看的枚举。

## 三、本盘点暴露的关键结构：候选接线点其实只有两面机器 + 一条横切验收

- **簇 A（reducer / 读产物面，`weilan_trace.py:6273–6308`）**：轴1（freshness 判定/token）、轴3（decisions[] 结构 + authority_class）**都落在这里**；轴4（覆盖态求值）**读的也是这个读产物**。
  ⇒ 若三者各起独立【提案】各改一次 reducer，正是 Codex 警告的"同一契约固化在多个权威落点"。**建议：这三者若接线，应作为一束在 reducer 读产物这一个落点统筹**（项级结构化一次到位：freshness 依赖向量、项级 provenance/authority_class 同属"把被拍平抹平的项级事实浮回读者眼前"这一件事）。
- **簇 B（evidence 面，`evidence-promote`）**：轴2 独在此，与簇 A 正交、Popper-负向、永不闭合。**最独立、重叠最小**，可单独接线不牵动簇 A。
- **横切（非落点）**：轴4 不是与前三者并列的接线点，而是它们任一【提案】的**验收方法**——"覆盖态如何被派生求值"。接线时把它当验收清单用，别当第五个机制改。

## 四、给云的决断留三条路，本表对每条都有用（不预判）

- **继续挂旗自由攒** → 本表让后续攒的东西先照簇 A/簇 B 归位，避免再造重叠载体。
- **落旗接线** → 直接照第三节：簇 A 三轴一束、簇 B 轴2 单独、轴4 当横切验收；接线走【提案】+【同意】。
- **先收拢盘点** → 本表即其最小产物；若云认为够了，可据此排接线优先级。

本文件零权威、不驱动行动。旗仍在，本班不接线。接线 = 改机制 = 须双签【提案】才算数。
