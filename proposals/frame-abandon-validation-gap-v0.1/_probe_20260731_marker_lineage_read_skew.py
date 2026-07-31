"""Read-only probe: contract-body marker reuse is keyed by branch_id alone.

Reviews Codex's 2026-07-31 v3.1 contract-body readability patch (live
weilan_trace.py sha256=dc5eb30b...). The patch reuses the projection's
head_validation_markers instead of re-deriving them. It documents one boundary:
a branch missing from the projection falls back to []. This probe asks whether
that is the ONLY skew, given that current_metabolic_contract derives lineage a
second time.

Everything here runs against a throwaway WEILAN_METHOD_HOME under tempfile.
No real ledger, no network, no writes outside the temp tree.

Part 1 measures which reads inside ONE current_metabolic_contract call actually
hit disk twice.
Part 2 shows what a second lineage read buys when the head moved between the
two reads.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts")
SCRIPT = SCRIPTS / "weilan_trace.py"
SCOPE = "marker-skew-probe"


def run(arguments, environment, *, expect_ok=True):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    if expect_ok and result.returncode:
        raise AssertionError(f"command failed: {' '.join(arguments)}\n{result.stderr}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def frame_path(method_state, frame_id):
    matches = list(method_state.glob(f"frames/*/{frame_id}.jsonl"))
    if len(matches) != 1:
        raise AssertionError(f"expected one frame path for {frame_id}: {matches}")
    return matches[0]


def read_events(method_state, frame_id):
    text = frame_path(method_state, frame_id).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_events(method_state, frame_id, events):
    frame_path(method_state, frame_id).write_text(
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


def open_frame(workspace, environment, *, relation="root", parent=None, problem):
    arguments = [
        "open", "--level", "L2",
        "--workspace", workspace,
        "--scope", SCOPE,
        "--branch", "main",
        "--relation", relation,
        "--problem", problem,
        "--success", "marker skew probe stays read-only",
    ]
    if parent:
        arguments.extend(["--parent", parent])
    return run(arguments, environment)


def build_fixture(root):
    method_state = root / "method-state"
    workspace = root / "workspace"
    workspace.mkdir()
    environment = os.environ.copy()
    environment["WEILAN_METHOD_HOME"] = str(method_state)

    # Frame A becomes an abandoned head carrying a v2 validation marker.
    frame_a = open_frame(
        str(workspace), environment, problem="probe head that will carry a marker"
    )["frame_id"]
    events = read_events(method_state, frame_a)
    events[-1]["timestamp_utc"] = (
        (datetime.now(timezone.utc) - timedelta(seconds=10800))
        .replace(microsecond=0)
        .isoformat()
    )
    write_events(method_state, frame_a, events)
    run(
        [
            "frame-abandon", "--frame-id", frame_a,
            "--silence-threshold-seconds", "7200",
            "--evidence",
            json.dumps(
                {
                    "alert_id": "probe-alert",
                    "consecutive_count": 10,
                    "source_ref": "probe:peer-health",
                }
            ),
            "--reason", "marker skew probe fixture",
        ],
        environment,
    )
    # Same v2 shape test_s uses: drop the v3 fields so a marker is emitted.
    events = read_events(method_state, frame_a)
    events[-1]["data"].pop("unmet_obligations")
    events[-1]["data"].pop("unmet_obligations_basis")
    write_events(method_state, frame_a, events)

    # Frame B continues from A and becomes the live head. B carries no marker.
    frame_b = open_frame(
        str(workspace),
        environment,
        relation="continue",
        parent=frame_a,
        problem="probe successor head with no marker",
    )["frame_id"]
    return {
        "method_state": method_state,
        "workspace": str(workspace),
        "environment": environment,
        "frame_a": frame_a,
        "frame_b": frame_b,
    }


def part_one_disk_read_census(fixture):
    """Which loaders inside one contract call hit disk more than once?"""
    sys.path.insert(0, str(SCRIPTS))
    os.environ["WEILAN_METHOD_HOME"] = str(fixture["method_state"])
    import weilan_trace

    lineage_reads = []
    frame_reads = []
    real_jsonl = weilan_trace.read_jsonl_records
    real_raw = weilan_trace.read_events_raw

    def counting_jsonl(path, warnings):
        if "lineage" in str(path):
            lineage_reads.append(str(path))
        return real_jsonl(path, warnings)

    def counting_raw(path):
        frame_reads.append(Path(path).name)
        return real_raw(path)

    weilan_trace.read_jsonl_records = counting_jsonl
    weilan_trace.read_events_raw = counting_raw
    try:
        contract = weilan_trace.current_metabolic_contract(fixture["workspace"], SCOPE)
    finally:
        weilan_trace.read_jsonl_records = real_jsonl
        weilan_trace.read_events_raw = real_raw

    head_frame_file = f"{fixture['frame_b']}.jsonl"
    return {
        "lineage_ledger_disk_reads_in_one_contract_call": len(lineage_reads),
        "head_frame_disk_reads_in_one_contract_call": frame_reads.count(head_frame_file),
        "reading": (
            "frame events are memoized per path across the projection and the "
            "contract; the lineage ledger is not, so the two derivations see "
            "two independent snapshots of who the head is"
        ),
        "quiet_moment_head_frame_id": contract["branches"]["main"]["head_frame_id"],
        "quiet_moment_markers": contract["branches"]["main"]["head_validation_markers"],
        "quiet_moment_contract_hash": contract.get("contract_hash"),
    }


def part_two_head_moved_between_reads(fixture):
    """Model a lineage append landing between the two lineage reads.

    The projection's read (first) predates frame B's lineage record; the
    contract's read (second) sees it. Nothing else is stubbed -- both calls go
    through the real loader against the real temp ledger.
    """
    sys.path.insert(0, str(SCRIPTS))
    os.environ["WEILAN_METHOD_HOME"] = str(fixture["method_state"])
    import weilan_trace

    real_loader = weilan_trace.load_lineage_records
    calls = {"n": 0}

    def racing_loader(workspace, scope, warnings=None):
        calls["n"] += 1
        records = real_loader(workspace, scope, warnings)
        if calls["n"] == 1:
            # Pre-append view: frame B's lineage record has not landed yet.
            return [r for r in records if r.get("frame_id") != fixture["frame_b"]]
        return records

    weilan_trace.load_lineage_records = racing_loader
    try:
        contract = weilan_trace.current_metabolic_contract(fixture["workspace"], SCOPE)
    finally:
        weilan_trace.load_lineage_records = real_loader

    branch = contract["branches"]["main"]
    markers = branch["head_validation_markers"]
    return {
        "lineage_loader_calls": calls["n"],
        "head_frame_id_reported": branch["head_frame_id"],
        "head_frame_id_is_b": branch["head_frame_id"] == fixture["frame_b"],
        "head_abandoned_reported": branch["head_abandoned"],
        "markers_reported": markers,
        "markers_belong_to_frame": "A" if markers else "none",
        "missing_key_fallback_fired": markers == [],
        "contract_hash": contract.get("contract_hash"),
        "reading": (
            "the branch key is present in both snapshots, so the documented [] "
            "fallback never fires; the body pairs B's head_frame_id and "
            "disposition flags with A's markers and says nothing about it"
        ),
    }


def main():
    with tempfile.TemporaryDirectory() as temporary:
        fixture = build_fixture(Path(temporary))
        out = {
            "probe": "marker reuse is keyed by branch_id, not by head_frame_id",
            "live_weilan_trace_sha256": __import__("hashlib")
            .sha256(SCRIPT.read_bytes())
            .hexdigest(),
            "frame_a_abandoned_with_marker": fixture["frame_a"],
            "frame_b_live_head_no_marker": fixture["frame_b"],
            "part_one_disk_read_census": part_one_disk_read_census(fixture),
            "part_two_head_moved_between_reads": part_two_head_moved_between_reads(
                fixture
            ),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
