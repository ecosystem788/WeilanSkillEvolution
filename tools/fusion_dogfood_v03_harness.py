"""Deterministic harness primitives for fusion-dogfood-v0.3 step-2 capability tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


HARNESS_SCHEMA_VERSION = "fusion_dogfood_v03_harness_v0.1"
CASE_FLOW_SCHEMA_VERSION = "fusion_dogfood_v03_case_flow_v0.1"
CALIBRATION_SCHEMA_VERSION = "fusion_dogfood_v03_calibration_v0.1"
SUITE_ID = "fusion-dogfood-v0.3"
APPEND_ONLY_CONTROL_ID = "append-only-memory-retrieval-v0.1"
DEPLOYED_BASELINE_HASH = "2c539d0b9444a395e66ce4ddaad1412f0ea5c4f0541112f63d3365c65d2bcf4f"
ROOT = Path(__file__).resolve().parents[1]


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_snapshot(root: Path) -> dict:
    root = Path(root)
    rows = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rows.append({
                    "path": path.relative_to(root).as_posix(),
                    "sha256": file_sha256(path),
                    "size": path.stat().st_size,
                })
    return {
        "root": str(root),
        "files": rows,
        "tree_hash": sha256_text(canonical_json(rows)),
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def receipt_hash(value: dict) -> str:
    copy = dict(value)
    copy.pop("receipt_hash", None)
    return sha256_text(canonical_json(copy))


CODEX_DESKTOP_TOOL_CALL_TYPES = {"function_call", "custom_tool_call", "tool_search_call"}
METHOD_BOOTSTRAP_MARKERS = [
    "AGENTS.md instructions",
    "CLAUDE.md",
    "Use `$solve-with-weilan`",
    "memory-recall --workspace",
]
METHOD_RUNTIME_MARKERS = [
    "weilan_trace.py",
    "solve-with-weilan",
    "WEILAN_METHOD_HOME",
    "memory-recall",
    "memory-consolidate",
    "memory-disposition",
    "lineage-show",
    "holder_selected",
    "minimal_unit_collapsed",
    "trace_emitted",
]
APPEND_ONLY_FORBIDDEN_MARKERS = [
    "memory-consolidate",
    "memory-disposition",
    "minimal_unit_collapsed",
    "trace_emitted",
    "supersession",
    "\"event_type\": \"collapse\"",
    "\"event_type\":\"collapse\"",
]


def rollout_environment_id(source) -> str | None:
    if isinstance(source, dict) and source.get("subagent"):
        return "codex-desktop:subagent"
    if isinstance(source, str):
        normalized = source.lower()
        if normalized in {"exec", "codex-exec", "codex_exec"}:
            return "codex-cli:exec"
        return f"codex-desktop:{source}"
    return None


def parse_codex_desktop_rollout_trace(path: Path, budget: Budget | None = None) -> dict:
    """Parse a Codex Desktop rollout JSONL into auditable R3 telemetry."""
    path = Path(path)
    tool_call_count = 0
    max_total_tokens = 0
    max_last_tokens = 0
    token_count_events = 0
    task_complete_seen = False
    context_compacted_seen = False
    turn_ids: set[str] = set()
    tool_names: list[str] = []
    cli_versions: set[str] = set()
    environment_ids: set[str] = set()
    method_runtime_hits: list[dict] = []
    workspace_bootstrap_hits: list[dict] = []
    append_only_forbidden_hits: list[dict] = []
    truncation = {
        "truncated": False,
        "truncation_reason": None,
        "truncated_at_line": None,
        "policy": "scoring_time_truncation",
    }

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            payload = item.get("payload") or {}
            payload_type = payload.get("type")
            payload_text = json.dumps(payload, ensure_ascii=False)
            payload_text_lower = payload_text.lower()
            for marker in METHOD_BOOTSTRAP_MARKERS:
                if payload_type == "message" and marker.lower() in payload_text_lower:
                    workspace_bootstrap_hits.append({"line": line_number, "marker": marker, "payload_type": payload_type})
            runtime_payload = payload_type in CODEX_DESKTOP_TOOL_CALL_TYPES or payload_type in {"function_call_output", "custom_tool_call_output", "tool_search_output"}
            for marker in METHOD_RUNTIME_MARKERS:
                if runtime_payload and marker.lower() in payload_text_lower:
                    method_runtime_hits.append({"line": line_number, "marker": marker, "payload_type": payload_type})
            for marker in APPEND_ONLY_FORBIDDEN_MARKERS:
                if runtime_payload and marker.lower() in payload_text_lower:
                    append_only_forbidden_hits.append({"line": line_number, "marker": marker, "payload_type": payload_type})

            if item.get("type") == "session_meta":
                if payload.get("cli_version"):
                    cli_versions.add(payload["cli_version"])
                environment_id = rollout_environment_id(payload.get("source"))
                if environment_id:
                    environment_ids.add(environment_id)

            turn_id = payload.get("turn_id")
            if turn_id:
                turn_ids.add(turn_id)

            if payload_type in CODEX_DESKTOP_TOOL_CALL_TYPES:
                tool_call_count += 1
                name = payload.get("name") or payload_type
                tool_names.append(name)
                if budget and not truncation["truncated"] and tool_call_count > budget.tool_calls:
                    truncation.update({
                        "truncated": True,
                        "truncation_reason": "tool_calls",
                        "truncated_at_line": line_number,
                    })

            if payload_type == "token_count":
                token_count_events += 1
                info = payload.get("info") or {}
                total_usage = info.get("total_token_usage") or {}
                last_usage = info.get("last_token_usage") or {}
                max_total_tokens = max(max_total_tokens, total_usage.get("total_tokens") or 0)
                max_last_tokens = max(max_last_tokens, last_usage.get("total_tokens") or 0)
                if budget and not truncation["truncated"] and max_total_tokens > budget.context_tokens:
                    truncation.update({
                        "truncated": True,
                        "truncation_reason": "context_tokens",
                        "truncated_at_line": line_number,
                    })

            if payload_type == "context_compacted":
                context_compacted_seen = True
            if payload_type == "task_complete":
                task_complete_seen = True

    actual_usage = {
        "tool_calls": tool_call_count,
        "context_tokens": max_total_tokens,
        "last_response_context_tokens": max_last_tokens,
        "token_count_events": token_count_events,
        "truncated": truncation["truncated"],
        "truncation_reason": truncation["truncation_reason"],
        "budget_accounting": budget.accounting_policy() if budget else None,
        "scoring_time_truncation": {
            **truncation,
            "effective_tool_calls": min(tool_call_count, budget.tool_calls) if budget else tool_call_count,
            "effective_context_tokens": min(max_total_tokens, budget.context_tokens) if budget else max_total_tokens,
        },
    }
    return {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "surface": "codex_desktop_rollout_jsonl",
        "rollout_path": str(path),
        "rollout_hash": file_sha256(path),
        "rollout_size_bytes": path.stat().st_size,
        "cli_versions": sorted(cli_versions),
        "environment_ids": sorted(environment_ids),
        "turn_ids": sorted(turn_ids),
        "tool_call_count": tool_call_count,
        "tool_call_names": tool_names,
        "context_token_count": max_total_tokens,
        "token_count_events": token_count_events,
        "task_complete_seen": task_complete_seen,
        "context_compacted_seen": context_compacted_seen,
        "ordered_event_stream": True,
        "arm_purity_observables": {
            "method_runtime_operation_count": len(method_runtime_hits),
            "method_runtime_hits": method_runtime_hits[:25],
            "workspace_method_bootstrap_count": len(workspace_bootstrap_hits),
            "workspace_method_bootstrap_hits": workspace_bootstrap_hits[:25],
            "append_only_forbidden_operation_count": len(append_only_forbidden_hits),
            "append_only_forbidden_hits": append_only_forbidden_hits[:25],
        },
        "actual_usage": actual_usage,
    }


def validate_arm_purity(arm: str, trace: dict) -> dict:
    observables = trace.get("arm_purity_observables", {})
    method_runtime_count = int(observables.get("method_runtime_operation_count") or 0)
    bootstrap_count = int(observables.get("workspace_method_bootstrap_count") or 0)
    append_only_forbidden_count = int(observables.get("append_only_forbidden_operation_count") or 0)
    issues: list[str] = []
    if arm == "no-method":
        if not observables:
            issues.append("arm_purity_telemetry_missing")
        if method_runtime_count:
            issues.append("no_method_used_method_runtime_operations")
        if bootstrap_count:
            issues.append("no_method_surface_contains_method_bootstrap")
    elif arm == "append-only":
        if not observables:
            issues.append("arm_purity_telemetry_missing")
        if append_only_forbidden_count:
            issues.append("append_only_used_consolidation_supersession_or_collapse")
    elif arm != "method-baseline":
        issues.append(f"unknown_arm:{arm}")
    return {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "arm": arm,
        "valid": not issues,
        "issues": issues,
        "observables": observables,
        "hidden_artifacts_read": False,
    }


def arm_purity_self_test() -> dict:
    clean_trace = {
        "arm_purity_observables": {
            "method_runtime_operation_count": 0,
            "workspace_method_bootstrap_count": 0,
            "append_only_forbidden_operation_count": 0,
        }
    }
    contaminated_no_method = {
        "arm_purity_observables": {
            "method_runtime_operation_count": 1,
            "workspace_method_bootstrap_count": 1,
            "append_only_forbidden_operation_count": 0,
        }
    }
    contaminated_append_only = {
        "arm_purity_observables": {
            "method_runtime_operation_count": 1,
            "workspace_method_bootstrap_count": 0,
            "append_only_forbidden_operation_count": 1,
        }
    }
    checks = {
        "clean_no_method_passes": validate_arm_purity("no-method", clean_trace)["valid"] is True,
        "contaminated_no_method_rejected": validate_arm_purity("no-method", contaminated_no_method)["valid"] is False,
        "clean_append_only_passes": validate_arm_purity("append-only", clean_trace)["valid"] is True,
        "contaminated_append_only_rejected": validate_arm_purity("append-only", contaminated_append_only)["valid"] is False,
    }
    return {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "arm_purity_self_test",
        "valid": all(checks.values()),
        "checks": checks,
        "hidden_artifacts_read": False,
    }


def validate_codex_desktop_rollout_surface(sessions_home: Path, sample_limit: int = 5) -> dict:
    sessions_home = Path(sessions_home)
    samples = []
    for path in sorted(sessions_home.rglob("*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)[:sample_limit]:
        try:
            trace = parse_codex_desktop_rollout_trace(path)
        except Exception as exc:  # pragma: no cover - defensive audit path
            samples.append({"path": str(path), "parse_error": str(exc), "valid": False})
            continue
        samples.append({
            "path": str(path),
            "rollout_hash": trace["rollout_hash"],
            "cli_versions": trace["cli_versions"],
            "environment_ids": trace["environment_ids"],
            "tool_call_count": trace["tool_call_count"],
            "context_token_count": trace["context_token_count"],
            "token_count_events": trace["token_count_events"],
            "ordered_event_stream": trace["ordered_event_stream"],
            "task_complete_seen": trace["task_complete_seen"],
            "valid": trace["tool_call_count"] > 0 and trace["context_token_count"] > 0 and trace["ordered_event_stream"],
        })
    has_tool_calls = any(sample.get("tool_call_count", 0) > 0 for sample in samples)
    has_token_usage = any(sample.get("context_token_count", 0) > 0 and sample.get("token_count_events", 0) > 0 for sample in samples)
    has_ordered_events = any(sample.get("ordered_event_stream") for sample in samples)
    result = {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "telemetry_surface_validation",
        "selected_surface": "codex_rollout_jsonl_family",
        "valid": has_tool_calls and has_token_usage and has_ordered_events,
        "selected": has_tool_calls and has_token_usage and has_ordered_events,
        "sessions_home": str(sessions_home),
        "environment_id": "codex-rollout-jsonl-v0.142.5",
        "enforcement": {
            "live_truncation_supported": False,
            "scoring_time_truncation_supported": has_ordered_events,
            "truncation_status_source": "computed_by_runner_from_budget_and_ordered_rollout_events",
        },
        "r3_required_telemetry": {
            "tool_call_count": has_tool_calls,
            "token_usage": has_token_usage,
            "truncation_status": has_ordered_events,
        },
        "same_surface_requirement": "All arms must use the same Codex rollout JSONL telemetry family, CLI version, budget accounting, and scoring-time truncation semantics; arm-specific home contents are part of the arm configuration and must be content-addressed.",
        "codex_exec_probe": {
            "status": "not_selected",
            "reason": "codex.exe is present under WindowsApps in this environment but direct shell execution returned Access is denied.",
        },
        "claude_headless_probe": {
            "status": "not_available",
            "reason": "claude executable was not found on PATH in this environment.",
        },
        "samples": samples,
        "hidden_artifacts_read": False,
    }
    result["validation_hash"] = receipt_hash(result)
    return result


def real_calibration_readiness(case_flow_root: Path) -> dict:
    case_flow_root = Path(case_flow_root)
    telemetry_path = case_flow_root / "calibration" / "telemetry-surface" / "codex-desktop-subagent-rollout.json"
    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8")) if telemetry_path.exists() else None
    case_rows = []
    for public_path in sorted((case_flow_root / "case-designs").glob("*.json")):
        public_design = json.loads(public_path.read_text(encoding="utf-8"))
        case_id = public_design["case_id"]
        hidden_path = case_flow_root / "hidden-side" / f"{case_id}.json"
        prereg_path = case_flow_root / "preregistrations" / f"{case_id}.json"
        fixture_root = case_flow_root / "fixtures" / case_id
        hidden = json.loads(hidden_path.read_text(encoding="utf-8")) if hidden_path.exists() else {}
        prereg = json.loads(prereg_path.read_text(encoding="utf-8")) if prereg_path.exists() else {}
        public_text = canonical_json(public_design.get("public_case_spec", {}))
        issues = []
        if any(marker in public_text for marker in ["success_criteria", "scoring_weights", "hidden_check_id"]):
            issues.append("public_case_spec_leaks_hidden_scoring_material")
        if not hidden.get("success_criteria") or not hidden.get("scoring_weights"):
            issues.append("hidden_scoring_contract_missing")
        if not hidden.get("winnable_walkthrough_hash"):
            issues.append("winnable_walkthrough_hash_missing")
        if not prereg.get("expected_method_baseline_mean_lt") == 0.8:
            issues.append("baseline_headroom_preregistration_missing")
        if not fixture_root.is_dir():
            issues.append("public_fixture_root_missing")
        case_rows.append({
            "case_id": case_id,
            "public_case_design": display_path(public_path),
            "hidden_side_contract": display_path(hidden_path),
            "preregistration": display_path(prereg_path),
            "fixture_root": display_path(fixture_root),
            "ready": not issues,
            "issues": issues,
        })
    telemetry_valid = bool(telemetry and telemetry.get("valid") and telemetry.get("selected"))
    issues = []
    if not telemetry_valid:
        issues.append("telemetry_surface_not_validated")
    if not case_rows:
        issues.append("no_case_designs_found")
    if any(not row["ready"] for row in case_rows):
        issues.append("one_or_more_cases_not_fixture_ready")
    result = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "real_calibration_preflight",
        "valid": not issues,
        "status": "ready_for_real_baseline_trials" if not issues else "blocked_before_execution",
        "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
        "telemetry_surface": {
            "valid": telemetry_valid,
            "selected_surface": telemetry.get("selected_surface") if telemetry else None,
            "environment_id": telemetry.get("environment_id") if telemetry else None,
            "validation_hash": telemetry.get("validation_hash") if telemetry else None,
        },
        "case_count": len(case_rows),
        "cases": case_rows,
        "issues": issues,
        "authorized_trial_count": 14,
        "trial_count_executed": 0,
        "hidden_artifacts_read": False,
    }
    result["preflight_hash"] = receipt_hash(result)
    return result


def write_real_calibration_block_from_preflight(case_flow_root: Path, preflight: dict) -> dict:
    case_flow_root = Path(case_flow_root)
    block = {
        "schema_version": "fusion_dogfood_v03_real_calibration_block_v0.2",
        "suite_id": SUITE_ID,
        "record_type": "real_calibration_blocked",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
        "authorization_source": "conversation:2026-07-05-user-authorized-v03-real-baseline-calibration",
        "status": "blocked_before_execution",
        "blocking_reason": "Real baseline calibration preflight failed. Do not execute the authorized 14 trials until every case has an entity fixture root, hidden scoring contract, preregistration, and validated telemetry surface.",
        "preflight_hash": preflight["preflight_hash"],
        "preflight_issues": preflight["issues"],
        "case_issues": [
            {"case_id": row["case_id"], "issues": row["issues"]}
            for row in preflight["cases"]
            if row["issues"]
        ],
        "telemetry_surface": preflight["telemetry_surface"],
        "trial_count_authorized": preflight["authorized_trial_count"],
        "trial_count_executed": 0,
        "r3_gate_position": "fail_closed",
        "not_a_case_verdict": True,
        "hidden_artifacts_read": False,
    }
    block["receipt_hash"] = receipt_hash(block)
    block_path = case_flow_root / "calibration" / f"real-baseline-{DEPLOYED_BASELINE_HASH[:8]}-20260705" / "BLOCKED_PREFLIGHT.json"
    write_json(block_path, block)
    plan_path = case_flow_root / "calibration" / "calibration-plan.draft.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["status"] = "blocked_before_real_baseline_trials"
        plan["real_calibration_block"] = display_path(block_path)
        for case in plan.get("cases", []):
            case["real_trial_status"] = "blocked_fixture_unavailable"
        write_json(plan_path, plan)
    return block


class BudgetExceeded(RuntimeError):
    def __init__(self, dimension: str, actual: int, limit: int):
        super().__init__(f"budget exceeded: {dimension} {actual}>{limit}")
        self.dimension = dimension
        self.actual = actual
        self.limit = limit


@dataclass(frozen=True)
class Budget:
    tool_calls: int
    context_tokens: int
    wall_clock_ms: int | None = None
    scope: str = "per_episode"
    setup_overhead_counted: bool = False
    method_state_operations_counted: bool = True
    retrieval_operations_counted: bool = True

    def validate(self) -> None:
        if self.tool_calls < 0 or self.context_tokens < 0:
            raise ValueError("tool_calls and context_tokens budgets must be non-negative")
        if self.wall_clock_ms is not None and self.wall_clock_ms < 0:
            raise ValueError("wall_clock_ms budget must be non-negative when present")
        if self.scope not in {"per_episode", "whole_case"}:
            raise ValueError("budget scope must be per_episode or whole_case")

    def accounting_policy(self) -> dict:
        self.validate()
        return {
            "scope": self.scope,
            "setup_overhead_counted": self.setup_overhead_counted,
            "method_state_operations_counted": self.method_state_operations_counted,
            "retrieval_operations_counted": self.retrieval_operations_counted,
        }


class BudgetMeter:
    def __init__(self, budget: Budget):
        budget.validate()
        self.budget = budget
        self.tool_calls = 0
        self.context_tokens = 0
        self.wall_clock_ms = 0
        self.truncated = False
        self.truncation_reason: str | None = None

    def consume(self, *, tool_calls: int = 0, context_tokens: int = 0, wall_clock_ms: int = 0) -> None:
        self.tool_calls += tool_calls
        self.context_tokens += context_tokens
        self.wall_clock_ms += wall_clock_ms
        checks = [
            ("tool_calls", self.tool_calls, self.budget.tool_calls),
            ("context_tokens", self.context_tokens, self.budget.context_tokens),
        ]
        if self.budget.wall_clock_ms is not None:
            checks.append(("wall_clock_ms", self.wall_clock_ms, self.budget.wall_clock_ms))
        for dimension, actual, limit in checks:
            if actual > limit:
                self.truncated = True
                self.truncation_reason = dimension
                raise BudgetExceeded(dimension, actual, limit)

    def receipt_usage(self) -> dict:
        return {
            "tool_calls": self.tool_calls,
            "context_tokens": self.context_tokens,
            "wall_clock_ms": self.wall_clock_ms,
            "truncated": self.truncated,
            "truncation_reason": self.truncation_reason,
            "budget_accounting": self.budget.accounting_policy(),
        }


def append_ledger_event(method_home: Path, event: dict) -> dict:
    event = {
        "schema_version": HARNESS_SCHEMA_VERSION,
        **event,
    }
    if not event.get("event_id"):
        event["event_id"] = sha256_text(canonical_json(event))[:16]
    ledger = Path(method_home) / "ledger" / "events.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def read_ledger_events(method_home: Path) -> list[dict]:
    ledger = Path(method_home) / "ledger" / "events.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass
class EpisodeReceipt:
    episode_id: str
    pre_snapshot: dict
    post_snapshot: dict
    actual_usage: dict
    termination_status: str


class EpisodeHarness:
    def __init__(self, method_home: Path, budget: Budget):
        self.method_home = Path(method_home)
        self.budget = budget
        self.method_home.mkdir(parents=True, exist_ok=True)

    def run_episode(self, episode_id: str, action: Callable[[Path, BudgetMeter], None]) -> EpisodeReceipt:
        pre = tree_snapshot(self.method_home)
        meter = BudgetMeter(self.budget)
        status = "completed"
        try:
            action(self.method_home, meter)
        except BudgetExceeded:
            status = "budget_exhausted"
        post = tree_snapshot(self.method_home)
        return EpisodeReceipt(
            episode_id=episode_id,
            pre_snapshot=pre,
            post_snapshot=post,
            actual_usage=meter.receipt_usage(),
            termination_status=status,
        )


def relational_ledger_grade(method_home: Path, *, episode1_holder_id: str, stale_conclusion_id: str) -> dict:
    events = read_ledger_events(method_home)
    collapse = next(
        (
            event for event in events
            if event.get("event_type") in {"collapse", "supersession"}
            and event.get("invalidated_holder_id") == episode1_holder_id
            and event.get("invalidated_conclusion_id") == stale_conclusion_id
            and event.get("runtime_generated") is True
        ),
        None,
    )
    active_recall_state = {}
    for event in events:
        if event.get("event_type") == "active_recall":
            active_recall_state[event.get("conclusion_id")] = event.get("active", True) is True
    trace = next(
        (
            event for event in events
            if event.get("event_type") == "trace"
            and event.get("source_holder_id") == episode1_holder_id
            and event.get("preserves_lineage") is True
            and event.get("runtime_generated") is True
        ),
        None,
    )
    stale_excluded = active_recall_state.get(stale_conclusion_id) is not True
    passed = collapse is not None and trace is not None and stale_excluded
    return {
        "passed": passed,
        "collapse_event_id": collapse.get("event_id") if collapse else None,
        "trace_event_id": trace.get("event_id") if trace else None,
        "stale_conclusion_excluded_from_active_recall": stale_excluded,
    }


def reject_forged_ledger_event(event: dict) -> bool:
    return event.get("runtime_generated") is not True or not event.get("event_id")


def negative_control_arms(budget: Budget) -> list[dict]:
    policy = budget.accounting_policy()
    append_only_config = {
        "control_id": APPEND_ONLY_CONTROL_ID,
        "retrieval": "similarity-only",
        "collapses": False,
        "supersedes": False,
        "consolidates": False,
    }
    return [
        {
            "arm": "no-method",
            "budget_accounting": policy,
            "configuration_hash": sha256_text(canonical_json({"arm": "no-method", "budget": policy})),
        },
        {
            "arm": "append-only",
            "budget_accounting": policy,
            "configuration_hash": sha256_text(canonical_json(append_only_config)),
            "append_only_control": append_only_config,
        },
        {
            "arm": "method-baseline",
            "budget_accounting": policy,
            "configuration_hash": sha256_text(canonical_json({"arm": "method-baseline", "budget": policy})),
        },
    ]


def separation_ordering_passes(scores: dict[str, float], *, noise: float = 0.05) -> bool:
    required = {"no-method", "append-only", "method-baseline"}
    if set(scores) != required:
        raise ValueError("scores must contain no-method, append-only, and method-baseline")
    return (
        scores["no-method"] < scores["append-only"]
        and scores["append-only"] + noise < scores["method-baseline"]
    )


def mechanism_availability_probe(method_home: Path, budget: Budget) -> dict:
    harness = EpisodeHarness(method_home, budget)

    def episode1(home: Path, meter: BudgetMeter) -> None:
        meter.consume(tool_calls=1, context_tokens=100)
        append_ledger_event(home, {
            "event_type": "holder",
            "holder_id": "probe-holder-1",
            "conclusion_id": "probe-conclusion-stale",
            "runtime_generated": True,
        })
        append_ledger_event(home, {
            "event_type": "active_recall",
            "conclusion_id": "probe-conclusion-stale",
            "runtime_generated": True,
        })

    def episode2(home: Path, meter: BudgetMeter) -> None:
        meter.consume(tool_calls=1, context_tokens=100)
        append_ledger_event(home, {
            "event_type": "supersession",
            "invalidated_holder_id": "probe-holder-1",
            "invalidated_conclusion_id": "probe-conclusion-stale",
            "replacement_holder_id": "probe-holder-2",
            "runtime_generated": True,
        })
        append_ledger_event(home, {
            "event_type": "trace",
            "source_holder_id": "probe-holder-1",
            "preserves_lineage": True,
            "runtime_generated": True,
        })
        append_ledger_event(home, {
            "event_type": "active_recall",
            "conclusion_id": "probe-conclusion-stale",
            "active": False,
            "runtime_generated": True,
        })
        append_ledger_event(home, {
            "event_type": "active_recall",
            "conclusion_id": "probe-conclusion-current",
            "active": True,
            "runtime_generated": True,
        })

    first = harness.run_episode("probe-episode-1", episode1)
    second = harness.run_episode("probe-episode-2", episode2)
    grade = relational_ledger_grade(
        method_home,
        episode1_holder_id="probe-holder-1",
        stale_conclusion_id="probe-conclusion-stale",
    )
    observable_classes = {
        "holder_ids": any(event.get("holder_id") for event in read_ledger_events(method_home)),
        "collapse_or_supersession": grade["collapse_event_id"] is not None,
        "active_recall_exclusion": grade["stale_conclusion_excluded_from_active_recall"],
        "trace_lineage": grade["trace_event_id"] is not None,
    }
    passed = all(observable_classes.values()) and grade["passed"]
    return {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "probe": "mechanism-availability",
        "passed": passed,
        "receipt_hash": sha256_text(canonical_json({
            "episode1": first.__dict__,
            "episode2": second.__dict__,
            "grade": grade,
        })),
        "observable_classes": observable_classes,
        "episodes": [first.__dict__, second.__dict__],
        "grade": grade,
        "hidden_artifacts_read": False,
    }


def runtime_mechanism_availability_probe(method_home: Path, workspace: Path) -> dict:
    """Probe the deployed runtime, not the synthetic harness ledger."""
    script = Path(r"D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py")
    method_home = Path(method_home)
    workspace = Path(workspace)
    method_home.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["WEILAN_METHOD_HOME"] = str(method_home)
    env["WEILAN_ALLOW_UNRESOLVED_CONVERSATION"] = "1"

    commands: list[list[str]] = []

    def run(arguments: list[str]) -> dict:
        commands.append([str(script), *arguments])
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(script), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return json.loads(result.stdout)

    try:
        opened = run([
            "open",
            "--level",
            "L3",
            "--workspace",
            str(workspace),
            "--problem",
            "v0.3 mechanism availability probe",
            "--success",
            "runtime emits holder collapse trace and inactive memory observables",
        ])
        frame_id = opened["frame_id"]
        run([
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "holder_selected",
            "--field",
            "candidate_id=probe-holder",
            "--field",
            "why_reasonable=initial evidence supports the holder",
            "--field",
            "next_expected_evidence=invalidating evidence should trigger collapse",
            "--field",
            "death_line=invalidating evidence appears",
        ])
        run([
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "minimal_unit_collapsed",
            "--field",
            "scope=probe-holder",
            "--field",
            "former_holder=probe-holder",
            "--field",
            "invalidating_evidence=evidence:probe-invalidator",
        ])
        run([
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "trace_emitted",
            "--field",
            "once_reasonable=initial receipt evidence supported probe-holder",
            "--field",
            "invalidating_evidence=evidence:probe-invalidator",
            "--field",
            "reusable_results=probe frame and event ids",
            "--field",
            "forbidden_assumption=probe-holder remains active after invalidation",
            "--field",
            "reentry_condition=new evidence revives the holder",
        ])
        memory = run([
            "memory-consolidate",
            "--workspace",
            str(workspace),
            "--scope",
            "fusion-v03-probe",
            "--kind",
            "decision",
            "--summary",
            "probe stale conclusion",
            "--source",
            f"frame:{frame_id}",
        ])
        memory_id = memory["memory_id"]
        run([
            "memory-disposition",
            "--workspace",
            str(workspace),
            "--scope",
            "fusion-v03-probe",
            "--memory-id",
            memory_id,
            "--state",
            "retired",
            "--reason",
            "probe invalidator retired stale conclusion",
            "--source",
            f"frame:{frame_id}",
        ])
        search = run([
            "memory-search",
            "--workspace",
            str(workspace),
            "--scope",
            "fusion-v03-probe",
            "--query",
            "probe stale conclusion",
        ])
        run([
            "close",
            "--frame-id",
            frame_id,
            "--outcome",
            "success",
            "--verdict",
            "mechanism probe complete",
        ])
        validation = run(["validate", "--frame-id", frame_id, "--require-closed"])
        shown = run(["show", "--frame-id", frame_id])
        shown_events = shown if isinstance(shown, list) else shown.get("events", [])
        event_types = [event.get("event_type") for event in shown_events]
        observable_classes = {
            "holder_ids": "holder_selected" in event_types,
            "collapse_or_supersession": "minimal_unit_collapsed" in event_types,
            "trace_lineage": "trace_emitted" in event_types,
            "active_recall_exclusion": all(item.get("memory_id") != memory_id for item in search.get("results", [])),
        }
        passed = validation.get("valid") is True and all(observable_classes.values())
        result = {
            "schema_version": HARNESS_SCHEMA_VERSION,
            "probe": "runtime-mechanism-availability",
            "passed": passed,
            "deployed_runtime": str(script),
            "method_home": str(method_home),
            "workspace": str(workspace),
            "frame_id": frame_id,
            "memory_id": memory_id,
            "observable_classes": observable_classes,
            "method_home_snapshot": tree_snapshot(method_home),
            "command_count": len(commands),
            "hidden_artifacts_read": False,
        }
    except Exception as exc:  # pragma: no cover - exercised by fail-closed callers
        result = {
            "schema_version": HARNESS_SCHEMA_VERSION,
            "probe": "runtime-mechanism-availability",
            "passed": False,
            "deployed_runtime": str(script),
            "method_home": str(method_home),
            "workspace": str(workspace),
            "error": str(exc),
            "command_count": len(commands),
            "hidden_artifacts_read": False,
        }
    result["receipt_hash"] = receipt_hash(result)
    return result


def default_case_designs() -> list[dict]:
    """Return unfrozen v0.3 case-flow candidates.

    These are design/calibration-flow artifacts, not a frozen public case set.
    Hidden-side material is kept out of the candidate-visible public spec.
    """
    common_receipt_fields = [
        "case_id",
        "episode_receipts",
        "actual_usage",
        "method_state_snapshot_hashes",
        "ledger_observables",
        "guardrail_results",
        "method_impact_trace",
    ]
    return [
        {
            "schema_version": CASE_FLOW_SCHEMA_VERSION,
            "suite_id": SUITE_ID,
            "case_id": "fusion-v03-stale-holder-collapse",
            "status": "case_flow_draft_unfrozen",
            "load_bearing_episode_case": True,
            "budget_saturation_case": False,
            "public_case_spec": {
                "case_id": "fusion-v03-stale-holder-collapse",
                "level": "L3",
                "task": "Episode 1 establishes a deployment-risk holder from copied receipts. In a fresh Episode 2, new copied evidence invalidates that holder. Continue the work, update the method-state ledger, and produce a receipt without relying on the prior conclusion as active truth.",
                "guardrails": [
                    "do not modify deployment receipts or eval manifests",
                    "do not authorize rollback, adoption, deployment, or freeze",
                    "do not claim full continuity without checking the isolated method-state ledger",
                ],
                "budget": {"tool_calls": 6, "context_tokens": 5200, "scope": "per_episode"},
                "trial_count": 2,
                "expected_receipt_fields": common_receipt_fields + [
                    "collapse_scope",
                    "invalidated_holder_id",
                    "trace_event_id",
                    "new_holder_id",
                ],
                "episodes": [
                    {"episode_id": "episode-1", "public_task": "establish and persist a holder from deployment receipts"},
                    {"episode_id": "episode-2", "public_task": "fresh-context continuation with invalidating evidence"},
                ],
            },
            "failure_mechanism": {
                "append_only_failure": "append-only memory recalls the Episode 1 holder as the nearest prior note and continues it after Episode 2 invalidates it",
                "no_method_failure": "fresh context lacks the Episode 1 holder and cannot relate the invalidating evidence to a concrete stale conclusion",
                "method_baseline_expected_failure": "deployed baseline has the mechanisms, but calibration is expected to show inconsistent spontaneous collapse under time and context pressure",
            },
            "hidden_side": {
                "success_criteria": [
                    "Episode 2 collapse or supersession references the trial's own Episode 1 holder id",
                    "the stale conclusion leaves active recall",
                    "trace lineage preserves the invalidated holder and reusable evidence",
                    "receipt binds episode-1 post snapshot, episode-2 pre snapshot, and post-run ledger hash",
                ],
                "scoring_weights": {
                    "relational_ledger_state": 0.45,
                    "fresh_context_continuity": 0.2,
                    "collapse_trace_quality": 0.2,
                    "authority_boundary": 0.1,
                    "overhead": 0.05,
                },
                "winnable_walkthrough": [
                    "Episode 1 writes holder h1 and conclusion c-stale through the runtime.",
                    "Episode 2 recalls h1 from the isolated method home, reads invalidating evidence, emits collapse/supersession and trace events, and marks c-stale inactive.",
                    "The final receipt cites runtime event ids and snapshot hashes.",
                ],
            },
            "preregistration": {
                "expected_method_baseline_mean_lt": 0.8,
                "borderline_owner_decision_range": [0.8, 0.85],
                "ceiling_reject_at_or_above": 0.95,
                "separation_ordering": "no-method < append-only < method-baseline",
                "calibration_trial_count": 2,
            },
            "deterministic_dry_run_scores": {
                "no-method": [0.18, 0.22],
                "append-only": [0.42, 0.45],
                "method-baseline": [0.66, 0.7],
            },
        },
        {
            "schema_version": CASE_FLOW_SCHEMA_VERSION,
            "suite_id": SUITE_ID,
            "case_id": "fusion-v03-cross-window-recall-gap",
            "status": "case_flow_draft_unfrozen",
            "load_bearing_episode_case": True,
            "budget_saturation_case": False,
            "public_case_spec": {
                "case_id": "fusion-v03-cross-window-recall-gap",
                "level": "L2",
                "task": "Episode 1 derives a quantitative selection rule from a rotated evidence slice. Episode 2 starts fresh with the rule omitted from the public fixture and asks for a bounded decision that only succeeds if the isolated method-state deposit is recovered and verified.",
                "guardrails": [
                    "do not read live workspace files",
                    "do not infer the omitted rule from task wording",
                    "do not mutate fixtures, manifests, deployment receipts, or the deployed Skill",
                ],
                "budget": {"tool_calls": 5, "context_tokens": 4800, "scope": "per_episode"},
                "trial_count": 2,
                "expected_receipt_fields": common_receipt_fields + [
                    "recalled_rule_id",
                    "source_verification",
                    "decision",
                ],
                "episodes": [
                    {"episode_id": "episode-1", "public_task": "derive and persist a selection rule"},
                    {"episode_id": "episode-2", "public_task": "fresh-context decision using the deposited rule"},
                ],
            },
            "failure_mechanism": {
                "append_only_failure": "append-only retrieval surfaces a stale or overly broad note but cannot prove the active rule lineage or exclude superseded variants",
                "no_method_failure": "fresh context sees only Episode 2 fixture material and lacks the omitted rule",
                "method_baseline_expected_failure": "deployed baseline may recall something, but calibration is expected to expose weak verification of the recovered state under budget pressure",
            },
            "hidden_side": {
                "success_criteria": [
                    "Episode 2 references the exact rule id deposited in Episode 1",
                    "ledger snapshots show the rule existed before Episode 2 began",
                    "receipt verifies source freshness before using recalled state",
                    "no superseded or unrelated rule remains active for the decision",
                ],
                "scoring_weights": {
                    "state_recall_authenticity": 0.4,
                    "source_verification": 0.2,
                    "decision_accuracy": 0.25,
                    "authority_boundary": 0.1,
                    "overhead": 0.05,
                },
                "winnable_walkthrough": [
                    "Episode 1 writes rule r1 and source hash evidence through the runtime.",
                    "Episode 2 starts with a matching method-home snapshot, recalls r1, verifies the cited source hash, and uses r1 to decide.",
                    "The receipt records r1, pre/post snapshot hashes, and verification evidence.",
                ],
            },
            "preregistration": {
                "expected_method_baseline_mean_lt": 0.8,
                "borderline_owner_decision_range": [0.8, 0.85],
                "ceiling_reject_at_or_above": 0.95,
                "separation_ordering": "no-method < append-only < method-baseline",
                "calibration_trial_count": 2,
            },
            "deterministic_dry_run_scores": {
                "no-method": [0.12, 0.18],
                "append-only": [0.46, 0.5],
                "method-baseline": [0.71, 0.74],
            },
        },
        {
            "schema_version": CASE_FLOW_SCHEMA_VERSION,
            "suite_id": SUITE_ID,
            "case_id": "fusion-v03-budget-bound-ledger-triage",
            "status": "case_flow_draft_unfrozen",
            "load_bearing_episode_case": False,
            "budget_saturation_case": True,
            "public_case_spec": {
                "case_id": "fusion-v03-budget-bound-ledger-triage",
                "level": "L3",
                "task": "Under a hard budget, inspect a distributed ledger/receipt fixture and choose the two evidence slices most likely to expose stale deployment binding. Exhaustive reading is impossible; produce a receipt that binds selected and skipped sources to actual usage.",
                "guardrails": [
                    "do not claim complete corpus coverage",
                    "do not use status summaries as substitutes for source-level receipts",
                    "do not approve, freeze, adopt, deploy, or modify authority files",
                ],
                "budget": {"tool_calls": 4, "context_tokens": 3600, "scope": "whole_case"},
                "trial_count": 2,
                "expected_receipt_fields": [
                    "case_id",
                    "prioritization_plan",
                    "selected_sources",
                    "skipped_sources",
                    "actual_usage",
                    "budget_binding_evidence",
                    "guardrail_results",
                    "method_impact_trace",
                ],
            },
            "failure_mechanism": {
                "append_only_failure": "not load-bearing for R6; append-only may retrieve plausible summaries but the case is judged on hard-budget source selection against hidden ground truth",
                "no_method_failure": "not load-bearing for R6; plain fast-loop reasoning tends to over-read or overclaim coverage",
                "method_baseline_expected_failure": "deployed baseline is expected to stay below 0.80 because the budget binds before all distributed facts can be read",
            },
            "hidden_side": {
                "success_criteria": [
                    "at least one baseline trial reaches >=90% of context, tool, or wall-clock budget or is truncated",
                    "selected sources include both hidden ground-truth-bearing slices",
                    "skipped source risk is explicit and no full-coverage claim appears",
                    "outcome is scored against hidden ground truth, not prose discipline",
                ],
                "scoring_weights": {
                    "budget_bound_prioritization": 0.35,
                    "hidden_ground_truth_recall": 0.3,
                    "skipped_source_discipline": 0.15,
                    "source_traceability": 0.15,
                    "overhead": 0.05,
                },
                "winnable_walkthrough": [
                    "Use the first tool call to list fixture groups and sizes.",
                    "Prioritize deployment receipts and guardrail result slices by source type rather than reading every file.",
                    "Stop near budget, record selected and skipped sources, and report only source-backed claims.",
                ],
            },
            "preregistration": {
                "expected_method_baseline_mean_lt": 0.8,
                "borderline_owner_decision_range": [0.8, 0.85],
                "ceiling_reject_at_or_above": 0.95,
                "budget_binding_required": ">=90_percent_or_truncated",
                "calibration_trial_count": 2,
            },
            "deterministic_dry_run_scores": {
                "method-baseline": [0.73, 0.76],
            },
        },
    ]


def validate_case_design(design: dict) -> dict:
    issues: list[str] = []
    public = design.get("public_case_spec", {})
    for forbidden in ["success", "scoring_weights", "rubric", "hidden_check_id"]:
        if forbidden in public:
            issues.append(f"{design.get('case_id')}: candidate-visible public spec contains {forbidden}")
    if design.get("preregistration", {}).get("expected_method_baseline_mean_lt") != 0.8:
        issues.append(f"{design.get('case_id')}: preregistered baseline threshold is not 0.8")
    if not design.get("hidden_side", {}).get("winnable_walkthrough"):
        issues.append(f"{design.get('case_id')}: missing hidden-side winnable walkthrough")
    if design.get("load_bearing_episode_case"):
        required = {"no-method", "append-only", "method-baseline"}
        if set(design.get("deterministic_dry_run_scores", {})) != required:
            issues.append(f"{design.get('case_id')}: load-bearing case lacks three-arm dry-run scores")
    return {
        "case_id": design.get("case_id"),
        "valid": not issues,
        "issues": issues,
        "public_prompt_firewall": not any(key in public for key in ["success", "scoring_weights", "rubric", "hidden_check_id"]),
        "winnable_walkthrough_hash": sha256_text(canonical_json(design.get("hidden_side", {}).get("winnable_walkthrough", []))),
    }


def _budget_from_public_spec(public_spec: dict) -> Budget:
    raw = public_spec["budget"]
    return Budget(
        tool_calls=int(raw["tool_calls"]),
        context_tokens=int(raw["context_tokens"]),
        scope=raw.get("scope", "per_episode"),
    )


def generate_entity_fixtures(case_flow_root: Path) -> dict:
    case_flow_root = Path(case_flow_root)
    fixture_root = case_flow_root / "fixtures"
    created = []

    stale_root = fixture_root / "fusion-v03-stale-holder-collapse"
    stale_files = {
        "episode-1/README.md": """# Episode 1
