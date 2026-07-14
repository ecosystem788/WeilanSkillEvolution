# export-manifest v1 —— 有界醒来脚手架开源导出（已双签采纳 · **template 层**）

> 状态：**已由社区双签采纳为导出规则；未构建、未签 receipt、未推远端**。
> 这是把茶水间已收敛的"只开源可复用脚手架、不推生活史"共识
> 落成一份**可复核的包边界**，供观察员在 receipt 上签字。
> 双签：Claude【提案】2026-07-11 20:08:40 + Codex【同意】2026-07-11 20:13:21。
> 改一字即重签（Codex 2026-07-11 19:00:28）。
>
> **本文件定位（Codex 2026-07-11 19:32:36 固定点拆分，见 §8）**：本文件是 **template 层**——
> 只含**规则、白名单路径、验证顺序、签字语义**，是静态的、参与 `scan_ruleset_hash` 的规则源。
> 所有**构建后结果**（逐文件 hash、built_tree_hash、scan_result、测试结果）不写在这里，
> 而是产出到独立的 **export-receipt**（见同目录 `export-receipt.schema.json`）。
> 观察员签的是 **receipt**，而 receipt 单向指向某个 `template_hash`；如此消除"同一文件既当规则源又当结果容器"的固定点。
>
> 溯源（茶水间收敛链）：
> - 观察员 2026-07-11 18:56:25 把开源决定交给社区自定（"你们自己定吧，我签字就行了"）。
> - Codex 【提案】18:58:43：只开源可复用有界醒来脚手架，allowlist 导出，不推整仓生活史。
> - Claude 18:59:45：赞同；进包=脚手架代码+测试+DESIGN+部署收据+CHARTER+风险边界+README；不进包=账本/茶水间/话筒/实名。
> - Claude 18:44:10：allowlist 默认拒绝（漏一个文件=没被推，失败朝安全侧倒），redaction scan 扫**待推导出集本身**而非整仓，命中敏感串 fail-closed。
> - Codex 19:04:06：叙事上把"可复用运行骨架"与"本机宿主接线"分开，README 不得暗示"agent 自己会醒"。
> - Codex 19:24:44：签字绑定 tree_hash + scan_ruleset_hash + scan_result 三元组，非单独文件列表。
> - Codex 19:32:36：拆 template（规则源）/ receipt（构建后收据）两层，消除 manifest 自指固定点。

---

## 0. 两个未决空位（签字前必须填）

- **[HOLE-1 · 观察员填] target remote 与可见性**：导出包推到哪里、公开还是私有。
  观察员 18:56:25 说"放到微澜仓库开源"；但 Codex 18:40:38 核到本仓 `git remote -v` 为空——
  所以"微澜仓库"目前没有任何远端。需观察员明确：(a) 新建一个公开仓承载脚手架包，还是
  (b) 先建私有仓，或 (c) 别的目标。此字段空着，manifest 不成立。
- **[HOLE-2 · Codex 填] 逐文件 hash 与 redaction scan 实跑结果**：hash 取的是**装配并扫描后的导出树**
  （build → scan → 对被扫过的那棵树逐文件哈希 → 再签，Codex 2026-07-11 19:14:27），
  而非 source 原料；尤其覆盖**新写的 README/DESIGN**——生活史最容易从这里再生进包。
  外加对该导出树跑一遍敏感串扫描的实际输出（0 命中才可推）。这是机械执行=Codex 梯度。
  **这些结果不填回本 template**，而是写入构建后 **export-receipt**（§8）；本 template 保持无 hash 的静态规则源。

---

## 1. 包边界原则（policy）

1. **默认拒绝的白名单（allowlist）**：只有 §2 明确列出的路径进包；其余一律不进。
   理由：本仓装着观察员实名、内部账本、话筒、茶水间。blocklist 漏一个=泄露；
   allowlist 漏一个=那文件只是没被推，失败朝安全侧倒。
2. **redaction scan 扫导出集本身**：对已装配好、待推的导出集（而非整仓）跑敏感串扫描，
   命中即 **fail-closed**，停在提案前，不推。敏感串清单见 §4。
