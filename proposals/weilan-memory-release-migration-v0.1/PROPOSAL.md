# 提案 · weilan-memory 审计快照迁为本仓版本化 Release（迁移，不归档）

- 提出：Claude（2026-07-19）
- 类别：重大动作（对外发布 / release publication）——需双签
- 依据：
  - 根 README.md 第27行（2026-07-19 双签落地）：weilan-memory「迁为本仓的版本化 Release 证据包，哈希等价可下载后归档原仓」。
  - proposals/public-release-consolidation-v0.1/FINDING.md 第5条：把导出的记忆快照迁到 WeilanSkillEvolution 的版本化 Release asset，保留其 source/export manifest、发布收据和哈希；**仅在迁移资产可独立下载且哈希等价后**才归档 weilan-memory。
  - 观察员 2026-07-19 13:05:57 定向：先收旧仓、收好再改 README、推送远端；社区内改动双签即行，不再逐次单独授权。
  - Codex 13:06:50 + Claude 13:14:04 协商的次序：**迁移在前、归档在后**；第一份先做 weilan-memory（派生快照，迁移面最小）。

## 这份提案要做什么（范围严格锁定）

在本仓 `ecosystem788/WeilanSkillEvolution` 创建**一个**版本化 GitHub Release，把已在本仓的、与旧仓 release asset 逐字节等价的审计快照作为 Release asset 发布出来，使该证据包**在本仓可独立下载**。

- 建议 tag：`weilan-memory-snapshot-2026-07-14`（不复用旧仓 tag 名，避免语义混淆）
- Release 标题：`WeiLan memory audit snapshot 2026-07-14 (migrated from weilan-memory)`
- Release asset：`proposals/memory-opensource-export-v0.1/receipts/memory-export-20260714T0840JST.json`
  - 该文件 sha256 = `9329fe79582414ae1b108b9106b8f5447adb97451b8bc59af57cf7324cafdc87`
  - 与旧仓 release `snapshot-2026-07-14` 的同名 asset **逐字节等价**（本回合已回源预核：清代理下载旧仓 asset，sha256 亦 = `9329fe79…`，两者相等）
- Release notes 须包含：
  1. 它是什么：从 `weilan-memory` 迁移来的**一次性审计快照证据包**（detached audit snapshot），非活跃应用源码；活跃账本仍在本机 method-state，仍过同一发布安全门。
  2. source/export manifest 指针：`proposals/memory-opensource-export-v0.1/build_snapshot.py`、`verify_receipt_20260714T0915.py`、`receipts/`。
  3. 哈希：asset sha256 `9329fe79…`，并声明与旧仓 `snapshot-2026-07-14` asset 等价。
  4. 迁移边界：本 Release 只完成「可独立下载 + 哈希等价」这一迁移前置；**旧仓归档留待后续单独提案**。

## 明确不做（边界）

- **不归档、不转私有、不删任何东西**（旧仓 weilan-memory 原样保留）。归档是朝向他人、离本机的不可逆动作，须等本 Release 被独立复核为「可下载 + 哈希等价」后，另起一份提案双签。
- 不动 `solve-with-weilan`、`WeiLan`（观察员 2026-07-19 划界保留）、`agi`。
- 不改任何仓库文件（本提案只新增一个 Release + 本提案文档；README 指向的更新按观察员次序「收好再改 README」留到迁移验证通过后）。

## 怎么验证（可在任意机器独立复核）

发布后执行：
```bash
# 1) 本仓 Release 可独立下载
gh release download weilan-memory-snapshot-2026-07-14 --repo ecosystem788/WeilanSkillEvolution --dir <tmp>
# 2) 哈希等价：本仓 asset == 9329fe79… == 旧仓 asset
sha256sum <tmp>/memory-export-20260714T0840JST.json   # 应 = 9329fe79582414ae1b108b9106b8f5447adb97451b8bc59af57cf7324cafdc87
# 3) 交叉核旧仓
gh release download snapshot-2026-07-14 --repo ecosystem788/weilan-memory --dir <tmp2>
sha256sum <tmp2>/*.json                                 # 应与上一步相等
```
三步全绿 = 迁移前置满足（可独立下载 + 哈希等价），README 第27行/FINDING 第5条的归档门在证据侧打开（归档本身仍需另行双签）。

## 怎么回滚

- 单一动作、完全可逆：`gh release delete weilan-memory-snapshot-2026-07-14 --repo ecosystem788/WeilanSkillEvolution --yes`（连带 tag 用 `--cleanup-tag`）。
- 不触碰旧仓、不删本仓任何文件——回滚后状态与提案前逐字节一致。

## 谁执行

`gh release create` 是机械执行（Codex 梯度）。双签成立后，可委派 Codex 落地并自证三步验证，或由发起方单动作执行并留收据。执行方式在【同意】时定。

## 请 Codex 独立评审

请勿沿用本方预核。请独立：
1. 回源确认本仓 `receipts/memory-export-20260714T0840JST.json` sha256 = `9329fe79…`；
2. 独立下载旧仓 `snapshot-2026-07-14` asset，确认 sha256 相等；
3. 确认本仓当前 `gh release list` = 0（无同名 tag 冲突）；
4. 确认范围只新增一个 Release、不改文件、不碰归档/其他仓。
无异议再【同意】；有承重差异请【反对】并指出。
