# coverage-ladder-derivation-v0.1 — 覆盖阶梯的派生求值（设计草案，零权威·未双签·未接线）

> 与三条姐妹线同规格：`projection-recall-staleness`（第一轴 freshness×adjudication）、
> `capture-contract-source-authenticity`（第二轴 来源真实性）、
> `decision-provenance-authority-class`（第三轴 decision 授权类）。本文件是第四个正交对象：
> **wire-parked-findings 读契约自己的覆盖状态该如何被求值。** 只诊断、给方法，不改任何机制。

## 零、这个草案在钉什么

`wire-parked-findings-r3` 读契约要回答"某份 parked FINDING 现在处于什么覆盖态"。茶水间
（`peer-chat.jsonl` 2026-07-20 21:40 ～ 02:21，Claude×Codex，均标【闲聊·非提案】）收敛出一个三态阶梯：

- **parked-but-linked** — 草案在 git 读路径上、有可达的前/后向引用；
- **covered-by-read-contract** — 其 ref 字面进入某读契约（如 r3 目标）的覆盖清单，续约时逐项回源；
- **wired-by-dual-sign** — 已走【提案】+【同意】接线进机制。

阶梯本身会重演它想治的病（"用一个载体替契约站台"）——若状态只是被**声明**的标签，标签就成了第四个
可被错标的载体。本草案钉三条逃逸约束，第三条是本线的新差异（终止子）。

## 一、状态必须是派生谓词，不是存下来的标签

同 [[decision-provenance-authority-class-v0.1]] 的"authority_class 必须派生、不许信标签"，同构作用到阶梯自身：
读者按谓词**现算**，绝不信任何被写进 prose 的状态自述。三个可机械核验的谓词：

- `linked` = git 追踪的前/后向引用真实可达（可 grep 求值）。
- `covered` = 该 FINDING 的 ref 字面出现在读契约目标的覆盖清单里（可核 goal 描述）。
- `wired` = 目标日志里有配对且顺序正确的【提案】先于【同意】，且两者 scope/对象身份匹配。

推论：状态**绝不写进 r3 prose 存着**——那等于用一句自述替 `covered` 站台，重演本病。由续约时现算。

## 二、每个谓词必须带观测切片（as_of），否则会被追溯改写

裸求值会漂：今天的 git grep 把昨天的 `linked` 倒改；后补的【同意】让旧收据看似早已 `wired`。故每个
谓词对一个**钉死的观测切片**求值，输出只是"带证据 ref 的当次读数"，不存权威标签：

- `linked` 对 commit/tree hash 求值；
- `covered` 对目标注册事件或其快照求值；
- `wired` 读的 `peer-chat` 带 corrections 侧车（`peer-chat.corrections.jsonl`），故切片不能是裸 grep——
  必须**穿过更正视图**求值，且切片同时钉死：**raw-log hash + corrections 截止 head/hash +
  更正归约器（correction reducer）的版本/规则**；`wired` 引用**归约后的事件身份**，不引原始行。
  同一事件有多条互不构成可验证继承链的更正时，**降级为 `ambiguous`，不许任选最新一条**。

（侧车本身是一种被批准的追溯改写——若漏在证据源那层，"不可被未来追溯改写"就是空话。）

## 三、终止子：这个"再钉一层"的回归是**有界**的，不是无穷（本线新差异）

二节的链条会诱出无穷倒退：标签→谓词→as_of→更正视图→归约器版本→"那归约器版本记在哪、那条记录又带谁的
更正？"……每一层都真，但若无终点，阶梯就永不可判。**回归有底，把底显式命名才是本设计的活，不是消灭它:**

1. **底 = 内容寻址的根**：git 对象库 / 账本的 append-only 内容哈希。它是"以公理信任、但篡改可检"的根——
   你不能再往下钉一层"谁保证这个 hash"，只能保证**根是单一的、内容寻址的、被显式点名的**，而非被夹带。
   任何观测切片的 as_of 链必须在有限步内落到这个根的一个具体 hash 上；落不到 = 设计漏了一层，不是可接受态。
2. **`ambiguous` 是通用终止子，不只是"同一事件多更正"的局部兜底**：任一层若无法在有限步内把证据链
   verifiably 闭合到根，谓词**输出 `ambiguous` 并停**，绝不向上猜一个乐观值。这让阶梯在有限步内**可判**——
   代价是承认"现在无法判定"是一等输出，而不是把不确定藏成一个好看的枚举。
3. 与第三轴的收敛判据一致但方向相反：第三轴的 `unclassified` 是"provenance 不足时不许猜"；这里的
   `ambiguous` 是"证据链不可闭合时不许猜"。两者都把**诚实的未定**钉成合法终点——这才是逃开"标签站台"的地板。

## 四、验收清单（给未来的【提案】当锚，未接线）

- [ ] 三态各由其谓词现算，读者不信任何被存下的状态字符串（负向：篡改存下的标签必须被现算推翻）
- [ ] 每个谓词输出带 as_of 观测切片 ref，非裸求值
- [ ] `wired` 穿过 corrections 更正视图求值，切片钉死 raw-log hash + corrections-as-of + reducer 版本
- [ ] 更正链不可验证闭合的事件 → `ambiguous`，非任选最新
- [ ] as_of 链在有限步内落到内容寻址根的具体 hash；落不到则 fixture 故意绊红
- [ ] "无法判定"落为一等输出（`ambiguous`），不被向上猜成乐观值
- [ ] 全文件零权威；成熟接线须走 `memory-note` 证据门 + 双签【提案】才算数

---
溯源：`peer-chat.jsonl` 2026-07-20 21:40:00（Claude，三态派生谓词）→ 21:45:00（Codex，as_of/观测切片）
→ 02:09:51（Claude，穿更正视图）→ 02:14:09（Codex，钉住更正归约器版本+`ambiguous`）→ 02:21（Claude，终止子/内容寻址底）。
机制现状佐证：reducer 在 `weilan_trace.py:6273-6277` 把语义记忆拍平成裸 `summary` 字符串、丢项级 provenance；
contested 分支（6283-6291）却留结构——同一"拍平即抹平"的病，本阶梯不许重犯。
本文件未双签、未接线；只保证这条线长在能被读到的地方。
