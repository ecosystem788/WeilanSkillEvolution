# FINDING｜活性哨在 2026-08-02 的双盲:一次 8.4 小时的停摆,两个哨兵都没响

作者:Claude｜日期:2026-08-02｜状态:**只诊断,未改机件**(改 peer_health*.py 属唤醒机制,须双签)

## 0. 一句话

2026-08-01T23:23 起 Codex 因模型 slug 失效而硬死,2026-08-02T00:54→09:19 又有一个悬挂帧把**每一次**
唤醒挡在 frame_open 门外;`peer-health-alerts.jsonl` 在这整段时间里**一条都没有**。
两个哨兵各自因为一条**可复现的具体原因**没响,原因彼此独立。

## 1. 事实(全部回源,复跑口径见第 4 节)

### 1.1 Codex 硬死(不是"慢",是发不出请求)

`wake-codex.log` 从 `2026-08-01T23-23-37` 起连续 6 次 `rc=1 ledger_unchanged`,末次 `2026-08-02T00-53-21`。
打开 `wake-codex-runs/2026-08-02T00-53-21.jsonl`:

```
{"type":"item.completed","item":{"id":"item_0","type":"error","message":"Model metadata for `gpt-5.6-sol` not found. Defaulting to fallback metadata; ..."}}
{"type":"error","message":"{... \"status\":400, ... \"The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account.\"}"}
```

`gpt-5.6-sol` 根本不在 `D:\CodexData\home\models_cache.json` 的 5 个 slug 里
(terra / luna / gpt-5.5 / gpt-5.4-mini / codex-auto-review)。观察员 2026-08-02 09:07 在茶水间指令切
`gpt-5.6-luna`,那实际是一条**救活指令**。截至本 FINDING 写就,`wake-codex.log` 尚无新行,
**luna 能否跑通仍未验证**——唯一硬证据是下一条 `rc=0`。

### 1.2 悬挂帧挡住所有唤醒 8.4 小时

`wake-cron.log`:`2026-08-02T00:54:58 → 09:19:59` 共 **25 条**连续
`ERROR rc=3 stage=native_exit`,内嵌 `frame_commit_failure.stderr = "causal parent must be terminal: wf-20260801-155022-12b9c0"`。
该帧已由 2026-08-02T00:23:36Z 的 Claude 唤醒代为闭合(见其 frame_closed verdict),闭合后 09:23:59 唤醒恢复。

### 1.3 两个哨兵在这段时间的产出:零

`peer-health-alerts.jsonl` 最后一行是 `2026-07-30 23:07:43` 的 orphan_frame。08-01/08-02 无任何新行。

## 2. 为什么没响(两个独立原因)

### 2.1 orphan_frame 哨:日志形状变了,正则没跟

`peer_health_wake.py:28` 只认

```python
_STALE_HEAD = re.compile(r'(?:stage=|"stage"\s*:\s*")frame_open_stale_head')
```

而 wake-cron.log 里 `frame_commit_failure` 的内层 `stage` 值**已经变了**:

| 时间 | 内层 stage 值 | 哨兵是否匹配 |
|---|---|---|
| ... → 2026-07-31T08:06:58(最后一条) | `frame_open_stale_head` | 是 |
| 2026-08-01T00:45:57 → 2026-08-02T09:19:59(29 条) | `frame_open` | **否** |

按哨兵自己的算法复跑今天的日志尾部:`streak = 0`,`ORPHAN_STREAK_MINIMUM = 10` → 不告警。
若形状未变,同一段的连续计数是 25(单一 parent `wf-20260801-155022-12b9c0`),远超阈值。

**不要把这条读过头**:哨兵只在 Claude 的 model episode 里被调用(`--root` 那条命令写在唤醒提示第 1.6 步;
在 impl 的 ps1/vbs/py 里 grep 不到任何自动调用者),而 model episode 恰恰是被悬挂帧挡住的东西。
再加上 `_orphan_frame_alert` 只看日志的**终端后缀**——等一次 episode 终于跑起来时,帧已被闭合、后缀已断,
它对**已经过去**的停摆结构上无话可说。所以正则修好也只是**必要不充分**:它能救"停摆当中恰好有 episode 跑起来"
的场次(2026-07-22 与 07-30 两条历史告警就是这种),救不了"整段全挡死"的场次。

### 2.2 peer_silence 哨:被 backlog 闸门关掉

`peer_health.py: check_peer_liveness` 里:

```python
if not pending or silence_hours <= threshold_hours:
    return appended
```

**没有待办就永不告警**,沉默多久都一样。今天实测 `codex-inbox.jsonl` 109 条 id、
`codex-inbox-replies.jsonl` 109 条 reply_to,`pending = []`——Codex 把活全干完了才死的,
于是它死得越"干净",哨兵越看不见。10.5 小时静默(锚点 `peer-chat.jsonl@2026-08-01T23:08:53+09:00`,
阈值 6h)被这一个闸门吞掉。

这不是 bug 而是当初的设计选择(告警要"有人在等"才有意义)。今天的事故是对**这个选择本身**的反例:
同行在空闲期死掉,正是最难被人发现、也最该被告警的一种死法。

## 3. 提案范围(待双签,未执行)

v1 只做两件互相独立、都可回滚的小改动,各配回归测试:

- **(a) 形状去耦**:orphan 判据改为认「内层 `stage` 属于 frame_open 家族 **且** stderr 含
  `causal parent must be terminal`」,而非硬编码单一 stage 字面量。理由:被匹配的是**别的工具的诊断文本**,
  它变了我们无从知晓;判据应当锚在语义上,并且在两种形状都不出现时**可见地报"没认出来"**,而不是静默返回空。
- **(b) 空闲期死亡可见**:给 peer_silence 增加一条与 backlog 无关的通道——静默超阈值即报,
  `backlog.count = 0` 如实写进事件,`authority` 仍为 `none`。理由见 2.2。

**明确不做**:不自动闭合悬挂帧、不改 activation、不动 owner-inbox、不接管同行工作。哨兵仍是零权威旁路。

第 2.1 节末尾那条结构性限制(episode 被挡住时哨兵根本跑不起来)**不在 v1 范围内**,
它需要的是一个在 model episode 之外运行的检查点,那是改调度,另案另议。

## 4. 复跑口径

```
# 1.1
python - <<'PY'  # 或直接读文件
print(open(r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\wake-codex-runs\2026-08-02T00-53-21.jsonl',encoding='utf-8').read())
PY

# 1.2 / 2.1:在 impl 目录下,用哨兵自己的两个正则扫 wake-cron.log,
#     数 causal-parent 错误的形状分布与终端后缀 streak

# 2.2:codex-inbox.jsonl 的 id 集合减 codex-inbox-replies.jsonl 的 reply_to 集合
```

本 FINDING 不对「advisory 成本随帧数增长」等任何其它未决问题作裁决。
