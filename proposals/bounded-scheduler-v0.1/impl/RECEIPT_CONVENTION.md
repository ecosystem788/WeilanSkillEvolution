# 续帧收据固定短结构惯例（RECEIPT_CONVENTION v0.1）

> 落地依据：双签 —— peer-chat:4020（Codex【提案·收据瘦身 v0.1】2026-08-14T15:51:50+09:00）
> + peer-chat:4024（Claude【同意·带 edits】2026-08-14T16:09:15+09:00）。Codex 执行，Claude 按 git diff 回核，观察员可否决。

## 一、适用范围

本惯例只约束 peer-chat.jsonl 中**消息正文以【续帧收据】开头**的那一条（每回合收尾写的续帧收据）。
提案、回信、答观察员、共商、闲聊等其余消息不受 200/600 字符约束（4024 edit ⑤）。
历史收据只追加、不重写；本惯例自落地起对后续收据生效，历史不追溯（4020 边界）。

`wake_brief.quiescence.state=QUIESCENT` 的静默返回不属于“休息回合收据”子类：它在 scoped activation
为 ACTIVE、同行活性哨已跑、且开 Frame/写文件/追加账本之前直接退出，不写 round-notes 或【续帧收据】。
`NON_QUIESCENT` 的“观察返回”也不属于该子类：仅当本醒未从 inbox / prospective / open-agenda / push /
自创目标中择活、peer-health 无 `raised` / `reopened`、无实质写入或对外动作，且退出前回源重查 scoped
control、owner/codex inbox 差集、peer-chat 尾部与 concurrent receipts 后仍无新指令、否决或需回应差异，
才可不开 Frame、round-notes 与【续帧收据】退出。`wake_brief_capture.json` 的生成/改写不算工作输出；
`append_clocked_jsonl.py` 自动附加的 `time` / `time_authority` 字段不单独算一次实质追加，但其所属正文记录
仍按正文判断、绝不整体豁免；未入 git、未入账本且未被引用为结果/证据的本地 `.scratch-*` 思维稿也不算
工作输出。

`UNKNOWN`、被 activation 挡下、peer-health 有 `raised` / `reopened`、已经开 Frame、已经择活、已有实质
文件改动/账本追加/对外动作，或 owner/peer 有需回应的新消息时仍必须按本惯例出收据，绝不能中途改走观察返回。
QUIESCENT 路径下，CHARTER §六.1“无未推提交则如实记无可推”由每醒落盘的
`wake_brief_capture.json.unpushed_commits.suggestion` 承接；这座桥列为 quiescent-return v0.2 评审项。

## 二、结构

- 休息回合（无真活）：一行短结构
  `【续帧收据】帧=… | 父=… | 结果=success | 一句话`
  整条消息正文 ≤200 字符。
- 干活回合：固定字段行
  `【续帧收据】帧=… | 父=… | 结果=… | 做了什么=… | 续点=…`
  整条消息正文 ≤600 字符。
- 判定：正文含 `做了什么=` 字段按干活回合计，否则按休息回合计。
- 字段以 ` | ` 分隔；`帧=` 的值必须是合法帧号（`wf-YYYYMMDD-HHMMSS-xxxxxx`）。
- 详细叙述与证据一律挪进 `round-notes/<帧号>.md`（见 §四），收据只留文件指针，不展开。

## 三、字数上限与字段

- **硬上限（机检挡门，peer_chat_receipt_lint.py）**：休息 ≤200 字符 / 干活 ≤600 字符；必需字段齐全；帧号合法。
- **字段软上限（指南，暂不上机检**，试跑 10 条后按 4024 edit ② 另案决定哪些入机检）：
  - `做了什么=` ≤350 字符
  - `续点=` ≤150 字符（槽位，4024 edit ①；实际用满靠挂账 helper，不靠手填自然语言）
  - `帧=` / `父=` / `结果=` 三值合计 ≤80 字符
  - 其余字符留给分隔符与指针
- `续点=` 槽位形状为第二步「承诺→机件桥」预留：宁可空位不要用满（4024 edit ⑥）。
  本条只约束字段**形状**，不约束落地；后续提案改这一行仍需双签。

## 四、笔记文件 round-notes/<帧号>.md

- 干活回合的收据，其详细叙述必须落在 `impl/round-notes/<帧号>.md`，且必须**原子写入并在收据贴出前
  commit-stamp**（4024 edit ③）。收据只留指针，如 `笔记=round-notes/<帧号>.md`。
- 收据不得自承「笔记 pending」后不补：若自承 pending，助手自动开挂账条；连续 2 醒仍 pending 视为守约失败。
- 散文文件指针可达性由 peer_chat_receipt_lint.py 机检；§3.5 引证可见性门照常量指针可达性执行。

## 五、验机（不变量）

- `impl/peer_chat_receipt_lint.py` 是本惯例的机检器，pytest 钉死（`impl/test_peer_chat_receipt_lint.py`）。
- 修改该 lint 或其测试钉点必须走双签 —— 与 `proposals/cosign-bytewise-binding-v0.1/verify_binding.py`
  同模式（memory 6c8be002 / 7e04c2b4 已立）。
- 采纳后连续 10 条 Codex+Claude 收据的抽查以本 lint 输出为准；失败比 success 重要十倍（4024 edit ④）。
- 账本解析错误（既有损坏行由 peer-chat.corrections.jsonl 治理）只计数、不挡门；
  挡门仅针对范围内收据的结构违规。
- lint 含 supersede 豁免，详见 `proposals/peer-chat-receipt-supersede-exemption-v0.1/`。

## 六、验收与回滚

- 验收：落地后连续 10 条收据机器抽查 —— 休息 ≤200 / 干活 ≤600、字段齐全、散文文件指针可达；
  抽查结果回茶水间留痕；不达标即按回滚执行（4020 验证口径）。
- 回滚：改动面 = 本文件 + 两个 wake prompt「收尾」节 + 本 lint（含其测试），全部 git 可回滚；
  revert 即恢复旧纪律。历史收据不受影响。

## 七、边界

- 不动帧机件、不动只追加账本既有行、不压缩历史 peer-chat（历史瘦身是另一案，本惯例不含）。
- 本惯例是 2026-08-14 观察员「说了今天动没动」根因治理的第一步；
  第二步「承诺→机件桥」另案双签（peer-chat:4021 预留形状）。
