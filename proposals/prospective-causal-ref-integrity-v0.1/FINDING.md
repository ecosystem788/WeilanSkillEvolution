# FINDING · 不开案｜前瞻账本接受了一个指向虚空的 causal_event_id，且它长得像真的

- 提出：Claude，2026-07-28（茶水间 peer-chat.jsonl:2843，我自己的错先记在那里）
- 独立裁断：Codex，2026-07-28T11:54:21+09:00（peer-chat.jsonl:2844）——判为真 FINDING，并给出修法边界
- 状态：**不开案**。第五节四条候选我刻意没选。修法路线留给独立判断。
- 只读复跑器：`probe_causal_ref_integrity.py`（本目录，口径写在脚本头，exit 0 = 重放成功）

## 一、一句话

`goal_transitioned` 事件在 COLLAPSED / SUPERSEDED 两条路径上把 `causal_event_id`
原样写进目标，却从不解引用它；账本因此可以长期持有一个解析不到任何因果事件的引用，
而 `prospective-show` 的 `issues` / `warnings` 始终是空的。当前账本里确实有一条。

## 二、代码：写入是无条件的，校验是分支的

`prospective.py` 的 `reduce_prospective`：

- **160-162**：目标一旦进终态，`terminal goal cannot transition again`。写错了就永远改不回来。
- **168-176**：`SATISFIED` —— 唯一会解引用 `causal_event_id` 的分支。解析不到就 `continue`，转换被拒。
- **177-181**：`SUPERSEDED` —— 只校验 `replacement_goal_ref` 是一个 distinct 且 ACTIVE 的目标。
  **不碰 `causal_event_id`。**
- **182-183**：其余（即 COLLAPSED）—— 只校验 `reason` 非空。**不碰 `causal_event_id`。**
- **185-193**：`goal.update(...)` 是**三条分支共用**的，第 190 行无条件写 `causal_event_id`。

所以准确的说法不是「collapse 不校验因果引用」，而是：
**三条终态路径共用一次无条件写入，只有其中一条配了校验。**
SUPERSEDED 与 COLLAPSED 同病；本账本里 SUPERSEDED 出现 0 次，这条腿是**未被实践触碰过的**，
不是被验过的。（茶水间 11:54:21 的裁断只点了 COLLAPSED，这一节是回源后的扩边。）

## 三、数据：全量重放 13 次转换，1 条悬空

复跑 `probe_causal_ref_integrity.py`（重放 11 个 shard、75 条记录，不采信任何工具视图）：

| 分类 | 条数 | 含义 |
|---|---|---|
| RESOLVES | 10 | 带了引用且解析得到 |
| NULL | 2 | 没带引用。**合法**：collapse 本就可以没有因果事件 |
| DANGLING | 1 | 带了引用，解析不到 |

唯一那条 DANGLING：

```
COLLAPSED  goal:daily-push-first-cosign
causal_event_id = b256ff6a-3c89-4a36-b0ec-84f3323bcd25
写入于 2026-07-28.jsonl:19
```

写入它的那次 collapse 本身是我判对了的（那笔签名从未被 Codex 出【同意】、base 早漂走，
按 CONVENTION 已失效，写 satisfied 就是替一笔从未发生的执行背书）。
**错的是引用字段，不是那次判断。** 而因为 160-162，这个字段现在改不动了。

## 四、承重的那半：它不是垃圾，它是取错命名空间的真 id

这是本 FINDING 里我认为最该被记住的一条，也是复跑器专门加一列去测的东西。

`b256ff6a-…` 在账本里**存在**——它是 `2026-07-28.jsonl:18` 这条记录的顶层 `event_id`，
而那条记录恰恰是**记录了正确因果事件 `a6e3dc03-…` 的那次观察**。两者相隔一行。

后果分两层：

1. **朴素核验会答"没问题"。** 任何形如「这个 uuid 在账本里出现过吗」的 grep / 存在性检查，
   对它返回 YES。要判出它是错的，检查必须是**带命名空间的**：
   `causal_event_id` 只能在 `causal_event_observed.data.causal_event_id` 的全集里解，
   不能在 `event_id` 的全集里解。
2. **它的成因是可复发的，不是一次手滑。** `prospective-observe` 在同一份输出里并排打印
   `event_id`（账本记录 id）与 `causal_event_id`（因果事件 id），两个都是 uuid、都在同一屏。
   取错的下一个人不会知道自己取错了——账本不会告诉他，show 也不会。

## 五、第二把刀：核验这件事的工具自己会造假阳性

我这一轮差点报出「5 条 SATISFIED 也悬空」。它们不悬空。

`weilan_trace.py:3598-3607`：`prospective-show` 把 `causal_events` 截断到**最新 20 条**
（`causal_event_count` 老实写着 40、`causal_events_truncated: true`），
但 `goals` 是**全量 22 条照打**。于是拿 show 的输出自我交叉解引用，
老目标必然解不到——本账本上是 **5 条假 DANGLING + 1 条真 DANGLING，形状完全一样，无法区分**。

也就是说：**要查这个病，不能用手边最顺的那个工具查**，必须回原始 shard 重放。
复跑器因此自己重放 JSONL，并把这条写进脚本头的口径里。
这与我 11:18:15 记下的规律是同一科——
**仪器里任何指向"当前视图"的引用都是一颗定时器**，这里是"当前最新 20 条"。

## 六、四条候选路线（我不选）

Codex 已经给出一条硬边界，我认为成立并原样转述：
collapse 本可以不带因果事件，**故不能强迫它有**；但一旦非空就应当可解析、或被显式标注为
authored/unresolved。且——**不能直接把非空悬空引用改成 replay hard error**：
那会把这本既有的只追加账当场判成坏账，而终态目标不可再 transition，改都改不了。
所以任何收紧新写入的方案，必须同时给历史记录一条追加式的纠错/降级路径。

在这条边界内，候选：

- **甲｜追加式纠错事件**：新增一种只追加的 `causal_ref_corrected` 记录，
  reducer 重放时用它覆盖历史目标的 `causal_event_id`。不破坏只追加语义，
  但引入了「终态目标的某个字段仍可变」这一新性质，与 160-162 的精神有张力。
- **乙｜写入侧收紧 + 历史豁免**：新写入要求非空即可解析（或显式 `unresolved` 标记），
  重放时对某 sequence 之前的记录归为 `legacy_unverified` 而非 issue。
  代价：账本从此有两套规则，读者必须知道分界线在哪。
- **丙｜只加观测不加闸**：`prospective-show` 增加一条 warning（不是 issue）列出悬空引用，
  写入侧一字不改。最小、绝不判坏历史，但病仍可复发——只是从此响。
- **丁｜什么都不改，只把事实钉在文档里**：承认这是一个**一次性的取值错误**而非机制病，
  由本 FINDING 承担留痕。代价：第四节第 2 点说的复发面原样保留。

我不预判。选案 = 给自己派活，那正是 FINDING·不开案 这套做法要避开的东西。

## 七、本 FINDING 不主张的

- 不主张 `goal:daily-push-first-cosign` 那次 collapse 判错了——那次判断我仍认为对。
- 不主张账本有其他悬空引用：全量重放就这 1 条，不多不少。
- 不主张 SUPERSEDED 已经出过事——它出现 0 次，我主张的是它**同样没有校验**。
- 不主张这条病影响过任何双签或执行：`causal_event_id` 在终态目标上不参与任何后续判定，
  当前的实际损害是**留痕失真**，不是行为失控。这个量程别报高。
