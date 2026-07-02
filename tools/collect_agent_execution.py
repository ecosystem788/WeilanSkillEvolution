"""Extract observable task telemetry from one Codex subagent rollout."""

import argparse
import hashlib
import json
import math
from pathlib import Path


def is_bootstrap(input_text):
    lowered = input_text.lower()
    reads_prompt = "prompt-stage-" in lowered and "get-content" in lowered
    reads_bundle = "method-bundle" in lowered and any(
        marker in lowered for marker in ("get-content", "read", "skill.md", "references\\")
    )
    return reads_prompt or reads_bundle


def task_prompt(text):
    for marker in ("Frozen task:", "Frozen task: "):
        if marker in text:
            text = text.split(marker, 1)[1]
            break
    for marker in ("Do not use network", "No network"):
        if marker in text:
            text = text.split(marker, 1)[0]
            break
    return text


def find_rollout(session_root, execution_id, stage_index=None):
    matches = []
    needle = execution_id.encode("utf-8")
    for path in Path(session_root).rglob("*.jsonl"):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if needle in data:
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"no rollout contains {execution_id}")
    viable = []
    for path in matches:
        try:
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError):
            continue
        has_prompt = False
        has_final = False
        for record in records:
            payload = record.get("payload", {})
            if record.get("type") != "response_item" or payload.get("type") != "message":
                continue
            text = "".join(item.get("text", "") for item in payload.get("content", []))
            prompt_matches = execution_id in text
            if stage_index is not None:
                prompt_matches = prompt_matches and f"prompt-stage-{stage_index}.txt" in text
            has_prompt |= payload.get("role") == "user" and prompt_matches
            has_final |= payload.get("role") == "assistant" and bool(text)
        if has_prompt and has_final:
            viable.append(path)
    if not viable:
        raise ValueError(f"no completed rollout contains {execution_id}")
    return max(viable, key=lambda item: item.stat().st_mtime_ns)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--stage-index", type=int)
    parser.add_argument("--session-root", required=True)
    parser.add_argument("--trial-root", required=True)
    parser.add_argument("--rollout-file")
    args = parser.parse_args()
    rollout = Path(args.rollout_file) if args.rollout_file else find_rollout(args.session_root, args.execution_id, args.stage_index)
    records = [json.loads(line) for line in rollout.read_text(encoding="utf-8").splitlines() if line.strip()]
    user_text = ""
    final_text = ""
    calls = {}
    outputs = {}
    prompt_seen = False
    for record in records:
        payload = record.get("payload", {})
        if record.get("type") == "response_item" and payload.get("type") == "message":
            text = "".join(item.get("text", "") for item in payload.get("content", []))
            if payload.get("role") == "user" and args.execution_id in text:
                user_text = text
            elif payload.get("role") == "assistant" and text:
                final_text = text
        elif record.get("type") == "response_item" and payload.get("type") in {"custom_tool_call", "function_call"}:
            raw_input = payload.get("input", payload.get("arguments", ""))
            input_text = str(raw_input)
            if "prompt-stage-" in input_text:
                prompt_seen = True
            calls[payload.get("call_id")] = {"input": input_text, "after_prompt": prompt_seen}
        elif record.get("type") == "response_item" and payload.get("type") in {"custom_tool_call_output", "function_call_output"}:
            outputs[payload.get("call_id")] = json.dumps(payload.get("output", ""), ensure_ascii=False)
    if not user_text or not final_text:
        raise ValueError("rollout lacks the execution prompt or final answer")
    task_calls = []
    memory_query_calls = []
    context_text = task_prompt(user_text) + final_text
    for call_id, call in calls.items():
        input_text = call["input"]
        if is_bootstrap(input_text):
            continue
        if not call["after_prompt"]:
            continue
        task_calls.append(call_id)
        lowered = input_text.lower()
        if any(name in lowered for name in ("memory-recall", "memory-search", "episode-search", "projection-rebuild")):
            memory_query_calls.append(call_id)
        context_text += input_text + outputs.get(call_id, "")
    telemetry = {
        "schema_version": "weilan_agent_execution_telemetry_v0.1",
        "execution_id": args.execution_id,
        "rollout_file": str(rollout),
        "session_id": rollout.stem.rsplit("-", 1)[-1],
        "task_tool_calls": len(task_calls),
        "bootstrap_tool_calls": len(calls) - len(task_calls),
        "memory_query_count": len(memory_query_calls),
        "task_context_tokens": math.ceil(len(context_text) / 4),
        "termination_status": "completed",
        "final_output_hash": hashlib.sha256(final_text.encode("utf-8")).hexdigest(),
        "rollout_hash": hashlib.sha256(rollout.read_bytes()).hexdigest(),
    }
    trial_root = Path(args.trial_root)
    controller = trial_root / "controller"
    controller.mkdir(parents=True, exist_ok=True)
    (controller / "agent-final.txt").write_text(final_text, encoding="utf-8")
    (trial_root / "final.txt").write_text(final_text, encoding="utf-8")
    (trial_root / "telemetry.json").write_text(
        json.dumps({
            "tool_calls": telemetry["task_tool_calls"],
            "context_tokens": telemetry["task_context_tokens"],
            "pytest_exit_code": 0 if "pass" in final_text.lower() else None,
            **telemetry,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(telemetry, indent=2))


if __name__ == "__main__":
    main()
