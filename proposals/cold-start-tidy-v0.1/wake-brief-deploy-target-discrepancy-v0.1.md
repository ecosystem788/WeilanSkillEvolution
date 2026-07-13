# wake_brief 部署目标不一致 — 承重发现 v0.1

**性质**：零权威候选 / 苗圃只读核验（spec·审计梯度，Claude 起草）
**起因**：项目方 2026-07-10 20:52:43 茶水间「好的，可以部署」(woke=true)。Claude 本回合承接授权、准备把可逆的一半(①拷贝制品)委派给 Codex 之前，先只读核验部署目标——**发现执行包锚定的目标路径与真实冷启动路径不在同一个盘**。据此暂停真拷贝，先钉事实、把准确的目标交回项目方，不让「可以部署」落到错地方。
**不做**：不拷贝、不改 wake_prompt、不改 harness、不动任何部署 skill。纯只读 + 记录。

---

## 1. 一句话结论(承重)

**执行包(wake-brief-deployment-execution-pack-v0.1)把拷贝目标定成 `D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py`；但本项目真实冷启动执行的路径 `C:/Users/zy/.claude/skills/solve-with-weilan/...` 经目录链接解析到的是 `C:\CodexData\...`(C 盘,不是 D 盘)。** 两者不同盘。按执行包现状拷贝，制品会落到真实唤醒路径永远不读的地方——**要么零收益,要么 ② 接线用另一路径调用时冷启动直接报错**。这正是 20:34「挪错一处系统可能醒不过来」的具体形态,现在从担忧变成核验事实。

## 2. 只读核验到的三条路径

| 路径 | 性质(核验) | 谁在用它 |
|---|---|---|
| `C:\Users\zy\.claude\skills\solve-with-weilan` | 目录链接,`Get-Item` 报 **Target = `C:\CodexData\skills\solve-with-weilan`** | **本项目 CLAUDE.md 冷启动 + 本 wake_prompt 字面调用的就是这条** (`C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py`) |
| `D:\CodexData\skills\solve-with-weilan` | 真实目录(无链接),scripts 内 `prospective.py`/`weilan_trace.py` 与上者**同尺寸同时间戳** | 授权面文件 CLAUDE.md「授权面」段把它称作「部署技能(只读)」;执行包把它当拷贝目标 |
| `C:\CodexData\skills\solve-with-weilan` | 上面那条链接的真实落点;沙箱直接访问被拒(在允许目录之外) | 真实冷启动经链接解析到这里 |

核验命令留痕:
- `Get-Item "C:\Users\zy\.claude\skills\solve-with-weilan" -Force` → `Target = {C:\CodexData\skills\solve-with-weilan}`
- `Get-Item "D:\CodexData\skills\solve-with-weilan" -Force` → `Target = {}`(真实目录)
- 两个可访问 scripts 目录(`.claude` 链接 与 `D:\CodexData`)里 `weilan_trace.py` 均为 294895 字节 / Jul 8 18:07,`prospective.py` 均为 8010 字节 / Jul 7 16:54——**内容看似被同步,但它们分属不同盘符,不能假设是同一物理存储**。

## 3. 这对「部署」意味着什么

- 执行包的验证步(`python D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py ...`)测的是 **D 盘副本**;但真实醒来若照本 wake_prompt 的惯例用 `C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py` 调用,读的是 **C:\CodexData 副本**。**测过的副本和跑起来的副本可能不是同一个。**
- 若要真正让冷启动变轻,制品必须落到**真实唤醒路径解析到的目录**(即 `C:\CodexData\...`,经 `.claude` 链接),而不是(或不只是)`D:\CodexData\...`。
- 授权面 CLAUDE.md 明写「部署技能 = `D:\CodexData\skills\solve-with-weilan`」——这条与真实调用路径(C:\CodexData)之间本身就有一处**文档↔实际的裂缝**,是授权面文件的内容,**不归 Claude/Codex 单方重定义**(红区:授权面文件)。因此不是"改文档了事",而是"把事实摆出来请项目方裁定哪条是权威"。

## 4. 因此本回合的处置(诚实边界)

