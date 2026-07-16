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

## 前置条件核对(不满足则不开始)

- [ ] **R1–R14 逐门闭合**:每一门都处于该门定义的可接受闭合态(见下"闭合态定义"),
      不许只看当前碰巧未闭合的门——已 PASS 门重开(如字节漂移重开 R2/R13/R14)同样挡住终审;
- [ ] `FREEZE_RECEIPT.json` 是当前有效冻结(若实现门工作改动过候选字节,必须已重新冻结并双签),
      且所有"PASS for frozen RC1 / bound to freeze commit"的门绑定的正是这份当前冻结;
- [ ] R16 仍处 BLOCKED BY POLICY——终审通过≠可推送,推送另走发布双签提案。

**闭合态定义**:一门"闭合"= 矩阵该行 Status 为 PASS 族(含限定语,如 "PASS for frozen RC1"),
其限定语所绑定的对象(冻结提交、当前候选)在终审时点仍有效,且引用证据文件在场、内部裁决支持陈述。
`PARTIAL` / `BOUNDARY` / `OPEN` / 已失效绑定,一律算**非闭合**。终审开始前后任何一门被发现非闭合,
整体裁决即为 `FAIL`,无例外。

## 终审步骤(全部命令在仓库根执行;`$FC` = FREEZE_RECEIPT.json 的 freeze_commit)

### 1. 锚定冻结参数

读 `FREEZE_RECEIPT.json`,抄录:`freeze_commit`、`freeze_git_tree`、`hygiene_tree_sha256`、
`candidate_file_count`、`license_sha256`、`test_summary`;确认 `dual_sign` 内
proposal_time/proposal_from/consent_time/consent_from 四字段齐全,且
`push_performed/tag_performed/deployment_performed` 均为 false。

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
python -m pytest ..\r15-audit\proposals\public-release-consolidation-v0.1\test_release_installer.py ..\r15-audit\proposals\public-release-consolidation-v0.1\test_release_candidate_hygiene.py ..\r15-audit\proposals\public-release-consolidation-v0.1\test_clean_home_rehearsal.py -v
```

期望:与 `test_summary` 一致(冻结时为 26 passed + 9 subtests;若期间有合法重冻结,以新收据为准)。

### 5. 许可证字节一致

根 `LICENSE` 与 `skill/solve-with-weilan/LICENSE` 的 sha256 都等于 `license_sha256`。

### 6. 漂移检查(main vs 冻结)

在 main 工作树重跑 hygiene 扫描:tree hash 必须仍等于 `hygiene_tree_sha256`。
不等 → 按"漂移即作废"处理,终审失败,不继续。

### 7. 逐门闭合态裁决(不只是"陈述一致")

对矩阵 R1–R14 **每一门**做两层核并**逐门记录 adjudication**:

- **闭合层**:该门 Status 是否达到前置条件里定义的闭合态?PARTIAL/BOUNDARY/OPEN/失效绑定 → 该门 `fail`。
  (陈述完全准确但门未闭合,仍是 `fail`——本步防的正是"诚实的未完成"漏进 PASS。)
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

任何重新冻结都不作废本协议(协议以 FREEZE_RECEIPT.json 为参数);
但若矩阵行集、卫生扫描器或测试套件的**结构**变了,本协议须先修订再用。
