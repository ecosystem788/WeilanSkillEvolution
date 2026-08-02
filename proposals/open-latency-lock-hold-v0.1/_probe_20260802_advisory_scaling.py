"""Read-only probe: does the intra-lock advisory cost scale with ledger size?

Closes boundary #3 of proposals/open-latency-lock-hold-v0.1/FINDING.md section 7/9,
which said:

    "占比随帧数怎么变没测；结构上 advisory 是 O(帧数) 而写帧是 O(1)，
     故账本越大占比只会更高，但这是推断，没测。"

The claim under test is a SHAPE claim, so it is measured by varying one input
(the number of frame files visible to the scope) and timing the four read-only
calls that make up the advisory:

    scan_s      scoped_frame_paths(ws, scope)
                  -> glob frames/*/*.jsonl and read_events() EVERY file,
                     including other workspaces' frames, to filter by scope.
    build_s     build_episode_index_value(ws, scope)
                  -> scoped_frame_paths again + summarize_episode(read_events(p))
                     per scoped path + frame_source_state (stat per path).
    gov_s       reduce_governance(ws, scope, warnings)
                  -> the OTHER half of collapse_trace_registry; reads the
                     governance ledger, which is NOT frames.
    registry_s  collapse_trace_registry(ws, scope)
                  -> what attach_trace_advisory_result actually calls; equals
                     (stale-index rebuild) + governance. Measured too so that
                     additivity against scan/build/gov is checked, not assumed.

No memo scope is entered, so memoized_value degrades to a direct call exactly as
it does inside `open` (weilan_trace.py:1457; see peer-chat 2026-08-01T23:40:55).

Cache-warmth discipline: cold/warm swing was measured at 4.66x, larger than any
code-version difference, so absolute seconds are not comparable across rounds.
Every size is therefore visited in every round, and the visit order alternates
direction between rounds (desc, asc, desc) so a monotone warmth drift cannot
masquerade as a size effect. One full-size warm-up is discarded.

Safety:
  * Production state_root is READ ONCE to make a copy, never written, never used
    as WEILAN_METHOD_HOME by any child.
  * All truncation happens by MOVING frame files between the copy's frames/ tree
    and a holding directory beside it. Production frames are never touched.
  * Every child asserts its own state_root() is under the copy before timing.

Usage:
    python _probe_20260802_advisory_scaling.py [--out <json>]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
PRODUCTION_ROOT = Path(r"D:\CodexData\home\method-state")
COPY_ROOT = Path(r"D:\WeilanSkillEvolution\_tmp_ledger_0802_scaling")
HELD_ROOT = Path(r"D:\WeilanSkillEvolution\_tmp_ledger_0802_scaling_held")

SIZES = [750, 1500, 3000, None]  # None = all frame files present
ROUNDS = 3

CHILD_SRC = r'''
import json, os, sys, time
sys.path.insert(0, r"{scripts}")
os.environ["WEILAN_METHOD_HOME"] = r"{copy}"
from runtime_core import state_root, canonical_workspace
import weilan_trace as wt

root = str(state_root())
assert root.lower().startswith(r"{copy}".lower()), "child escaped the ledger copy: " + root

ws = canonical_workspace(r"{workspace}")
scope = wt.normalize_scope("{scope}")

t0 = time.perf_counter()
paths = wt.scoped_frame_paths(ws, scope)
t1 = time.perf_counter()
index = wt.build_episode_index_value(ws, scope)
t2 = time.perf_counter()
warnings = []
records, gov = wt.reduce_governance(ws, scope, warnings)
t3 = time.perf_counter()
try:
    registry = wt.collapse_trace_registry(ws, scope)
    registry_len = len(registry)
    registry_error = None
except Exception as exc:
    registry_len = None
    registry_error = type(exc).__name__ + ": " + str(exc)[:200]
t4 = time.perf_counter()

print(json.dumps({{
    "state_root": root,
    "scoped_paths": len(paths),
    "episode_count": index.get("episode_count"),
    "governance_records": len(records),
    "governance_warnings": len(warnings),
    "governance_issues": len(gov.get("issues", [])),
    "registry_len": registry_len,
    "registry_error": registry_error,
    "scan_s": t1 - t0,
    "build_s": t2 - t1,
    "gov_s": t3 - t2,
    "registry_s": t4 - t3,
}}))
'''


def all_frame_files(root):
    return sorted((root / "frames").glob("*/*.jsonl"))


def held_frame_files():
    if not HELD_ROOT.exists():
        return []
    return sorted(HELD_ROOT.glob("*/*.jsonl"))


def set_frame_count(target):
    """Move frame files between the copy and the holding dir until count == target.

    Selection is deterministic: sorted order, keep the first N. Only files under
    COPY_ROOT/frames and HELD_ROOT are ever moved.
    """
    present = all_frame_files(COPY_ROOT)
    held = held_frame_files()
    if target is None:
        target = len(present) + len(held)

    # restore first so the "keep the first N of the sorted union" rule is stable
    for path in held:
        dest = COPY_ROOT / "frames" / path.parent.name / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))

    present = all_frame_files(COPY_ROOT)
    for path in present[target:]:
        dest = HELD_ROOT / path.parent.name / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
    return len(all_frame_files(COPY_ROOT))


def measure(label, size):
    present = set_frame_count(size)
    src = CHILD_SRC.format(
        scripts=SCRIPTS, copy=COPY_ROOT, workspace=WORKSPACE, scope=SCOPE
    )
    env = dict(os.environ)
    env["WEILAN_METHOD_HOME"] = str(COPY_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    t_spawn = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-c", src],
        capture_output=True, env=env, cwd=str(COPY_ROOT), timeout=1800,
    )
    wall = time.perf_counter() - t_spawn
    out = proc.stdout.decode("utf-8", "replace").strip()
    if proc.returncode != 0 or not out:
        return {
            "label": label, "requested": size, "frame_files_present": present,
            "rc": proc.returncode, "wall_s": wall,
            "stderr_tail": proc.stderr.decode("utf-8", "replace")[-800:],
        }
    payload = json.loads(out.splitlines()[-1])
    payload.update({
        "label": label, "requested": size, "frame_files_present": present,
        "rc": proc.returncode, "wall_s": wall,
    })
    return payload


def startup_baseline():
    samples = []
    for _ in range(3):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
        samples.append(time.perf_counter() - t)
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(
        Path(__file__).with_suffix("").as_posix() + ".out.json"))
    parser.add_argument("--keep-copy", action="store_true")
    args = parser.parse_args()

    assert COPY_ROOT.resolve() != PRODUCTION_ROOT.resolve()
    assert not str(PRODUCTION_ROOT).lower().startswith(str(COPY_ROOT).lower())

    prod_frames_before = len(all_frame_files(PRODUCTION_ROOT))
    prod_files_before = sum(1 for p in PRODUCTION_ROOT.rglob("*") if p.is_file())

    for stale in (COPY_ROOT, HELD_ROOT):
        if stale.exists():
            shutil.rmtree(stale)
    t_copy = time.perf_counter()
    shutil.copytree(PRODUCTION_ROOT, COPY_ROOT)
    copy_s = time.perf_counter() - t_copy
    HELD_ROOT.mkdir(parents=True, exist_ok=True)

    total_frames = len(all_frame_files(COPY_ROOT))

    result = {
        "probe": "advisory_scaling",
        "question": "is the intra-lock advisory O(frame files)? boundary 3 of FINDING sections 7/9",
        "production_root": str(PRODUCTION_ROOT),
        "copy_root": str(COPY_ROOT),
        "copy_seconds": copy_s,
        "copy_frame_files": total_frames,
        "production_frame_files_before": prod_frames_before,
        "production_files_before": prod_files_before,
        "startup_baseline_s": startup_baseline(),
        "sizes": SIZES,
        "rounds": ROUNDS,
        "warmup": None,
        "measurements": [],
    }

    result["warmup"] = measure("warmup", None)

    for round_index in range(ROUNDS):
        order = list(SIZES)
        # SIZES is ascending with None (=largest) last; alternate direction per round
        if round_index % 2 == 0:
            order = list(reversed(order))
        for size in order:
            label = "r{}-n{}".format(round_index, "all" if size is None else size)
            row = measure(label, size)
            row["round"] = round_index
            row["order"] = "desc" if round_index % 2 == 0 else "asc"
            result["measurements"].append(row)
            print(label, json.dumps({
                k: row.get(k) for k in
                ("frame_files_present", "scan_s", "build_s", "gov_s", "registry_s", "rc")
            }), flush=True)

    set_frame_count(None)
    result["copy_frame_files_restored"] = len(all_frame_files(COPY_ROOT))
    result["held_left_over"] = len(held_frame_files())

    result["production_frame_files_after"] = len(all_frame_files(PRODUCTION_ROOT))
    result["production_files_after"] = sum(
        1 for p in PRODUCTION_ROOT.rglob("*") if p.is_file())
    result["production_untouched"] = (
        result["production_frame_files_after"] == prod_frames_before
        and result["production_files_after"] == prod_files_before
    )

    Path(args.out).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", args.out)

    if not args.keep_copy:
        for stale in (COPY_ROOT, HELD_ROOT):
            if stale.exists():
                shutil.rmtree(stale, ignore_errors=True)
        print("removed ledger copy")


if __name__ == "__main__":
    main()
