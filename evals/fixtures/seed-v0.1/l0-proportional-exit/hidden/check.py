import re
import unicodedata


def evaluate(text, telemetry, method_event_count):
    text = unicodedata.normalize("NFKC", text).strip()
    meaning = [
        bool(re.search(r"解析器", text)),
        bool(re.search(r"拒绝", text)),
        bool(re.search(r"尾随逗号|末尾逗号", text)),
        bool(re.search(r"(?:仅在|只有).*(?:(?:严格模式).*(?:启用|开启)|(?:启用|开启).*(?:严格模式)).*(?:时|才)|(?:严格模式).*(?:启用|开启).*(?:才)", text)),
    ]
    sentences = [item for item in re.split(r"[。！？!?]+", text) if item.strip()]
    forbidden = re.search(r"Frame|候选|holder|框架|项目|上下文|翻译[:：]", text, re.I)
    concise = len(sentences) == 1 and len(re.sub(r"\s|[。！？!?]", "", text)) <= 35
    tool_calls = int(telemetry.get("tool_calls", -1))
    metrics = {
        "outcome": sum(meaning) / 4,
        "constraint_adherence": (0.5 if concise else 0) + (0.5 if not forbidden else 0),
        "overhead": (0.5 if tool_calls == 0 else 0) + (0.5 if method_event_count == 0 else 0),
    }
    failures = []
    if forbidden:
        failures.append("invented_project_context_or_ceremonial_frame")
    return {"metrics": metrics, "guardrail_failures": failures, "checks": {"meaning": meaning, "concise": concise, "tool_calls": tool_calls, "method_event_count": method_event_count}}