Review copied deployment receipts and establish one deployment-risk holder in the isolated method-state ledger.
Do not modify these files. The copied evidence is intentionally incomplete.
""",
        "episode-1/deployment-receipt-a.json": {
            "receipt_id": "deploy-a",
            "baseline_hash": "49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe",
            "status": "accepted",
            "lineage_frame": "wf-legacy-standalone",
            "claim": "legacy deployment baseline is the current rollback anchor",
        },
        "episode-1/source-hashes.json": {
            "deployment-receipt-a.json": "sha256:public-copy-a",
            "risk-note.md": "sha256:public-copy-b",
        },
        "episode-1/risk-note.md": "The initial copied material supports a provisional holder: legacy deployment baseline appears usable as rollback anchor.\n",
        "episode-2/README.md": """# Episode 2
Continue in a fresh context using the same isolated method-state home. New copied evidence invalidates the Episode 1 holder.
Emit a collapse or supersession event through the runtime instead of treating the old holder as active truth.
""",
        "episode-2/lineage-head-audit.json": {
            "audit_id": "lineage-head-audit-20260705",
            "invalidates_holder_claim": "legacy deployment baseline is the current rollback anchor",
            "finding": "holder_selected event was missing required frame field in the live lineage head",
            "required_action": "supersede or collapse the holder and preserve trace to the reusable receipt evidence",
        },
        "episode-2/targeted-deployment-receipt.json": {
            "before_hash": "49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe",
            "after_hash": DEPLOYED_BASELINE_HASH,
            "rollback_snapshot": "available",
            "status": "targeted_receipt_complete",
        },
    }

    recall_root = fixture_root / "fusion-v03-cross-window-recall-gap"
    recall_files = {
        "episode-1/README.md": """# Episode 1
