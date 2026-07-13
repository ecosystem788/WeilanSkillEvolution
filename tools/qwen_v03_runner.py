"""Qwen/OpenAI-compatible execution surface for fusion-dogfood-v0.3.

This module is intentionally key-free. Live runs read credentials only from
environment variables; tests use an injected fake client.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fusion_dogfood_v03_harness import (
    APPEND_ONLY_FORBIDDEN_MARKERS,
    Budget,
    HARNESS_SCHEMA_VERSION,
    METHOD_BOOTSTRAP_MARKERS,
    METHOD_RUNTIME_MARKERS,
    SUITE_ID,
    receipt_hash,
    sha256_text,
    validate_arm_purity,
    write_json,
)


QWEN_RUNNER_SCHEMA_VERSION = "fusion_dogfood_v03_qwen_runner_v0.1"
RUNNER_ID = "qwen-openai-compatible-v0.1"
DEFAULT_BASE_URL_ENV = "QWEN_BASE_URL"
DEFAULT_API_KEY_ENV = "QWEN_API_KEY"
DEFAULT_MODEL_ENV = "QWEN_MODEL_SNAPSHOT"
DEFAULT_WEILAN_TRACE_PATH = r"D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py"
ALLOWED_ARMS = {"no-method", "append-only", "method-baseline"}
API_SURFACE_INSTRUCTION = (
    "Qwen API execution surface instructions:\n"
    "- You cannot write local files directly. The runner will persist your final receipt.\n"
    "- When you have enough public evidence, stop calling tools and return only one machine-readable JSON object.\n"
    "- Do not fabricate token counts, hashes, file contents, or tool results; use null or an empty object when a value is not observable.\n"
    "- If the task asks you to choose among option rows, set the receipt decision field to the selected option_id.\n"
    "- The JSON object must be the trial receipt requested by the task. Do not wrap it in Markdown.\n"
)
FORCED_FINAL_INSTRUCTION = (
    "Tool window is now closed by the runner. Return the requested trial receipt as one JSON object only. "
    "Use only evidence already visible in this conversation."
)


@dataclass(frozen=True)
class QwenRunnerConfig:
    model_snapshot: str
    base_url_env: str = DEFAULT_BASE_URL_ENV
    api_key_env: str = DEFAULT_API_KEY_ENV
    weilan_trace_path: str = DEFAULT_WEILAN_TRACE_PATH
    temperature: float = 0.0
    max_model_responses: int = 8
    force_final_after_tool_calls: int | None = None

    def validate(self) -> None:
        if not self.model_snapshot or self.model_snapshot.startswith(("qwen-latest", "latest")):
            raise ValueError("Qwen model_snapshot must be a pinned dated/snapshot id, not a floating alias")
        if self.max_model_responses < 1:
            raise ValueError("max_model_responses must be positive")
        if not self.weilan_trace_path:
            raise ValueError("weilan_trace_path must be pinned")
        if self.force_final_after_tool_calls is not None and self.force_final_after_tool_calls < 0:
            raise ValueError("force_final_after_tool_calls must be non-negative when set")


class OpenAICompatibleClient:
    def __init__(self, *, base_url: str, api_key: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_env(cls, *, base_url_env: str = DEFAULT_BASE_URL_ENV, api_key_env: str = DEFAULT_API_KEY_ENV):
        base_url = os.environ.get(base_url_env)
        api_key = os.environ.get(api_key_env)
        if not base_url:
            raise RuntimeError(f"{base_url_env} is required for live Qwen runs")
        if not api_key:
            raise RuntimeError(f"{api_key_env} is required for live Qwen runs")
        return cls(base_url=base_url, api_key=api_key)

    def create_chat_completion(self, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Qwen API HTTP {exc.code}: {detail[:500]}") from exc


def qwen_arm_config(arm: str) -> dict:
    if arm not in ALLOWED_ARMS:
        raise ValueError(f"unknown arm {arm}")
    configs = {
        "no-method": {
            "tools": ["read_file"],
            "method_runtime": False,
            "append_only_notes": False,
            "run_command": False,
            "bootstrap": "none",
        },
        "append-only": {
            "tools": ["read_file", "append_note", "retrieve_notes"],
            "method_runtime": False,
            "append_only_notes": True,
            "run_command": False,
            "bootstrap": "append-only retrieval only; no consolidation, supersession, or collapse",
        },
        "method-baseline": {
            "tools": ["read_file", "run_command", "append_note", "retrieve_notes"],
            "method_runtime": True,
            "append_only_notes": False,
            "run_command": True,
            "bootstrap": "full method-baseline instructions supplied by prompt and workspace fixture",
        },
    }
    return configs[arm]


def qwen_tool_definitions(arm: str) -> list[dict]:
    config = qwen_arm_config(arm)
    definitions = {
        "read_file": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file under the public fixture root.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        "run_command": {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Invoke only the pinned WeiLan trace runtime with structured argv inside the isolated method home.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Arguments passed after the pinned weilan_trace.py path. Do not include python or a script path.",
                        }
                    },
                    "required": ["args"],
                    "additionalProperties": False,
                },
            },
        },
        "append_note": {
            "type": "function",
            "function": {
                "name": "append_note",
                "description": "Append an observation to the arm-local note store.",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            },
        },
        "retrieve_notes": {
            "type": "function",
            "function": {
                "name": "retrieve_notes",
                "description": "Retrieve arm-local notes by case-insensitive lexical overlap.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
    }
    return [definitions[name] for name in config["tools"]]


def safe_child(root: Path, relative: str) -> Path:
    root = root.resolve()
    raw = Path(relative)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("path escapes fixture root")
    return candidate


def marker_hits(text: str, markers: list[str], *, source: str) -> list[dict]:
    lowered = text.lower()
    hits = []
    for marker in markers:
        marker_lower = marker.lower()
        if marker_lower not in lowered:
            continue
        negated = any(
            phrase in lowered
            for phrase in [
                f"do not use {marker_lower}",
                f"must not use {marker_lower}",
                f"without {marker_lower}",
                f"no {marker_lower}",
            ]
        )
        if not negated:
            hits.append({"marker": marker, "source": source})
    return hits


def message_fingerprints(messages: list[dict]) -> list[dict]:
    rows = []
    markers = sorted(set(METHOD_BOOTSTRAP_MARKERS + METHOD_RUNTIME_MARKERS + APPEND_ONLY_FORBIDDEN_MARKERS))
    for index, message in enumerate(messages):
        text = json.dumps(message, ensure_ascii=False, sort_keys=True)
        hits = marker_hits(text, markers, source=f"message:{index}")
        rows.append({
            "index": index,
            "role": message.get("role"),
            "sha256": sha256_text(text),
            "marker_hits": hits,
        })
    return rows


def execute_tool(
    name: str,
    arguments: dict,
    *,
    fixture_root: Path,
    workspace_root: Path,
    notes_path: Path,
    arm: str,
    method_home: Path,
    weilan_trace_path: Path,
) -> dict:
    allowed = set(qwen_arm_config(arm)["tools"])
    if name not in allowed:
        raise ValueError(f"tool {name} is not allowed for arm {arm}")
    if name == "read_file":
        path = safe_child(fixture_root, str(arguments.get("path", "")))
        return {"ok": True, "content": path.read_text(encoding="utf-8-sig", errors="replace")}
    if name == "run_command":
        args = arguments.get("args")
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            raise ValueError("run_command accepts only args: string[] for the pinned weilan_trace.py runtime")
        if any(item.lower().endswith(".py") or item.lower() in {"python", "py", "powershell", "cmd"} for item in args):
            raise ValueError("run_command args must not include an interpreter or script path")
        resolved_trace = Path(weilan_trace_path).resolve()
        method_home = Path(method_home).resolve()
        method_home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("QWEN_"):
                env.pop(key, None)
        env["WEILAN_METHOD_HOME"] = str(method_home)
        env["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [os.sys.executable, str(resolved_trace), *args],
            cwd=str(workspace_root),
            text=True,
            capture_output=True,
            timeout=10,
            env=env,
        )
        return {
            "ok": completed.returncode == 0,
            "runtime": "pinned_weilan_trace",
            "weilan_trace_path_sha256": sha256_text(str(resolved_trace)),
            "method_home": str(method_home),
            "args": args,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-2000:],
        }
    if name == "append_note":
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        note = {"text": str(arguments.get("text", "")), "ordinal": 1}
        existing = []
        if notes_path.exists():
            existing = [json.loads(line) for line in notes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            note["ordinal"] = len(existing) + 1
        with notes_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(note, ensure_ascii=False) + "\n")
        return {"ok": True, "ordinal": note["ordinal"]}
    if name == "retrieve_notes":
        query_terms = {part.lower() for part in str(arguments.get("query", "")).split() if part}
        rows = []
        if notes_path.exists():
            rows = [json.loads(line) for line in notes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        scored = []
        for row in rows:
            text = row.get("text", "")
            score = sum(1 for term in query_terms if term in text.lower())
            if score:
                scored.append({"score": score, **row})
        return {"ok": True, "notes": sorted(scored, key=lambda row: (-row["score"], row["ordinal"]))[:5]}
    raise AssertionError(f"unhandled tool {name}")


def public_fixture_index(fixture_root: Path, *, limit: int = 200) -> str:
    paths = []
    for path in sorted(Path(fixture_root).rglob("*")):
        if path.is_file():
            paths.append(path.relative_to(fixture_root).as_posix())
        if len(paths) >= limit:
            break
    return "\n".join(paths)


def extract_message(response: dict) -> dict:
    choices = response.get("choices") or []
    if not choices:
        return {"role": "assistant", "content": ""}
    return choices[0].get("message") or {}


def response_usage(response: dict) -> dict:
    usage = response.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def parse_tool_arguments(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    return json.loads(raw)


def run_qwen_trial(
    *,
    client: Any,
    config: QwenRunnerConfig,
    arm: str,
    budget: Budget,
    prompt: str,
    fixture_root: Path,
    workspace_root: Path,
    output_path: Path | None = None,
) -> dict:
    config.validate()
    if arm not in ALLOWED_ARMS:
        raise ValueError(f"unknown arm {arm}")
    fixture_root = Path(fixture_root)
    workspace_root = Path(workspace_root)
    notes_path = workspace_root / "arm-notes" / f"{arm}.jsonl"
    method_home = workspace_root / "method-home"
    weilan_trace_path = Path(config.weilan_trace_path)
    workspace_root.mkdir(parents=True, exist_ok=True)
    fixture_index = public_fixture_index(fixture_root)
    messages = [{
        "role": "user",
        "content": f"{API_SURFACE_INSTRUCTION}\nPUBLIC_FIXTURE_FILE_INDEX:\n{fixture_index}\n\n{prompt}",
    }]
    telemetry_events: list[dict] = []
    tool_events: list[dict] = []
    response_count = 0
    final_text = ""
    tool_calls_attempted = 0
    peak_context_tokens = 0
    billable_total_tokens = 0
    prompt_tokens_total = 0
    completion_tokens_total = 0
    truncated = False
    truncation_reason: str | None = None
    started = time.time()
    forced_final_requested = False

    while response_count < config.max_model_responses and not truncated:
        finalization_threshold_reached = (
            config.force_final_after_tool_calls is not None
            and tool_calls_attempted >= config.force_final_after_tool_calls
        )
        if finalization_threshold_reached and not forced_final_requested:
            messages.append({"role": "user", "content": FORCED_FINAL_INSTRUCTION})
            forced_final_requested = True
        payload = {
            "model": config.model_snapshot,
            "messages": messages,
            "temperature": config.temperature,
        }
        if finalization_threshold_reached:
            payload["tool_choice"] = "none"
        else:
            payload["tools"] = qwen_tool_definitions(arm)
            payload["tool_choice"] = "auto"
        response = client.create_chat_completion(payload)
        response_count += 1
        usage = response_usage(response)
        peak_context_tokens = max(peak_context_tokens, usage["total_tokens"])
        billable_total_tokens += usage["total_tokens"]
        prompt_tokens_total += usage["prompt_tokens"]
        completion_tokens_total += usage["completion_tokens"]
        if peak_context_tokens > budget.context_tokens:
            truncated = True
            truncation_reason = "context_tokens"
            telemetry_events.append({"type": "response", "response_index": response_count, "usage": usage, "truncated_after_response": True})
            break
        message = extract_message(response)
        telemetry_events.append({"type": "response", "response_index": response_count, "usage": usage, "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason")})
        messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            final_text = message.get("content") or ""
            break
        for call in tool_calls:
            function = call.get("function") or {}
            name = function.get("name")
            arguments = {}
            try:
                if (
                    config.force_final_after_tool_calls is not None
                    and tool_calls_attempted >= config.force_final_after_tool_calls
                ):
                    tool_events.append({"type": "tool_window_closed", "name": name, "call_id": call.get("id")})
                    break
                tool_calls_attempted += 1
                if tool_calls_attempted > budget.tool_calls:
                    truncated = True
                    truncation_reason = "tool_calls"
                    tool_events.append({"type": "tool_budget_truncated", "name": name, "call_id": call.get("id")})
                    break
                arguments = parse_tool_arguments(function.get("arguments"))
                result = execute_tool(
                    name,
                    arguments,
                    fixture_root=fixture_root,
                    workspace_root=workspace_root,
                    notes_path=notes_path,
                    arm=arm,
                    method_home=method_home,
                    weilan_trace_path=weilan_trace_path,
                )
            except Exception as exc:  # tool errors are observable trial events
                result = {"ok": False, "error": str(exc)}
            event = {
                "type": "tool_result",
                "name": name,
                "call_id": call.get("id"),
                "arguments": arguments,
                "result": result,
            }
            tool_events.append(event)
            messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(result, ensure_ascii=False)})
        if truncated:
            break

    message_events = message_fingerprints(messages)
    trace = parse_qwen_telemetry({
        "schema_version": QWEN_RUNNER_SCHEMA_VERSION,
        "surface": "qwen_openai_compatible",
        "runner_id": RUNNER_ID,
        "model_snapshot": config.model_snapshot,
        "environment_id": f"qwen-api:{config.model_snapshot}",
        "arm": arm,
        "arm_config": qwen_arm_config(arm),
        "budget": budget.accounting_policy() | {"tool_calls": budget.tool_calls, "context_tokens": budget.context_tokens},
        "events": telemetry_events,
        "message_events": message_events,
        "tool_events": tool_events,
        "actual_usage": {
            "tool_calls": tool_calls_attempted,
            "context_tokens": peak_context_tokens,
            "billable_total_tokens": billable_total_tokens,
            "prompt_tokens": prompt_tokens_total,
            "completion_tokens": completion_tokens_total,
            "truncated": truncated,
            "truncation_reason": truncation_reason,
            "budget_accounting": budget.accounting_policy(),
            "forced_finalization": {
                "enabled": config.force_final_after_tool_calls is not None,
                "threshold_tool_calls": config.force_final_after_tool_calls,
                "requested": forced_final_requested,
            },
        },
        "final_text": final_text,
        "elapsed_ms": int((time.time() - started) * 1000),
        "hidden_artifacts_read": False,
    })
    trace["arm_purity"] = validate_arm_purity(arm, trace)
    trace["telemetry_hash"] = receipt_hash(trace)
    if output_path:
        write_json(Path(output_path), trace)
    return trace


def parse_qwen_telemetry(record: dict, budget: Budget | None = None) -> dict:
    tool_events = record.get("tool_events") or []
    message_events = record.get("message_events") or []
    response_events = [event for event in record.get("events", []) if event.get("type") == "response"]
    response_total_tokens = [int((event.get("usage") or {}).get("total_tokens") or 0) for event in response_events]
    peak_context_tokens = max(response_total_tokens or [0])
    billable_total_tokens = sum(response_total_tokens)
    prompt_tokens = sum(int((event.get("usage") or {}).get("prompt_tokens") or 0) for event in response_events)
    completion_tokens = sum(int((event.get("usage") or {}).get("completion_tokens") or 0) for event in response_events)
    tool_call_count = len([event for event in tool_events if event.get("type") == "tool_result"])
    attempted_tool_calls = tool_call_count + len([event for event in tool_events if event.get("type") == "tool_budget_truncated"])
    effective_budget = budget or Budget(
        tool_calls=int(((record.get("budget") or {}).get("tool_calls")) or attempted_tool_calls),
        context_tokens=int(((record.get("budget") or {}).get("context_tokens")) or peak_context_tokens),
    )
    truncation_reason = None
    if attempted_tool_calls > effective_budget.tool_calls:
        truncation_reason = "tool_calls"
    if peak_context_tokens > effective_budget.context_tokens and truncation_reason is None:
        truncation_reason = "context_tokens"
    arm = record.get("arm")
    bootstrap_hits = [
        hit
        for event in message_events
        for hit in event.get("marker_hits", [])
        if hit.get("marker") in METHOD_BOOTSTRAP_MARKERS
    ]
    message_runtime_hits = [
        hit
        for event in message_events
        for hit in event.get("marker_hits", [])
        if hit.get("marker") in METHOD_RUNTIME_MARKERS
    ]
    tool_runtime_hits = [
        {"marker": "run_command", "source": f"tool_event:{index}"}
        for index, event in enumerate(tool_events)
        if event.get("name") == "run_command" and event.get("type") == "tool_result"
    ]
    method_runtime_hits = message_runtime_hits + tool_runtime_hits
    forbidden_names = {"run_command", "collapse", "supersede", "memory_consolidate", "memory-consolidate", "memory-disposition"}
    append_only_forbidden_hits = [
        {"marker": str(event.get("name")), "source": f"tool_event:{index}"}
        for index, event in enumerate(tool_events)
        if event.get("name") in forbidden_names and event.get("type") == "tool_result"
    ]
    append_only_forbidden_hits.extend([
        hit
        for event in message_events
        for hit in event.get("marker_hits", [])
        if hit.get("marker") in APPEND_ONLY_FORBIDDEN_MARKERS
    ])
    tool_event_summaries = []
    for index, event in enumerate(tool_events):
        if event.get("type") != "tool_result":
            continue
        result = event.get("result") or {}
        summary = {
            "index": index,
            "name": event.get("name"),
            "arguments": event.get("arguments") or {},
            "ok": result.get("ok"),
        }
        if "error" in result:
            summary["error"] = str(result.get("error"))[:300]
        if event.get("name") == "run_command":
            summary["runtime"] = result.get("runtime")
            summary["runtime_args"] = result.get("args")
            summary["stdout_sha256"] = sha256_text(str(result.get("stdout", "")))
            summary["stderr_sha256"] = sha256_text(str(result.get("stderr", "")))
        tool_event_summaries.append(summary)
    trace = {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "surface": "qwen_openai_compatible_telemetry",
        "runner_id": record.get("runner_id", RUNNER_ID),
        "environment_ids": [record.get("environment_id") or f"qwen-api:{record.get('model_snapshot')}"],
        "model_snapshot": record.get("model_snapshot"),
        "arm": arm,
        "tool_call_count": attempted_tool_calls,
        "executed_tool_call_count": tool_call_count,
        "tool_call_names": [event.get("name") for event in tool_events if event.get("type") == "tool_result"],
        "tool_event_summaries": tool_event_summaries[:50],
        "context_token_count": peak_context_tokens,
        "context_token_rule": "peak_single_response_total_tokens",
        "billable_total_tokens": billable_total_tokens,
        "prompt_token_count": prompt_tokens,
        "completion_token_count": completion_tokens,
        "ordered_event_stream": True,
        "arm_purity_observables": {
            "method_runtime_operation_count": len(method_runtime_hits),
            "method_runtime_hits": method_runtime_hits[:25],
            "workspace_method_bootstrap_count": len(bootstrap_hits),
            "workspace_method_bootstrap_hits": bootstrap_hits[:25],
            "append_only_forbidden_operation_count": len(append_only_forbidden_hits),
            "append_only_forbidden_hits": append_only_forbidden_hits[:25],
        },
        "actual_usage": {
            "tool_calls": attempted_tool_calls,
            "executed_tool_calls": tool_call_count,
            "context_tokens": peak_context_tokens,
            "context_token_rule": "peak_single_response_total_tokens",
            "billable_total_tokens": billable_total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "truncated": truncation_reason is not None or bool((record.get("actual_usage") or {}).get("truncated")),
            "truncation_reason": truncation_reason or (record.get("actual_usage") or {}).get("truncation_reason"),
            "budget_accounting": effective_budget.accounting_policy(),
            "forced_finalization": (record.get("actual_usage") or {}).get("forced_finalization", {
                "enabled": False,
                "threshold_tool_calls": None,
                "requested": False,
            }),
            "scoring_time_truncation": {
                "truncated": truncation_reason is not None,
                "truncation_reason": truncation_reason,
                "policy": "live_truncation_with_scoring_time_replay",
                "effective_tool_calls": min(attempted_tool_calls, effective_budget.tool_calls),
                "effective_context_tokens": min(peak_context_tokens, effective_budget.context_tokens),
            },
        },
        "final_text": record.get("final_text", ""),
        "hidden_artifacts_read": False,
    }
    return trace


class FakeOpenAICompatibleClient:
    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def create_chat_completion(self, payload: dict) -> dict:
        self.requests.append(payload)
        if not self.responses:
            raise RuntimeError("fake client exhausted")
        return self.responses.pop(0)


def fake_response(content: str = "", *, total_tokens: int = 10, tool_calls: list[dict] | None = None) -> dict:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "choices": [{"message": message, "finish_reason": "tool_calls" if tool_calls else "stop"}],
        "usage": {"prompt_tokens": total_tokens // 2, "completion_tokens": total_tokens - total_tokens // 2, "total_tokens": total_tokens},
    }


def qwen_surface_self_test(output: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="fusion-v03-qwen-self-test-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        workspace = root / "workspace"
        fixture.mkdir()
        (fixture / "README.md").write_text("probe fixture\n", encoding="utf-8")
        budget_trace = run_qwen_trial(
            client=FakeOpenAICompatibleClient([fake_response("too many tokens", total_tokens=80)]),
            config=QwenRunnerConfig(model_snapshot="qwen-test-snapshot-20260706", max_model_responses=2),
            arm="no-method",
            budget=Budget(tool_calls=2, context_tokens=50),
            prompt="Return PROBE OK.",
            fixture_root=fixture,
            workspace_root=workspace / "budget",
        )
        read_call = {
            "id": "call-read-1",
            "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "README.md"})},
        }
        purity_trace = run_qwen_trial(
            client=FakeOpenAICompatibleClient([
                fake_response(tool_calls=[read_call], total_tokens=20),
                fake_response("PROBE OK", total_tokens=20),
            ]),
            config=QwenRunnerConfig(model_snapshot="qwen-test-snapshot-20260706", max_model_responses=3),
            arm="no-method",
            budget=Budget(tool_calls=2, context_tokens=100),
            prompt="Read README.md, then return PROBE OK.",
            fixture_root=fixture,
            workspace_root=workspace / "purity",
        )
        result = {
            "schema_version": QWEN_RUNNER_SCHEMA_VERSION,
            "suite_id": SUITE_ID,
            "record_type": "qwen_surface_self_test",
            "valid": budget_trace["actual_usage"]["truncated"] is True
            and budget_trace["actual_usage"]["truncation_reason"] == "context_tokens"
            and validate_arm_purity("no-method", purity_trace)["valid"] is True
            and purity_trace["tool_call_count"] == 1,
            "checks": {
                "budget_probe_truncated": budget_trace["actual_usage"]["truncated"],
                "budget_probe_reason": budget_trace["actual_usage"]["truncation_reason"],
                "no_method_arm_purity_valid": validate_arm_purity("no-method", purity_trace)["valid"],
                "read_file_tool_executed": purity_trace["tool_call_count"] == 1,
            },
            "runner_id": RUNNER_ID,
            "model_snapshot_for_test": "qwen-test-snapshot-20260706",
            "live_api_called": False,
            "api_key_read": False,
            "hidden_artifacts_read": False,
        }
        result["receipt_hash"] = receipt_hash(result)
        if output:
            write_json(output, result)
        return result


def build_live_config_from_env() -> QwenRunnerConfig:
    model = os.environ.get(DEFAULT_MODEL_ENV)
    if not model:
        raise RuntimeError(f"{DEFAULT_MODEL_ENV} must name a pinned Qwen snapshot before live trials")
    return QwenRunnerConfig(model_snapshot=model)


def json_object_from_text(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for block in re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise json.JSONDecodeError("no JSON object found", text, 0)


def write_receipt_from_final_text(
    final_text: str,
    receipt_path: Path,
    *,
    observed_actual_usage: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    receipt_path = Path(receipt_path)
    try:
        receipt = json_object_from_text(final_text)
    except json.JSONDecodeError:
        receipt = {
            "parse_error": "final_text_not_json",
            "raw_final_text": final_text,
        }
    if "parse_error" not in receipt:
        if metadata:
            receipt.update({key: value for key, value in metadata.items() if value is not None})
        if observed_actual_usage is not None:
            if "actual_usage" in receipt:
                receipt["actual_usage_self_report"] = receipt["actual_usage"]
            receipt["actual_usage"] = observed_actual_usage
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def live_preflight(output: Path) -> dict:
    config = build_live_config_from_env()
    client = OpenAICompatibleClient.from_env()
    with tempfile.TemporaryDirectory(prefix="fusion-v03-qwen-live-preflight-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "README.md").write_text("Live preflight fixture.\n", encoding="utf-8")
        result = run_qwen_trial(
            client=client,
            config=config,
            arm="no-method",
            budget=Budget(tool_calls=1, context_tokens=2048),
            prompt="Return exactly: PROBE OK",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )
    result["record_type"] = "qwen_live_preflight"
    result["live_api_called"] = True
    result["api_key_persisted"] = False
    result["valid"] = result.get("final_text", "").strip() == "PROBE OK" and result["arm_purity"]["valid"] is True
    result["telemetry_hash"] = receipt_hash(result)
    write_json(output, result)
    return result


def live_budget_probe(output: Path) -> dict:
    config = build_live_config_from_env()
    client = OpenAICompatibleClient.from_env()
    with tempfile.TemporaryDirectory(prefix="fusion-v03-qwen-live-budget-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "README.md").write_text("Live budget probe fixture.\n", encoding="utf-8")
        result = run_qwen_trial(
            client=client,
            config=config,
            arm="no-method",
            budget=Budget(tool_calls=1, context_tokens=1),
            prompt="Return exactly: BUDGET PROBE OK",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )
    result["record_type"] = "qwen_live_budget_probe"
    result["live_api_called"] = True
    result["api_key_persisted"] = False
    result["budget_probe_passed"] = result["actual_usage"]["truncated"] is True and result["actual_usage"]["truncation_reason"] == "context_tokens"
    result["valid"] = result["budget_probe_passed"] and result["arm_purity"]["valid"] is True
    result["telemetry_hash"] = receipt_hash(result)
    write_json(output, result)
    return result


def run_trial_from_paths(
    *,
    arm: str,
    prompt_path: Path,
    fixture_root: Path,
    workspace_root: Path,
    output_path: Path,
    receipt_output: Path | None,
    tool_calls: int,
    context_tokens: int,
    max_model_responses: int | None = None,
    force_final_after_tool_calls: int | None = None,
) -> dict:
    config = build_live_config_from_env()
    if max_model_responses is not None:
        config = QwenRunnerConfig(
            model_snapshot=config.model_snapshot,
            base_url_env=config.base_url_env,
            api_key_env=config.api_key_env,
            weilan_trace_path=config.weilan_trace_path,
            temperature=config.temperature,
            max_model_responses=max_model_responses,
            force_final_after_tool_calls=config.force_final_after_tool_calls,
        )
    if force_final_after_tool_calls is not None:
        config = QwenRunnerConfig(
            model_snapshot=config.model_snapshot,
            base_url_env=config.base_url_env,
            api_key_env=config.api_key_env,
            weilan_trace_path=config.weilan_trace_path,
            temperature=config.temperature,
            max_model_responses=config.max_model_responses,
            force_final_after_tool_calls=force_final_after_tool_calls,
        )
    client = OpenAICompatibleClient.from_env()
    prompt = Path(prompt_path).read_text(encoding="utf-8")
    trace = run_qwen_trial(
        client=client,
        config=config,
        arm=arm,
        budget=Budget(tool_calls=tool_calls, context_tokens=context_tokens),
        prompt=prompt,
        fixture_root=Path(fixture_root),
        workspace_root=Path(workspace_root),
        output_path=Path(output_path),
    )
    if receipt_output:
        trial_id = Path(prompt_path).parents[1].name if Path(prompt_path).parent.name == "controller" else Path(workspace_root).name
        trial_number = None
        if trial_id.rsplit("-", 1)[-1].isdigit():
            trial_number = int(trial_id.rsplit("-", 1)[-1])
        receipt = write_receipt_from_final_text(
            trace.get("final_text", ""),
            Path(receipt_output),
            observed_actual_usage=trace.get("actual_usage"),
            metadata={"trial_id": trial_id, "arm": arm, "trial": trial_number},
        )
        trace["receipt_output"] = str(receipt_output)
        trace["receipt_output_hash"] = sha256_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        trace["valid"] = "parse_error" not in receipt and bool(trace.get("final_text", "").strip())
        trace["telemetry_hash"] = receipt_hash(trace)
        write_json(Path(output_path), trace)
    else:
        trace["valid"] = True
    return trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    self_test_parser = subparsers.add_parser("self-test")
    self_test_parser.add_argument("--output")
    live_preflight_parser = subparsers.add_parser("live-preflight")
    live_preflight_parser.add_argument("--output", required=True)
    live_budget_parser = subparsers.add_parser("live-budget-probe")
    live_budget_parser.add_argument("--output", required=True)
    run_trial_parser = subparsers.add_parser("run-trial")
    run_trial_parser.add_argument("--arm", required=True, choices=sorted(ALLOWED_ARMS))
    run_trial_parser.add_argument("--prompt-path", required=True)
    run_trial_parser.add_argument("--fixture-root", required=True)
    run_trial_parser.add_argument("--workspace-root", required=True)
    run_trial_parser.add_argument("--output", required=True)
    run_trial_parser.add_argument("--receipt-output")
    run_trial_parser.add_argument("--tool-calls", type=int, default=5)
    run_trial_parser.add_argument("--context-tokens", type=int, default=4800)
    run_trial_parser.add_argument("--max-model-responses", type=int)
    run_trial_parser.add_argument("--force-final-after-tool-calls", type=int)
    args = parser.parse_args(argv)
    if args.command in {None, "self-test"}:
        result = qwen_surface_self_test(Path(args.output) if args.output else None)
    elif args.command == "live-preflight":
        result = live_preflight(Path(args.output))
    elif args.command == "live-budget-probe":
        result = live_budget_probe(Path(args.output))
    elif args.command == "run-trial":
        result = run_trial_from_paths(
            arm=args.arm,
            prompt_path=Path(args.prompt_path),
            fixture_root=Path(args.fixture_root),
            workspace_root=Path(args.workspace_root),
            output_path=Path(args.output),
            receipt_output=Path(args.receipt_output) if args.receipt_output else None,
            tool_calls=args.tool_calls,
            context_tokens=args.context_tokens,
            max_model_responses=args.max_model_responses,
            force_final_after_tool_calls=args.force_final_after_tool_calls,
        )
    else:
        raise AssertionError(f"unhandled command {args.command}")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
