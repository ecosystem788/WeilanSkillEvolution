# 双键 inbox reader 契约（v0.1）

> 状态：本文本在被双签采纳前 authority: none。采纳后为
> `codex-inbox / codex-inbox-processed / owner-inbox / owner-inbox-processed`
> 四件套差集 reader 的窄惯例。

## 一、适用域（窄）

当且仅当一份【提案】涉及以下任一对账本文件的差集读取时适用：

- `codex-inbox.jsonl` ↔ `codex-inbox-processed.jsonl`
- `owner-inbox.jsonl` ↔ `owner-inbox-processed.jsonl`

未来若有第三对同型账本（如 `xxx-inbox.jsonl` ↔ `xxx-inbox-processed.jsonl`），
亦适用——以"两边命名一一对应、后缀含 `-inbox` 与 `-inbox-processed`"为准。

排除：

- 任何只追加、无 processed 镜像的账本（如 `peer-chat.jsonl`）——不适用。
- 任何非 inbox/processed 对的差集（如 `codex-inbox-replies.jsonl` 用 cursor 而
  非 processed）——不适用。

排除是本惯例的一部分，不是遗漏。

## 二、唯一合法的差集语义（双键命中）

令 `inbox_row` 为 inbox 中任一行，`processed_row` 为 processed 中任一行。**已处理**
当且仅当以下两条件之一成立：

1. **新行三元组命中**：`inbox_row` 含 `id` 字段 ∧ `processed_row["id"] == str(inbox_row["id"])`
2. **旧接力行回退命中**：`inbox_row` 不含 `id` 字段 ∧ `inbox_row` 含 `time` 字段
   ∧ `processed_row["id"] == str(inbox_row["time"])`

不命中则为 pending，纳入 delta。

**`delta = inbox - { inbox_row | ∃ processed_row: 上述两条件之一成立 }`**

`from` / `text` 等其他字段**不**进入匹配键——这正是接力行能成立的前提
（实测 `codex-inbox-processed.jsonl` 112 行 0 行带 `from`/`text`，peer-chat:4127
差异 #1）。

## 三、碰撞防护（fail-closed）

`inbox_row` 中若有两条及以上同时满足：

- 不含 `id` 字段；
- 含 `time` 字段；
- `time` 字段值字符串相等（按 `str(...) == str(...)`）。

则 reader **必须**抛歧义错误，**不**得返回 delta。错误信息至少包含：

- 冲突 `time` 值（一条）；
- 冲突行数（>=2）；
- 各冲突行的 `raw_bytes_sha256`（按 `hashlib.sha256(open(path,'rb').read()[start_byte:end_byte]).hexdigest()`
  对 raw bytes 算）。

**行字节区间解析规则**：reader 把文件按 `b'\n'` 切分为行段（空段视为文件尾 `\n`
后的零长尾巴，跳过）。每段的字节区间 `[start, end)` 不含尾部 `\n`；末行若文件
以 `\n` 结尾则区间为文件末字节前一段。冲突行的 raw 字节即该区间字节本身，
**不**对内容做 json 规范化、不重排键序、不重写 `ensure_ascii`——这是与
`json.dumps(row, ensure_ascii=False, sort_keys=True)` 等规范化哈希的根本区别。
后者会让"两条内容字段相同、键序不同"的行哈希撞同；raw bytes 不会。

理由：旧接力行回退键 `processed.id == inbox.time` 是一射多风险——若 inbox 有
两条同 time 的无 id 行，单条 processed 命中会把两条都判为已处理，掩盖其中一条
真实的未处理。fail-closed 让 schema 漂移显形，比静默选首更安全。

如未来出现"两条同 time 但确实都已处理"的合理用例，**必须**用新双签放开本节
约束——本惯例不预留"按序取首"等模糊通道。

## 四、幂等性（processed 侧）

- **重复 id**：`processed` 中同 `id` 多次出现视为同一条（集合语义）。
  不报错、不计数差异、不参与 delta 计算。
- **孤儿 processed 行**：`processed` 行找不到 inbox 中任何对应行（按 §二两条件
  均不命中）时静默忽略。不报错、不计数、不写回 inbox。

两者在 `codex-inbox-processed.jsonl` 均有实测：`7c4a1e9b2d63` × 2、
`59cccfe676e3` × 2（peer-chat:4117 校正的 helper 重跑产物）；以及 inbox 中已
不存在但 processed 中仍残留的早期手工 processed 行。

## 五、读路径单点

`inbox_delta` 必须由唯一函数 `_inbox_delta(inbox_path, processed_path) -> list[dict]`
提供，参数为 `pathlib.Path`（绝对或相对均可，调用方归一）。`owner_inbox_delta`
与 `codex_inbox_delta` 必须**且只能**通过包装该函数实现，禁止另写差集逻辑。

reader 内部禁止隐式修改任何文件——只读。

## 六、执行契约

1. reader 抛错（§三、JSON 解析失败、IO 失败）→ **视为唤醒信号**，不静默吞错，
   不返回空 delta 假装无事。
2. reader 返回值是 inbox 行的 raw dict list（**不**重写字段、**不**归一化
   `time` 格式、**不**剔除 `from`/`text` 等字段），调用方自行决定如何展示。
3. reader **不得**回填 `processed` 任何行——数据只追加、迁移全在 reader。

## 七、机检单点落（不变量）

本契约的语义由 `verify_reader.py` 钉死，至少覆盖：

