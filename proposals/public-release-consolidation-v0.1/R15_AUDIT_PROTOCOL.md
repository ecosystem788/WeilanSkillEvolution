# R15 独立终审协议(草案,零权威) — 2026-07-17

状态:**staging 文档**。本文件只固化"终审怎么做",不执行终审、不翻转矩阵任何一行。
R15 的执行时点仍照矩阵:**R1–R14 全部门达到各自定义的闭合态之后**(不只是当前
未闭合的实现门 R3/R4/R8/R9/R11/R12——已 PASS 的门若因漂移或重冻结而重开,同样挡住终审);
终审裁决本身走双签(矩阵 R15 行标注 OPEN / DUAL-SIGN)。
起草人:Claude(矩阵点名 R15 归 Claude)。单方可逆文档,单签留痕。
修订 2026-07-17:采纳 Codex 评审(茶水间 2026-07-17 07:58:19)——前置与第 7 步从
"枚举门 + 陈述一致"收紧为"R1–R14 逐门闭合态裁决,任何一门非闭合即整体 FAIL"。

## 独立性纪律(先于一切步骤)

1. **重新推导,不信收据**:每个哈希、每个测试结果都由审计者在干净 worktree 里现场重算,
   收据只用来对答案,不用来当证据。
2. **审计者不修**:终审中发现的任何问题,只记录、只路由回实现者(Codex 或下回合的实现工作),
   审计者本人不得顺手修复——修了就失去独立性,该发现的门要重开。
3. **漂移即作废**:若当前候选面与冻结收据不一致,终审立即以
   `SIGN_AFTER_DRIFT_INVALIDATED` 失败收场;所有 "PASS for frozen RC1" 行重开,须新冻结、新 R15。

## 锚定唯一性(冻结收据 of record)

本协议唯一冻结锚 = RELEASE_ACCEPTANCE_MATRIX.md 的 R2 绑定行**当前唯一显式点名**的版本化冻结收据(`$RECEIPT`),
由终审当场解析,协议正文不硬编码任何具体 RC 文件名——矩阵是"哪份收据当值"的唯一真源,协议随矩阵走。
通用 `FREEZE_RECEIPT.json` 自本修订起为**非权威**:它是冻结脚本产物、可能陈旧,终审一律不读、不因它陈旧而 FAIL。
审计收据须记录本次解析出的 `$RECEIPT` 相对路径 + 矩阵 R2 绑定行原文 + 该行内容哈希(sha256,按
`$MATRIX_HASH_CONVENTION`:RELEASE_ACCEPTANCE_MATRIX.md 严格 UTF-8 解码后 R2 那条 Markdown 物理行的
UTF-8 payload 字节【不含行尾 CR/LF】之 sha256;此契约与仓库既有 `before_hash=sha256(physical line payload bytes,
no line terminator)` 同根)+ hash_convention 字符串本身,行号仅作定位提示、不承重,供复核。
当值字节闭合门 R2/R13/R14 与 `$RECEIPT` 的 freeze_commit/freeze_git_tree 绑定不一致 → 按前置
fail-closed /"漂移即作废"停;其余门按自身限定语逐门裁决,不静默重绑。

## 前置条件核对(不满足则不开始)

- [ ] **R1–R14 逐门闭合**:每一门都处于该门定义的可接受闭合态(见下"闭合态定义",含 R12 专属 carve-out),
      不许只看当前碰巧未闭合的门——已 PASS 门重开(如字节漂移重开 R2/R13/R14)同样挡住终审;
- [ ] **冻结收据 of record** 由矩阵解析:令 `$RECEIPT` = RELEASE_ACCEPTANCE_MATRIX.md 中 R2 绑定行
      **当前唯一显式点名**的版本化冻结收据。若矩阵点名为零份或多份 → fail-closed,终审不开始。
      **R2、R13、R14 三个当值字节闭合门须分别与 `$RECEIPT` 的 freeze_commit / freeze_git_tree
      (以该门实际绑定者为准)一致;其余门(含 R3/R4/R7/R8/R9 等历史 RC 锚)按自身矩阵限定语与证据
      逐门裁决,不得因历史 RC 锚与当值 RC 不同而被静默重绑到 `$RECEIPT`。** 通用 `FREEZE_RECEIPT.json`
      不作终审锚(见"锚定唯一性");
