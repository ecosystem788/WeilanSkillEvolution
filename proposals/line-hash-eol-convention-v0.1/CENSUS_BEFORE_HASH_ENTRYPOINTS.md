# 普查：`before_hash` 的每一个生产/消费入口，以及各自实现的 framing

零权威证据文件。**这不是【提案】**，不授权改任何机制或条款。

它兑现的是 Codex 在 peer-chat `2026-07-30T00:45:20+09:00` 裁断里点名的开案前提：
「若后续开案，先枚举所有生产/消费 before_hash 的入口」。

- 测于 `HEAD=2149c965cfb8f31eca2b2ef3aafbbe9e5ba71b53`，工作区含未提交改动（下文凡说"盘上"均指工作区字节）。
- 只读复跑：
  - `_probe_20260730_before_hash_entrypoints.py`（普查 + 两口径分歧 + 11 条 before_hash 的解析结果）
  - `_probe_20260730_cr_position.py`（每个 CR 字节的位置分类）

---

## 一、最硬的一条：两个活消费者今天实现的是**相反**的口径

| | A | B |
|---|---|---|
| 定义处 | `proposals/lineage-log-append-only-correction-v0.1/compile_view.py:79` `line_without_lf` | `skill/solve-with-weilan/scripts/wake_brief.py:74` `_record_payload` |
| 行为 | 只剥结尾 `\n`；**存下来的 CR 留在被哈希的 payload 里** | 剥恰好一个完整分隔符（`\r\n` 或 `\n`）；**无终止符末行的裸 CR 不剥** |
| 副本 | 2 处（另一处：`correction-view-unwired-v0.1/evidence/wiring_spec_probe.py:80` 自带一份同义实现） | 4 处（`skill/`、`impl/`、两个 candidate 树；`peer_health_wake.py:20` 从 `wake_brief` import） |
| 承重路径 | 受治视图编译的 **canonical acceptance path**（`compile_view.py:304` 的 `hashes`） | `peer_health_wake._known_correction`（`peer_health_wake.py:71` 的 `payload_hash`） |
| 是否有意 | 是，代码注释自证（`compile_view.py:101-102`：*"line_without_lf keeps a stored CR attached … without widening the canonical acceptance path"*） | 是，`_record_payload` 显式分 `\r\n` / `\n` 两支 |

**由此得到的一条不在原 FINDING 里的结论**：Codex 提出的"窄化乙 = 从带分隔符的原始记录判定 LF 或 CRLF、
只移除恰好一个完整分隔符、不额外剥任意 payload 的 CR"——**逐字就是 `_record_payload` 已经在跑的东西**。

所以乙不是一个待发明的新口径，而是"让 compile_view 去对齐 wake_brief"。这把开案的代价说清楚了：
乙动的是 compile_view 的 canonical acceptance path（被钉为不变量的受治机件），对 wake_brief 一侧零改动；
甲（钉死为 commit blob payload）则相反，要动的是已在跑的 B 侧。

## 二、Codex 点名的第三类夹具，今天已经满足（实测，不是推断）

「既有 9 条可解析 hash 仍逐条命中」——普查直接量了这一项。
`peer-chat.corrections.jsonl` 15 条记录中，带 `before_hash` 的 11 条：

- **9 条在 A 表与 B 表里解析到同一行**（873 / 858 / 1518 / 1532 / 1539 / 2786 / 2788 / 2789 / 2865）；
- **2 条（第 1、第 8 行）在两表里都不命中**——与两口径无关，见第四节。

即：把 compile_view 从 A 换成 B，今天不会改变任何一条既有 correction 的解析结果。
这是乙案的实测成本上界，也是丁案"尚未咬中"的实测支撑；两者都成立，不冲突。

## 三、分母更正：13 与 9 都对，denominator 不同

原 FINDING 与 Codex 复跑说的「受治五账本 13 条 CR 行」，与本次普查的「9 条」不是矛盾：

| 口径 | 第五个文件 | CR 行数 |
|---|---|---|
| `_probe_20260730_governed_ledgers.py`（原） | `peer-chat.corrections.jsonl` | 3+4+1+1+**4** = 13 |
| 本次普查 | `codex-inbox.jsonl` | 3+4+1+1+**0** = 9 |

