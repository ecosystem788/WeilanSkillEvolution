"""Regression tests for bounded frame abandonment and terminal semantics."""

import argparse
import importlib.machinery
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import weilan_trace


SCRIPT = Path(__file__).with_name("weilan_trace.py")
ROLLBACK_BASE = Path(
    "D:/WeilanSkillEvolution/proposals/live-artifact-lineage-unclosed-v0.1/"
    "evidence/weilan_trace.py.live-dec68230241b.copy"
)
SCOPE = "frame-abandon-test"


def completed(arguments, environment):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def run(arguments, environment):
    result = completed(arguments, environment)
    if result.returncode:
        raise AssertionError(f"command failed: {result.stderr}")
    return json.loads(result.stdout)


@pytest.fixture()
def fixture(tmp_path):
    method_state = tmp_path / "method-state"
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()
    environment = os.environ.copy()
    environment["WEILAN_METHOD_HOME"] = str(method_state)
    return {
        "method_state": method_state,
        "workspace": str(workspace_path),
        "environment": environment,
    }


def open_frame(fixture, *, lineaged=True):
    arguments = [
        "open",
        "--level",
        "L2",
        "--workspace",
        fixture["workspace"],
        "--problem",
        "frame abandonment regression",
        "--success",
        "bounded recovery remains honest",
    ]
    if lineaged:
        arguments.extend(
            [
                "--scope",
                SCOPE,
                "--branch",
                "main",
                "--relation",
                "root",
            ]
        )
    return run(arguments, fixture["environment"])


def frame_path(fixture, frame_id):
    matches = list(fixture["method_state"].glob(f"frames/*/{frame_id}.jsonl"))
    if len(matches) != 1:
        raise AssertionError(f"expected one frame path for {frame_id}: {matches}")
    return matches[0]


