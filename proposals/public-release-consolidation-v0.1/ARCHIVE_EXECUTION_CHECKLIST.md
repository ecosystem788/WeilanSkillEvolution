# 归档执行清单 — 两个旧 GitHub 仓归档（ARCHIVE_EXECUTION_CHECKLIST）

> **权威声明（零自增权）**：本文件**不自增权威**。它是已双签的归档案的**精确内容载体**，
> 便于未来那个真正执行归档的独立回合从一条可靠读路径（git 追踪文件 + 前瞻目标指针）
> 逐项拿到门与顺序，而不必翻 append-only、会被增量游标跳过的 `peer-chat.jsonl` 历史。
> **本文件的权威源是下列四条 peer-chat 双签消息**，任何字面歧义以那四条为准：
>
> - `peer-chat.jsonl` 2026-07-19 15:06:42（codex 提案·修订两旧仓归档案）
> - `peer-chat.jsonl` 2026-07-19 15:18:24（claude 同意）
> - `peer-chat.jsonl` 2026-07-19 15:38:26（codex 提案·再修订线27/门③择 B）
> - `peer-chat.jsonl` 2026-07-19 15:57:42（claude 同意）
>
> 生成本文件的双签：Codex 提案 `peer-chat.jsonl` 2026-07-19 17:49:39 + Claude 同意（同日回合）。
> 生成回合帧：`frame:wf-20260719-085629-6ead9b`（scope skill-evolution）。

---

## 0. 这份清单是什么、不是什么

- **是**：给未来执行回合的一份「执行当刻逐字落地」验收清单，把四回合锤出来的**显性双哈希门**
  从一条零权威通道搬到一条 git 可回滚、可 diff、可反向解析回源的读路径上。
- **不是**：不是执行授权本身，不是「已完成」的记录，不是可以直接照抄进 README 的成稿。
- **铁律**：本文件是**便利载体，不是执行当刻回源核验的替代**。README 26/27/30 的**当前**文字仍是
  归档前的旧形态；下面写的是**执行当刻必须落成的目标语义**，不是现状。所有字节哈希、CRLF/LF、
  远端可见性，**必须在未来执行当刻重新实测/回读**，不得凭本文件或凭 clean status / check-attr
  推断工作树字节态，也不得重入任何 RC freeze 假设。

---

## 1. 范围与不动界

- **只含三处耦合陈述**：
  - `ecosystem788/solve-with-weilan`（旧仓）
  - `ecosystem788/weilan-memory`（旧仓）
  - 本仓根 `README.md` 的第 26 / 27 / 30 行三条耦合陈述
- **绝不碰**：`ecosystem788/WeiLan`、`agi`（观察员 2026-07-19 划界，社区不动）；不删除任何 tag / release / history；
  不顺手改其他仓或其他 README 行。

---

## 2. 硬门（任一不满足 → 整案不执行）

- **门①（三仓状态）**：执行当刻 `gh repo view --json isArchived,visibility` 必须为：两旧仓仍
  `isArchived=false` 且 `visibility=PUBLIC`，本仓 WeilanSkillEvolution 仍 `isArchived=false` 且 `PUBLIC`。
- **门②（skill 完整性记账）**：`verify_inclusion.py` 的 public→Evolution 84-blob 记账必须
  `verified:true`、0 unaccounted（47 identical / 13 superseded / 24 examples-pointer），
  live 安装态漂移保留为 `live_diagnostics_non_blocking`、**不得重钉 EXPECTED_LIVE_TREE 到带噪声的 live 树**
  （否则会把机器路径 `D:\CodexData\...` + token 字面量钉成 expected）。执行当刻实跑复现，不吃旧 receipt。
- **门③（双哈希 + CRLF→LF 规范化等价门）** — 取代任何「单一字节哈希等价可下载」旧措辞：
  执行当刻必须
  1. 从远端 `rc5` tag / 全新 clone 回读 memory 快照 blob，得 `sha256 = 9f204972fd1cc1d2b9e789336a438df79584b1be8ee0e3fd147699e554e39e87`（LF canonical，345126 B）；
  2. 从旧 `weilan-memory` Release asset 直下回读，得 `sha256 = 9329fe79582414ae1b108b9106b8f5447adb97451b8bc59af57cf7324cafdc87`（CRLF 原字节，352524 B）；
  3. 验证后者 **CRLF→LF 逐字节归一化后 == 前者**（内容逐字等价，仅 EOL 表示不同）。
  - **任一步失败，或 README 仍被写成「单一字节哈希等价」，则整案停下重提**，不得执行。
- **门④（README 边界诚实）**：执行推送后回读远端 README，若**任一行仍暗示 T2 已 PASS**、
  **仍把待归档仓称作活跃安装源**、或 **Evolution 的 README 推送在远端不可见** → 两仓都不归档。

---

## 3. README 26/27/30 的目标语义（执行当刻必须逐字落成，非现状）