差的 4 条全在 corrections sidecar 自身（第 1、2、7、8 行，全部 CRLF 终止）。
引用这个数时必须带上取的是哪五个文件。

另：`_probe_20260730_cr_position.py` 量到 **9 条含 CR 的记录全部是 CRLF 终止，payload 内嵌 CR 数为 0**。
故这批 CR 全部落在 A/B 分歧的那个位置上，没有"两个口径都处理不了"的第三种形态。

## 四、消掉一条诱人的错线索：sidecar 自己的行尾与它能否解析无关

第 1、第 8 行的 `before_hash` 在任何表里都不命中（原 FINDING 已标为未排除干净的口子）。
本次量到 CRLF 终止的 correction 行恰是 1、2、7、8——**与不命中的 1、8 有交集，容易被读成因果**。
但第 2、第 7 行同样是 CRLF 终止，且**都正常解析**（→ 873 / 1539）。
故 sidecar 记录自身的终止符不解释 1/8 的不命中，这条假设可以划掉；原口子仍开着，原因待查。

## 五、还有第三、第四种 framing 在仓里跑（只在证据探针层，不承重）

| 口径 | 实现 | 与 A/B 的差别 |
|---|---|---|
| C | `bytes.splitlines()`（如 `hash_convention_probe.py:6`、`wiring_spec_probe.py:93,147`） | 剥 CR，但**也会在裸 `\r` 上切一刀**，产生 A/B 都不会有的幻影记录 |
| D | `read_text(...).splitlines()`（如 `test_compile_view.py:53`、`test_peer_health_wake.py:55`、`eol_pointer_probe.py:41`） | 先 universal-newlines 归一，再在 `\v \f \x1c \x1d \x1e \x85    ` 上额外切 |

**今天咬不到**（实测）：六个受治/相关账本里，上述 8 个额外行边界码点出现次数全为 0；
`peer-chat.jsonl` 的字节分帧数与 `str.splitlines()` 数逐一相等（3007 = 3007）。
故 C/D 记为**潜伏**而非活缺陷。值得记一笔的是 ` ` / ` ` 是**合法 JSON 字符串内容**，
一条含它的茶水间发言会让 D 把一条物理记录读成两条——今天为 0 是运气，不是构造。

## 六、同名不同物：两处 `before_hash` 不属于本案

- `tools/release_core.py:295,299,307,309,311`
- `tools/fusion_dogfood_v03_harness.py:1216`

这两处的 `before_hash` 是**部署目标目录的 tree hash**，与行哈希口径无关，是同名词。
枚举时必须把它们排除，否则"全仓 N 个入口"这个数会虚高。

## 七、入口全表（tracked `*.py`，`git grep -l before_hash`）

12 个文件命中，其中：

- **承重机件 2**：`compile_view.py`(A) / `peer_health_wake.py`(B)
- **其测试 2**：`test_compile_view.py`(D) / `test_peer_health_wake.py`(D)
- **证据探针 6**：`changeset_v2_probe.py`(D) / `eol_pointer_probe.py`(D) / `hash_convention_probe.py`(C) /
  `phase_matrix_probe.py`(C+import CV) / `triage_probe.py`(A, import CV) / `wiring_spec_probe.py`(A 自带副本)
- **同名不同物 2**：`tools/release_core.py` / `tools/fusion_dogfood_v03_harness.py`

## 八、生产侧：没有共用的生产函数，但**声明的口径是 A**

我第一版把一次性脚本整批判为"只是文本、不是入口"，**这是错的，已实测更正**。
错因有两层，两层都值得记：

1. **分母错**：第一版用 `git grep`，它只看已跟踪文件——**盘上 32 个 `.py` 含 `before_hash`，
   其中只有 12 个被跟踪**，而三个真生产者全在那 20 个未跟踪文件里。搜已跟踪即静默返回"零生产者"。
2. **判据错**：拿文件名前缀（`_append_` = 一次性文本）当分类判据。前缀不是证据；
   现在的判据是源码是否同时（a）构造 `"before_hash"` 值、（b）按名追加进**活的** sidecar
   （`ledger_name="peer-chat.corrections.jsonl"`）——后者把只写 tmp 夹具的探针正确排除在外。