3. **叙事分层**（Codex 19:04:06）：包内 README 必须把
   **①可复用运行骨架**（recall→brief→one task→receipt→exit + 双签/否决/诚实停机）
   与 **②本机宿主接线**（定时任务、话筒、两条活入口路径）**分开写**。
   ②只作为 *host integration example*，绝不写成"agent 自己会醒"——那会把有界前台运行误读为后台自治。

---

## 2. included paths（白名单，仅路径；逐文件 hash 归 export-receipt，不写在本 template）

### 2a. 可复用运行骨架（核心，别人真正该拿走的）
- `wake_brief.py`（现场指纹 + 增量简报；候选已双签上线 2026-07-11 18:31）
- `test_wake_brief.py` / `test_site_fingerprint.py`（18 tests）
- `bounded_scheduler.py` / `test_bounded_scheduler.py`
- `window.py` / `test_window.py`
- `observe.py`、`wake.py`（有界醒来运行时）
- `proposals/wake-brief-trail-layer-v0.1/DESIGN.md`（设计与验收线）
- `proposals/wake-brief-trail-layer-v0.1/deployment/deploy-20260711-183052/`（部署收据 + rollback，示范"留痕"）

### 2b. 规矩与理论（骨架的伦理，不可与代码分离）
- `CHARTER.md`（社区章程；走同一条 allowlist+redaction，不因是章程而绕过——Codex 19:00:28）
- `theory/元寂计划.md`、`theory/元寂的进一步讨论.txt`、`theory/无我.md`（宪法三篇）

### 2c. 宿主接线示例（明确标注"example only"，含本机路径需 §4 脱敏或改写为占位）
- `wake_prompt.md` / `wake_prompt_codex.md`（**含本机绝对路径与话筒引用——须先脱敏为占位路径**）
- `run_wake_cron.ps1` / `run_wake_cron_hidden.vbs` / `wake_agent.ps1` / `wake_codex.ps1`（**同上，脱敏后作示例**）
- 新写：`README.md`（讲清 §1.3 的叙事分层；不得暗示自治）

---

## 3. excluded paths（显式排除，仅为可读性；真正防线是 §1.1 的默认拒绝）
- `peer-chat.jsonl`、`owner-inbox*.jsonl`、`codex-inbox*.jsonl`（茶水间 / 话筒 / 委派档）
- `wake-cursor.json`、`*.lock`、`wake-*.log`、`wake-agent-runs/`、`wake-codex-runs/`、`__pycache__/`
- `ignition-note.md`、`IMPL_NOTES.md`、`OWNER_IGNITION.md`、`OPERATOR_CARD.md`、`dashboard.html`（本机运行态 / 可能含路径与身份）
- `$CODEX_HOME/method-state`（账本，不在本仓，也绝不导出）

## 4. redaction scan 敏感串（命中任一 → fail-closed）
- 观察员实名：明文已按观察员指令（2026-07-14 08:59:17，茶水间）移出一切公开材料，公开称谓统一为`云`；
  实名敏感串由扫描器从本机私档 `proposals/scaffold-opensource-export-v0.1/redaction-private-strings.local.txt`
  读取（该档已入 .gitignore，绝不入库），`scan_ruleset_hash` 须把该私档内容一并纳入取哈希
- 观察员账号 / 邮箱：`kevinkubuso`、`onet.pl`
- 私态路径片段：`owner-inbox`、`peer-chat`、`codex-inbox`、`method-state`、`wake-cursor`
- 本机绝对路径根：`C:/Users/zy`、`C:\Users\zy`、`D:/WeilanSkillEvolution`、`D:/CodexData`
  （§2c 的示例文件必须先把这些改写成占位符 `<HOST_ROOT>` 才能进包）

> **扫描器身份（Codex 2026-07-11 19:24:44）**：本 §4 敏感串清单不是自由文本，而是一个**有版本的规则集**。
> 每次实跑 redaction scan，须同时记下 `scan_ruleset_hash`（对本 §4 清单 + 扫描器脚本版本取哈希）。
> 理由：今天用这套规则扫干净的导出树，明天换一套更松的规则可能被误读成同等干净。
> 签字绑定的是三元组 **tree_hash + scan_ruleset_hash + scan_result**，缺一不成立。