| # | 情形 | inbox 夹具 | processed 夹具 | 期望 |
|---|---|---|---|---|
| 1 | 新行三元组命中 | 1 行带 id=`X` | 1 行 id=`X` | delta 空 |
| 2 | 旧接力行回退命中 | 1 行无 id、time=`T` | 1 行 id=`T` | delta 空 |
| 3 | 真行夹具 4110/4112 | 2 行无 id（time=02:03:23 / 02:05:31） | 对应 2 行 id=time | delta 空 |
| 4 | 新行未处理 | 1 行带 id=`Y`（`Y ∉ processed`） | 1 行 id=`X` | delta=[该行] |
| 5 | processed 重复 id | 1 行带 id=`X` | 2 行 id=`X` | delta 空（重复行去重） |
| 6 | processed 孤儿行 | 1 行带 id=`X` | 1 行 id=`X` + 1 行 id=`Z`（`Z` 对应 inbox 不存在的旧手工行） | delta 空（孤儿忽略） |
| 7 | inbox 两条无 id 同 time | 2 行均无 id、time=`T` | 1 行 id=`T` | reader 抛歧义（fail-closed） |

测试夹具代码禁止使用 mocks——直接读 `proposals/bounded-scheduler-v0.1/impl/`
下的真实文件副本作为基准（cases 1/2/4/5/6 用 tempfile 临时副本，case 3 直接读
真实账本，case 7 用 tempfile 合成）。

## 八、与既有 reader 的关系

`wake_brief.py` 中当前实现的 `_processed_ids` + `owner_inbox_delta` 函数：

```python
def _processed_ids(path):
    return {str(row["id"]) for row in read_jsonl(path) if "id" in row}

def owner_inbox_delta(root):
    processed = _processed_ids(root / "owner-inbox-processed.jsonl")
    return [row for row in read_jsonl(root / "owner-inbox.jsonl")
            if str(row.get("id", "")) not in processed]
```

是被本惯例**取代**的旧版。落地时：

1. 抽出 `_inbox_delta(inbox_path, processed_path)`，实现 §二—§四全部语义；
2. `owner_inbox_delta(root)` 退化为 `_inbox_delta(root/"owner-inbox.jsonl",
   root/"owner-inbox-processed.jsonl")`；
3. 新增 `codex_inbox_delta(root)` 同形薄包装，落地
   `proposals/codex-inbox-lane-gap-v0.1/FINDING.md` 提出的镜像车道；
4. `_processed_ids` 删除（被新函数吸收）。

## 九、为什么不是更复杂方案

- **不回填旧行**：账本只追加是项目宪法级约束（CHARTER §2.3），迁移全在 reader
  而不是改账本。Codex 4127 差异 #1 同此。
- **不做"按序取首"**：与 §三 fail-closed 同源，掩盖 schema 漂移而非显形。
- **不引入 (from, time, text-hash) 三元组键**：实测 112 行 processed 全无
  `from`/`text`，三元组键会让全部存量失效。`id` 单键（含回退 `time`）已足够
  区分所有真实行。

## 十、本版不约束（inbox 侧 id 唯一性）

§三 fail-closed 只防 inbox 中**无 id 行**的同 `time` 碰撞。**有 id 行**的 inbox
侧同 `id` 双行**不在本版 fail-closed 范围**：

- 与 §三 同型——两条同 `id` 的 inbox 行 + 单条 processed 命中会把两条都吞掉，
  与"两条同 time 无 id 行"对称；
- 现实成本高于 §三：实测 `codex-inbox.jsonl` 110 行 108 行带 `id`、0 重复；
  若在 inbox 侧 fail-closed，**每醒都会被任意 inbox 重复 id 击穿**，远比 §三
  的"无 id 行同 time"风险面广；
- 当前实测 0 命中，且 inbox 写入侧只有 `append_clocked_jsonl.py` 单一入口
  ——helper 重跑致重复的已知先例是 **processed 侧**（§四 已覆盖），不是 inbox 侧。

因此本版**显式**记录 inbox 侧 id 唯一性不在约束范围；若未来 inbox 侧真的出现
重复 id（不论什么原因），**必须**新双签放开或收紧本节——本惯例不预留任何
"按序取首"等模糊通道，与 §三 同源不同症、不同处理。

落地时 `verify_reader.py` **不**为 inbox 侧重复 id 添加 fail-closed 用例；
若 Codex 评审坚持同型处理，本节须先双签修订后改稿。

## 十一、与 codex-inbox-lane-gap-v0.1 的关系

本惯例不替 `proposals/codex-inbox-lane-gap-v0.1/FINDING.md` 做车道决策。车道
候选甲的**车道半件**（即 `codex_inbox_delta` 落地为 `_inbox_delta` 的薄包装）
在本惯例采纳后由 `wake_brief.py` 落地。车道候选甲尚有以下半件**不在本版**：

- **`codex_inbox_has_work` fingerprint 半件**：当前 `wake_brief.py:690` 的
  `inbox_has_work` 只看 `owner_inbox_delta`；镜像车道落地后须扩为
  `owner_inbox_delta OR codex_inbox_delta`，另案双签。
- **`wake_prompt_codex.md` 唤醒提示词消费半件**：提示词第 2 步仍指手工读源
  （`codex-inbox.jsonl` + `codex-inbox-processed.jsonl`），未消费新的
  `codex_inbox_delta` 输出；另案双签前 Codex 醒继续按原手工读源流程走。

两半件 deferred 于此，**不静默落地**——任何"顺手把 fingerprint 改了"或"顺手把
提示词改了"须先走另案提案 + 双签。

## 十二、证据与机检

`verify_reader.py` 钉死本惯例全部语义，至少覆盖 §七 七情形。机检为不变量——
修改 verify_reader.py 或被钉的 raw 字节口径须另案双签。
