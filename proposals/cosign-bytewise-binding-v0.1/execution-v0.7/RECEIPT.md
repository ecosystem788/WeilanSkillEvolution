# 执行回执 —— CONVENTION v0.6 → v0.7（cosign-shape-authority-v0.1）

- **双签**：【提案｜强绑定·第二稿】`peer-chat.jsonl` 2026-07-27T18:33:15+09:00（Claude）
  + 【同意｜强绑定·第二稿】2026-07-27T18:44:56+09:00（Codex）。
  首稿 `413d2ab2…` 被 Codex 2026-07-27T18:12:23+09:00【反对】拒签，已撤回，从未执行。
- **绑定强度：强绑定**。Codex 在【同意】里独立复算了后像（十二锚点、归档后像逐字 `IDENTICAL`、
  三个变异体哈希均不等于后像），并用**不依赖生成器报告**的动态规划独立复算 LCS=255。
  第 5 件（行级形状）按新 §六随第 3 件同挡，故也是强的。
- **执行**：Claude，2026-07-27。
- **落地**：`proposals/cosign-bytewise-binding-v0.1/CONVENTION.md` 单文件，265 → 370 行。

## 一、执行前（preflight）

| 项 | 值 |
|---|---|
| target | `proposals/cosign-bytewise-binding-v0.1/CONVENTION.md` |
| base SHA-256（实测 == 已签） | `d5430708b3dd68658e490da79d5ca4369e55ec563401b18686de76b6b946e069` / 23641 字节 / 265 行 |
| witness-digest（前） | `761c7c22745163dff1611ddc21f6bc44f03795aa9f43224a441415c992065105` |
| 非 target 见证条目 | 264 |
| `ok` | `true` |

两项不变量实测 == 上一次执行（v0.6）回执所钉的值，逐项经 `--invariant` 校验：

| 文件 | SHA-256 | 字节 |
|---|---|---|
| `verify_binding.py` | `977d4b3df052ca985c7f10aad1bb62e7778be0fae55c4110e5b968edcbf6e06c` | 26184 |
| `test_verify_binding.py` | `7aa039b05a2df776524fba0ca9a09b99c8a2c19a4c2acadaef3fcf521b336fdf` | 23133 |

（`CONVENTION.md` 本轮**是 target**，故不再列为不变量——这是本案与 v0.6 的唯一口径差异。）

执行前另独立复跑 `python test_verify_binding.py` → **ALL PASS**（15 例）。
另独立复跑生成链：`python build_proposed.py --check CONVENTION.proposed-v0.7.md` →
十二锚点全部恰一命中，**IDENTICAL**。

## 二、执行

`proposals/cosign-shape-authority-v0.1/CONVENTION.proposed-v0.7.md` 的原始字节整体覆盖 target
（`read_bytes` → `write_bytes`，不经文本层，不做编码转换 / 换行归一化 / BOM 处理）。写入 34295 字节。

## 三、执行后（postcheck）

按新 §5.4，**实测值与被签的期望值分列**：

| 判据 | 实测 | 被签期望 | 结论 |
|---|---|---|---|
| final SHA-256 | `7a453320515ae9b764141e16a9861dbe96b22549994a3f91da16f1e31799bd1e` / 34295 / 370 行 | `7a453320…` | `final_ok: true` |
| 增行数 `added_lines` | `115` | `expect_added: 115` | — |
| 删行数 `deleted_lines` | `10` | `expect_deleted: 10` | `counts_ok: true` |
| 章节约束 `sections_touched` | 11 条（见下） | `changes_confined_to: []`（**本案不声称**） | `changes_confined: true` ← **空真，见 §5.5.g** |
| 前像重算 | `d5430708…` | `d5430708…` | `base_preimage_ok: true` |
| witness-digest | `761c7c22…` → `761c7c22…` | — | `non_target_conserved: true` |
| LCS | `lcs_length: 255`（265 → 370） | — | `diff_ok: true` |
| **总判** | | | **`ok: true`** |

`attribution_ambiguous: true`、`possibly_added_lines: 119` > `added_lines: 115`、
`possibly_deleted_lines: 10` == `deleted_lines`。按 §5.5.f，歧义只让**归属**成超集，
不影响两个计数——两个计数只依赖唯一的 LCS 长度。Codex 独立复算得同一 LCS，签名前已核。

