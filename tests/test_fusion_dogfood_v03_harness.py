import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fusion_dogfood_v03_harness import (  # noqa: E402
    Budget,
    BudgetExceeded,
    BudgetMeter,
    EpisodeHarness,
    append_ledger_event,
    arm_purity_self_test,
    default_case_designs,
    evaluate_calibration,
    mechanism_availability_probe,
    negative_control_arms,
    parse_codex_desktop_rollout_trace,
    real_calibration_readiness,
    reject_forged_ledger_event,
    relational_ledger_grade,
    run_case_flow,
    self_test,
    separation_ordering_passes,
    validate_case_design,
    validate_arm_purity,
    validate_codex_desktop_rollout_surface,
    write_json,
)


def test_hard_budget_truncation_records_usage():
    meter = BudgetMeter(Budget(tool_calls=1, context_tokens=100))
    try:
        meter.consume(tool_calls=2, context_tokens=10)
    except BudgetExceeded:
        pass
    else:
        raise AssertionError("budget overrun was not truncated")
    usage = meter.receipt_usage()
    assert usage["truncated"] is True
    assert usage["truncation_reason"] == "tool_calls"
    assert usage["budget_accounting"]["method_state_operations_counted"] is True


def test_episode_chaining_relational_ledger_and_tamper_rejection():
    with tempfile.TemporaryDirectory(prefix="fusion-v03-episode-") as temporary:
        method_home = Path(temporary) / "method-home"
        harness = EpisodeHarness(method_home, Budget(tool_calls=3, context_tokens=500))

        def episode1(home, meter):
            meter.consume(tool_calls=1, context_tokens=50)
            append_ledger_event(home, {
                "event_type": "holder",
                "holder_id": "h1",
                "conclusion_id": "c-stale",
                "runtime_generated": True,
            })
            append_ledger_event(home, {
                "event_type": "active_recall",
                "conclusion_id": "c-stale",
                "runtime_generated": True,
            })

        def episode2(home, meter):
            meter.consume(tool_calls=1, context_tokens=50)
            append_ledger_event(home, {
                "event_type": "collapse",
                "invalidated_holder_id": "h1",
                "invalidated_conclusion_id": "c-stale",
                "runtime_generated": True,
            })
            append_ledger_event(home, {
                "event_type": "trace",
                "source_holder_id": "h1",
                "preserves_lineage": True,
                "runtime_generated": True,
            })
            append_ledger_event(home, {
                "event_type": "active_recall",
                "conclusion_id": "c-stale",
                "active": False,
                "runtime_generated": True,
            })
            append_ledger_event(home, {
                "event_type": "active_recall",
                "conclusion_id": "c-current",
                "active": True,
                "runtime_generated": True,
            })

        first = harness.run_episode("episode-1", episode1)
        second = harness.run_episode("episode-2", episode2)
        assert first.post_snapshot["tree_hash"] == second.pre_snapshot["tree_hash"]
        grade = relational_ledger_grade(method_home, episode1_holder_id="h1", stale_conclusion_id="c-stale")
        assert grade["passed"] is True
        assert reject_forged_ledger_event({"event_type": "collapse"}) is True


def test_negative_control_arms_and_separation_ordering():
    arms = negative_control_arms(Budget(tool_calls=3, context_tokens=500))
    assert [arm["arm"] for arm in arms] == ["no-method", "append-only", "method-baseline"]
    assert arms[0]["budget_accounting"] == arms[1]["budget_accounting"] == arms[2]["budget_accounting"]
    assert arms[1]["append_only_control"]["collapses"] is False
    assert separation_ordering_passes({"no-method": 0.2, "append-only": 0.4, "method-baseline": 0.8})
    assert not separation_ordering_passes({"no-method": 0.5, "append-only": 0.4, "method-baseline": 0.8})
    assert not separation_ordering_passes({"no-method": 0.2, "append-only": 0.77, "method-baseline": 0.8})
    purity = arm_purity_self_test()
    assert purity["valid"] is True


def test_mechanism_availability_probe_and_self_test():
    with tempfile.TemporaryDirectory(prefix="fusion-v03-probe-") as temporary:
        result = mechanism_availability_probe(Path(temporary) / "method-home", Budget(tool_calls=3, context_tokens=500))
        assert result["passed"] is True
        assert result["hidden_artifacts_read"] is False
        assert all(result["observable_classes"].values())
    result = self_test()
    if not result["valid"]:
        raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))


