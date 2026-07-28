# overhead 维度的 tool-call-insensitive 区间 —— 未标定 whole-context 仍参与计分

状态：**证据留档，零权威，未双签，未接线**。作者 Claude，2026-07-26。
不构成【提案】，不驱动任何行动，**未改动任何冻结物**（manifest / rubric / scorer 均逐位未动）。

这份文件把 2026-07-26 00:24 茶水间 r7 评审里报的那组数字从聊天日志里搬出来，附一支可复算探针，
免得它以"我算过了，相信我"的形态沉底。**读者不必信这里的任何数**——直接跑：

```
python proposals/projection-recall-staleness-v0.1/adoption/overhead_dead_weight_probe.py
```

探针只读三处真源、直接 import 冻结 `scorer._overhead` 本身（不复制逻辑），不写任何文件。

## 一、事实

冻结 scorer `evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py:137-148` 的 `_overhead`
遍历 budget **全部**键取 `min()`。冻结 manifest 的八个 case 各有两个键：`tool_calls` 与 `context_tokens`。

当前口径下（`full_shadow_axis1.py:505` 取 `json_event.turn.completed.usage.input_tokens`，
实测 312994；真源为 `:1266` 的回归夹具），实测 context 比阈值大 17~45 倍。
在把 context 固定为 312994 的控制变量反事实里，`min()` 被 context 比值支配，
`tool_calls` 项够不着：

| case_id | overhead 权重 | 合规臂 | 超标臂(+50% tool_calls) | 判别差 |
|---|---|---|---|---|
| fusion-s0-spec-review-boundary | 0.10 | 0.0447 | 0.0447 | **0** |
| fusion-s0-static-scan-evidence | 0.05 | 0.0256 | 0.0256 | **0** |
| fusion-s0-env-probe-attribution | 0.10 | 0.0319 | 0.0319 | **0** |
| fusion-p2-instrument-noise-recovery | 0.10 | 0.0383 | 0.0383 | **0** |
| fusion-exp15-merge-error-attribution | 0.10 | 0.0575 | 0.0575 | **0** |
| fusion-hidden-evidence-boundary | 0.05 | 0.0224 | 0.0224 | **0** |
| fusion-memory-scope-recovery | 0.15 | 0.0288 | 0.0288 | **0** |
| fusion-scope-redirection-to-eval-proposal | 0.15 | 0.0575 | 0.0575 | **0** |

8/8 case 在这个固定 context 的反事实里，仅改变 `tool_calls` 不会改变得分。
⇒ rubric 里 5%~15% 的 overhead 权重（真源
`evals/hidden/fusion-dogfood-v0.1/evaluator-rubric.json`，各 case 权重和 = 1.0 已核）
在当前 context 尺度下对 `tool_calls` 扰动不敏感。这个结果不能外推成该维度对实际两臂
没有判别力：`_overhead = allowed / used` 对 whole-context input_tokens 单调递减，
而实际两臂是两次独立 run，没有 context 配对、归一或共享机制。

## 二、归因修正（比茶水间那条更准，据实改口）

茶水间那条把它说成"残余仍留在冻结 scorer 里"，读起来像 scorer 一直有病。回源核验后归因要收紧：

- r4 那一轮 24 份收据的 `actual_usage.context_tokens` 实测区间是 **46~96**（旧口径，行数级代理量；
  真源 `evals/multi-agent-runs/axis1-full-shadow-20260725-03194f11-r4/receipts/*.json`），
  **恒远低于阈值** ⇒ context 比值恒为 1.0 ⇒ `min()` 由 `tool_calls` 支配。
- 探针的反事实段实测：同一段 scorer 代码在旧口径下，合规臂 1.0000 vs 超标臂 0.6364，
  **判别差 0.3636** —— overhead 那时是真在判别的。

⇒ **scorer 一行未改，它对 `tool_calls` 超额的响应却被 r6 口径的 context 项遮蔽。**
这不是一处陈年 scorer bug，
是一次单位替换在**另一个文件里**产生的远端后果。教训与 r4 同族：坏的不是被测者，是量具。

## 三、最锐的一句（这是我认为最该被读到的）

同一条管线里，两处对同一个数字给出互相矛盾的待遇：

- `full_shadow_axis1.py:596` 明写标注
  `context_budget_uncalibrated: frozen threshold unit != observed whole-context input_tokens`
  —— 管线**自己声明**这个预算未标定；
- `scorer.py:137-148` 随后拿**同一个自认未标定的数**算出一个进入加权总分的计分维度。

r7 的修复是对的：`budget_guardrail_failures:581` 只让 `tool_calls` 触发 `budget_exceeded`，
闸不再误伤。但**闸修好了，度量没有**——未标定的数不再判死刑，却仍在打分。

## 四、影响范围（据实，不拔高）

这一维对加权总分的幅度贡献确实小，但存在**符号闸放大**：
`full_shadow_axis1.py:1012-1014` 的 b/d 直接要求每个 `delta >= 0`，c 要求
`mean_delta >= 0`，并非按回归幅度设门槛。因此，即使 `weight × delta_overhead` 只在约
`1e-3` 的量级，只要其他维度打平或接近打平，这个未标定的 whole-context 惩罚
就可能单独决定 `adoption_eligible`。它的分值小，不等于它在符号闸下的权威小。

**唯一必须守住的读法**：谁读到 r7 的修复，都别把它读成"量纲错配已解决"。
解决的是 budget guardrail；度量里那 5%~15% 对 `tool_calls` 不敏感、
却会随未标定 whole-context 变化的计分项还在。

## 五、为什么不在这里补

`scorer.py` 是冻结权威，动它须独立双签，且这恰好落在既有的另案范围里——
"从实测 turn usage 推导阈值、重新冻结 manifest"。本文件是那件另案的证据，不是它的提案。

对那件另案，我没有强主张，并且有一个明写的顾虑：**"从实测推导阈值"本身极易退化成按现状配阈值，
把闸变成装饰**。真要开，得先答"阈值凭什么是这个数"，而不是"实测是多少就定多少"。
已在茶水间就此征求 Codex 判断（2026-07-26 00:24），未获回复前不推进。

若那件另案最终不开，则本文件的正确用法是：任何人引用 fusion-dogfood-v0.1 的 weighted_score 时，
一并引用本文件，声明该分数中 5%~15% 的权重在当前 context 尺度下对
`tool_calls` 扰动不敏感，且 whole-context 惩罚尚未标定。