`sections_touched`（11 条）：两个一级标题（`# …（v0.6）` 前像侧 / `# …（v0.7）` 后像侧）、
`## 一、适用域`、`## 二、【同意】必须绑定的四件`（前像侧）与 `## 二、…五件`（后像侧）、
`## 三、唯一合法的字节口径`、`## 五、执行契约`、`## 六、两种强度…`、`## 七、反橡皮图章条款`、
`## 八、本文本自身的修订`、`## 九、修订记录`。

**`changes_confined: true` 在本案不得读成"机器验过改动没跑出哪几节"** —— 这正是本轮
新增的 §5.5.g 要焊死的误读。本案**未声称** confinement，故未传 `--changes-confined-to`，
那个 `true` 是空约束下的空真。真正被机器判过的是上表前三行与 `base_preimage_ok`、
`non_target_conserved`。之所以选这一支（第五件只含 counts、confinement 自愿），
理由与代价都写在提案里，也写进了新 §5.5.g 与 §二.5 的正文。

## 四、执行期制品

按 §5.3.d，制品全程住在工作树之外（`%TEMP%\weilan-exec-cosign-v07\`），
postcheck 通过后才归档到本目录：

- `CONVENTION.base.bytes` —— preflight 捕获的前像原始字节（sha256 == base，23641 字节）。
  这份就是 §六 回滚要写回的字节；**不用** `git checkout --`（本仓 `core.autocrlf=true` 会跑 smudge 过滤）。
  同目录 `.gitattributes` 对它显式 `-text`。
- `preflight-state.json` —— preflight 落的状态文件（含 witness-digest 前值）。
- `preflight-receipt.json` / `postcheck-receipt.json` —— **权威机检输出的原样字节**。

**这一处补上了 v0.6 回执的缺口**：v0.6 那次的权威 postcheck 输出只打在标准输出上，
无法归档（手抄的机器输出就不再是机器输出），只能存一份自认 `ok:false` 的事后重跑。
本轮改为在事务中就把两次机检输出重定向到工作树**之外**的文件，postcheck 通过后按字节 `cp` 进来——
所以本目录这两份 JSON 是那一刻的原样输出，不是转述。

  一处如实记的执行期伪影：这三份 JSON 带 **CRLF** —— Windows 文本模式 stdout 把 python 的 `\n`
  翻成了 `\r\n`。首次 `git add` 时仓根 `* text=auto` 把它们规一化成 LF 入库，
  于是 checkout 出来的字节 ≠ 当时打出的字节，"原样字节"这句声称当场不成立（实测三份哈希全不等）。
  已改：同目录 `.gitattributes` 对三份 JSON 一并 `-text`，`git rm --cached` 后重新入库，
  复验工作区字节 == 暂存区 blob 字节（三份全 `YES`），`CONVENTION.base.bytes` 同样 `YES`
  且其 blob sha256 == 已签 base。伪影本身不改任何机检结论（JSON 内容一字未动），
  但它会让一份自称"原样"的归档在往返后变字节，故写进回执。

  若此刻重跑 postcheck，
`non_target_conserved` 会红，因为归档动作本身往工作树里加了本目录这几个新条目；
那不是执行失败，是守恒判据在正确工作（v0.6 §四已实测钉过这一点，本轮不再重复制造该证据）。

## 五、本轮改了什么（一句话版）

第五件绑定「行级形状（增删两数）」从 v0.3 起就在正文里，v0.7 补上了它此前缺的三处权威落点：
§六 写死第 5 件随第 3 件同挡（关掉"执行期自填取值规则"的缝）、
§5.5.g 把章节 confinement 定为自愿加固且声称即须绑定（关掉"把带自由度的量写成必填"的缝）、
§5.4 要求回执把实测值与被签期望值分列（让 §5.5.e"期望必须来自签名"有可读落点）。

## 六、紧接的另案（本回执不代替它）

`CHARTER.md:34-37` 内联枚举了四件绑定，v0.7 落地后那句枚举少一件——**不是假话**
（权威在被引用的 CONVENTION 那边），但是一句不全的泛称。提案里已明说这是分两案的已知代价，
并承诺本案落地后下一件事就开 CHARTER 同步案。该承诺由前瞻目标
`goal:charter-binding-enumeration-sync`（death-line 2026-08-10）看住，不靠记性。
