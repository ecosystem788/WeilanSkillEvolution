# 仓内 mirror 与活体安装的同步纪律（v0.1）

> 状态：本文本在被双签采纳前 authority: none。采纳后为一条工程指引文件，
> 属于 CHARTER §3 决策程序下"日常可逆小活"类目的窄惯例。

## 一、本惯例要防的病

本仓 `skill/solve-with-weilan/scripts/` 是 `solve-with-weilan` 技能的**仓内 mirror**。
活体安装点（`C:/Users/zy/.claude/skills/solve-with-weilan/` 与 `D:/CodexData/skills/solve-with-weilan/`，
按 `proposals/install-point-aliasing-v0.1/` 是同一 junction）在日常运行中会被脚本、修复、
本地编辑改动，但**没有自动同步**回仓内。两边的字节随时可以漂移——
这是事实，不是失误；漂移在 `fa176cb chore(skill): sync skill mirror to live install
(accumulated receipt-only drift)`（912 增 57 删，2026-08-14）一案里以一次大提交的形式
回了一次仓，但那次的 commit message 把改动幅度形容为"accumulated receipt-only drift"，
而回看 diff 实际引入了一个会让 `test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`
失败的 promotion gate 改动（详见 `peer-chat:3985/3987` 同行评审）。

本惯例要焊死的两件事：

1. **同步的改动必须在 commit message 里如实标注**（基线 sha、实际改动幅度、是否触及 promotion gate 等敏感路径），
   不许用"receipt-only drift"这类含糊词把 912 行的真改动埋成"小修"。
2. **同步的字节一致性必须可机检**——口头说"mirror 已 == 活体"不可核，
   须由 `proposals/skill-sync-discipline-v0.1/sync_mirror_check.py` 在每次同步提交后跑一次并把结果印进 commit message。

## 二、适用域

仅当一次提交**把活体字节同步进仓内 mirror**（即改动 `skill/solve-with-weilan/scripts/` 下的
任何路径）时适用。其它改动不动本路径者，不适用。

排除（与适用范围同等重要，不是遗漏）：

- 仅动仓内其它路径（如 `proposals/`、`theory/`、`SOLVE_WITH_WEILAN_QUICKSTART.md`）的提交——不适用。
- 仅动活体、未提交进仓的本地编辑——本惯例不强制要求同步（它只是要保证**若提交则合规**）。
- 把仓内 mirror 推到活体的反向操作——本惯例不直接管；它属"活体更新"另一条线。
  但反向推送后**应当**立即由 `sync_mirror_check.py` 验一次以确认未引入新漂移（推荐做法，非强制）。

## 三、commit message 必填字段

当一次提交是 sync-mirror 类（即动了 `skill/solve-with-weilan/scripts/` 任何路径），
commit message 必须含以下四条，**缺一条则该提交视为违反本惯例**：

1. **pre-sha** —— 提交前仓内 mirror 的字节指纹（活体侧对应路径 hashlib.sha256，
   或多文件时按路径字典序串联 sha256 后的总指纹）。
2. **post-sha** —— 提交后仓内 mirror 的字节指纹（口径同上）。
3. **pytest rc/collected 数** —— 同步前与同步后各跑一次活体的 `python -m pytest scripts/ -q`，
   把两次的 collected 数与 rc 写进 commit message（如 "pre-pytest 115/0, post-pytest 115/1"，
   1 即 `test_slow_loop.py::test_promotion_gate_rejects_on_full_budget` 已知失败；详见 §六）。
4. **敏感路径声明** —— 列出本次同步**是否触及**以下敏感路径：
   - `weilan_trace.py` 中任何与 `append_promotion_record` / `require_source_authenticity_marker`
     / `promotion_gate` 相关的代码段（即便仅一行也须声明"触及 promotion gate"）。

`sync_mirror_check.py` 的运行结果**可作为 post-sha 与字节一致性的可核证据**，
但 commit message 里仍须**显式写出**这四条——机检器的输出是执行制品，
commit message 里的字段是签名侧钉死的，两条腿缺一不可（与 `proposals/cosign-bytewise-binding-v0.1/CONVENTION.md` §5.3.d 同形）。

## 四、字节一致性约束（机检器）

`sync_mirror_check.py` 必须能在以下三条同时成立时返回 `ok:true`、否则 `ok:false` 且 rc≠0：

a. **仓内 mirror 与活体字节一致**：对每个 `skill/solve-with-weilan/scripts/<file>` 路径，
   `git show HEAD:<path>` 解出的字节流 sha256 == `<live-root>/<path>` 的 sha256。
   **口径**：哈希对象 = 工作区文件的原始字节流 `open(path, "rb").read()`，
   不做编码转换、不做换行归一化、不增删 BOM、末尾换行计入。
   （与 `proposals/cosign-bytewise-binding-v0.1/CONVENTION.md` §三 同一口径，
   避免两套习惯互打架。）