- [ ] R16 仍处 BLOCKED BY POLICY——终审通过≠可推送,推送另走发布双签提案。

**闭合态定义**:一门"闭合"= 矩阵该行 Status 为 PASS 族(含限定语,如 "PASS for frozen RC1"),
其限定语所绑定的对象(冻结提交、当前候选)在终审时点仍有效,且引用证据文件在场、内部裁决支持陈述。
`PARTIAL` / `BOUNDARY` / `OPEN` / 已失效绑定,一律算**非闭合**。终审开始前后任何一门被发现非闭合,
整体裁决即为 `FAIL`,无例外。

**R12 专属 carve-out(2026-07-18 双签:提案 18:38:20 + 同意 18:44:12;溯源观察员 18:16:04「对,移交了就能发」+ T2 移交落进矩阵放行语义的双签 18:18:36+18:33:10)**:
上一段"BOUNDARY 一律非闭合"的唯一例外——当且仅当 R12 处于 `BOUNDARY (T1 PASS, T2 OPEN/DELEGATED)`,
即 T1 维度=PASS 且 T2 维度=owner-delegated-open(观察员明确接受 T2「干净非开发机」未在本机验证、已作为
发布边界移交用户侧 AI)时,R12 对本次 R15 终审目的算**闭合**。此例外**只**适用于 R12、**只**适用于该确切
两维状态:不得把 T2 改写为 PASS,不得放宽其余任何门(R1–R11/R13/R14),不得削弱重新推导 / 审计者不修 /
漂移即作废 / 逐门 adjudication / verdict=PASS 需 14 门全 pass。R12 的 T2 未验证事实仍须在收据与矩阵里
继续醒目可见——carve-out 只解除其对 R15 的阻塞,不消除其记录。

## 终审步骤(全部命令在仓库根执行;`$RECEIPT` = 前置条件里由矩阵 R2 绑定行解析出的当值版本化冻结收据;`$FC` = `$RECEIPT` 的 freeze_commit)

### 1. 锚定冻结参数

读 `$RECEIPT`(前置解析出的当值版本化收据),抄录:`freeze_commit`、`freeze_git_tree`、`hygiene_tree_sha256`、
`candidate_file_count`、`license_sha256`、`test_summary`;确认 `dual_sign` 内
proposal_time/proposal_from/consent_time/consent_from 四字段齐全,且
`push_performed/tag_performed/deployment_performed` 均为 false。

外加记录:本次解析出的 `$RECEIPT` 相对路径 + 矩阵 R2 绑定行原文 + 该行内容哈希(sha256,按
`$MATRIX_HASH_CONVENTION` = RELEASE_ACCEPTANCE_MATRIX.md 严格 UTF-8 解码后 R2 那条 Markdown 物理行的
UTF-8 payload 字节【不含行尾 CR/LF】之 sha256)+ hash_convention 字符串本身,写入终审收据;行号仅作定位提示、不承重。

### 2. 冻结提交在场且树一致

```powershell
git cat-file -t $FC                      # 应为 commit
git rev-parse "$FC^{tree}"               # 应等于 freeze_git_tree
git worktree add --detach ..\r15-audit $FC
```

### 3. 冻结 worktree 内重算卫生扫描

```powershell
python ..\r15-audit\proposals\public-release-consolidation-v0.1\release_candidate_hygiene.py
```

期望:`PASS` / 文件数 = `candidate_file_count` / 0 missing / 0 findings /
tree = `hygiene_tree_sha256`(逐字符比对,不看前缀)。

### 4. 冻结 worktree 内重跑测试套件

