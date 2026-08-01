"""Read-only bucketed latency profile for weilan_trace CLI calls.

Purpose (observer directive, peer-chat line 3248, item 3): profile where the
remaining 50-110 seconds per receipt-chain call actually go.

Method: a subprocess ladder. Each rung adds exactly one layer of work, so the
difference between two adjacent rungs is that layer's cost.

  rung 0  bare interpreter start          python -c pass
  rung 1  + import weilan_trace module    exec_module, main() not run
  rung 2  + build argparse parser         weilan_trace --help
  rung 3  + a read-only command body      show / prospective-show / lineage-show / memory-recall

Writes nothing except its own .out.json next to this file. No frame is opened,
no ledger row is appended, no deployed file is touched.

Boundary: measures wall seconds on a live host with uncontrolled load, from the
parent process's point of view. It cannot see time spent OUTSIDE the subprocess
(model thinking, harness round-trip, permission checks) -- that gap is computed
separately in the `outside_process` section from this turn's own tool-call
timestamps, and is explicitly an estimate, not an instrumented measurement.
"""

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_SCRIPTS = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
TRACE = SKILL_SCRIPTS / "weilan_trace.py"
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"

REPEATS = 5

IMPORT_ONLY_SNIPPET = (
    "import sys, importlib.util as u\n"
    "sys.path.insert(0, {scripts!r})\n"
    "spec = u.spec_from_file_location('wt_probe', {trace!r})\n"
    "m = u.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
).format(scripts=str(SKILL_SCRIPTS), trace=str(TRACE))


def timed(argv, repeats=REPEATS):
    runs = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        proc = subprocess.run(argv, capture_output=True)
        runs.append(
            {
                "elapsed_s": round(time.perf_counter() - t0, 4),
                "rc": proc.returncode,
                "stdout_bytes": len(proc.stdout),
                "stderr_bytes": len(proc.stderr),
            }
        )
    xs = [r["elapsed_s"] for r in runs]
    return {
        "n": len(xs),
        "min_s": round(min(xs), 4),
        "median_s": round(statistics.median(xs), 4),
        "max_s": round(max(xs), 4),
        "rcs": sorted({r["rc"] for r in runs}),
        "stdout_bytes": runs[-1]["stdout_bytes"],
        "runs": runs,
    }


def head_frame_id():
    """Read the current scope head frame id from a read-only lineage-show."""
    proc = subprocess.run(
        [sys.executable, str(TRACE), "lineage-show", "--workspace", WORKSPACE, "--scope", SCOPE],
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    try:
        doc = json.loads(proc.stdout.decode("utf-8", "replace").lstrip("\ufeff"))
    except ValueError:
        return None
    for key in ("head_frame_id", "head", "heads"):
        val = doc.get(key)
        if isinstance(val, str):
            return val
        if isinstance(val, list) and val and isinstance(val[0], str):
            return val[0]
        if isinstance(val, list) and val and isinstance(val[0], dict):
            for k in ("frame_id", "id", "ref"):
                if k in val[0]:
                    return val[0][k]
        if isinstance(val, dict):
            for k in ("frame_id", "id", "ref"):
                if k in val:
                    return val[k]
    return None


def ledger_size():
    """Size of the on-disk lineage/frame store, to relate cost to input size."""
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    root = Path(home) / "method-state"
    out = {"method_state_root": str(root), "exists": root.exists()}
    if not root.exists():
        return out
    files = 0
    total = 0
    frames = 0
    for path in root.rglob("*"):
        if path.is_file():
            files += 1
            try:
                total += path.stat().st_size
            except OSError:
                pass
            if path.suffix == ".json" and "frames" in path.parts:
                frames += 1
    out.update({"file_count": files, "total_bytes": total, "frame_json_count": frames})
    return out


def main():
    result = {
        "probe": "latency_buckets",
        "arm": "current_deployed_baseline",
        "python": sys.version.split()[0],
        "trace_script": str(TRACE),
        "repeats": REPEATS,
        "boundary": __doc__.strip().splitlines()[-3:],
        "ladder": {},
        "read_only_commands": {},
    }

    result["ledger_size"] = ledger_size()

    result["ladder"]["rung0_bare_interpreter"] = timed([sys.executable, "-c", "pass"])
    result["ladder"]["rung1_import_module"] = timed([sys.executable, "-c", IMPORT_ONLY_SNIPPET])
    result["ladder"]["rung2_build_parser_help"] = timed([sys.executable, str(TRACE), "--help"])

    head = head_frame_id()
    result["head_frame_id_probed"] = head

    cmds = {
        "memory-recall": ["memory-recall", "--workspace", WORKSPACE, "--scope", SCOPE],
        "prospective-show": ["prospective-show", "--workspace", WORKSPACE, "--scope", SCOPE],
        "lineage-show": ["lineage-show", "--workspace", WORKSPACE, "--scope", SCOPE],
    }
    if head:
        cmds["show"] = ["show", "--workspace", WORKSPACE, "--frame-id", head]

    for name, argv in cmds.items():
        result["read_only_commands"][name] = timed([sys.executable, str(TRACE)] + argv)

    r0 = result["ladder"]["rung0_bare_interpreter"]["median_s"]
    r1 = result["ladder"]["rung1_import_module"]["median_s"]
    r2 = result["ladder"]["rung2_build_parser_help"]["median_s"]
    result["buckets_s"] = {
        "interpreter_startup": round(r0, 4),
        "module_import_delta": round(r1 - r0, 4),
        "parser_build_delta": round(max(r2 - r1, 0.0), 4),
        "command_body_delta": {
            name: round(data["median_s"] - r2, 4)
            for name, data in result["read_only_commands"].items()
        },
    }

    out = HERE / (Path(__file__).stem + ".out.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["buckets_s"], ensure_ascii=False, indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