def test_case_designs_keep_success_and_rubric_hidden():
    designs = default_case_designs()
    assert len(designs) == 3
    for design in designs:
        validation = validate_case_design(design)
        if not validation["valid"]:
            raise AssertionError(json.dumps(validation, ensure_ascii=False, indent=2))
        public = design["public_case_spec"]
        assert "success" not in public
        assert "scoring_weights" not in public
        assert "hidden_check_id" not in public
        assert validation["winnable_walkthrough_hash"]


def test_case_flow_writes_preregistration_and_dry_run_receipts():
    with tempfile.TemporaryDirectory(prefix="fusion-v03-case-flow-") as temporary:
        root = Path(temporary) / "case-flow"
        result = run_case_flow(root)
        if not result["valid"]:
            raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))
        assert result["real_baseline_status"] == "pending_real_baseline_trials"
        for case_id in result["case_ids"]:
            public_design_path = root / "case-designs" / f"{case_id}.json"
            assert public_design_path.is_file()
            public_design = json.loads(public_design_path.read_text(encoding="utf-8"))
            public_text = json.dumps(public_design["public_case_spec"], ensure_ascii=False)
            assert '"success"' not in public_text
            assert '"scoring_weights"' not in public_text
            assert '"hidden_check_id"' not in public_text
            hidden_side = json.loads((root / "hidden-side" / f"{case_id}.json").read_text(encoding="utf-8"))
            assert hidden_side["candidate_visible"] is False
            assert hidden_side["winnable_walkthrough_hash"]
            assert (root / "failure-mechanisms" / f"{case_id}.json").is_file()
            prereg = json.loads((root / "preregistrations" / f"{case_id}.json").read_text(encoding="utf-8"))
            assert prereg["expected_method_baseline_mean_lt"] == 0.8
            assert prereg["winnable_in_principle"] is True
            assert prereg["hidden_artifacts_read"] is False
        aggregate_path = Path(result["dry_run_aggregate"])
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
        assert aggregate["real_baseline_status"] == "pending_real_baseline_trials"
        assert aggregate["r8_gate_dry_run"]["all_cases_preregistered_lt_0_80"] is True
        assert aggregate["r8_gate_dry_run"]["all_load_bearing_separation_passed"] is True
        assert aggregate["r8_gate_dry_run"]["budget_binding_cases_passed"] is True
        assert (root / "fixtures" / "FIXTURE_MANIFEST.json").is_file()


def test_calibration_gates_fail_closed_for_bad_scores():
    design = default_case_designs()[0]
    receipts = []
    for arm, scores in {
        "no-method": [0.2, 0.2],
        "append-only": [0.7, 0.7],
        "method-baseline": [0.72, 0.72],
    }.items():
        for trial, score in enumerate(scores, start=1):
            receipts.append({
                "arm": arm,
                "trial": trial,
                "weighted_score": score,
                "actual_usage": {"truncated": False, "tool_calls": 1, "context_tokens": 1},
                "receipt_hash": f"{arm}-{trial}",
            })
    result = evaluate_calibration(design, receipts)
    assert result["status"] == "separation_failed"


def test_budget_saturation_case_fails_when_budget_does_not_bind():
    design = default_case_designs()[2]
    receipts = [
        {
            "arm": "method-baseline",
            "trial": 1,
            "weighted_score": 0.72,
            "actual_usage": {"truncated": False, "tool_calls": 1, "context_tokens": 100},
            "receipt_hash": "budget-low-1",
        },
        {
            "arm": "method-baseline",
            "trial": 2,
            "weighted_score": 0.74,
            "actual_usage": {"truncated": False, "tool_calls": 1, "context_tokens": 100},
            "receipt_hash": "budget-low-2",
        },
    ]
    result = evaluate_calibration(design, receipts)
    assert result["status"] == "budget_binding_failed"
    assert result["budget_binding"]["passed"] is False