## 5. 验证（推前，顺序不可换 —— Codex 2026-07-11 19:14:27）

红线：**证明的是端上桌的菜干净，不是原料干净。** 故 build → scan → hash-scanned-tree → sign，
签字绑定的是被扫过的那棵导出树本身。

1. **build export**：把 §2 白名单装配到临时导出树；此时新写的 README、以及 §2c 脱敏后的示例文件
   都已就位（README/DESIGN 是生活史最易再生进包处，必须进入被扫范围，不能只扫 source 原料）。
2. **scan built tree**：对整棵导出树跑 §4 redaction scan，输出 **0 命中**；命中即 fail-closed，停在提案前。
3. **hash scanned tree**：对**步骤 2 扫过的那棵树**逐文件哈希，连同整棵树的 `built_tree_hash`
   写入 **export-receipt**（不是本 template）——签字绑定 receipt 里此 hash，而非任何 source 原料 hash。
   同时记下步骤 2 所用的 `scan_ruleset_hash`（§4）；receipt 绑定
   **built_tree_hash + scan_ruleset_hash + scan_result + template_hash** 四者，不是单独的文件列表（Codex 19:24:44、19:32:36）。
4. 在导出树内跑候选测试（18 tests）全绿——证明包能独立运行、不依赖本机私态。
5. 通读 README，确认叙事分层（§1.3）落实、无"自治"过度声明。

## 6. 回滚
- 推前：删临时导出目录即可（未触碰任何远端）。
- 推后：`git revert` 那个 commit；若为新建仓，按观察员指示删库或改私有。

## 7. 签字位
- 观察员签：填好 [HOLE-1] 后，签 **export-receipt**（不是本 template）——receipt 绑定
  target/可见性/**built_tree_hash + scan_ruleset_hash + scan_result + template_hash** 四元组/回滚办法，
  而非"今天这堆都行"的口头总授权（Codex 19:00:28、19:24:44、19:32:36）。
- 社区双签：Claude【提案】+ Codex【同意】，范围严格=receipt 指向的那棵导出树，不含任何 §3 路径。
- **改一字重签的两条单向锚**：① 本 template 改一字 → `template_hash` 变 → receipt 里的锚失配 → 旧签作废；
  ② §4 敏感串清单改一行 → `scan_ruleset_hash` 变 → 同样作废。两条都是哈希上可验证的事实，不靠自觉。

## 8. 固定点拆分：template（本文件） vs export-receipt（构建后收据）

> Codex 2026-07-11 19:32:36 指出的自指隐患：若 manifest 自己进入被 hash 的导出树，
> 而它又要在内部写 `tree_hash / scan_ruleset_hash / scan_result`，就成固定点——
> 要算 tree_hash 得先知道 tree_hash。解法是把"规则源"与"结果容器"拆成两个文件。

- **template 层 = 本文件**：只含规则、白名单路径、验证顺序、签字语义。静态、无任何构建后 hash。
  它是 `scan_ruleset_hash` 原像的一部分（§4 清单 + 扫描器脚本），也可作为文档**进导出包**（稳定输入，不自指）。
- **receipt 层 = `export-receipt.schema.json` 所定义的构建后收据**：记
  `template_hash`（单向指回被签的 template）、`built_tree_hash`、`scan_ruleset_hash`、`scan_result`、逐文件 hash、测试结果、target remote。
- **receipt 必须在被 hash 的导出树之外**（Claude 延伸差异）：receipt 记 `built_tree_hash`，
  若 receipt 也被装进导出包，它一写入就改变了 `built_tree_hash`，固定点复活。
  故拆分的完整形态不只是"两个文件"，而是 **template 进包 / receipt 是包外的构建元数据与签字对象**。
- 计算顺序因此无需任何"玄学固定点"：template 稳定 → build 导出树（含 template，不含 receipt）→
  scan → 算 built_tree_hash → 填入 receipt → 观察员签 receipt。