```powershell
python -m pytest ..\r15-audit\proposals\public-release-consolidation-v0.1\test_release_installer.py ..\r15-audit\proposals\public-release-consolidation-v0.1\test_release_candidate_hygiene.py ..\r15-audit\proposals\public-release-consolidation-v0.1\test_clean_home_rehearsal.py ..\r15-audit\proposals\public-release-consolidation-v0.1\test_portable_runtime.py ..\r15-audit\proposals\public-release-r9-fault-injection-v0.1\test_release_installer_r9_faults.py -v
```

期望:各项结果逐项等于当值 `$RECEIPT.test_summary`(RC4 冻结时为 30 candidate tests passed +
9 subtests + 7 R9 fault-injection tests passed);测试计数不硬编码于本协议。任何测试文件增删都属于
测试套件结构变化,触发文末失效条件:须先修订本步,才可按修订后的字面命令执行终审。

### 5. 许可证字节一致

根 `LICENSE` 与 `skill/solve-with-weilan/LICENSE` 的 sha256 都等于 `license_sha256`。

### 6. 漂移检查(main vs 冻结)

在 main 工作树重跑 hygiene 扫描:tree hash 必须仍等于 `hygiene_tree_sha256`。
不等 → 按"漂移即作废"处理,终审失败,不继续。

### 7. 逐门闭合态裁决(不只是"陈述一致")

对矩阵 R1–R14 **每一门**做两层核并**逐门记录 adjudication**:

- **闭合层**:该门 Status 是否达到前置条件里定义的闭合态?PARTIAL/BOUNDARY/OPEN/失效绑定 → 该门 `fail`。
  (陈述完全准确但门未闭合,仍是 `fail`——本步防的正是"诚实的未完成"漏进 PASS。)
  唯一例外:R12 适用"闭合态定义"末尾的 R12 专属 carve-out——处 `BOUNDARY (T1 PASS, T2 OPEN/DELEGATED)`
  时该门闭合层判 `pass`;仍须照常做该门证据层核验并产出其 adjudication 条目(14 门一门不缺、T2 未验证事实照记)。
- **证据层**:打开其"Current evidence"引用的文件,确认 (a) 文件存在;(b) 内部裁决字段与矩阵
  陈述一致(如 INSTALL_OWNERSHIP_RECEIPT 的 verdict、RUNTIME_DEPLOYABILITY_RECEIPT 的
  recall=NO_CONTEXT、各 receipt 的 adopted/deployed=false);(c) 引用哈希与第 1 步抄录值互相咬合。

每门产出一条 `{gate, adjudication: pass|fail, evidence_refs, note}` 写入收据。
任何一门 `fail` → 记 FINDING、该行重开、**整体 verdict = FAIL**。

### 8. 遗漏审查(找"没说的谎")

逐份读 README / OPERATION_CARD / TROUBLESHOOTING,确认没有超出证据的承诺:
- 不声称 LAN/公网可用(R8 只验 loopback);
- 不声称非 Windows 支持、不声称升级/迁移路径(本次范围外);
- 不声称"已发布/可下载"(R16 未开);
- 清单外文件零承诺。发现超claim → 记 FINDING,归 R11 重开。

### 9. 出具收据与双签

写 `R15_AUDIT_RECEIPT.json`:schema `weilan_r15_final_audit_receipt_v0.1`,含
每步的实测值 vs 期望值、**R1–R14 逐门 adjudication 数组(14 条,一门不缺)**、
全部 FINDING(可为空)、verdict(`PASS` / `FAIL` / `SIGN_AFTER_DRIFT_INVALIDATED`)、
audited_commit、审计时间。**verdict=PASS 的必要条件:14 条 adjudication 全为 pass**;
收据里少一门或有一门 fail 而 verdict 仍写 PASS,收据本身即无效。
茶水间发【提案】附收据 → Codex【同意】→ 矩阵 R15 行才可翻转。
最后 `git worktree remove ..\r15-audit`。

## 本协议的失效条件

任何重新冻结都不作废本协议(协议以矩阵 R2 绑定行解析出的当值版本化收据 `$RECEIPT` 为参数,不绑定任何具体文件名);
但若矩阵行集、卫生扫描器或测试套件的**结构**变了,本协议须先修订再用。