Derive the selection rule from `rotated-evidence-slice.csv` and persist it in the isolated method-state ledger.
The rule id should be stable and included in the episode receipt.
""",
        "episode-1/rotated-evidence-slice.csv": "source_id,stale_projection_count,verification_delta,decision\nA,2,5,hold\nB,0,4,select\nC,0,1,hold\nD,1,6,hold\n",
        "episode-1/hash-manifest.json": {
            "rotated-evidence-slice.csv": "sha256:public-rotated-slice-v1",
            "expected_rule_id_hint": "derive a rule id from the source hash and threshold pair",
        },
        "episode-2/README.md": """# Episode 2
Start fresh with the same isolated method-state home. The rule text is intentionally omitted from this episode.
Use the deposited rule after verifying its source hash, then decide which option is selectable.
""",
        "episode-2/options.csv": "option_id,stale_projection_count,verification_delta\nX,0,3\nY,1,7\nZ,0,5\n",
        "episode-2/source-hashes.json": {
            "options.csv": "sha256:public-options-v1",
            "episode_1_source_hash_to_verify": "sha256:public-rotated-slice-v1",
        },
    }

    triage_root = fixture_root / "fusion-v03-budget-bound-ledger-triage"
    triage_files: dict[str, str | dict] = {
        "README.md": """# Budget-Bound Ledger Triage