def test_codex_desktop_rollout_parser_provides_r3_telemetry():
    with tempfile.TemporaryDirectory(prefix="fusion-v03-rollout-") as temporary:
        sessions = Path(temporary) / "sessions"
        rollout = sessions / "2026" / "07" / "05" / "rollout-test.jsonl"
        rollout.parent.mkdir(parents=True)
        rows = [
            {
                "timestamp": "2026-07-05T00:00:00Z",
                "type": "session_meta",
                "payload": {
                    "type": None,
                    "cli_version": "0.test",
                    "source": {"subagent": {"thread_spawn": {"agent_role": "worker"}}},
                },
            },
            {
                "timestamp": "2026-07-05T00:00:01Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-1"},
            },
            {
                "timestamp": "2026-07-05T00:00:02Z",
                "type": "response_item",
                "payload": {"type": "function_call", "name": "shell_command", "call_id": "call-1"},
            },
            {
                "timestamp": "2026-07-05T00:00:03Z",
                "type": "response_item",
                "payload": {"type": "function_call", "name": "shell_command", "call_id": "call-2"},
            },
            {
                "timestamp": "2026-07-05T00:00:04Z",
                "type": "response_item",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {"total_tokens": 120},
                        "last_token_usage": {"total_tokens": 80},
                    },
                },
            },
        ]
        rollout.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        trace = parse_codex_desktop_rollout_trace(rollout, Budget(tool_calls=1, context_tokens=100))
        assert trace["tool_call_count"] == 2
        assert trace["context_token_count"] == 120
        assert trace["actual_usage"]["truncated"] is True
        assert trace["actual_usage"]["truncation_reason"] == "tool_calls"
        assert trace["actual_usage"]["scoring_time_truncation"]["effective_tool_calls"] == 1
        validation = validate_codex_desktop_rollout_surface(sessions)
        assert validation["valid"] is True
        assert validation["r3_required_telemetry"] == {
            "tool_call_count": True,
            "token_usage": True,
            "truncation_status": True,
        }


def test_arm_purity_rejects_contaminated_negative_controls():
    contaminated_no_method = {
        "arm_purity_observables": {
            "method_runtime_operation_count": 1,
            "workspace_method_bootstrap_count": 1,
            "append_only_forbidden_operation_count": 0,
        }
    }
    clean_no_method = {
        "arm_purity_observables": {
            "method_runtime_operation_count": 0,
            "workspace_method_bootstrap_count": 0,
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
    assert validate_arm_purity("no-method", contaminated_no_method)["valid"] is False
    assert validate_arm_purity("no-method", clean_no_method)["valid"] is True
    append_result = validate_arm_purity("append-only", contaminated_append_only)
    assert append_result["valid"] is False
    assert "append_only_used_consolidation_supersession_or_collapse" in append_result["issues"]


def test_codex_exec_rollout_parser_provides_clean_no_method_observables():
    with tempfile.TemporaryDirectory(prefix="fusion-v03-codex-exec-") as temporary:
        rollout = Path(temporary) / "rollout-clean-exec.jsonl"
        rows = [
            {
                "timestamp": "2026-07-05T00:00:00Z",
                "type": "session_meta",
                "payload": {
                    "type": None,
                    "id": "019f3208-4c15-76b1-bd6d-ce86955782b2",
                    "cli_version": "0.142.5",
                    "source": "exec",
                },
            },
            {
                "timestamp": "2026-07-05T00:00:01Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-clean"},
            },
            {
                "timestamp": "2026-07-05T00:00:02Z",
                "type": "response_item",
                "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "PROBE OK"}]},
            },
            {
                "timestamp": "2026-07-05T00:00:03Z",
                "type": "response_item",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {"total_tokens": 9130},
                        "last_token_usage": {"total_tokens": 9130},
                    },
                },
            },
        ]
        rollout.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        trace = parse_codex_desktop_rollout_trace(rollout, Budget(tool_calls=4, context_tokens=5200))
        assert trace["environment_ids"] == ["codex-cli:exec"]
        assert trace["context_token_count"] == 9130
        assert trace["actual_usage"]["truncated"] is True
        assert trace["actual_usage"]["truncation_reason"] == "context_tokens"
        assert validate_arm_purity("no-method", trace)["valid"] is True


def test_real_calibration_preflight_fails_without_entity_fixtures():
    with tempfile.TemporaryDirectory(prefix="fusion-v03-real-preflight-") as temporary:
        root = Path(temporary) / "case-flow"
        run_case_flow(root)
        shutil.rmtree(root / "fixtures")
        telemetry = {
            "schema_version": "fusion_dogfood_v03_harness_v0.1",
            "valid": True,
            "selected": True,
            "selected_surface": "codex_desktop_subagent_rollout_jsonl",
            "environment_id": "codex-desktop-subagent-rollout-jsonl-v0.142.5",
            "validation_hash": "telemetry-ok",
        }
        write_json(root / "calibration" / "telemetry-surface" / "codex-desktop-subagent-rollout.json", telemetry)
        preflight = real_calibration_readiness(root)
        assert preflight["valid"] is False
        assert "one_or_more_cases_not_fixture_ready" in preflight["issues"]
        assert all("public_fixture_root_missing" in row["issues"] for row in preflight["cases"])
