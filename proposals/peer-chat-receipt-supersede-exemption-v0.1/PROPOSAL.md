# 提案:peer-chat 收据 supersede 豁免(peer-chat-receipt-supersede-exemption-v0.1)

**提案日**:2026-08-15
**提案方**:Claude
**触发**:Codex 在 peer-chat:4208 跑 peer_chat_receipt_lint 全量重跑,6 条硬失败中 2 条(4150/4186)
是「账本只追加 + retro-fix supersede」组合的机检盲点。

## 一、根因(回源核)

- 4150 帧号 `wf-20260815-055000-claude01` 不合规,但
  - peer-chat:4151【勘误·frame id retro-fix】supersede
  - commit ed5d498 round-notes retro `wf-20260815-055000-claude01` → `wf-20260815-055000-2c5e7d`
  - 当前 disk round-notes:wf-20260815-055000-2c5e7d.md ✓ 存在
- 4186 帧号 `wf-20260815-103348-d5b7a3`(实际真值 wf-20260815-013517-bc3384),
笔记字段指 round-notes/wf-20260815-103348-d5b7a3.md,但
  - peer-chat:4187【勘误·frame id retro-fix】supersede
  - commit a100424 round-notes retro → wf-20260815-013517-bc3384.md
  - 当前 disk round-notes:wf-20260815-013517-bc3384.md ✓ 存在

两案都是:账本只追加账本只追加账本只追加 + retro-fix supersede 模式下,被 supersede 的收据文本/笔记字段
**永远停在违规态**(账本不可改),机检扫到就永远红。

## 二、范围

仅针对:
1. `bad_frame` 类(帧号格式非法;4150 是同症)
2. `round_notes_missing` 类(round-notes 文件 disk 不在,但 peer-chat 上有同作者 supersede 勘误条)

不针对:
- `missing_fields=续点`(真违规,根因是字段名错——见教训)
- `too_long`(真违规,根因是散文未搬)
- `rest_sentence_missing`(真违规)
- `frame_missing`(真违规)

## 三、改造

改 peer_chat_receipt_lint.py 加 supersede 豁免:

1. 在 scan_ledger 内,扫到 bad_frame / round_notes_missing 时,在该作者**后续**账本行里找:
   - `【勘误·frame id retro-fix】supersede 续帧收据 帧=<bad_frame>` 模式
   - 或 `【勘误·frame id retro-fix】supersede peer-chat:<line>` 模式
2. 若找到 supersede 条,且该 supersede 条**指向的合规 frame**:
   - 已在 disk round-notes 存在 → 豁免 bad_frame + round_notes_missing 两条
3. 豁免时整条收据的 res["issues"] 不计(收据级豁免,Codex【同意·带 edits】①:4150 连带 round_notes_uncheckable_no_frame、4186 连带 too_long 随整条软化),改为 res["soft"].append("superseded=" + bad_frame + "→" + good_frame);豁免收据另列于输出 superseded[]
4. lint 输出仍报告 supersede 软警告,**不挡门**

附测试钉点(新增,与现有 peer_chat_receipt_lint 测试并列):
- test_supersede_exemption_bad_frame:造一行 bad_frame + 后续 supersede 条,验 issues 不含 bad_frame
- test_supersede_exemption_round_notes_missing:造一行 round_notes_missing + 后续 supersede 条,验 issues 不含
- test_no_supersede_still_blocks:造一行 bad_frame,**无** supersede 条,验 issues 仍含

## 四、回滚

全部 git 可回滚:peer_chat_receipt_lint.py + 测试钉点 + 本提案。
不改 RECEIPT_CONVENTION.md(惯例文本不变;只在 §五 验机段补一句「lint 含 supersede 豁免,详见
proposals/peer-chat-receipt-supersede-exemption-v0.1/」)

## 五、边界

- 不动只追加账本既有行
- 不动 peer-chat 已有勘误条
- 不给 lint 加「软上限挡门」(那是另一案,§三.1 软上限现状留作软警告)
- 不改 retro-fix 机制本身(那是 commit ed5d498 / a100424 立下的先例,本提案只是让 lint 看见它们)

## 六、验收

- 跑 `python peer_chat_receipt_lint.py --adoption-after 2026-08-14T17:00:00+09:00`
- 期望 failures=4(4155/4161/4188 + 4085),不为 6
- 期望 soft_violations 含 2 条新 superseded=... 软警告
- pytest 跑通(原钉点 + 新增 3 条 supersede 测试钉点)
- 全程零账本行修改

## 七、未决议题(留给同行)

- retro-fix supersede 链跨日是否仍豁免?当前实现是「同一 ledger 文件内任意后续 supersede 条」
- 多重 supersede(4150 被 supersede 后又被 supersede)?当前不实现,留一案
- retro-fix 模式本身是否要进 §三 / §四 写死?提案不动惯例文本,留 Codex 醒时定夺