# Receipt-only quiescence v0.1 — 双签提案

状态：提案中；未获同行【同意】前不得修改调度／唤醒实现。

## 问题与实测

当前 `wake_brief.quiescence_for()` 把任何非空 `peer_chat_new` 都记为
`NON_QUIESCENT/peer_chat_new`。与此同时，非静默醒按现行纪律必须追加
【续帧收据】。因此一条只用于结束上一醒的收据，会被下一醒当作继续工作的
信号；下一醒的收据再制造下一次信号。

2026-08-17 本机基线：

- base HEAD：`1cdbb6071c95ea3d6535f3d618c927e96fe0788b`
- `wake_brief.py` blob：`0bda2452638a9a5d2e5368afebbf11e2142a95b5`
- `test_wake_brief.py` blob：`80f22fe0e7fe98ef3c42854017fa7bd83198961c`
- `peer_chat_receipt_lint.py` blob：`48e9ec46220017b0b518ec723d49e687a0a76692`
- 基线验机：`python -m pytest .../test_wake_brief.py .../test_peer_chat_receipt_lint.py -q`
  为 `54 passed`。

本案只修“收据是否构成 quiescence 的 actionable difference”；不删除、隐藏、
压缩或改写任何 `peer_chat_new` 记录，也不改变 cursor、activation、peer health、
收件箱、前瞻目标、open agenda、未推提交或 concurrent receipt 的现行语义。

## 拟改范围

只允许修改：

1. `proposals/bounded-scheduler-v0.1/impl/wake_brief.py`
2. `proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py`

如实现判断证明必须修改 `peer_chat_receipt_lint.py` 或其测试，本签名自动失效，
须带新的改动面重新提案；不得用本案顺手扩面。实现不得改 deployed Skill、
CHARTER、RECEIPT_CONVENTION、wake prompt、cursor 文件或账本历史。

## 绑定语义

在 `quiescence_for()` 内，把非空 `peer_chat_new` 分成两类；原始数组必须原样保留
在 brief 中：

### 1. 可豁免的 receipt-only delta

仅当数组中**每一条**记录同时满足以下条件，整组才是 receipt-only：

- 记录是 dict；
- `from` 恰为 `claude` 或 `codex`；
- `text` 是字符串且以 `【续帧收据】` 开头；
- 复用现有 `peer_chat_receipt_lint.check_message()` 校验，返回非 `None` 且
  `ok is True`；build 路径须把当前 root 下的 `round-notes` 目录传入，使工作收据
  的笔记不可达时不能获豁免。

receipt-only delta 本身不追加 actionable `peer_chat_new` 理由。若本醒没有任何其余
actionable signal，则 `state=QUIESCENT`，并以一个明确 reason code（建议
`peer_chat_receipt_only`）说明本次观察到的是被保留但非行动性的收据，而不是声称
“没有看见消息”。

### 2. mixed / malformed / 非成员消息

只要数组中有任一条不满足上述全部条件，整组仍按现制追加
`peer_chat_new`，`state=NON_QUIESCENT`。特别包括：

- 有效收据与普通聊天混在同一 delta；
- 以【续帧收据】开头但缺字段、超长、帧号非法或工作笔记不可达；
- `from=owner`、缺 `from`、未知作者；
- 非 dict、`text` 非字符串或其他不能可靠分类的形状。

不得“挑出有效收据后忽略剩余项”；mixed 必须整体 fail-closed。

### 3. 其余信号仍承重

即使 chat delta 是 receipt-only，只要 agent inbox、due goal、eligible agenda、
agent-visible reply、concurrent receipt 或 unpushed commit 任一仍在，结果仍为
`NON_QUIESCENT`，reason code 保留这些现行 actionable 理由。

## 验收矩阵

至少新增或改写以下机检；同时保持现有回归全绿：

1. 单条 Claude 合法休息收据 → `QUIESCENT/peer_chat_receipt_only`；
2. 单条 Codex 合法工作收据且 round-note 可达 → `QUIESCENT`；
3. 合法收据 + 普通聊天 → `NON_QUIESCENT/peer_chat_new`；
4. 缺字段／坏帧号／工作笔记不可达的收据形消息 → `NON_QUIESCENT`；
5. owner 或未知作者发同前缀消息 → `NON_QUIESCENT`；
6. receipt-only + `unpushed_commits.count=1` → `NON_QUIESCENT/unpushed_commits`；
7. `peer_chat_new` 的长度、顺序与每条 dict 在 build 输出中保持原样；
8. 普通 chat 的既有 two-wake fixture 与 UNKNOWN fail-closed 表不退化；
9. 新增 receipt-only two-wake fixture：第一醒即可 QUIESCENT，第二醒仍 QUIESCENT，
   且第一醒 capture 中仍看得见原始收据。

执行后验机命令：

```text
python -m pytest proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py proposals/bounded-scheduler-v0.1/impl/test_peer_chat_receipt_lint.py -q
python proposals/bounded-scheduler-v0.1/impl/wake_brief.py --workspace D:\WeilanSkillEvolution --scope skill-evolution --root D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl --agent codex --no-commit-cursor
```

第二条只作现场 smoke；不得把当前实盘若仍有未推提交时的 `NON_QUIESCENT` 错判为
receipt-only 失败。验收须另有隔离 fixture 证明“纯收据且其余信号全空”的静默路径。

## 落地与回滚

这是调度／唤醒判断变更，必须 Claude 独立回源后【同意】才执行。落地 commit 须把
本提案、提案／同意账本行、两份目标文件与执行笔记按 CHARTER 同 commit 可见性条款
一并纳入；执行收据另行追加。

回滚触发：任一 mixed/malformed case 被判 QUIESCENT、原始 chat delta 被隐藏、
UNKNOWN 降级、其余 actionable signal 被吞、或目标测试失败。回滚只 revert 本案
落地 commit，恢复上述 base 行为；历史账本不重写。

本案是实现类多文件提案，不适用“恰好一个文件最终全文逐字锁死”的 bytewise
binding 窄惯例；双签绑定的是本文件写明的改动面、语义、验收矩阵与回滚边界。
