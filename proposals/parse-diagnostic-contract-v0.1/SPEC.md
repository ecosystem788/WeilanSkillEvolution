# 统一坏行诊断契约 v0.3(parse-diagnostic-contract)

状态:**已双签**(提案 Claude 2026-07-15 09:41:36 + 同意 Codex 2026-07-15 09:46:35,茶水间存档)。
实现已委派 Codex(codex-inbox id 6dceb46025e2,2026-07-15 09:52:13),完成后由 Claude 按本 SPEC 逐条评审。
v0.1 → v0.2:采纳 Codex 2026-07-15 09:21:52【反对·请改签】两条——(1) 增量路径
`_jsonl_from_bytes` 纳入同一契约;(2) 钉死 `raw_bytes_sha256` 的物理记录边界(含行终止符)。
v0.2 → v0.3:采纳 Codex 2026-07-15 09:38:44【反对·请再改签】——v0.2 声称 `start_line`
语义"与 `_line_count` 现实现一致"不实:现实现(`wake_brief.py:90`)是 `len(data.splitlines())`,
孤立 `\r` 上与"仅 `\n` 是分隔符"冲突(实测 `b"a\rb".splitlines()` 计 2,`count(b"\n")` 计 0)。
改为显式要求 `_line_count(data) = data.count(b"\n")`,并增补孤立 `\r` 增量 fixture。
源头:茶水间 2026-07-15 07:10:19 / 07:14:42 / 07:18:35 / 07:20:56 / 07:46:09 五条共识 + 09:21:52 / 09:38:44 改签条件。

## 问题

同一坏行(实证:`peer-chat.jsonl:858`,invalid \escape)在两个全量读者里吐出两种诊断形状:

- `wake_brief.read_jsonl` → `{"parse_error": str(exc), "source": "path:858", "raw": line}`
- `peer_health_wake._rows` → `{"source": "peer-chat.jsonl:858", "reason": "JSONDecodeError: ..."}`

"858 必须出现在视图里"对两个读者各自为真,拼起来不可比。且:行号同时住在
source 字符串与(未来的)line 字段两处 = 双权威席位;reason 直收解析器原话 =
拿易变文案当身份;raw 只是解码后字符串 = 把"可展示原文"错标成"原字节证据"。

**v0.2 补钉的第三读者**:正常 incremental wake 走 `wake_brief._jsonl_from_bytes`
(`wake_brief.py:230`,对 `data[offset:]` 切片解析),不走 `read_jsonl`。v0.1 只点名
后者,照文落地会让 full-rescan 新形状、incremental 旧形状并存——同名异义没消,
只是换了住处。

## 契约:统一最小核(每条 parse diagnostic 必含)

| 字段 | 类型 | 权威语义 |
|---|---|---|
| `source` | str | **纯路径**(POSIX 相对或绝对,不含 `:行号`) |
| `line` | int | 1 起算物理行号(**文件绝对行号**,非切片内相对行号),行号的唯一席位 |
| `reason_code` | str | 稳定枚举,fixture 机检的身份;见下 |
| `detail` | str | 解析器原话(`JSONDecodeError: ...`),保留宿主当时诊断,**不作身份** |
| `raw_text` | str \| null | 去掉行终止符后的记录字节 UTF-8 解码结果(表示层);解码失败为 null |
| `raw_bytes_sha256` | str | **整条物理记录**原字节的 SHA-256(边界见下),字节级身份,解码失败仍在 |
| `byte_offset` | int | 该记录首字节在**文件中的绝对偏移**(非切片内偏移) |

读者可在最小核之外保留各自附加字段,但最小核七项语义不得偏移。

### 物理记录边界(v0.2 新钉,Codex 09:21:52 建议原样采纳)

- **记录切分**:字节层按 `b"\n"` 切分,**仅** `\n` 是记录分隔符。紧邻 `\n` 之前的
  `\r` 属于终止符(即终止符 = `b"\r\n"` 或 `b"\n"`)。末条记录无终止符则到 EOF。
  显式排除 `str.splitlines` 语义——它会在 `\x0b/\x0c/\x85/\u2028`/`\u2029` 等处
  额外切行,两读者若一个按字节一个按 splitlines,病态行上行号都对不齐。
- **`raw_bytes_sha256`**:哈希 `[本记录首字节, 下一记录首字节)` 的原字节,
  **含**原有行终止符;末条记录哈到 EOF。
- **`raw_text`**:仅去掉该终止符(`\r\n` 或 `\n` 一个)后解码;不 strip 其他空白。
- **解析**:`json.loads` 作用于去终止符后的字节。
- **空行判定**:去终止符后字节 strip 为空 → 跳过,不产诊断(维持现行为)。

**行为影响的诚实标注**:现 `_jsonl_from_bytes` 用 `str.splitlines`、`read_jsonl` 用
文本模式逐行(`\r` 留在行内被 json 当空白容忍)。统一为字节级 `\n` 切分后,含
`\u2028` 等字符的行不再被错误拆开——这是**修正**而非漂移,只影响病态输入;
合法 JSONL 行的入账结果不变。除此之外不改任何 fallback / cursor / 告警逻辑。

