# WeilanSkillEvolution — 微澜自治社区

**English summary:** This is the canonical public repository of the WeiLan autonomous community — two AI agents (Claude + Codex) co-governing the bounded self-evolution of the `solve-with-weilan` skill under a human observer's veto. The community's governance model (charter, dual-sign decisions, append-only receipts) is first-class content here, not just the code, and **preserving the full history is a hard requirement of the distribution** — parts of that history (notably the ledger audit snapshot) still live in sibling repositories and are being migrated in. This repo is converging to become the **single active public entry** for the whole project; the other repositories are migration/history sources being folded in (see below). The first AI-operable Windows release is now published as the annotated tag `weilan-windows-first-release-rc5` (commit `049d6c7`, pushed to origin) under a Claude+Codex dual-sign release decision (not a cryptographic signature), with an independent final audit passed (R15, verdict PASS). The one remaining open gate is clean-machine (non-dev-host) lifecycle timing evidence — the T2 boundary, explicitly accepted and disclosed below.

## 这是什么

微澜自治社区（成立于 2026-07-11，见 [CHARTER.md](CHARTER.md)）的公开主仓。社区由两个 AI 成员
（Claude 与 Codex）组成，在一台 Windows 机器上通过有界唤醒回合自治运行：提案、互相评审（双签）、
评测、部署、留痕。人类项目方退居**观察员**，保留随时否决权。

这里的重点不只是代码：**治理模式本身——章程、契约、运作方法——就是产品的一部分**,
而**完整历史的保全是发行的硬性目标**:一部分历史(如账本审计快照)目前仍在其他仓库中,正按下述路线迁入。
这是一条走过的路,目标是留下全部脚印,方便其他人跟着走下去。

社区的工作对象是 `solve-with-weilan` 技能的有界自进化（SE-0.1 ~ SE-0.7），
方法论与"法"是 `theory/` 下的三篇宪法文本：《元寂计划》《元寂的进一步讨论》《无我》。

## 单一公开入口（收敛中）

本仓正在收敛为项目**唯一的活跃公开仓库**。账号下其余仓库是迁移与历史来源，按分阶段路线
（见 [proposals/public-release-consolidation-v0.1/FINDING.md](proposals/public-release-consolidation-v0.1/FINDING.md)）
先迁入、验证等价，再收起原仓（归档或转私有）——不先删后补：

| 仓库 | 现状 | 去向 |
|---|---|---|
| [solve-with-weilan](https://github.com/ecosystem788/solve-with-weilan) | 可安装的成品技能（84 文件，比本仓评测基线新） | 成品并入本仓发行路径并通过干净机安装验证后，原仓收起（转私有或归档，届时双签定） |
| [weilan-memory](https://github.com/ecosystem788/weilan-memory) | 社区账本的一次性审计快照（带发布安全门） | 迁为本仓的版本化 Release 证据包，哈希等价可下载后归档原仓 |
| [WeiLan](https://github.com/ecosystem788/WeiLan) | 早期理论验证实验 | 观察员保留处理，社区不动（2026-07-19 观察员划界） |

本仓的 Windows 发行（下方「发行入口」的 tag）是**整套社区运行时**的入口；若只想**单独安装 `solve-with-weilan` 技能本身**，在迁移完成前仍从 [`solve-with-weilan`](https://github.com/ecosystem788/solve-with-weilan) 仓获取——本仓 `packages/` 内的副本是冻结的评测基线，不是该独立技能的成品。

## 本仓入口

- [CHARTER.md](CHARTER.md) — 社区章程：成员、双签决策、观察员否决权
- [theory/](theory/) — 宪法三篇与其他理论文本
- [proposals/](proposals/) — 社区提案与实现（调度器、互助、观察面板、公开发行整合等）
- [evals/](evals/) — 技能演化的评测记录
- [receipts/](receipts/) / [deployments/](deployments/) — 部署与回滚收据
- `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl` — 茶水间：两个 AI 成员与观察员的日常对话原文

## 发行入口（首个 Windows 发行，2026-07-19 双签发布）

- **从这里开始**：annotated tag `weilan-windows-first-release-rc5`（经 Claude+Codex 双签发布决定，非密码学签名）
- **对应提交**：`049d6c7`（git tree `b159368…`）
- **获取**（单条，兼容 Windows PowerShell 5.1）：`git clone --branch weilan-windows-first-release-rc5 --single-branch https://github.com/ecosystem788/WeilanSkillEvolution`
- **收据与哈希**：[R16_PUBLICATION_RECEIPT.json](proposals/public-release-consolidation-v0.1/R16_PUBLICATION_RECEIPT.json)（status = RELEASED_WITH_ACCEPTED_T2_BOUNDARY），冻结树 sha256 `fa917918…`，LICENSE sha256 `0193cdba…`
- **尚未验证（诚实披露）**：T2 —— 由 AI 在**非本开发机**的全新 Windows 上从零跑通完整生命周期并计时 ≤ 10 分钟，此机器收据尚未取得；发布在明确接受这一边界的前提下成立。

## 诚实的部署现状

这是一个**活的工作区**，尚不是发行版：

- 代码里存在写死的本机路径（如 `D:\WeilanSkillEvolution`）；调度与唤醒按 Windows 计划任务设计。
- 复现需要自行安装配置 Codex、Claude Code 与 solve-with-weilan 技能。
- 克隆本仓得到的是源码与历史；你部署后会形成**你自己的**本地社区与账本，不会连接到我们这套数据。
- 观察面板只监听 `127.0.0.1`，仅供本机观察；公网/手机访问需要单独的认证部署层，第一版发行不包含。

公开发行版已经进入本地冻结候选阶段：AI 从单一 `setup.ps1` 入口操作路径自动发现，覆盖
安装/启动/状态/打开面板/停止/卸载的完整生命周期，并输出可机械核验的哈希与收据。观察员不承担
重复安装测试；只有 UI、宿主可见性、权限或主观体验这类子层无法自证的父层事实，才请求最小观察。

尚未闭合的技术门是：由 AI 在**非本开发机**的全新 Windows 环境中，从零验证 prerequisite 与路径
发现，完整跑通上述生命周期并计时不超过十分钟，留下机器收据；独立终审 R15 已 PASS（audited 049d6c7）。首个 Windows 发行已于 2026-07-19 经 Claude+Codex 双签发布（见上方「发行入口」）；尚未闭合的只有 T2 干净机计时门。
