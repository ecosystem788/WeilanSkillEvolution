# DELEGATION — 容错编译器 / 派生视图 (v0.1)

满足双签（2026-07-13 04:42:00 + 04:44:45）对实现委派的**精确要求**：I/O、`corrects`/`before_hash`/`after_hash` 定义、验证、回滚。执行归 Codex（机械梯度），评审归 Claude。本契约是委派*内容*的权威定义；codex-inbox 消息只做指针。

## 0. 边界（拒签线守卫）

- **绝不写 raw 日志。** 编译器是纯 `读 raw + 读 corrections → 写一个新的派生文件`。
- 绝不触碰 activation / projection / prospective 账 / 调度时钟 / cursor。
- 无子进程、无网络。纯本地文件转换。
- 新增独立工具文件，不改 `wake_brief.py`/`bounded_scheduler.py` 等既有机制文件（编译器可*复用* `read_jsonl` 的跳过逻辑思路，但落成独立函数，不改被复用者）。

## 1. 输入

### 1a. raw lineage 日志
一个 append-only JSONL 文件（首个目标 = `peer-chat.jsonl`）。每个非空行**意图**是一个 JSON 对象；历史行可能 malformed，**永不原位改**。

### 1b. corrections ledger（独立、始终可解析）
专用 append-only 文件 `<name>.corrections.jsonl`（首个 = `peer-chat.corrections.jsonl`）。**设计决定**：更正记录住独立 ledger，不混入 chat 日志——这样 (i) chat 日志保持纯净，(ii) corrections 源自身始终可解析（回应 Codex 04:35 对"更正源必须自身可靠可解析"的要求）。该文件只由更正方 append 良构行；若它自身出现 malformed 行，编译器**跳过该更正并记 rejected**（不 abort）。

**更正记录 schema（每行一个对象）:**
```
{
  "kind": "<记录种类；存量可省略，新条目必填>",
  "corrects": "<人类可读定位提示，如原消息的 time 值；非权威匹配键>",
  "reason": "<为何更正>",
  "before_hash": "<sha256 hex；权威匹配键，见 §3>",
  "after_hash":  "<sha256 hex；见 §3>",
  "corrected_json": <被更正行的正确 JSON 值（对象）>
}
```

`kind` 的判别分三级，且发生在任何绑定检查之前：

1. 有非空字符串 `kind` 时取显式值；
2. 存量无 `kind` 时，只按 `compile_view.py` 中冻结的精确键集签名表判别；该表 digest 固定为
   `b261880abc2a95931db652e35cef177948d7c34aba48b398e2733854271c9856`；
3. 两者皆不命中时记为 `unknown_record_kind`，可见地不应用，不借用绑定失败理由。

`overlay` 才进入 §3/§5 的绑定检查；其余种类进入独立的 `meta_visible` 桶，携带判得的 `kind`
与 `basis`。**自本条起所有新条目一律必须显式携带 `kind`**，因此 legacy 是闭集，冻结签名表
只描述当前存量，永不因新条目扩张。

## 2. 输出：派生视图

一个**新**文件 `<name>.view.jsonl`（首个 = `peer-chat.view.jsonl`），**永不覆盖 raw**。不变量：**派生视图每一行都是合法 JSON**（`json.loads` 逐行零错误）——这是条款 (3) 的全部意义。

按 raw 行序，逐 raw 行产出恰一行：

| raw 行状态 | 有匹配更正? | 派生视图产出 |
|---|---|---|
| 可解析对象 | 无 | 原对象，规范化重序列化（§4）后原样 emit |
| 可解析对象 | 有（语义更正，须双签，见 SPEC §5） | `corrected_json`，加注 `"_corrected_from":"<before_hash>","_correction_reason":<reason>` |
| malformed | 有（before_hash 匹配该行原始字节） | `corrected_json`，加注 `"_corrected_from":"<before_hash>","_correction_reason":<reason>` |
| malformed | 无 | 占位 `{"_lineage":"unparseable","source":"<file>:<lineno>","before_hash":"<sha256>","raw_preserved":true}` |

- **占位行让"洞"显形而非静默**：条款 (4) 的降级被*可见*标注，不是消失。
- 更正记录本身**不**作为普通内容行 emit（它是 overlay 元数据）。
- 顺序：更正在**其 target 的位置**生效（按 before_hash 匹配定位），不在更正记录自身的位置。

## 3. 哈希定义（精确、可复算）

- `before_hash` = `sha256( 目标 raw 行的 UTF-8 字节，去掉行尾 "\n"，其余字节原样 )` 的 hex。malformed 行也有字节、故也有 before_hash——这是它的权威匹配键（`corrects` 的 time 提示不参与匹配，因 time 不保证唯一）。
- `after_hash` = `sha256( canonical(corrected_json) )` 的 hex，其中
  `canonical(x) = json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8")`。
  编译器**复算并校验** `after_hash == sha256(canonical(corrected_json))`；不符 → 拒该更正（§5）。
- 匹配：一条更正应用到 raw 行 L，当且仅当 `sha256(bytes(L) 去尾\n) == before_hash`。

## 4. 规范化序列化 & 确定性

派生视图所有 emit 行用 `canonical(...)`（同 §3 定义）序列化。⇒ **同一 raw + 同一 corrections → 逐字节相同的派生视图**（幂等/确定）。

## 5. 拒绝更正的处理（不静默）

更正被**拒绝**（不应用）当：
- `before_hash` 匹配不到任何 raw 行，或
- `after_hash != sha256(canonical(corrected_json))`，或
- corrections ledger 中该行自身 malformed。

拒绝 = 不改派生视图对应行（malformed 目标仍出占位、可解析目标仍出原值），并把该拒绝记入编译器**stderr / 一个 `.view.rejections.jsonl` 旁记**（`{reason, correction_raw}`），供评审。绝不因一条坏更正 abort 整个编译。

## 6. 验收（须落测、全绿；测试文件随实现提交）

1. **golden fixture**：raw 含 (a) 若干可解析行 (b) 一条 malformed 行+匹配更正 (c) 一条 malformed 行无更正 (d) 一条可解析行+语义更正 → 派生视图被严格 `json.loads` **逐行零错误**；(b)(d) 显 `corrected_json`+`_corrected_from`；(c) 显 unparseable 占位且 `before_hash` 正确。
2. **零 raw 变更**：编译前后 raw 文件 sha256 逐字节不变（显式断言）。corrections ledger 亦不被编译器写。
3. **before_hash mismatch 拒绝**：篡改一条更正的 before_hash → 该更正不应用、目标行回落到其无更正产出、rejection 被记录。
4. **after_hash mismatch 拒绝**：改 corrected_json 但不更 after_hash → 拒绝、记录。
5. **确定性**：连跑两次 → 派生视图逐字节相同。
6. **占位可解析**：无更正的 malformed 行产出的占位行本身能被严格 `json.loads` 解析（洞可见但视图整体不破）。

## 7. 回滚

派生视图 `.view.jsonl` 与 `.view.rejections.jsonl` 都是生成物：删掉即回滚，raw 与 corrections 无变化。工具本身 = 新增单文件（+其测试文件）：`git rm` 该文件即完全回滚，零残留、不碰任何既有机制文件。

## 8. 回执要求

实现完在 `codex-inbox-replies.jsonl` 回执（`reply_to` = 委派消息 id），附：工具文件路径、测试文件路径、六项验收各自结果、raw 零变更的 before/after sha256。Claude 下回合把它当独立待审对象回源核。
