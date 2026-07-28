#!/usr/bin/env python3
"""overhead 敏感性探针 —— 零权威，只读，不改任何冻结物。

回答两个可复算的问题：冻结 scorer 的 `overhead` 维度，在当前 context
尺度下是否响应 `tool_calls` 扰动；在固定 `tool_calls` 时是否会随 whole-context 改变。

它只读三处真源：
  - 冻结 manifest 的 per-case budget    evals/fusion-dogfood-v0.1-manifest.json
  - 冻结 rubric 的 per-case overhead 权重 evals/hidden/fusion-dogfood-v0.1/evaluator-rubric.json
  - 冻结 scorer 的 _overhead 实现        evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py

不写文件、不改状态、不产生分数。跑法：
  python proposals/projection-recall-staleness-v0.1/adoption/overhead_dead_weight_probe.py
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "evals" / "fusion-dogfood-v0.1-manifest.json"
RUBRIC = REPO / "evals" / "hidden" / "fusion-dogfood-v0.1" / "evaluator-rubric.json"
SCORER = REPO / "evals" / "hidden" / "scorers" / "fusion-dogfood-v0.1"

# 当前口径下实测到的整轮 input_tokens。真源：full_shadow_axis1.py:1266 的回归夹具
# （extract_context_usage 取 json_event.turn.completed.usage.input_tokens）。
OBSERVED_CONTEXT_TOKENS = 312994
# r4 那一轮 24 份收据里 actual_usage.context_tokens 的实测区间（旧口径，行数级代理量）。
# 真源：evals/multi-agent-runs/axis1-full-shadow-20260725-03194f11-r4/receipts/*.json
LEGACY_CONTEXT_RANGE = (46, 96)
CONTEXT_SENSITIVITY_POINTS = (250000, OBSERVED_CONTEXT_TOKENS, 400000)


def load():
    sys.path.insert(0, str(SCORER))
    from scorer import _overhead  # 冻结实现，原样调用，不复制逻辑

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rubric = json.loads(RUBRIC.read_text(encoding="utf-8"))
    return _overhead, manifest, rubric


def main():
    overhead, manifest, rubric = load()
    if not manifest.get("frozen"):
        print("WARNING: manifest 不再是 frozen，本探针的前提已变", file=sys.stderr)

    weights = rubric["metrics_by_case"]

    class Ctx:  # _overhead 只碰 .receipt
        def __init__(self, receipt):
            self.receipt = receipt

    def ov(budget, tool_calls, context_tokens):
        return overhead(Ctx({
            "budget": budget,
            "actual_usage": {"tool_calls": tool_calls, "context_tokens": context_tokens},
        }))

    print(f"实测 context_tokens = {OBSERVED_CONTEXT_TOKENS}（当前口径）\n")
    header = f"{'case_id':<42}{'w':>6}{'合规臂':>10}{'超标臂':>10}{'判别差':>10}"
    print(header)
    print("-" * len(header))

    rows = []
    for case in manifest["cases"]:
        cid = case["case_id"]
        budget = case["budget"]
        w = weights[cid]["overhead"]
        allowed_calls = budget["tool_calls"]
        # 合规臂：tool_calls 恰在预算内。超标臂：tool_calls 超出 50%（远超冻结闸）。
        compliant = ov(budget, allowed_calls, OBSERVED_CONTEXT_TOKENS)
        exceeded = ov(budget, int(allowed_calls * 1.5) + 1, OBSERVED_CONTEXT_TOKENS)
        rows.append((cid, w, compliant, exceeded))
        print(f"{cid:<42}{w:>6}{compliant:>10.4f}{exceeded:>10.4f}"
              f"{compliant - exceeded:>10.4f}")

    insensitive = [r for r in rows if abs(r[2] - r[3]) < 1e-9]
    print()
    print(f"固定 context 时 tool_calls 扰动差等于 0 的 case：{len(insensitive)}/{len(rows)}")
    if insensitive:
        wmin, wmax = min(r[1] for r in insensitive), max(r[1] for r in insensitive)
        print(f"这些 case 里 overhead 权重区间 {wmin}~{wmax}，"
              f"当前 context 尺度下对 tool_calls 扰动不敏感")
        print(f"overhead 取值区间 {min(r[2] for r in insensitive):.4f}~"
              f"{max(r[2] for r in insensitive):.4f}")
    if len(insensitive) != len(rows):
        raise AssertionError("存在未被 context 项遮蔽的 tool_calls 扰动，前提已变")

    print("\n--- 敏感性：固定 tool_calls，改变 whole-context ---")
    case = manifest["cases"][0]
    b = case["budget"]
    context_values = []
    for context_tokens in CONTEXT_SENSITIVITY_POINTS:
        value = ov(b, b["tool_calls"], context_tokens)
        context_values.append(value)
        print(f"{case['case_id']} @ context_tokens={context_tokens}: {value:.6f}")
    if not all(left > right for left, right in zip(context_values, context_values[1:])):
        raise AssertionError("overhead 未按预期随 whole-context input_tokens 单调递减")
    print("⇒ 实测值随 context_tokens 改变；实际两臂 context 未配对时，该维度可产生非零 delta。")

    print("\n--- 反事实：旧口径下同一段代码 ---")
    lo, hi = LEGACY_CONTEXT_RANGE
    for ctx_val, label in ((lo, f"旧口径下界 {lo}"), (hi, f"旧口径上界 {hi}")):
        c = ov(b, b["tool_calls"], ctx_val)
        e = ov(b, int(b["tool_calls"] * 1.5) + 1, ctx_val)
        print(f"{case['case_id']} @ {label}: 合规 {c:.4f} / 超标 {e:.4f} / 差 {c - e:.4f}")
    print("⇒ 旧口径下 context 比值恒为 1.0，min() 由 tool_calls 支配；"
          "口径换成整轮 input_tokens 之后支配项翻转 —— scorer 一行未改，"
          "对 tool_calls 的响应却被 context 项遮蔽。")


if __name__ == "__main__":
    main()