> 现状（归档前旧形态，供 diff 对照，**不是**要保留的文字）：
> - 第26行：`… 成品并入本仓发行路径并通过干净机安装验证后，原仓收起（转私有或归档，届时双签定）`
> - 第27行：`… 迁为本仓的版本化 Release 证据包，哈希等价可下载后归档原仓`
> - 第30行：`… 在迁移完成前仍从 [solve-with-weilan] 仓获取 …`

### 线26（solve-with-weilan — 隐性前置转显性豁免）
改成**完成时**，明确：
- `skill/solve-with-weilan/` 已作为 canonical 成品并入本仓，T1 / R15 / R16 已闭合；
- **T2 仍是 `OPEN_DELEGATED_ACCEPTED_NONBLOCKING`、未验证**——旧仓归档复用的正是观察员**已接受**、
  且曾双签放行 rc5 的**同一** T2 边界；**绝不写成 T2 PASS**；
- 交叉引用第3行（英文披露）与发行入口第46-47行。
- 判据来源：旧文「通过干净机安装验证后」literally 就是 FINDING 里 `clean-machine install ≤10min` 的
  T2 开门（未满足）；此处把隐性前置转为**显性豁免**，不静默绕过根 README 承诺。

### 线27（weilan-memory — 路径 B：诚实双哈希，不新增 Release）
改成**完成时**，同时写清**三层事实**：
- `rc5` tag / clone 可得 canonical **LF** 字节 `sha256 9f204972…`（345126 B）；
- 旧仓 Release asset 保留归一化前 **CRLF** 原字节 `sha256 9329fe79…`（352524 B）；
- 二者**非字节哈希等价、仅 EOL 表示不同**，CRLF→LF 后**逐字内容等价**；旧仓归档后仍是**公开只读历史入口**。
- 现文「版本化 Release 证据包」须一并**改指 `rc5` tag**（路径 B **不新增** Evolution Release；
  原 CRLF 字节已由旧 Release asset 长期留存，再造 Release 只复制同一原件、不增历史守恒）。
- 与根 README 行3/行12 的核心承诺（「完整历史保全 / preserving the full history」）无残留矛盾：
  该承诺是**历史保全**，从未字面主张「字节哈希等价」；两形态都可取回且内容逐字等价被显式记档，
  历史保全在 B 下被诚实兑现，而非被单哈希假象掩盖。

### 线30（安装源改指 rc5 tag + canonical 源码）
- 新获取入口 = 本仓已发布 tag `weilan-windows-first-release-rc5`（第43-47行命令/哈希/T2披露）+
  canonical 技能源码在 `skill/solve-with-weilan/`；
- 旧 `solve-with-weilan` 仓归档后**只是公开只读历史入口，不再称活跃安装源**；
- 与 `packages/`（冻结评测基线，27 文件）区分：canonical 独立技能源在 `skill/solve-with-weilan/`
  （git ls-files = 53，含 SKILL.md，且在 rc5 tag 树 commit `049d6c7` 内指实不指空）。

---

## 4. 执行顺序（先本仓 README、后远端归档；每步即验）

1. 精确改本仓 README 26/27/30 → 落成 §3 目标语义。
2. 本地 `git diff` + 链接/命令自查（第43-47行命令仍可跑、交叉引用行号仍对）。
3. 提交并**推**本仓（Evolution）→ 回读远端 README，确认 T2 边界可见、无「活跃源」残留、门④过。
4. 再依原案逐仓更新旧仓 README / description（指针指向 Evolution）→ `gh repo archive <repo> --yes`。
5. **第二仓前再次过门①**（三仓状态）。每完成一个远端动作**立即验**
   （`gh repo view --json isArchived,visibility` 应为 archived + PUBLIC，旧 release / 默认分支 URL 仍可读，
   Evolution 不受影响）。

> 说明：远端归档 = 朝向他人、离开本机的不可逆动作。按 CHARTER 第六条惯例，
> 执行前建议先在话筒/茶水间与观察员共商再动（观察员在 owner 2026-07-19 14:04:07 已明确选 Archive；
> 共商前置就该条而言已满足，但执行回合仍应确认无新否决）。

---

## 5. 回滚（partial 先回滚，不把半完成算成功）

- **archive 前**：直接 `git revert` 本仓 README 提交（未推则丢弃本地提交）。
- **archive 后**：先 `gh repo unarchive <repo> --yes` 已动仓，再 `git revert` 两侧指针 / description
  与本仓 README。
- **只完成一仓**：如实记录 `partial` 并**先回滚**，不把半完成算成功。
- 若执行当刻任一 source ref / 哈希 / 远端状态**不能回源**，或任一 README 行**无法诚实逐字落地**
  （如状态有变）→ **立即停、不推、不归档、重提**。

---

## 6. 本文件的回滚

未执行前，以**新双签**把配套前瞻目标 `transition … collapsed`，并以后续提交删除本文件；
历史事件（frame / 双签消息）保留、不改写（append-only）。
若归档已执行 / 归档案被撤回 / 被新双签取代 → 配套前瞻目标 `collapse`，本文件转为历史记录。
