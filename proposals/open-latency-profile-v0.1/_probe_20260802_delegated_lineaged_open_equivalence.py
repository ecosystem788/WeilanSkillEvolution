"""Read-only review probe: exercise the signed lineaged-open call site.

This probe calls ``command_open_lineaged`` in a caller-provided sandbox, so
the candidate executes the exact wrapper added by the signed change. Its text
is a real current collapse-trace forbidden assumption and must produce a
non-empty advisory.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import os
import pathlib
import shutil
import sys
import time
import types
import uuid
from datetime import datetime as RealDateTime, timezone


MATCHING_PROBLEM = (
    "Advisory budget prose is enough to make agents stay under hard evaluation budgets."
)
MATCHING_SUCCESS = (
    "A successor must encode concrete call-shape limits and exact long-horizon scope, "
    "then pass the approved gate."
)


class FixedDateTime(RealDateTime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 8, 2, 9, 1, 0, tzinfo=tz or timezone.utc)


def load_trace(path):
    script_dir = str(pathlib.Path(path).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "weilan_trace_review_probe", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_compact_state(source_state, work, parent):
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    frame_source = next(source_state.joinpath("frames").rglob(f"{parent}.jsonl"))
    frame_target = work / "frames" / frame_source.parent.name / frame_source.name
    frame_target.parent.mkdir(parents=True)
    shutil.copy2(frame_source, frame_target)
    first = json.loads(frame_source.read_text(encoding="utf-8").splitlines()[0])
    causal = first["data"]["causal"]
    lineage_target = (
        work / "memory" / "lineage" / "workspaces" / "d431c38105a9a791"
        / "c36aecb1ff20" / "2026-08-02.jsonl"
    )
    lineage_target.parent.mkdir(parents=True)
    lineage_target.write_text(
        json.dumps(
            {
                "schema_version": "weilan_frame_lineage_v0.4",
                "event_id": causal["lineage_event_id"],
                "timestamp_utc": first["timestamp_utc"],
                "workspace": r"D:\WeilanSkillEvolution",
                "workspace_key": "d431c38105a9a791",
                "scope": "skill-evolution",
                "scope_key": "c36aecb1ff20",
                "frame_id": parent,
                "branch_id": "main",
                "relation": "continue",
                "parent_frame_ids": causal["parent_frame_ids"],
                "joined_branch_ids": [],
            },
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--source-state", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--parent", required=True)
    args = parser.parse_args()

    source_state = pathlib.Path(args.source_state)
    work = pathlib.Path(args.work)
    prepare_compact_state(source_state, work, args.parent)
    os.environ["WEILAN_METHOD_HOME"] = str(work)
    sys.modules.pop("weilan_trace_review_probe", None)
    wt = load_trace(args.script)
    source_index_path = (
        source_state / "memory" / "episode-indexes" / "workspaces"
        / "d431c38105a9a791" / "c36aecb1ff20.json"
    )
    source_index = json.loads(source_index_path.read_text(encoding="utf-8"))
    trace = next(
        trace
        for episode in source_index["episodes"]
        for trace in episode.get("traces", [])
        if trace.get("forbidden_assumption") == MATCHING_PROBLEM
    )
    index = {
        "schema_version": source_index["schema_version"],
        "authority": "derived_rebuildable_episode_index_never_activation_authority",
        "workspace": args.workspace,
        "workspace_key": "d431c38105a9a791",
        "scope": args.scope,
        "scope_key": "c36aecb1ff20",
        "episode_count": 1,
        "episodes": [{"source": "frame:real-collapse-trace", "traces": [trace]}],
    }
    index_path = wt.episode_index_path(args.workspace, args.scope)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index["source_state"] = wt.frame_source_state(
        wt.scoped_frame_paths(args.workspace, args.scope)
    )
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    original_write = wt.write_event_file_atomic

    def write_and_refresh(path, event):
        result = original_write(path, event)
        refreshed = json.loads(index_path.read_text(encoding="utf-8"))
        refreshed["source_state"] = wt.frame_source_state(
            wt.scoped_frame_paths(args.workspace, args.scope)
        )
        index_path.write_text(
            json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result

    wt.write_event_file_atomic = write_and_refresh
    values = itertools.count(1)
    wt.datetime = FixedDateTime
    wt.uuid = types.SimpleNamespace(uuid4=lambda: uuid.UUID(int=next(values)))
    wt.utc_now = lambda: "2026-08-02T09:01:00+00:00"
    call_args = types.SimpleNamespace(
        level="L2",
        problem=MATCHING_PROBLEM,
        success=MATCHING_SUCCESS,
        budget="review",
        workspace=args.workspace,
        scope=args.scope,
        branch="probe-review",
        relation="fork",
        parent=[args.parent],
    )
    output = io.StringIO()
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(output):
            wt.command_open_lineaged(call_args)
    finally:
        os.environ.pop("WEILAN_METHOD_HOME", None)
    elapsed = time.perf_counter() - started
    stdout = output.getvalue()
    parsed = json.loads(stdout)
    payload = json.dumps(
        parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    print(
        json.dumps(
            {
                "script": str(pathlib.Path(args.script).resolve()),
                "script_sha256": hashlib.sha256(
                    pathlib.Path(args.script).read_bytes()
                ).hexdigest(),
                "runtime_core_sha256": hashlib.sha256(
                    (pathlib.Path(args.script).resolve().parent / "runtime_core.py").read_bytes()
                ).hexdigest(),
                "advisory_keys": sorted(parsed.keys()),
                "advisory_count": len(parsed.get("trace_advisories", [])),
                "advisory_count_nonzero": bool(parsed.get("trace_advisories")),
                "advisory_payload_sha256": hashlib.sha256(
                    payload.encode("utf-8")
                ).hexdigest(),
                "advisory_payload_len": len(payload),
                "seconds_lineaged_open": round(elapsed, 3),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
