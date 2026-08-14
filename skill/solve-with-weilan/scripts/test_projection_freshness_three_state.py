"""Axis-1 v1 three-state projection freshness regression arms (A/B/C/D).

Anchors the current stateless recomputation behavior: projection_freshness is
a pure function of (projection, current sources, current control heads). If a
later, separately authorized proposal introduces forced rebuild, the no-write
arm is expected to fail deliberately until that contract is revised.

Dual-signed axis-1 v1 contract (2026-08-14): the fresh field becomes a
three-state string fresh|stale|contested; contested_present surfaces
unresolved adjudication conflicts read from the actual
contested_semantic_entries key; stale stays gated while contested is surfaced
but not gated; the backward-compatible bool mapping is explicit
(fresh->True / stale->False / contested->True), never Python truthiness.
"""

import copy

import weilan_trace


SCOPE = "axis1-v1-fixture"
CONTROL = {
    "workspace": None,
    "scope": SCOPE,
    "state": "active",
    "event_id": "fixture-control-0001",
    "resume_requires_confirmation": False,
    "directive": "axis-1 v1 fixture",
}


def fixture_controls(workspace):
    control = dict(CONTROL)
    control["workspace"] = str(workspace)
    return [control]


def build_projection(workspace, source_path):
    source = str(source_path.name)
    return {
        "schema_version": weilan_trace.PROJECTION_SCHEMA_VERSION,
        "projection_id": "fixture-projection-0001",
        "workspace": str(workspace),
        "scope": SCOPE,
        "generated_at_utc": "2026-08-14T00:00:00+00:00",
        "focus": "axis-1 v1 fixture",
        "sources": [source],
        "source_snapshots": weilan_trace.source_snapshots([source], str(workspace)),
        "contested_semantic_entries": [],
        "control_heads": {"workspace": None, "scope": CONTROL["event_id"]},
    }


def test_arm_a_fresh_baseline(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("stable source bytes", encoding="utf-8")
    projection = build_projection(tmp_path, source)
    controls = fixture_controls(tmp_path)
    baseline = weilan_trace.projection_freshness(projection, controls)
    assert baseline["fresh"] == "fresh"
    assert baseline["reason_codes"] == []
    assert weilan_trace.freshness_bool(baseline["fresh"]) is True
    activation = weilan_trace.evaluate_activation(
        str(tmp_path), SCOPE, projection, controls
    )
    assert activation["state"] == "ACTIVE"
    assert activation["continuation_allowed"] is True


def test_arm_b_source_drift_blocks(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("stable source bytes", encoding="utf-8")
    projection = build_projection(tmp_path, source)
    controls = fixture_controls(tmp_path)
    assert weilan_trace.projection_freshness(projection, controls)["fresh"] == "fresh"
    source.write_text("drifted source bytes", encoding="utf-8")
    stale = weilan_trace.projection_freshness(projection, controls)
    assert stale["fresh"] == "stale"
    assert "source_changed" in stale["reason_codes"]
    assert weilan_trace.freshness_bool(stale["fresh"]) is False
    activation = weilan_trace.evaluate_activation(
        str(tmp_path), SCOPE, projection, controls
    )
    assert activation["state"] == "STALE"
    assert activation["continuation_allowed"] is False


def test_arm_c_restoration_rejudges_fresh(tmp_path):
    original = "stable source bytes"
    source = tmp_path / "source.txt"
    source.write_text(original, encoding="utf-8")
    projection = build_projection(tmp_path, source)
    controls = fixture_controls(tmp_path)
    baseline = weilan_trace.projection_freshness(projection, controls)
    assert baseline["fresh"] == "fresh"
    source.write_text("drifted source bytes", encoding="utf-8")
    assert weilan_trace.projection_freshness(projection, controls)["fresh"] == "stale"
    source.write_text(original, encoding="utf-8")
    restored = weilan_trace.projection_freshness(projection, controls)
    assert restored == baseline
    assert restored["fresh"] == "fresh"
    activation = weilan_trace.evaluate_activation(
        str(tmp_path), SCOPE, projection, controls
    )
    assert activation["state"] == "ACTIVE"
    assert activation["continuation_allowed"] is True


def test_arm_d_contested_surfaced_not_gated(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("stable source bytes", encoding="utf-8")
    projection = build_projection(tmp_path, source)
    projection["contested_semantic_entries"] = [
        {
            "memory_id": "memory-fixture-alpha",
            "kind": "decision",
            "summary": "contested alpha",
            "contested_with": ["memory-fixture-beta"],
        }
    ]
    controls = fixture_controls(tmp_path)
    contested = weilan_trace.projection_freshness(projection, controls)
    assert contested["fresh"] == "contested"
    assert "contested_present" in contested["reason_codes"]
    assert weilan_trace.freshness_bool(contested["fresh"]) is True
    activation = weilan_trace.evaluate_activation(
        str(tmp_path), SCOPE, projection, controls
    )
    assert activation["state"] == "ACTIVE"
    assert activation["continuation_allowed"] is True
    assert "contested_present" in activation["reason_codes"]


def test_explicit_bool_mapping():
    assert weilan_trace.freshness_bool("fresh") is True
    assert weilan_trace.freshness_bool("stale") is False
    assert weilan_trace.freshness_bool("contested") is True
    assert weilan_trace.freshness_bool("unknown-future-state") is False


def test_no_write_pure_function(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("stable source bytes", encoding="utf-8")
    projection = build_projection(tmp_path, source)
    controls = fixture_controls(tmp_path)
    before = copy.deepcopy(projection)
    weilan_trace.projection_freshness(projection, controls)
    weilan_trace.evaluate_activation(str(tmp_path), SCOPE, projection, controls)
    assert projection == before