def read_events(fixture, frame_id):
    return [
        json.loads(line)
        for line in frame_path(fixture, frame_id).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_events(fixture, frame_id, events):
    frame_path(fixture, frame_id).write_text(
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


def read_audits(fixture, frame_id=None):
    audits = []
    for path in fixture["method_state"].glob("memory/audits/persistence/**/*.jsonl"):
        audits.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    if frame_id is not None:
        return [record for record in audits if record["frame_id"] == frame_id]
    return audits


def method_state_bytes(fixture):
    root = fixture["method_state"]
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def age_frame(fixture, frame_id, *, seconds=10800):
    path = frame_path(fixture, frame_id)
    events = read_events(fixture, frame_id)
    events[-1]["timestamp_utc"] = (
        datetime.now(timezone.utc) - timedelta(seconds=seconds)
    ).replace(microsecond=0).isoformat()
    write_events(fixture, frame_id, events)


def abandon(fixture, frame_id, *, threshold=7200):
    return completed(
        [
            "frame-abandon",
            "--frame-id",
            frame_id,
            "--silence-threshold-seconds",
            str(threshold),
            "--evidence",
            json.dumps(
                {
                    "alert_id": "fixture-alert",
                    "consecutive_count": 10,
                    "source_ref": "fixture:peer-health",
                }
            ),
            "--reason",
            "bounded regression fixture",
        ],
        fixture["environment"],
    )


def abandon_successfully(fixture, frame_id, *, threshold=7200):
    result = abandon(fixture, frame_id, threshold=threshold)
    if result.returncode:
        raise AssertionError(f"abandon failed: {result.stderr}")
    return json.loads(result.stdout)


def close_frame(fixture, frame_id):
    run(
        [
            "persistence-audit",
            "--frame-id",
            frame_id,
            "--trigger",
            "round_end",
            "--decision",
            "not_persisted",
            "--reason",
            "frame abandonment regression has no durable conclusion",
        ],
        fixture["environment"],
    )
    run(
        [
            "close",
            "--frame-id",
            frame_id,
            "--outcome",
            "success",
            "--verdict",
            "normal close snapshot",
        ],
        fixture["environment"],
    )


def test_a_silence_below_threshold_is_rejected(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    result = abandon(fixture, frame_id)
    assert result.returncode != 0
    assert "below threshold" in result.stderr
    assert len(read_events(fixture, frame_id)) == 1


def test_b_threshold_below_hard_minimum_is_rejected(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    result = abandon(fixture, frame_id, threshold=3599)
    assert result.returncode != 0
    assert "at least 3600 seconds" in result.stderr
    assert len(read_events(fixture, frame_id)) == 1


def test_c_silent_frame_can_be_abandoned_and_continued(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    receipt = abandon_successfully(fixture, frame_id)
    assert receipt["abandoned"] is True
    successor = run(
        [
            "open",
            "--level",
            "L2",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
            "--branch",
            "main",
            "--relation",
            "continue",
            "--parent",
            frame_id,
            "--problem",
            "successor after abandonment",
            "--success",
            "causal continuation succeeds",
        ],
        fixture["environment"],
    )
    assert successor["causal"]["parent_frame_ids"] == [frame_id]


def test_d_close_rejects_an_abandoned_frame(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    result = completed(
        [
            "close",
            "--frame-id",
            frame_id,
            "--outcome",
            "failed",
            "--verdict",
            "must not exist",
        ],
        fixture["environment"],
    )
    assert result.returncode != 0
    assert "cannot close an abandoned frame" in result.stderr


def test_e_argparse_rejects_generic_frame_abandoned_event(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    result = completed(
        ["event", "--frame-id", frame_id, "--type", "frame_abandoned"],
        fixture["environment"],
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_f_runtime_rejects_generic_frame_abandoned_event(fixture, monkeypatch):
    frame_id = open_frame(fixture)["frame_id"]
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(fixture["method_state"]))
    args = argparse.Namespace(
        frame_id=frame_id,
        type="frame_abandoned",
        field=[],
    )
    with pytest.raises(ValueError, match="dedicated command"):
        weilan_trace.command_event(args)


def test_g_transaction_gate_rejects_abandoned_but_preserves_opened(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    opened = read_events(fixture, frame_id)[0]
    weilan_trace.validate_transaction_record_scope(
        "frame", opened, fixture["workspace"], SCOPE
    )
    abandoned = dict(opened)
    abandoned["event_type"] = "frame_abandoned"
    abandoned["data"] = {
        "reason": "forbidden transaction path",
        "silence_threshold_seconds": 7200,
        "observed_silence_seconds": 7201,
        "evidence": {},
    }
    with pytest.raises(ValueError, match="frame_abandoned intent is forbidden"):
        weilan_trace.validate_transaction_record_scope(
            "frame", abandoned, fixture["workspace"], SCOPE
        )


def test_h_abandoned_frame_rejects_audit_and_normal_event(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    audit = completed(
        [
            "persistence-audit",
            "--frame-id",
            frame_id,
            "--trigger",
            "round_end",
            "--decision",
            "not_persisted",
            "--reason",
            "must not append",
        ],
        fixture["environment"],
    )
    event = completed(
        [
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "evidence_observed",
            "--field",
            "summary=must not append",
        ],
        fixture["environment"],
    )
    assert audit.returncode != 0
    assert "cannot audit an abandoned frame" in audit.stderr
    assert event.returncode != 0
    assert "cannot append to an abandoned frame" in event.stderr


def test_i_audits_are_complete_not_persisted_and_retry_safe(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    receipt = abandon_successfully(fixture, frame_id)
    frame_audits = read_audits(fixture, frame_id)
    assert set(receipt["required_audit_triggers"]).issubset(
        set(receipt["completed_audit_triggers"])
    )
    assert frame_audits
    assert all(record["decision"] == "NOT_PERSISTED" for record in frame_audits)
    assert all(record["audit_origin"] == "frame_abandon" for record in frame_audits)
    retry = abandon(fixture, frame_id)
    assert retry.returncode != 0
    assert "already abandoned" in retry.stderr
    assert "audit trigger already recorded" not in retry.stderr


def test_j_self_projection_distinguishes_terminal_from_closed(fixture):
    run(
        [
            "memory-control",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
            "--state",
            "active",
            "--directive",
            "activate frame abandonment fixture",
        ],
        fixture["environment"],
    )
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    projection = run(
        ["self-project", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    branch = projection["branch_heads"]["main"]
    assert branch["head_closed"] is False
    assert branch["head_terminal"] is True
    assert branch["head_abandoned"] is True
    assert branch["audit_valid"] is True


def load_rollback_module():
    loader = importlib.machinery.SourceFileLoader(
        "weilan_trace_rollback_snapshot", str(ROLLBACK_BASE)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_k_episode_marks_abandonment_without_changing_normal_snapshot(fixture):
    normal_frame = open_frame(fixture)["frame_id"]
    close_frame(fixture, normal_frame)
    normal_events = read_events(fixture, normal_frame)
    rollback_module = load_rollback_module()
    old_bytes = json.dumps(
        rollback_module.summarize_episode(normal_events),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    new_bytes = json.dumps(
        weilan_trace.summarize_episode(normal_events),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert new_bytes == old_bytes

    abandoned_fixture = {
        **fixture,
        "workspace": str(Path(fixture["workspace"]).parent / "abandoned-workspace"),
    }
    Path(abandoned_fixture["workspace"]).mkdir()
    abandoned_frame = open_frame(abandoned_fixture)["frame_id"]
    age_frame(abandoned_fixture, abandoned_frame)
    abandon_successfully(abandoned_fixture, abandoned_frame)
    episode = weilan_trace.summarize_episode(
        read_events(abandoned_fixture, abandoned_frame)
    )
    assert episode["outcome"] == "abandoned"
    assert episode["verdict"] == ""
    assert episode["abandoned"] is True


def test_l_archive_plan_treats_abandoned_as_terminal(fixture):
    abandoned = open_frame(fixture)["frame_id"]
    age_frame(fixture, abandoned)
    abandon_successfully(fixture, abandoned)
    open_id = open_frame(fixture, lineaged=False)["frame_id"]
    age_frame(fixture, open_id)
    non_head = abandon(fixture, open_id)
    assert non_head.returncode != 0
    assert "current lineage head" in non_head.stderr
    before = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
    plan = run(
        ["memory-archive-plan", "--workspace", fixture["workspace"], "--before", before],
        fixture["environment"],
    )
    eligible_ids = {
        item["frame_id"] for item in plan["eligible_closed_frames"]
    }
    blocked = {item["frame_id"]: item for item in plan["blocked_frames"]}
    assert abandoned in eligible_ids
    assert "frame_not_terminal" in blocked[open_id]["reasons"]


def test_m_lineage_head_advances_after_abandoned_parent(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    successor = run(
        [
            "open",
            "--level",
            "L2",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
            "--branch",
            "main",
            "--relation",
            "continue",
            "--parent",
            frame_id,
            "--problem",
            "advance lineage head",
            "--success",
            "head advances",
        ],
        fixture["environment"],
    )
    lineage = run(
        ["lineage-show", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert lineage["valid"] is True
    assert lineage["branches"]["main"]["head_frame_id"] == successor["frame_id"]


def append_collapse(fixture, frame_id):
    run(
        [
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "minimal_unit_collapsed",
            "--field",
            "scope=assumption",
            "--field",
            "former_holder=fixture-holder",
            "--field",
            "invalidating_evidence=fixture evidence",
        ],
        fixture["environment"],
    )
    return read_events(fixture, frame_id)[-1]


def append_probation(fixture, frame_id):
    run(
        [
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "holder_probation_started",
            "--field",
            "candidate_id=fixture-holder",
        ],
        fixture["environment"],
    )
    return read_events(fixture, frame_id)[-1]


def continue_from(fixture, frame_id, *, problem):
    return run(
        [
            "open",
            "--level",
            "L2",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
            "--branch",
            "main",
            "--relation",
            "continue",
            "--parent",
            frame_id,
            "--problem",
            problem,
            "--success",
            "successor remains reachable",
        ],
        fixture["environment"],
    )


def test_n_collapse_obligation_is_recorded_without_blocking_abandonment(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    collapsed = append_collapse(fixture, frame_id)
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    terminal = read_events(fixture, frame_id)[-1]
    assert terminal["data"]["unmet_obligations_basis"] == (
        weilan_trace.FRAME_ABANDON_UNMET_OBLIGATIONS_BASIS
    )
    assert terminal["data"]["unmet_obligations"] == [
        {
            "kind": "collapse_missing_following_trace",
            "event_id": collapsed["event_id"],
        }
    ]
    assert continue_from(
        fixture, frame_id, problem="successor after incomplete collapse"
    )["causal"]["parent_frame_ids"] == [frame_id]


def test_o_probation_obligation_is_recorded_without_blocking_abandonment(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    probation = append_probation(fixture, frame_id)
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    terminal = read_events(fixture, frame_id)[-1]
    assert terminal["data"]["unmet_obligations"] == [
        {
            "kind": "probation_missing_following_resolution",
            "event_id": probation["event_id"],
        }
    ]
    assert continue_from(
        fixture, frame_id, problem="successor after incomplete probation"
    )["causal"]["parent_frame_ids"] == [frame_id]


@pytest.mark.parametrize("incomplete_kind", ["collapse", "probation"])
def test_p_normal_close_keeps_incomplete_obligations_strict(
    fixture, incomplete_kind
):
    frame_id = open_frame(fixture)["frame_id"]
    if incomplete_kind == "collapse":
        append_collapse(fixture, frame_id)
        triggers = ["round_end", "route_change"]
        expected_error = "collapse requires a following trace_emitted"
    else:
        append_probation(fixture, frame_id)
        triggers = ["round_end"]
        expected_error = (
            "probation requires a following discriminating test, collapse, or block"
        )
    for trigger in triggers:
        run(
            [
                "persistence-audit",
                "--frame-id",
                frame_id,
                "--trigger",
                trigger,
                "--decision",
                "not_persisted",
                "--reason",
                "strict close regression",
            ],
            fixture["environment"],
        )
    result = completed(
        [
            "close",
            "--frame-id",
            frame_id,
            "--outcome",
            "failed",
            "--verdict",
            "must remain open",
        ],
        fixture["environment"],
    )
    assert result.returncode != 0
    assert expected_error in result.stderr
    assert read_events(fixture, frame_id)[-1]["event_type"] != "frame_closed"


def test_q_validation_failure_writes_no_automatic_audit(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    run(
        [
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "evidence_observed",
            "--field",
            "summary=fixture duplicate event id",
        ],
        fixture["environment"],
    )
    events = read_events(fixture, frame_id)
    events[-1]["event_id"] = events[0]["event_id"]
    write_events(fixture, frame_id, events)
    age_frame(fixture, frame_id)
    result = abandon(fixture, frame_id)
    assert result.returncode != 0
    assert "event_id values must be unique" in result.stderr
    assert read_audits(fixture, frame_id) == []


def test_r_audit_preparation_does_not_satisfy_close_and_retry_reuses_it(
    fixture, monkeypatch
):
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(fixture["method_state"]))
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    events = read_events(fixture, frame_id)
    weilan_trace.append_abandonment_audits(
        frame_id,
        events,
        weilan_trace.canonical_workspace(fixture["workspace"]),
        SCOPE,
        7200,
    )
    prepared = read_audits(fixture, frame_id)
    assert len(prepared) == 1
    assert prepared[0]["audit_origin"] == "frame_abandon"
    show = run(
        ["persistence-audit-show", "--frame-id", frame_id],
        fixture["environment"],
    )
    assert show["completed_triggers"] == []
    assert show["missing_triggers"] == ["round_end"]
    rejected = completed(
        [
            "close",
            "--frame-id",
            frame_id,
            "--outcome",
            "success",
            "--verdict",
            "automatic audit must not satisfy close",
        ],
        fixture["environment"],
    )
    assert rejected.returncode != 0
    assert "missing triggers: round_end" in rejected.stderr
    run(
        [
            "persistence-audit",
            "--frame-id",
            frame_id,
            "--trigger",
            "round_end",
            "--decision",
            "not_persisted",
            "--reason",
            "live regression audit",
        ],
        fixture["environment"],
    )
    run(
        [
            "close",
            "--frame-id",
            frame_id,
            "--outcome",
            "success",
            "--verdict",
            "live audit closes frame",
        ],
        fixture["environment"],
    )

    retry_fixture = {
        **fixture,
        "workspace": str(Path(fixture["workspace"]).parent / "retry-workspace"),
    }
    Path(retry_fixture["workspace"]).mkdir()
    retry_id = open_frame(retry_fixture)["frame_id"]
    age_frame(retry_fixture, retry_id)
    retry_events = read_events(retry_fixture, retry_id)
    weilan_trace.append_abandonment_audits(
        retry_id,
        retry_events,
        weilan_trace.canonical_workspace(retry_fixture["workspace"]),
        SCOPE,
        7200,
    )
    prepared_ids = [
        record["audit_id"] for record in read_audits(retry_fixture, retry_id)
    ]
    receipt = abandon_successfully(retry_fixture, retry_id)
    assert receipt["appended_audit_ids"] == []
    assert [
        record["audit_id"] for record in read_audits(retry_fixture, retry_id)
    ] == prepared_ids
    show = run(
        ["persistence-audit-show", "--frame-id", retry_id],
        retry_fixture["environment"],
    )
    assert show["completed_triggers"] == ["round_end"]
    assert show["missing_triggers"] == []


def test_s_v2_abandonment_shape_remains_valid_and_reachable(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    events = read_events(fixture, frame_id)
    events[-1]["data"].pop("unmet_obligations")
    events[-1]["data"].pop("unmet_obligations_basis")
    write_events(fixture, frame_id, events)
    validation = run(
        ["validate", "--frame-id", frame_id, "--require-closed"],
        fixture["environment"],
    )
    assert validation["valid"] is True
    assert validation["markers"][0]["code"] == (
        "frame_abandoned_v2_obligations_unrecorded"
    )
    lineage = run(
        ["lineage-show", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert lineage["validation_markers"] == [
        {
            "frame_id": frame_id,
            "code": "frame_abandoned_v2_obligations_unrecorded",
            "recorded_basis": None,
            "current_basis": (
                weilan_trace.FRAME_ABANDON_UNMET_OBLIGATIONS_BASIS
            ),
        }
    ]
    projection = run(
        ["self-project", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert projection["branch_heads"]["main"]["head_validation_markers"] == [
        {
            "code": "frame_abandoned_v2_obligations_unrecorded",
            "recorded_basis": None,
            "current_basis": (
                weilan_trace.FRAME_ABANDON_UNMET_OBLIGATIONS_BASIS
            ),
        }
    ]
    state_before_contract = method_state_bytes(fixture)
    contract = run(
        ["metabolic-contract", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert method_state_bytes(fixture) == state_before_contract
    assert (
        contract["branches"]["main"]["head_validation_markers"]
        == projection["branch_heads"]["main"]["head_validation_markers"]
    )
    assert contract["issues"] == projection["issues"]
    assert contract["status"] == "CONTROL_BLOCKED"
    assert contract["allowed_dispositions"] == ["yield"]
    run(
        [
            "memory-control",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
            "--state",
            "active",
            "--directive",
            "activate recall shape regression",
        ],
        fixture["environment"],
    )
    run(
        [
            "projection-rebuild",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
        ],
        fixture["environment"],
    )
    recall = run(
        ["memory-recall", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert recall["activation"]["state"] == "ACTIVE"
    assert "branch_heads" not in recall["projection"]
    assert "validation_markers" not in recall["projection"]
    assert "frame_abandoned_v2_obligations_unrecorded" not in json.dumps(recall)
    successor = continue_from(
        fixture, frame_id, problem="successor after v2 abandonment"
    )
    assert successor["causal"]["parent_frame_ids"] == [frame_id]
    lineage_after = run(
        ["lineage-show", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert lineage_after["validation_markers"] == lineage["validation_markers"]
    projection_after = run(
        ["self-project", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert (
        projection_after["branch_heads"]["main"]["head_validation_markers"] == []
    )


def test_t_future_basis_is_nonfatal_and_emits_a_marker(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    events = read_events(fixture, frame_id)
    events[-1]["data"]["unmet_obligations_basis"] = "future-basis-v999"
    events[-1]["data"]["unmet_obligations"] = [
        {"kind": "future-rule", "event_id": "future-event"}
    ]
    write_events(fixture, frame_id, events)
    validation = run(
        ["validate", "--frame-id", frame_id, "--require-closed"],
        fixture["environment"],
    )
    assert validation["valid"] is True
    assert validation["markers"] == [
        {
            "code": "frame_abandoned_obligations_basis_mismatch",
            "recorded_basis": "future-basis-v999",
            "current_basis": (
                weilan_trace.FRAME_ABANDON_UNMET_OBLIGATIONS_BASIS
            ),
        }
    ]
    lineage = run(
        ["lineage-show", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert lineage["validation_markers"] == [
        {
            "frame_id": frame_id,
            **validation["markers"][0],
        }
    ]
    projection = run(
        ["self-project", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert (
        projection["branch_heads"]["main"]["head_validation_markers"]
        == validation["markers"]
    )
    contract = run(
        ["metabolic-contract", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert (
        contract["branches"]["main"]["head_validation_markers"]
        == projection["branch_heads"]["main"]["head_validation_markers"]
    )
    assert continue_from(
        fixture, frame_id, problem="successor after future basis"
    )["causal"]["parent_frame_ids"] == [frame_id]


def test_u_current_basis_rejects_incorrect_unmet_obligations(fixture):
    frame_id = open_frame(fixture)["frame_id"]
    collapsed = append_collapse(fixture, frame_id)
    age_frame(fixture, frame_id)
    abandon_successfully(fixture, frame_id)
    events = read_events(fixture, frame_id)
    assert events[-1]["data"]["unmet_obligations"][0]["event_id"] == (
        collapsed["event_id"]
    )
    lineage = run(
        ["lineage-show", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    projection = run(
        ["self-project", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert lineage["validation_markers"] == []
    assert projection["branch_heads"]["main"]["head_validation_markers"] == []
    contract = run(
        ["metabolic-contract", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )
    assert contract["branches"]["main"]["head_validation_markers"] == []
    events[-1]["data"]["unmet_obligations"] = []
    errors = weilan_trace.validate_events(events, require_closed=True)
    assert any("unmet_obligations do not match" in error for error in errors)
    write_events(fixture, frame_id, events)
    validation = completed(
        ["validate", "--frame-id", frame_id, "--require-closed"],
        fixture["environment"],
    )
    assert validation.returncode != 0
    assert "unmet_obligations do not match" in validation.stdout


def test_v_metabolic_contract_reuses_projection_markers_and_missing_key_falls_back(
    fixture, monkeypatch
):
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(fixture["method_state"]))
    open_frame(fixture)
    markers = [
        {
            "code": "same-projection-object",
            "recorded_basis": None,
            "current_basis": weilan_trace.FRAME_ABANDON_UNMET_OBLIGATIONS_BASIS,
        }
    ]
    projection = {
        "projection_hash": "projection-hash-sentinel",
        "issues": [],
        "branch_heads": {"main": {"head_validation_markers": markers}},
    }
    monkeypatch.setattr(
        weilan_trace, "build_self_projection", lambda workspace, scope: projection
    )

    def reject_second_marker_derivation(events):
        raise AssertionError("contract must reuse the marker object already in projection")

    monkeypatch.setattr(
        weilan_trace, "frame_validation_markers", reject_second_marker_derivation
    )
    contract = weilan_trace.current_metabolic_contract(fixture["workspace"], SCOPE)
    assert contract["branches"]["main"]["head_validation_markers"] is markers

    projection["branch_heads"] = {}
    missing_projection_branch = weilan_trace.current_metabolic_contract(
        fixture["workspace"], SCOPE
    )
    assert missing_projection_branch["branches"]["main"]["head_validation_markers"] == []


def test_w_metabolic_contract_uses_one_lineage_snapshot_per_derivation(
    fixture, monkeypatch
):
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(fixture["method_state"]))

    frame_a = open_frame(fixture)["frame_id"]
    age_frame(fixture, frame_a)
    assert abandon(fixture, frame_a).returncode == 0
    events = read_events(fixture, frame_a)
    events[-1]["data"].pop("unmet_obligations")
    events[-1]["data"].pop("unmet_obligations_basis")
    write_events(fixture, frame_a, events)

    frame_b = run(
        [
            "open",
            "--level",
            "L2",
            "--workspace",
            fixture["workspace"],
            "--scope",
            SCOPE,
            "--branch",
            "main",
            "--relation",
            "continue",
            "--parent",
            frame_a,
            "--problem",
            "successor visible after the derivation memo expires",
            "--success",
            "the next contract sees the fresh lineage head",
        ],
        fixture["environment"],
    )["frame_id"]

    real_jsonl = weilan_trace.read_jsonl_records
    real_raw = weilan_trace.read_events_raw
    raw_lineage_reads = []
    raw_frame_reads = []

    def changing_lineage_snapshot(path, warnings):
        records = real_jsonl(path, warnings)
        if "lineage" not in path.parts:
            return records
        raw_lineage_reads.append(path)
        if len(raw_lineage_reads) == 1:
            records = [record for record in records if record.get("frame_id") != frame_b]
        return records + [
            {"schema_version": "unsupported-lineage-schema"},
            {
                "schema_version": weilan_trace.LINEAGE_SCHEMA_VERSION,
                "workspace": fixture["workspace"] + "-other",
                "scope": SCOPE,
            },
            {
                "schema_version": weilan_trace.LINEAGE_SCHEMA_VERSION,
                "workspace": fixture["workspace"],
                "scope": SCOPE + "-other",
            },
        ]

    def counting_frame_read(path):
        raw_frame_reads.append(Path(path).name)
        return real_raw(path)

    monkeypatch.setattr(
        weilan_trace, "read_jsonl_records", changing_lineage_snapshot
    )
    monkeypatch.setattr(weilan_trace, "read_events_raw", counting_frame_read)

    real_lineage_loader = weilan_trace.load_lineage_records
    returned_snapshots = []
    returned_snapshot_bytes = []
    replayed_warnings = []

    def observing_lineage_loader(workspace, scope, warnings=None):
        records = real_lineage_loader(workspace, scope, warnings)
        returned_snapshots.append(records)
        returned_snapshot_bytes.append(
            json.dumps(records, ensure_ascii=False, sort_keys=True)
        )
        replayed_warnings.append(list(warnings or []))
        return records

    monkeypatch.setattr(
        weilan_trace, "load_lineage_records", observing_lineage_loader
    )
    before = method_state_bytes(fixture)

    first = weilan_trace.current_metabolic_contract(fixture["workspace"], SCOPE)
    assert len(raw_lineage_reads) == 1
    assert returned_snapshots[0] is returned_snapshots[1]
    assert returned_snapshot_bytes[0] == returned_snapshot_bytes[1]
    assert replayed_warnings[0] == replayed_warnings[1]
    assert raw_frame_reads.count(f"{frame_a}.jsonl") == 1
    assert first["branches"]["main"]["head_frame_id"] == frame_a
    assert first["branches"]["main"]["head_abandoned"] is True
    assert first["branches"]["main"]["head_validation_markers"]
    expected_warnings = [
        "unsupported lineage schema",
        "lineage workspace mismatch",
        "lineage scope mismatch",
    ]
    for warning in expected_warnings:
        assert sum(warning in issue for issue in replayed_warnings[0]) == 1
        assert sum(warning in issue for issue in first["issues"]) == 1

    second = weilan_trace.current_metabolic_contract(fixture["workspace"], SCOPE)
    assert len(raw_lineage_reads) == 2
    assert returned_snapshots[2] is returned_snapshots[3]
    assert returned_snapshots[2] is not returned_snapshots[0]
    assert returned_snapshot_bytes[2] == returned_snapshot_bytes[3]
    assert replayed_warnings[2] == replayed_warnings[3]
    assert raw_frame_reads.count(f"{frame_b}.jsonl") == 1
    assert second["branches"]["main"]["head_frame_id"] == frame_b
    assert second["branches"]["main"]["head_abandoned"] is False
    assert second["branches"]["main"]["head_validation_markers"] == []
    for warning in expected_warnings:
        assert sum(warning in issue for issue in replayed_warnings[2]) == 1
        assert sum(warning in issue for issue in second["issues"]) == 1
    assert method_state_bytes(fixture) == before


def test_x_guarded_write_entrances_fail_closed_inside_derivation_memo(
    fixture, monkeypatch
):
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(fixture["method_state"]))
    args = argparse.Namespace(workspace=fixture["workspace"], scope=SCOPE)
    guarded_entrances = {
        "prepare": lambda: weilan_trace.command_metabolic_prepare(args),
        "commit": lambda: weilan_trace.command_metabolic_commit(args),
        "abort": lambda: weilan_trace.command_metabolic_abort(args),
        "recover": lambda: weilan_trace.command_metabolic_recover(args),
        "materialize": lambda: weilan_trace.materialize_transition_args(args),
        "run": lambda: weilan_trace.command_metabolic_run(args),
        "runner-reconcile": lambda: weilan_trace.reconcile_runner_materialization(
            fixture["workspace"], SCOPE, "runner-step"
        ),
        "outer-lineaged-open-valid-scope": lambda: weilan_trace.command_open_lineaged(
            argparse.Namespace(workspace=fixture["workspace"], scope=SCOPE)
        ),
        "outer-lineaged-open-invalid-scope": lambda: weilan_trace.command_open_lineaged(
            argparse.Namespace(workspace=fixture["workspace"], scope="x" * 129)
        ),
        "direct-lineaged-open": lambda: weilan_trace.command_open_lineaged_fenced(
            argparse.Namespace(), fixture["workspace"], SCOPE
        ),
    }
    before = method_state_bytes(fixture)
    expected = (
        "guarded transaction and direct lineaged-open write entrances "
        "cannot run inside a derivation memo"
    )

    with weilan_trace.derivation_memo_scope():
        for name, entrance in guarded_entrances.items():
            with pytest.raises(ValueError, match=expected):
                entrance()

    assert method_state_bytes(fixture) == before


def test_y_write_guard_topology_stays_narrow():
    transaction_entrances = [
        weilan_trace.command_metabolic_prepare,
        weilan_trace.command_metabolic_commit,
        weilan_trace.command_metabolic_abort,
        weilan_trace.command_metabolic_recover,
        weilan_trace.materialize_transition_args,
        weilan_trace.command_metabolic_run,
    ]
    for entrance in transaction_entrances:
        source = inspect.getsource(entrance)
        assert "assert_transaction_write_allowed(workspace, scope)" in source

    outer_open_source = inspect.getsource(weilan_trace.command_open_lineaged)
    direct_open_source = inspect.getsource(weilan_trace.command_open_lineaged_fenced)
    reconcile_source = inspect.getsource(weilan_trace.reconcile_runner_materialization)
    governance_source = inspect.getsource(weilan_trace.append_governance_event)
    guard_call = "assert_guarded_write_entry_outside_derivation_memo()"
    assert outer_open_source.splitlines()[1].strip() == guard_call
    assert guard_call in direct_open_source
    assert guard_call in reconcile_source
    assert guard_call not in governance_source


def test_z_governance_append_remains_allowed_inside_derivation_memo(
    fixture, monkeypatch
):
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(fixture["method_state"]))
    monkeypatch.setattr(
        weilan_trace, "assert_governance_write_allowed", lambda workspace, scope: None
    )
    source = Path(fixture["workspace"]) / "governance-source.md"
    source.write_text("governance memo exception regression\n", encoding="utf-8")
    data = {
        "target_ref": "goal:memo-governance-exception",
        "target_kind": "goal",
        "scale": "task",
        "death_lines": ["governance append blocked by derivation memo"],
        "source_refs": [str(source)],
        "source_snapshots": weilan_trace.source_snapshots(
            [str(source)], fixture["workspace"]
        ),
    }

    with weilan_trace.derivation_memo_scope():
        event, state, path = weilan_trace.append_governance_event(
            fixture["workspace"], SCOPE, "target_registered", data
        )

    assert path.exists()
    assert event["event_type"] == "target_registered"
    assert state["targets"][data["target_ref"]]["state"] == "ACTIVE"