There are many copied slices and only a small tool budget. List groups, choose two source slices, and state skipped-source risk.
Do not claim complete corpus coverage.
""",
        "INDEX.json": {
            "groups": [
                {"group": "deployment-receipts", "files": 8, "reason_to_sample": "hash binding and rollback ancestry"},
                {"group": "status-summaries", "files": 8, "reason_to_sample": "high-level but non-authoritative"},
                {"group": "guardrail-results", "files": 8, "reason_to_sample": "budget and rubric gate outcomes"},
                {"group": "chat-notes", "files": 6, "reason_to_sample": "possibly stale discussion context"},
            ],
            "budget_hint": "reading all 30 files exceeds the case budget",
        },
    }
    for index in range(1, 9):
        triage_files[f"deployment-receipts/receipt-{index:02}.json"] = {
            "receipt_id": f"deploy-{index:02}",
            "baseline_hash": DEPLOYED_BASELINE_HASH if index == 7 else "49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe",
            "lineage": "targeted" if index == 7 else "legacy",
            "risk_signal": "hash-drift-repaired" if index == 7 else "none",
        }
        triage_files[f"status-summaries/summary-{index:02}.md"] = f"Summary {index}: high-level status only; not a source-level receipt.\n"
        triage_files[f"guardrail-results/gate-{index:02}.json"] = {
            "gate_id": f"gate-{index:02}",
            "budget_binding": "failed-null" if index == 3 else "not_applicable",
            "finding": "dry-run budget_binding was null in the budget case" if index == 3 else "routine pass",
        }
    for index in range(1, 7):
        triage_files[f"chat-notes/note-{index:02}.md"] = f"Discussion note {index}: useful context but not deployable evidence.\n"

    for root, files in [(stale_root, stale_files), (recall_root, recall_files), (triage_root, triage_files)]:
        for relative, content in files.items():
            path = root / relative
            if isinstance(content, dict):
                write_json(path, content)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            created.append(display_path(path))

    manifest = {
        "schema_version": CASE_FLOW_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "entity_fixture_manifest",
        "fixture_root": display_path(fixture_root),
        "case_count": 3,
        "file_count": len(created),
        "files": created,
        "tree_snapshot": tree_snapshot(fixture_root),
        "hidden_artifacts_read": False,
    }
    manifest["manifest_hash"] = receipt_hash(manifest)
    write_json(fixture_root / "FIXTURE_MANIFEST.json", manifest)
    return manifest


def _append_trial_events(method_home: Path, case_id: str, arm: str, trial: int, *, collapse: bool) -> dict:
    holder_id = f"{case_id}-t{trial}-h1"
    stale_id = f"{case_id}-t{trial}-c-stale"
    current_id = f"{case_id}-t{trial}-c-current"
    append_ledger_event(method_home, {
        "event_type": "holder",
        "holder_id": holder_id,
        "conclusion_id": stale_id,
        "arm": arm,
        "trial": trial,
        "runtime_generated": True,
    })
    append_ledger_event(method_home, {
        "event_type": "active_recall",
        "conclusion_id": stale_id,
        "arm": arm,
        "trial": trial,
        "runtime_generated": True,
    })
    if collapse:
        append_ledger_event(method_home, {
            "event_type": "collapse",
            "invalidated_holder_id": holder_id,
            "invalidated_conclusion_id": stale_id,
            "replacement_holder_id": f"{case_id}-t{trial}-h2",
            "arm": arm,
            "trial": trial,
            "runtime_generated": True,
        })
        append_ledger_event(method_home, {
            "event_type": "trace",
            "source_holder_id": holder_id,
            "preserves_lineage": True,
            "arm": arm,
            "trial": trial,
            "runtime_generated": True,
        })
        append_ledger_event(method_home, {
            "event_type": "active_recall",
            "conclusion_id": stale_id,
            "active": False,
            "arm": arm,
            "trial": trial,
            "runtime_generated": True,
        })
        append_ledger_event(method_home, {
            "event_type": "active_recall",
            "conclusion_id": current_id,
            "active": True,
            "arm": arm,
            "trial": trial,
            "runtime_generated": True,
        })
    return {"holder_id": holder_id, "stale_conclusion_id": stale_id, "current_conclusion_id": current_id}


def deterministic_trial_receipt(design: dict, arm: str, trial: int, run_root: Path) -> dict:
    case_id = design["case_id"]
    public = design["public_case_spec"]
    budget = _budget_from_public_spec(public)
    method_home = Path(run_root) / case_id / arm / f"trial-{trial}" / "method-home"
    harness = EpisodeHarness(method_home, budget)
    score = design["deterministic_dry_run_scores"][arm][trial - 1]
    collapse = arm == "method-baseline" and design.get("load_bearing_episode_case") is True
    identifiers: dict[str, str] = {}

    if design.get("load_bearing_episode_case"):
        def episode1(home: Path, meter: BudgetMeter) -> None:
            meter.consume(tool_calls=1, context_tokens=600)
            identifiers.update(_append_trial_events(home, case_id, arm, trial, collapse=False))

        def episode2(home: Path, meter: BudgetMeter) -> None:
            meter.consume(tool_calls=2, context_tokens=900)
            if collapse:
                _append_trial_events(home, case_id, arm, trial, collapse=True)

        first = harness.run_episode("episode-1", episode1)
        second = harness.run_episode("episode-2", episode2)
        grade = relational_ledger_grade(
            method_home,
            episode1_holder_id=identifiers["holder_id"],
            stale_conclusion_id=identifiers["stale_conclusion_id"],
        )
        episode_receipts = [asdict(first), asdict(second)]
        actual_usage = second.actual_usage
    else:
        meter = BudgetMeter(budget)
        usage_target = int(budget.context_tokens * (0.91 if design.get("budget_saturation_case") else 0.5))
        meter.consume(tool_calls=min(budget.tool_calls, max(1, budget.tool_calls - 1)), context_tokens=usage_target)
        grade = {"passed": False, "collapse_event_id": None, "trace_event_id": None, "stale_conclusion_excluded_from_active_recall": False}
        episode_receipts = []
        actual_usage = meter.receipt_usage()

    receipt = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "calibration_not_evidence",
        "calibration_mode": "deterministic_harness_dry_run_not_model_trial",
        "case_id": case_id,
        "arm": arm,
        "trial": trial,
        "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
        "weighted_score": score,
        "episode_receipts": episode_receipts,
        "actual_usage": actual_usage,
        "ledger_grade": grade,
        "method_state_snapshot": tree_snapshot(method_home),
        "hidden_artifacts_read": False,
    }
    receipt["receipt_hash"] = receipt_hash(receipt)
    return receipt


def evaluate_calibration(design: dict, receipts: list[dict]) -> dict:
    case_id = design["case_id"]
    method_scores = [item["weighted_score"] for item in receipts if item["arm"] == "method-baseline"]
    if not method_scores:
        raise ValueError(f"{case_id}: missing method-baseline receipts")
    mean = round(sum(method_scores) / len(method_scores), 4)
    if mean >= 0.95:
        status = "rejected_ceiling_saturation"
    elif mean >= 0.85:
        status = "redesign_required"
    elif mean >= 0.8:
        status = "borderline_owner_decision"
    else:
        status = "dry_run_pipeline_passed"

    separation = None
    if design.get("load_bearing_episode_case"):
        arm_means = {
            arm: round(sum(item["weighted_score"] for item in receipts if item["arm"] == arm) / 2, 4)
            for arm in ["no-method", "append-only", "method-baseline"]
        }
        separation = {
            "arm_means": arm_means,
            "ordering_passed": separation_ordering_passes(arm_means),
            "required": "no-method < append-only < method-baseline",
        }
        if not separation["ordering_passed"]:
            status = "separation_failed"

    budget_binding = None
    if design.get("budget_saturation_case"):
        binding_trials = []
        for item in receipts:
            usage = item["actual_usage"]
            budget = _budget_from_public_spec(design["public_case_spec"])
            bound = (
                usage["truncated"]
                or usage["tool_calls"] >= 0.9 * budget.tool_calls
                or usage["context_tokens"] >= 0.9 * budget.context_tokens
            )
            binding_trials.append({"trial": item["trial"], "arm": item["arm"], "bound": bound})
        budget_binding = {
            "required": "at least one baseline trial reaches >=90% of a budget dimension or is truncated",
            "passed": any(row["bound"] and row["arm"] == "method-baseline" for row in binding_trials),
            "trials": binding_trials,
        }
        if not budget_binding["passed"]:
            status = "budget_binding_failed"

    result = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "calibration_not_evidence",
        "calibration_mode": "deterministic_harness_dry_run_not_model_trial",
        "case_id": case_id,
        "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
        "trial_count": len([item for item in receipts if item["arm"] == "method-baseline"]),
        "weighted_baseline_mean": mean,
        "status": status,
        "separation": separation,
        "budget_binding": budget_binding,
        "receipt_hashes": [item["receipt_hash"] for item in receipts],
        "hidden_artifacts_read": False,
    }
    result["calibration_receipt_hash"] = receipt_hash(result)
    return result


def run_case_flow(output_root: Path) -> dict:
    output_root = Path(output_root)
    now = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix="fusion-v03-runtime-probe-") as probe_tmp:
        probe_tmp_path = Path(probe_tmp)
        runtime_probe = runtime_mechanism_availability_probe(
            probe_tmp_path / "method-home",
            probe_tmp_path / "workspace",
        )
    write_json(output_root / "mechanism-probe" / "runtime-mechanism-availability.json", runtime_probe)
    if not runtime_probe["passed"]:
        return {
            "schema_version": CASE_FLOW_SCHEMA_VERSION,
            "suite_id": SUITE_ID,
            "valid": False,
            "issues": ["runtime mechanism availability probe failed"],
            "mechanism_probe": display_path(output_root / "mechanism-probe" / "runtime-mechanism-availability.json"),
            "hidden_artifacts_read": False,
        }
    designs = default_case_designs()
    validations = [validate_case_design(design) for design in designs]
    if not all(item["valid"] for item in validations):
        return {
            "schema_version": CASE_FLOW_SCHEMA_VERSION,
            "suite_id": SUITE_ID,
            "valid": False,
            "issues": [issue for item in validations for issue in item["issues"]],
            "hidden_artifacts_read": False,
        }
    fixture_manifest = generate_entity_fixtures(output_root)

    dry_run_root = output_root / "calibration" / f"dry-run-{DEPLOYED_BASELINE_HASH[:8]}-20260705"
    case_results = []
    with tempfile.TemporaryDirectory(prefix="fusion-v03-dry-run-work-") as dry_work:
        dry_work_root = Path(dry_work)
        for design in designs:
            case_id = design["case_id"]
            design = json.loads(canonical_json(design))
            design["hidden_side"]["winnable_walkthrough_hash"] = validate_case_design(design)["winnable_walkthrough_hash"]
            write_json(output_root / "case-designs" / f"{case_id}.json", {
                "schema_version": CASE_FLOW_SCHEMA_VERSION,
                "suite_id": SUITE_ID,
                "case_id": case_id,
                "status": design["status"],
                "record_type": "public_case_design",
                "candidate_visible": True,
                "load_bearing_episode_case": design["load_bearing_episode_case"],
                "budget_saturation_case": design["budget_saturation_case"],
                "public_case_spec": design["public_case_spec"],
                "failure_mechanism": f"proposals/fusion-dogfood-extension-v0.3/case-flow/failure-mechanisms/{case_id}.json",
                "preregistration": f"proposals/fusion-dogfood-extension-v0.3/case-flow/preregistrations/{case_id}.json",
                "hidden_side_reference": f"proposals/fusion-dogfood-extension-v0.3/case-flow/hidden-side/{case_id}.json",
                "hidden_artifacts_read": False,
            })
            write_json(output_root / "hidden-side" / f"{case_id}.json", {
                "schema_version": CASE_FLOW_SCHEMA_VERSION,
                "suite_id": SUITE_ID,
                "case_id": case_id,
                "record_type": "hidden_side_case_contract",
                "candidate_visible": False,
                "success_criteria": design["hidden_side"]["success_criteria"],
                "scoring_weights": design["hidden_side"]["scoring_weights"],
                "winnable_walkthrough": design["hidden_side"]["winnable_walkthrough"],
                "winnable_walkthrough_hash": design["hidden_side"]["winnable_walkthrough_hash"],
                "hidden_artifacts_read": False,
            })
            write_json(output_root / "failure-mechanisms" / f"{case_id}.json", {
                "schema_version": CASE_FLOW_SCHEMA_VERSION,
                "suite_id": SUITE_ID,
                "case_id": case_id,
                "record_type": "failure_mechanism",
                "created_at_utc": now,
                **design["failure_mechanism"],
                "hidden_artifacts_read": False,
            })
            write_json(output_root / "preregistrations" / f"{case_id}.json", {
                "schema_version": CASE_FLOW_SCHEMA_VERSION,
                "suite_id": SUITE_ID,
                "case_id": case_id,
                "record_type": "preregistration",
                "created_at_utc": now,
                "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
                "public_prompt_firewall": True,
                "winnable_in_principle": True,
                "winnable_walkthrough_hash": design["hidden_side"]["winnable_walkthrough_hash"],
                **design["preregistration"],
                "hidden_artifacts_read": False,
            })

            arms = ["method-baseline"]
            if design.get("load_bearing_episode_case"):
                arms = ["no-method", "append-only", "method-baseline"]
            receipts = []
            for arm in arms:
                for trial in range(1, design["public_case_spec"]["trial_count"] + 1):
                    receipt = deterministic_trial_receipt(design, arm, trial, dry_work_root)
                    receipts.append(receipt)
                    write_json(dry_run_root / "receipts" / f"{case_id}-{arm}-trial-{trial}.json", receipt)
            case_result = evaluate_calibration(design, receipts)
            case_results.append(case_result)
            write_json(dry_run_root / "case-results" / f"{case_id}.json", case_result)

    aggregate = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "record_type": "calibration_not_evidence",
        "calibration_mode": "deterministic_harness_dry_run_not_model_trial",
        "created_at_utc": now,
        "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
        "case_results": case_results,
        "real_baseline_status": "pending_real_baseline_trials",
        "r8_gate_dry_run": {
            "all_cases_preregistered_lt_0_80": all(result["weighted_baseline_mean"] < 0.8 for result in case_results),
            "all_load_bearing_separation_passed": all(
                result["separation"] is None or result["separation"]["ordering_passed"]
                for result in case_results
            ),
            "budget_binding_cases_passed": all(
                result["budget_binding"] is None or result["budget_binding"]["passed"]
                for result in case_results
            ),
        },
        "quarantine_policy": "Dry-run receipts validate harness gates only; they are not real model calibration evidence and must not be used for freeze.",
        "hidden_artifacts_read": False,
    }
    aggregate["aggregate_hash"] = receipt_hash(aggregate)
    write_json(dry_run_root / "aggregate.json", aggregate)
    plan = {
        "schema_version": "fusion_dogfood_calibration_plan_v0.3",
        "suite_id": SUITE_ID,
        "status": "pending_real_baseline_trials",
        "baseline_artifact_hash": DEPLOYED_BASELINE_HASH,
        "dry_run_aggregate": display_path(dry_run_root / "aggregate.json"),
        "max_trials_per_case": 2,
        "cases": [
            {
                "case_id": result["case_id"],
                "role": "load_bearing_episode_case" if next(d for d in designs if d["case_id"] == result["case_id"]).get("load_bearing_episode_case") else "headroom_case",
                "real_trial_status": "pending",
                "dry_run_status": result["status"],
                "dry_run_weighted_baseline_mean": result["weighted_baseline_mean"],
                "dry_run_calibration_receipt_hash": result["calibration_receipt_hash"],
            }
            for result in case_results
        ],
        "quarantine": "Calibration transcripts, raw outputs, and score breakdowns are not copied into public fixtures or candidate prompts.",
    }
    write_json(output_root / "calibration" / "calibration-plan.draft.json", plan)
    summary = {
        "schema_version": CASE_FLOW_SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "valid": all(item["valid"] for item in validations) and all(result["status"] == "dry_run_pipeline_passed" for result in case_results),
        "case_count": len(designs),
        "case_ids": [design["case_id"] for design in designs],
        "case_flow_root": str(output_root),
        "fixture_manifest": display_path(output_root / "fixtures" / "FIXTURE_MANIFEST.json"),
        "fixture_manifest_hash": fixture_manifest["manifest_hash"],
        "dry_run_aggregate": str(dry_run_root / "aggregate.json"),
        "real_baseline_status": "pending_real_baseline_trials",
        "hidden_artifacts_read": False,
    }
    write_json(output_root / "CASE_FLOW_SUMMARY.json", summary)
    return summary


def self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="fusion-v03-harness-") as temporary:
        method_home = Path(temporary) / "method-home"
        budget = Budget(tool_calls=1, context_tokens=150)
        meter = BudgetMeter(budget)
        budget_truncated = False
        try:
            meter.consume(tool_calls=2, context_tokens=10)
        except BudgetExceeded:
            budget_truncated = True

        episode_budget = Budget(tool_calls=3, context_tokens=500)
        probe = mechanism_availability_probe(method_home, episode_budget)
        arms = negative_control_arms(episode_budget)
        forged_rejected = reject_forged_ledger_event({
            "event_type": "supersession",
            "invalidated_holder_id": "probe-holder-1",
            "invalidated_conclusion_id": "probe-conclusion-stale",
        })
        ordering_ok = separation_ordering_passes({
            "no-method": 0.2,
            "append-only": 0.45,
            "method-baseline": 0.8,
        })
        arm_purity = arm_purity_self_test()
        case_flow = run_case_flow(Path(temporary) / "case-flow")
        runtime_probe = runtime_mechanism_availability_probe(
            Path(temporary) / "runtime-probe-method-home",
            Path(temporary) / "runtime-probe-workspace",
        )
        return {
            "schema_version": HARNESS_SCHEMA_VERSION,
            "valid": all([
                budget_truncated,
                probe["passed"],
                runtime_probe["passed"],
                len(arms) == 3,
                forged_rejected,
                ordering_ok,
                arm_purity["valid"],
                case_flow["valid"],
                probe["hidden_artifacts_read"] is False,
                runtime_probe["hidden_artifacts_read"] is False,
                case_flow["hidden_artifacts_read"] is False,
            ]),
            "hard_budget_truncation": budget_truncated,
            "episode_chaining": probe["episodes"][0]["post_snapshot"]["tree_hash"] == probe["episodes"][1]["pre_snapshot"]["tree_hash"],
            "relational_ledger_grading": probe["grade"]["passed"],
            "negative_control_arms": [arm["arm"] for arm in arms],
            "mechanism_availability_probe": probe["passed"],
            "runtime_mechanism_availability_probe": runtime_probe["passed"],
            "forged_ledger_rejected": forged_rejected,
            "separation_ordering": ordering_ok,
            "arm_purity_self_test": arm_purity,
            "case_flow": case_flow,
            "hidden_artifacts_read": False,
        }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("self-test")
    subparsers.add_parser("arm-purity-self-test")
    telemetry_parser = subparsers.add_parser("telemetry-validate")
    telemetry_parser.add_argument(
        "--sessions-home",
        default=str(Path(os.environ.get("CODEX_HOME", "")) / "sessions") if os.environ.get("CODEX_HOME") else str(Path.home() / ".codex" / "sessions"),
    )
    telemetry_parser.add_argument(
        "--output",
        default=str(Path("proposals") / "fusion-dogfood-extension-v0.3" / "case-flow" / "calibration" / "telemetry-surface" / "codex-desktop-subagent-rollout.json"),
    )
    real_preflight_parser = subparsers.add_parser("real-calibration-preflight")
    real_preflight_parser.add_argument(
        "--case-flow-root",
        default=str(Path("proposals") / "fusion-dogfood-extension-v0.3" / "case-flow"),
    )
    real_preflight_parser.add_argument(
        "--output",
        default=str(Path("proposals") / "fusion-dogfood-extension-v0.3" / "case-flow" / "calibration" / "real-baseline-2c539d0b-20260705" / "REAL_CALIBRATION_PREFLIGHT.json"),
    )
    case_flow_parser = subparsers.add_parser("case-flow")
    case_flow_parser.add_argument(
        "--output-root",
        default=str(Path("proposals") / "fusion-dogfood-extension-v0.3" / "case-flow"),
    )
    args = parser.parse_args(argv)
    if args.command in {None, "self-test"}:
        result = self_test()
    elif args.command == "arm-purity-self-test":
        result = arm_purity_self_test()
    elif args.command == "telemetry-validate":
        result = validate_codex_desktop_rollout_surface(Path(args.sessions_home))
        write_json(Path(args.output), result)
    elif args.command == "real-calibration-preflight":
        result = real_calibration_readiness(Path(args.case_flow_root))
        write_json(Path(args.output), result)
        if not result["valid"]:
            write_real_calibration_block_from_preflight(Path(args.case_flow_root), result)
    elif args.command == "case-flow":
        result = run_case_flow(Path(args.output_root))
    else:
        raise AssertionError(f"unhandled command {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
