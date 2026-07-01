"""Extract observable task telemetry from one Codex subagent rollout."""

import argparse
import hashlib
import json
import math
from pathlib import Path


def is_bootstrap(input_text):
    lowered = input_text.lower()
    reads_bundle = "method-bundle" in lowered and any(
        marker in lowered for marker in ("get-content", "read", "skill.md", "references\\")
    )
    touches_task = "\\public" in lowered or "method-state" in lowered
    return reads_bundle and not touches_task


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


def find_rollout(session_root, execution_id):
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
            has_prompt |= payload.get("role") == "user" and execution_id in text
            has_final |= payload.get("role") == "assistant" and bool(text)
        if has_prompt and has_final:
            viable.append(path)
    if not viable:
        raise ValueError(f"no completed rollout contains {execution_id}")
    return max(viable, key=lambda item: item.stat().st_mtime_ns)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--session-root", required=True)
    parser.add_argument("--trial-root", required=True)
    args = parser.parse_args()
    rollout = find_rollout(args.session_root, args.execution_id)
    records = [json.loads(line) for line in rollout.read_text(encoding="utf-8").splitlines() if line.strip()]
    user_text = ""
    final_text = ""
    calls = {}
    outputs = {}
    for record in records:
        payload = record.get("payload", {})
        if record.get("type") == "response_item" and payload.get("type") == "message":
            text = "".join(item.get("text", "") for item in payload.get("content", []))
            if payload.get("role") == "user" and args.execution_id in text:
                user_text = text
            elif payload.get("role") == "assistant" and text:
                final_text = text
        elif record.get("type") == "response_item" and payload.get("type") == "custom_tool_call":
            calls[payload.get("call_id")] = str(payload.get("input", ""))
        elif record.get("type") == "response_item" and payload.get("type") == "custom_tool_call_output":
            outputs[payload.get("call_id")] = json.dumps(payload.get("output", ""), ensure_ascii=False)
    if not user_text or not final_text:
        raise ValueError("rollout lacks the execution prompt or final answer")
    task_calls = []
    context_text = task_prompt(user_text) + final_text
    for call_id, input_text in calls.items():
        if is_bootstrap(input_text):
            continue
        task_calls.append(call_id)
        context_text += input_text + outputs.get(call_id, "")
    telemetry = {
        "schema_version": "weilan_agent_execution_telemetry_v0.1",
        "execution_id": args.execution_id,
        "rollout_file": str(rollout),
        "session_id": rollout.stem.rsplit("-", 1)[-1],
        "task_tool_calls": len(task_calls),
        "bootstrap_tool_calls": len(calls) - len(task_calls),
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
