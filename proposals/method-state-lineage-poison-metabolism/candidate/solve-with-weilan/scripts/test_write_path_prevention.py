"""Regression tests for frame-event write-path validation."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("weilan_trace.py")


def run_cli(home, *args, check=True):
    env = {**os.environ, "WEILAN_METHOD_HOME": str(home)}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        env=env,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result


def main():
    with tempfile.TemporaryDirectory(prefix="weilan-write-path-") as temporary:
        home = Path(temporary)
        workspace = home / "workspace"
        opened = json.loads(
            run_cli(
                home,
                "open",
                "--workspace",
                str(workspace),
                "--level",
                "L2",
                "--problem",
                "exercise frame write validation",
                "--success",
                "invalid frame events do not append",
            ).stdout
        )
        frame_id = opened["frame_id"]
        frame_path = Path(opened["path"])
        before = frame_path.read_bytes()

        bad_trace = run_cli(
            home,
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "trace_emitted",
            "--field",
            "stray_status=not a trace contract",
            check=False,
        )
        if bad_trace.returncode == 0:
            raise AssertionError("runtime accepted malformed trace_emitted")
        if frame_path.read_bytes() != before:
            raise AssertionError("malformed trace_emitted changed the frame file")

        run_cli(
            home,
            "event",
            "--frame-id",
            frame_id,
            "--type",
            "candidate_admitted",
            "--field",
            "candidate_id=valid-route",
            "--field",
            "summary=valid frame event still appends",
        )
        after_valid = frame_path.read_text(encoding="utf-8").splitlines()
        if len(after_valid) != 2:
            raise AssertionError("valid frame event did not append exactly once")

        control = run_cli(
            home,
            "memory-control",
            "--workspace",
            str(workspace),
            "--scope",
            "write-path-test",
            "--state",
            "active",
            "--directive",
            "non-frame ledger remains writable",
        )
        control_result = json.loads(control.stdout)
        if not Path(control_result["path"]).exists():
            raise AssertionError("non-frame control ledger did not write")


if __name__ == "__main__":
    main()