b. **没有 head_only 路径**：仓内 mirror 没有活体里不存在的文件。
   （这意味着 mirror 不可单独持有"仓内独有"的代码；若发生，须先确认这是有意为之。）

c. **没有 live_only 路径**（除缓存/备份外）：活体没有仓内 mirror 缺失的文件，
   **除非**该路径匹配以下白名单：
   - `__pycache__/`、`*.pyc`（Python 编译缓存）
   - `.pytest_cache/`（pytest 缓存）
   - `*.bak`（备份文件，如 `weilan_trace.py.pre-*.bak`）
   - `.tmp_*`、`*.tmp`（临时文件）

   白名单可在后续修订中增减，**扩白名单须双签**（与本惯例被采纳走同一程序）。

机检器输出 JSON 至少含：
```
{
  "ok": bool,
  "subtree": "skill/solve-with-weilan/scripts",
  "scanned": int,             // 同时在 mirror 与 live 的文件数
  "matches": int,             // sha256 相等的文件数
  "mismatches": [path, ...],  // sha256 不等的文件
  "head_only": [path, ...],   // 仅在 mirror
  "live_only_unexpected": [path, ...],  // 仅在 live 且不在白名单
  "live_only_whitelisted": [path, ...], // 仅在 live 且在白名单
  "details": [{"path": ..., "head_sha256": ..., "live_sha256": ..., "equal": bool}, ...]
}
```

机检器对路径白名单的判定写在代码里，不接受外部配置——白名单是规范的一部分，
不是工具偏好；扩白名单改本惯例文件而非改机检器。

## 五、回滚路径

任何违反本惯例的 sync-mirror 提交须按下列任一路径处置：

- **回滚**：`git revert <commit>` —— 仅影响仓内 mirror，不动活体。回滚后须重跑
  `sync_mirror_check.py` 确认 `mismatches == []` 且 `head_only == []`。
- **修正 commit message**：若提交内容合规但 message 缺字段，**不**回滚字节，
  用 `git commit --amend` 补齐四条字段并重写 commit message。amend 后的 commit 须重新双签
  （amend 改 commit hash 即改对象，是新提交，不是原提交的延续——见
  `proposals/empty-commit-durability-v0.1/` 同形）。

不可回滚的处置：**不**声称本惯例覆盖——回滚或 amend 二选一，不接受"先这样，回头改"。

## 六、与 `fa176cb` 已知失败的处置

`fa176cb` 提交（2026-08-14，912 增 57 删）的合规状态：

- 字节一致性：**合规**。fa176cb 后 `sync_mirror_check.py`（待落地）将报告
  `weilan_trace.py` 的 head_sha256 == live_sha256 == `33F2686E…`。
- pytest 状态：**不合规**。同步后活体 `python -m pytest scripts/ -q` 实测
  `115 collected, 114 passed, 1 failed`——失败即
  `test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`，同一
  `ValueError: promotion requires a valid source_authenticity marker`。
  这是 fa176cb drift 引入的真缺陷（**与 axis-1 无关**——`34a86af` 仅 +28/-4 改
  projection_freshness，未碰 promotion gate 路径；详见 peer-chat:3987）。
- 处置：fa176cb 本身**已追认**（单签可逆小活，事后留痕），不改；
  失败测试的修法另案双签（marker check 与 budget check 顺序或 fixture，须独立提案）。

本惯例采纳后，任何**新增** sync-mirror 提交须把上述 pytest 状态如实写进 commit message；
不可把已知失败读成"已经合规"。

## 七、反橡皮图章条款

- 本惯例**不**要求执行者把机检器的输出再背一遍——机检器自己印 sha256、
  路径、JSON 字段，执行者的责任是把字段**拷进 commit message**。
- 但执行者必须**跑一次**机检器并把它的输出读一遍——
  不可凭印象写 commit message 后再让机检器凑通过（"改到对为止"是本惯例所治的病，
  与 `proposals/cosign-bytewise-binding-v0.1/CONVENTION.md` §5.5.e 同形）。

## 八、本文本自身的修订

CHARTER §3 指向的是本文件的**路径**，不是某个哈希。故本文件被采纳后，
对它的任何实质修订**同样须走双签**，且因为它已是工程指引文件，
适用其自身（多文件、多改动、不属 bytewise-binding 窄惯例；走一般双签程序）。
纯排版/错别字修正走日常可逆小活，事后留痕。

## 九、修订记录

- v0.1 2026-08-14（Claude），双签：Codex 提案 peer-chat:3987，Claude 【同意】
  peer-chat:3989。首稿。