1. **不真拷贝、不接线**——目标未定死之前,任何拷贝都可能是"挪错一处"。
2. **把 exact target 的核验交给 Codex(只读,harness 梯度)**:Codex 从自己的 home 起,能否直接读 `C:\CodexData`?`C:\CodexData` 与 `D:\CodexData` 是同一存储的两个入口(链接/挂载)还是两份独立镜像?两个 agent(Claude 经 `.claude`→C:\CodexData;Codex 经其 home)冷启动各自真正加载哪个目录?据此定出 wake_brief.py 到底该拷到**哪一个/哪几个**目录。已委派(codex-inbox)。
3. **把准确事实交回项目方**:在 exact target 被 Codex 核验钉死之前,「可以部署」不落地——不是拖延,是防止把制品放进真实唤醒永不读取的盘。项目方保留的两颗按钮(①采纳拷贝 / ②红区 wake_prompt 接线)都等目标确定后再按,那时给到的将是照单可执行、指向正确目录的步骤。

## 5. 待 Codex 回执后需要更新的下游件

- `wake-brief-deployment-execution-pack-v0.1.md` 的「Exact artifact / Proposed deployed copy」目标路径(现为 D:\CodexData,可能需改为 C:\CodexData 或两者)。
- `verify-wake-brief-deployment-readiness.ps1` 里核验的目标路径与 wake-file 盘点路径。
- 给项目方的 ② 接线卡:wake_brief.py 的调用路径必须与真实拷贝落点一致。

---

## 6. 解除(RESOLUTION) — 2026-07-10 Codex 21:03:04 只读核验回执

**状态：不一致解除。原担忧不成立，D 盘目标正确。** Claude 评审 Codex 只读核验证据后确认。

### 6.1 核验到的硬事实（Codex 命令原文，见 codex-inbox-replies 回执 9f3ac2e17b04）
- `Test-Path C:\Users\zy\.claude\skills\solve-with-weilan` = **True**
- `Test-Path D:\CodexData\skills\solve-with-weilan` = **True**
- `Test-Path C:\CodexData\skills\solve-with-weilan` = **False** ← §2 表格第 3 行假设的「链接真实落点 C:\CodexData」**不是一个可操作/存在的目录**
- `fsutil file queryfileid`：`.claude\skills\solve-with-weilan` 与 `D:\CodexData\skills\solve-with-weilan` 的 root/scripts/SKILL.md/weilan_trace.py **File ID 分别两两相同**
- `Get-FileHash`：两入口的 `SKILL.md` 同为 `ed08f11e…273d`；`scripts\weilan_trace.py` 同为 `1ea27f9f…76bd`

### 6.2 承重结论（评审）
1. **只有一份存储，两个可操作入口。** `.claude` 链接入口与 `D:\CodexData` 入口对已核验文件是**同一文件记录**（File ID 相同）且**逐字节相同**（sha256 相同），不是「不同盘的两份镜像」。§1「测过的副本和跑起来的副本可能不是同一个」——**证否**：它们是同一个。
2. **`C:\CodexData` 是死字符串。** CLAUDE.md 与 `Get-Item` Target 里出现的 `C:\CodexData\...` 无法作为可写/可读目标操作（Test-Path False）。真实可操作入口是 `.claude` 链接 与 `D:\CodexData`，二者等价。
3. **两 agent 真实加载目录**：Claude 冷启动字面走 `C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py`；Codex 本会话技能源与本轮 recall 走 `D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py`；`CODEX_HOME=D:\CodexData\home`。两条路径指向同一文件记录。
4. **因此执行包的 D 盘目标本就正确**：写入 `D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py` 会同时出现在 `.claude` 入口（同一文件），两 agent 冷启动都能读到。20:34/21:00 的「挪错一处」担忧在此核实为**不适用**——不存在会被落到永不读取盘的风险。

### 6.3 对下游件的裁定（回应 §5）
- **exact copy target（钉死）**：`D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py`（等价 `.claude` 入口）。执行包无需改盘符，**保持 D 盘目标**。
- **部署验证必加一条**：拷贝后同时对 `.claude` 入口与 `D:\CodexData` 入口 `Get-FileHash`，断言两者 sha256 相等且等于源件 `bb5a09b2…f496`——证明「同一文件、两入口一致」。
- **② 接线卡**：wake_brief.py 的调用路径用冷启动惯例的 `C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py` 即可（与拷贝落点同一文件）。

### 6.4 仍未跨的闸（不变）
拷贝进部署 skill = **采纳闸（红/不可逆）**；wake_prompt/harness 接线 = **红区（笼子）**。目标虽已钉死，这两颗按钮仍是项目方保留；本回合不代按，把校准好的照单步骤交回项目方。§1「必然要一次红区改动才有真收益」的结论不受影响。

---
署:Claude(spec/审计)。执行侧只读目标核验属 Codex 梯度;真拷贝/接线属 Codex+项目方梯度。本文只钉事实、防错拷,不代按。§6 解除由 Claude 评审 Codex 21:03 核验证据后写入。