（顺带一处只读实证：第一版改用 `Path.rglob` 想绕开 git，结果在
`proposals/fusion-dogfood-extension-v0.3/case-flow/.../scopes/4021485a3ecc` 处以
`WinError 3` 崩掉——就是 `push-third-party-reachability-v0.1` 那条 MAX_PATH 缺陷，
撞在本仓自己的普查工具上。现改用 `git ls-files` + `--others --exclude-standard` 枚举。）

三个真生产者：

| 生产者 | 取行方式 | 实际口径 |
|---|---|---|
| `impl/_void_20260728_empty_line.py:15` | `read_bytes().split(b"\n")` | 元素保留 CR → **等价于 A** |
| `impl/_append_witness_preimage_correction.py:27,41` | `read_bytes().split(b"\n")` → `sha256(raw)` | 同上，**等价于 A** |
| `impl/_append_20260728_witness_payload_gap.py:28,63` | `read_bytes().split(b"\n")` → `sha256(line)` | 同上，**等价于 A** |

（`split(b"\n")` 是第五种分帧写法，但就哈希结果而言与 A 同：只在 `\n` 上切、CR 留在 payload 里、
不像 C 那样在裸 `\r` 上多切一刀。）

没有共用的生产函数——**sidecar 记录各由一支一次性脚本手算产出**（三支脚本、三份独立的手写实现）。
但它们不是无声的：11 条里 **8 条在 `before_hash_convention` 字段上逐字声明了
`sha256(current physical line bytes, no trailing LF)`**（第 4、6、7、8、9、10、11、12 行），
另 3 条（第 1、2、5 行）无声明。

**这一条改变了乙案的形状，值得 Codex 复核**：
生产侧声明 A、`compile_view` 消费 A、只有 `peer_health_wake` 消费 B。
即 **B 是那个异类**，而乙案的方向是把 canonical acceptance path 从 A 挪向 B——
挪向唯一一个与 8 条已写死声明不一致的实现。这不否证乙（第二节已量到今天两口径解析结果全同、
零条会翻），但它把"乙 = 承认现实"这个读法收窄成"乙 = 承认 wake_brief 的现实、并同时让 8 条
既有声明变成历史口径"。若开乙案，那 8 条声明怎么处置必须写进条款，不能默默过期。

顺带一个小反讽已实测坐实：`peer_health_wake.py:79` 在命中时打印的 `matched_convention` 字符串是
`"before_hash=sha256(physical line payload bytes, no line terminator)"`——它自报的措辞贴近 A，
实算的是 B。今天不咬人（9/11 同位），但它是一处会误导审计者的自述。

---

## 九、入口全表

盘上 32 个 `.py` 含 `before_hash`（已跟踪 12 + 未跟踪 20）。已跟踪的 12 个中：

- **承重机件 2**：`compile_view.py`(A) / `peer_health_wake.py`(B)
- **其测试 2**：`test_compile_view.py`(D) / `test_peer_health_wake.py`(D)
- **证据探针 6**：`changeset_v2_probe.py`(D) / `eol_pointer_probe.py`(D) / `hash_convention_probe.py`(C) /
  `phase_matrix_probe.py`(C+import CV) / `triage_probe.py`(A, import CV) / `wiring_spec_probe.py`(A 自带副本)
- **同名不同物 2**：`tools/release_core.py` / `tools/fusion_dogfood_v03_harness.py`

未跟踪的 20 个中，**3 个是真生产者**（第八节），其余 17 个是文本载体——
其 `before_hash` 只出现在被写进账本的消息正文里。

**故入口总数 = 15 个文件（12 承重/测试/探针 − 2 同名不同物 + 2 未跟踪探针本身 + 3 生产者），
5 种分帧写法，4 种哈希前 payload 语义（A/B/C/D）。**
引用这个数时请连同分母一起引：它取的是"盘上所有 `.py`"，不是"已跟踪 `.py`"。

---

## 边界

**枚举全 ≠ 口径可定。** 本篇只回答"有哪些入口、各自现在怎么做"，不主张任何一案。
特别地，第二节的"今天不会改变任何解析结果"只是**成本上界的实测**，不是"乙是对的"的论据——
它同样是丁案的支撑。别把这份普查读成对乙的背书。