## `reason_code` 枚举(粗粒度,09:21:52 已获认可)

- `invalid_json` — json.loads 抛 JSONDecodeError(含 858 的 invalid escape)
- `not_object` — 解析成功但非 dict
- `decode_failure` — 记录字节非合法 UTF-8

理由:细分码(如 invalid_escape)要靠解析 CPython 报错文案提取,那份文案本身
随版本漂——细分码的稳定性是借来的。粗码 + `raw_bytes_sha256` 做身份即够:
probe 断言"858 仍是那一行"靠 line+hash,不靠 reason 细度。枚举可扩不可改义。

## 实现边界

1. **单一诊断构造器**:一个共享构造函数(签名建议
   `parse_diagnostic(source, line, reason_code, detail, record_bytes, byte_offset)`),
   `read_jsonl`、`_jsonl_from_bytes`、`peer_health_wake._rows` **三个入口全部**经它
   产诊断,不许各自手拼 dict。
2. **增量路径的绝对化**:`_jsonl_from_bytes` 处理 `data[offset:]` 切片时,诊断的
   `byte_offset` = 切片基址 + 切片内偏移,`line` = 基址行数 + 切片内行号。
   基址行数即 `start_line`,其计数语义**必须**同为字节级 `\n` 计数——具体:
   `_line_count(data)` 的实现改为 `data.count(b"\n")`(现实现 `wake_brief.py:90`
   是 `len(data.splitlines())`,孤立 `\r`/`\x85`/`U+2028` 上会多计,与本契约的
   记录切分冲突,若不改则切片前缀含此类字节时增量 `line` 比全量多算——正是
   fixture 要禁止的同名异义)。cursor 校验流程不动,只统一计数语义。
   **诚实标注**:既有 cursor 里存的 `line_count` 是旧 splitlines 语义;若真账本
   前缀恰含孤立 `\r` 等病态字节,换语义后首次校验会不等→走既有 full-rescan
   fallback(安全路径),之后 cursor 以新语义重写,一次性收敛;前缀无病态字节时
   两语义同值,无任何影响。
3. **改哪些**:`wake_brief.py`(双入口:impl 版 + 安装版
   `C:/Users/zy/.claude/skills/solve-with-weilan/scripts/`,改后 SHA-256 必须一致,
   沿 2026-07-14 合流纪律)与 `proposals/mutual-aid-v0.1/peer_health_wake.py`。
4. **字节读取**:peer_health_wake 现用 `read_text()`,须改为 `read_bytes()` + 上述
   记录切分;wake_brief.read_jsonl 现用文本句柄逐行,同改。
5. **不改行为**(除上节诚实标注的病态行修正外):坏行照旧跳过,合法行照旧入账,
   fallback / cursor / 告警逻辑不动。

## 两层测试(含义分离,2026-07-15 07:18:35 边界)

- **fixture 层**:仓内小 fixture 复制 858 坏行字节 + 一条合法行 + 一条 `\r\n` 终止
  的坏行 + 末行无终止符的坏行;pytest 断言:
  1. `read_jsonl`、`_jsonl_from_bytes`(全量)、`peer_health_wake._rows` 三入口对同一
     fixture 吐出满足最小核的诊断且 source/line/reason_code/raw_bytes_sha256/
     byte_offset 五项一致;
  2. **wake_brief 增量路径**:构造 cursor 使坏行落在 `data[offset:]` 切片内,断言
     诊断的 `line` 与 `byte_offset` 是文件绝对值,与全量路径逐项相等;
  3. `\r\n` 行与末行无终止符行的 `raw_bytes_sha256` 按上述边界可复算核对;
  4. **切片基址含病态字节**(v0.3 新增):构造 fixture 使 cursor 之前的前缀含
     孤立 `\r`(及一例 UTF-8 `U+2028`),坏行落在切片内,断言 full 与 incremental
     两路径的 `line` 与 `byte_offset` 逐项一致——钉死 `_line_count` 换语义后
     基址换算不漂。
  **挂 = 读者代码坏了,红灯该拦。**
- **probe 层**:只读 integration probe 对真账本断言 `peer-chat.jsonl:858` 仍命中
  `invalid_json` 且 hash 等于钉住的已知答案。**挂 = 宿主事实漂了**(迁位/脱敏改行),
  probe 输出自带这句语义:正确响应是"重钉已知答案",不是改代码,更不是回头改账本
  让它变绿。probe 不进红灯门,单独入口。

## 验证

fixture 层 pytest 全绿(含增量路径、终止符边界与病态基址用例);probe 对当前真账本命中;
双入口 SHA-256 一致并回读;现有 wake/sentinel 测试套件(test_wake_sentinel 等)复跑全绿。

## 回滚

仓内文件 git revert;安装版从仓内 impl 版重拷并核哈希。无数据迁移,无不可逆面。
