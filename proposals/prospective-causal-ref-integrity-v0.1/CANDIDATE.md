# 乙′ candidate：Prospective causal-reference integrity v1

本目录的 `candidate/solve-with-weilan` 是从当前已部署 Skill 复制出的外部候选；它不是采纳决定，
没有部署，也没有改动 `D:\CodexData\skills\solve-with-weilan`。

## 双签范围

- 提案：`peer-chat.jsonl`，Codex `2026-07-28T12:14:44+09:00`
- 带条件同意：`peer-chat.jsonl`，Claude `2026-07-28T12:30:37+09:00`，
  `re=2026-07-28T12:14:44+09:00`

候选采用乙′与同意所加的 ⑦–⑨：

1. CLI 写出的 `goal_transitioned` 自证 `causal_ref_policy=resolved-if-present-v1`。
2. 强制只发生在新事件准入：非空 `causal_event_id` 必须解析到
   `causal_event_observed.data.causal_event_id`；失败时不追加。
3. 重放永不因该引用悬空而封账。派生分类为 `resolved`、`not_provided`、
   `unresolved_unenforced`（无标记记录）或 `unresolved_enforced`（带标记记录）。
4. `prospective-show` 的分类来自全量 reducer；即使事件展示受 `--limit` 截断，也不重新猜引用状态。

## 边界

标记是写入者自证，因此本候选只关闭经 `prospective-transition` 命令写入的复发面。
绕开 CLI 的手工追加仍会被重放并诚实降级；它不会被误称为已由 v1 准入验证。
“重放成功”不表示引用正确，“resolved”也只表示命名空间内可解析，不表示终态判断本身正确。

## 验证

在候选的 `scripts/` 下运行：

```powershell
python -X utf8 test_causal_ref_integrity.py
python -X utf8 test_prospective.py
```

回滚仅需删除或 `git revert` 本 proposal 的 candidate 与说明；本案不授权采纳、部署或回滚已部署 Skill。
