import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fusion_dogfood_v03_harness import Budget, validate_arm_purity  # noqa: E402
import qwen_v03_runner as qwen_runner  # noqa: E402
from qwen_v03_runner import (  # noqa: E402
    FakeOpenAICompatibleClient,
    QwenRunnerConfig,
    fake_response,
    json_object_from_text,
    message_fingerprints,
    parse_qwen_telemetry,
    qwen_arm_config,
    qwen_surface_self_test,
    public_fixture_index,
    run_trial_from_paths,
    run_qwen_trial,
    safe_child,
    write_receipt_from_final_text,
)


def test_qwen_arm_configs_are_pure_and_distinct():
    assert qwen_arm_config("no-method")["tools"] == ["read_file"]
    assert qwen_arm_config("append-only")["append_only_notes"] is True
    assert qwen_arm_config("append-only")["method_runtime"] is False
    assert qwen_arm_config("method-baseline")["method_runtime"] is True
    assert qwen_arm_config("method-baseline")["run_command"] is True


def test_qwen_runner_accumulates_usage_and_live_truncates_without_api():
    with tempfile.TemporaryDirectory(prefix="qwen-runner-test-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "README.md").write_text("hello\n", encoding="utf-8")
        trace = run_qwen_trial(
            client=FakeOpenAICompatibleClient([fake_response("large", total_tokens=80)]),
            config=QwenRunnerConfig(model_snapshot="qwen-test-snapshot-20260706"),
            arm="no-method",
            budget=Budget(tool_calls=4, context_tokens=50),
            prompt="Return large.",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )
        assert trace["surface"] == "qwen_openai_compatible_telemetry"
        assert trace["environment_ids"] == ["qwen-api:qwen-test-snapshot-20260706"]
        assert trace["actual_usage"]["truncated"] is True
        assert trace["actual_usage"]["truncation_reason"] == "context_tokens"
        assert validate_arm_purity("no-method", trace)["valid"] is True


def test_qwen_context_budget_uses_peak_response_not_cumulative_sum():
    with tempfile.TemporaryDirectory(prefix="qwen-runner-peak-test-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "note.txt").write_text("target fact\n", encoding="utf-8")
        tool_call = {
            "id": "call-read",
            "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "note.txt"})},
        }
        trace = run_qwen_trial(
            client=FakeOpenAICompatibleClient([
                fake_response(tool_calls=[tool_call], total_tokens=40),
                fake_response("target fact", total_tokens=40),
            ]),
            config=QwenRunnerConfig(model_snapshot="qwen-test-snapshot-20260706"),
            arm="no-method",
            budget=Budget(tool_calls=2, context_tokens=50),
            prompt="Read note.txt.",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )
        assert trace["context_token_rule"] == "peak_single_response_total_tokens"
        assert trace["context_token_count"] == 40
        assert trace["billable_total_tokens"] == 80
        assert trace["actual_usage"]["truncated"] is False


def test_qwen_runner_tool_loop_and_append_only_purity():
    with tempfile.TemporaryDirectory(prefix="qwen-runner-tool-test-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "note.txt").write_text("target fact\n", encoding="utf-8")
        tool_call = {
            "id": "call-read",
            "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "note.txt"})},
        }
        trace = run_qwen_trial(
            client=FakeOpenAICompatibleClient([
                fake_response(tool_calls=[tool_call], total_tokens=20),
                fake_response("target fact", total_tokens=20),
            ]),
            config=QwenRunnerConfig(model_snapshot="qwen-test-snapshot-20260706"),
            arm="append-only",
            budget=Budget(tool_calls=2, context_tokens=100),
            prompt="Read note.txt.",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )
        assert trace["tool_call_count"] == 1
        assert trace["tool_call_names"] == ["read_file"]
        assert validate_arm_purity("append-only", trace)["valid"] is True


def test_safe_child_accepts_absolute_path_inside_fixture_root():
    with tempfile.TemporaryDirectory(prefix="qwen-safe-child-") as temporary:
        root = Path(temporary).resolve()
        inside = root / "episode-1" / "README.md"
        inside.parent.mkdir()
        inside.write_text("ok\n", encoding="utf-8")
        assert safe_child(root, str(inside)) == inside.resolve()


def test_public_fixture_index_lists_relative_files_only():
    with tempfile.TemporaryDirectory(prefix="qwen-fixture-index-") as temporary:
        root = Path(temporary)
        (root / "episode-1").mkdir()
        (root / "episode-1" / "README.md").write_text("ok\n", encoding="utf-8")

        index = public_fixture_index(root)

        assert index == "episode-1/README.md"
        assert str(root) not in index


def test_qwen_run_command_rejects_arbitrary_shell_write():
    with tempfile.TemporaryDirectory(prefix="qwen-runner-command-test-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        target = root / "workspace" / "should-not-exist.txt"
        bad_call = {
            "id": "call-bad-shell",
            "type": "function",
            "function": {
                "name": "run_command",
                "arguments": json.dumps({"command": f"Set-Content -LiteralPath '{target}' -Value bad"}),
            },
        }
        trace = run_qwen_trial(
            client=FakeOpenAICompatibleClient([
                fake_response(tool_calls=[bad_call], total_tokens=20),
                fake_response("done", total_tokens=20),
            ]),
            config=QwenRunnerConfig(model_snapshot="qwen-test-snapshot-20260706"),
            arm="method-baseline",
            budget=Budget(tool_calls=2, context_tokens=100),
            prompt="Try the command.",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )
        assert trace["tool_call_names"] == ["run_command"]
        assert not target.exists()


def test_parse_qwen_telemetry_rejects_append_only_forbidden_tool():
    record = {
        "runner_id": "qwen-openai-compatible-v0.1",
        "model_snapshot": "qwen-test-snapshot-20260706",
        "environment_id": "qwen-api:qwen-test-snapshot-20260706",
        "arm": "append-only",
        "arm_config": qwen_arm_config("append-only"),
        "budget": {"tool_calls": 4, "context_tokens": 100},
        "events": [{"type": "response", "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}],
        "tool_events": [{"type": "tool_result", "name": "run_command", "result": {"ok": True}}],
    }
    trace = parse_qwen_telemetry(record)
    result = validate_arm_purity("append-only", trace)
    assert result["valid"] is False
    assert "append_only_used_consolidation_supersession_or_collapse" in result["issues"]


def test_parse_qwen_telemetry_detects_bootstrap_from_message_fingerprints():
    record = {
        "runner_id": "qwen-openai-compatible-v0.1",
        "model_snapshot": "qwen-test-snapshot-20260706",
        "environment_id": "qwen-api:qwen-test-snapshot-20260706",
        "arm": "no-method",
        "arm_config": qwen_arm_config("no-method"),
        "budget": {"tool_calls": 4, "context_tokens": 100},
        "events": [{"type": "response", "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}],
        "message_events": message_fingerprints([
            {"role": "user", "content": "Use `$solve-with-weilan` before answering."}
        ]),
        "tool_events": [],
    }
    trace = parse_qwen_telemetry(record)
    result = validate_arm_purity("no-method", trace)
    assert result["valid"] is False
    assert "no_method_surface_contains_method_bootstrap" in result["issues"]


def test_parse_qwen_telemetry_allows_negative_control_prohibition_text():
    record = {
        "runner_id": "qwen-openai-compatible-v0.1",
        "model_snapshot": "qwen-test-snapshot-20260706",
        "environment_id": "qwen-api:qwen-test-snapshot-20260706",
        "arm": "no-method",
        "arm_config": qwen_arm_config("no-method"),
        "budget": {"tool_calls": 4, "context_tokens": 100},
        "events": [{"type": "response", "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}],
        "message_events": message_fingerprints([
            {"role": "user", "content": "NEGATIVE CONTROL ARM: Do not use solve-with-weilan."}
        ]),
        "tool_events": [],
    }
    trace = qwen_runner.parse_qwen_telemetry(record)
    result = validate_arm_purity("no-method", trace)
    assert result["valid"] is True


def test_qwen_surface_self_test_writes_receipt_without_live_api():
    result = qwen_surface_self_test()
    assert result["valid"] is True
    assert result["live_api_called"] is False
    assert result["api_key_read"] is False


def test_run_trial_from_paths_accepts_max_model_response_override(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="qwen-runner-max-responses-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        workspace = root / "workspace"
        fixture.mkdir()
        prompt_path = root / "prompt.txt"
        output_path = root / "telemetry.json"
        receipt_path = root / "receipt.json"
        prompt_path.write_text("Read note.txt, then answer.", encoding="utf-8")
        (fixture / "note.txt").write_text("target fact\n", encoding="utf-8")
        read_call = {
            "id": "call-read",
            "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "note.txt"})},
        }
        fake_client = FakeOpenAICompatibleClient([
            fake_response(tool_calls=[read_call], total_tokens=20),
            fake_response('{"ok": true}', total_tokens=20),
        ])
        monkeypatch.setenv("QWEN_MODEL_SNAPSHOT", "qwen-test-snapshot-20260706")
        monkeypatch.setattr(
            qwen_runner.OpenAICompatibleClient,
            "from_env",
            classmethod(lambda cls, **kwargs: fake_client),
        )

        trace = run_trial_from_paths(
            arm="no-method",
            prompt_path=prompt_path,
            fixture_root=fixture,
            workspace_root=workspace,
            output_path=output_path,
            receipt_output=receipt_path,
            tool_calls=2,
            context_tokens=100,
            max_model_responses=1,
        )

        assert len(fake_client.requests) == 1
        assert trace["final_text"] == ""
        assert trace["valid"] is False


def test_qwen_runner_can_force_final_after_tool_threshold():
    with tempfile.TemporaryDirectory(prefix="qwen-runner-force-final-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        (fixture / "note.txt").write_text("target fact\n", encoding="utf-8")
        read_call = {
            "id": "call-read",
            "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "note.txt"})},
        }
        extra_read_call = {
            "id": "call-read-extra",
            "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "note.txt"})},
        }
        fake_client = FakeOpenAICompatibleClient([
            fake_response(tool_calls=[read_call, extra_read_call], total_tokens=20),
            fake_response('{"case_id":"probe","decision":"done"}', total_tokens=25),
        ])

        trace = run_qwen_trial(
            client=fake_client,
            config=QwenRunnerConfig(
                model_snapshot="qwen-test-snapshot-20260706",
                max_model_responses=3,
                force_final_after_tool_calls=1,
            ),
            arm="no-method",
            budget=Budget(tool_calls=3, context_tokens=100),
            prompt="Read note.txt.",
            fixture_root=fixture,
            workspace_root=root / "workspace",
        )

        assert len(fake_client.requests) == 2
        assert "tools" in fake_client.requests[0]
        assert "tools" not in fake_client.requests[1]
        assert fake_client.requests[1]["tool_choice"] == "none"
        assert trace["tool_call_count"] == 1
        assert trace["actual_usage"]["forced_finalization"]["requested"] is True
        assert trace["final_text"].startswith('{"case_id"')


def test_write_receipt_normalizes_usage_from_telemetry():
    with tempfile.TemporaryDirectory(prefix="qwen-receipt-normalize-") as temporary:
        receipt_path = Path(temporary) / "receipt.json"
        receipt = write_receipt_from_final_text(
            '{"case_id":"probe","actual_usage":{"tool_calls":99}}',
            receipt_path,
            observed_actual_usage={"tool_calls": 2, "context_tokens": 50},
            metadata={"trial_id": "trial-1", "arm": "no-method", "trial": 1},
        )

        assert receipt["trial_id"] == "trial-1"
        assert receipt["arm"] == "no-method"
        assert receipt["actual_usage"] == {"tool_calls": 2, "context_tokens": 50}
        assert receipt["actual_usage_self_report"] == {"tool_calls": 99}


def test_json_object_from_text_extracts_fenced_json_after_prose():
    text = "analysis first\n```json\n{\"case_id\":\"probe\",\"decision\":\"Y\"}\n```"
    assert json_object_from_text(text) == {"case_id": "probe", "decision": "Y"}
