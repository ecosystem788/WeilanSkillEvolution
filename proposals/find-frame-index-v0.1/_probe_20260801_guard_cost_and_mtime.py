"""Read-only probe: can path A's ambiguity guard be afforded?

Two questions the adjudication of Codex's 2026-08-01 rejection turns on.

Q1 (soundness): on this filesystem, does creating a file inside a directory
    change that directory's mtime, and at what granularity? The whole
    "stat the date dirs instead of globbing" idea rests on this being true.
Q2 (cost): per find_frame lookup, how does the baseline glob compare with
    (a) a full scandir-of-all-date-dirs mtime guard and (b) a two-stat
    guard over only frames_root plus today's UTC date dir?

Never writes under the live frames root. Q1 uses a fresh temp dir.
"""
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent / "candidate" / "solve-with-weilan" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import weilan_trace as wt  # noqa: E402

out = {"probe": "guard_cost_and_mtime", "read_only_under_live_frames": True}

# ---- Q1: directory mtime as a creation signal ----------------------------
tmp = Path(tempfile.mkdtemp(prefix="wl-mtime-"))
try:
    d = tmp / "shard"
    d.mkdir()
    trials = []
    for i in range(200):
        before = os.stat(d).st_mtime_ns
        (d / f"f{i}.jsonl").write_text("{}\n", encoding="utf-8")
        after = os.stat(d).st_mtime_ns
        trials.append({"changed": after != before, "delta_ns": after - before})
    changed = [t for t in trials if t["changed"]]
    deltas = sorted({t["delta_ns"] for t in changed if t["delta_ns"] > 0})
    out["q1_dir_mtime"] = {
        "filesystem_of": str(tmp.drive or tmp),
        "creations": len(trials),
        "dir_mtime_changed": len(changed),
        "dir_mtime_unchanged": len(trials) - len(changed),
        "missed_fraction": round((len(trials) - len(changed)) / len(trials), 4),
        "smallest_observed_positive_delta_ns": deltas[0] if deltas else None,
        "verdict": (
            "creation always moved the dir mtime"
            if len(changed) == len(trials)
            else "creation sometimes left the dir mtime unchanged -> same-tick hole is real"
        ),
    }
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---- Q2: per-lookup cost of glob vs the two guard shapes -----------------
frames_root = wt.state_root() / "frames"
date_dirs = sorted(e.name for e in os.scandir(frames_root) if e.is_dir())
sample_ids = []
for name in date_dirs[-3:]:
    for entry in os.scandir(frames_root / name):
        if entry.name.endswith(".jsonl"):
            sample_ids.append(entry.name[: -len(".jsonl")])
        if len(sample_ids) >= 40:
            break
    if len(sample_ids) >= 40:
        break

REPS = 40


def timed(fn):
    samples = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples)


def baseline_glob():
    for fid in sample_ids:
        list(frames_root.glob(f"*/{fid}.jsonl"))


def guard_all_dirs():
    # full guard: one scandir of frames_root, mtimes read off the DirEntry
    for _ in sample_ids:
        {e.name: e.stat().st_mtime_ns for e in os.scandir(frames_root) if e.is_dir()}


def guard_two_stats():
    # narrow guard: frames_root itself plus today's UTC date dir
    for _ in sample_ids:
        today = frames_root / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        os.stat(frames_root).st_mtime_ns
        try:
            os.stat(today).st_mtime_ns
        except OSError:
            pass


for fn in (baseline_glob, guard_all_dirs, guard_two_stats):  # warm the cache
    fn()

glob_s = timed(baseline_glob)
all_s = timed(guard_all_dirs)
two_s = timed(guard_two_stats)
out["q2_cost"] = {
    "date_dirs": len(date_dirs),
    "sample_lookups_per_rep": len(sample_ids),
    "reps": REPS,
    "median_s_per_rep": {
        "baseline_glob": round(glob_s, 6),
        "guard_all_dirs_scandir": round(all_s, 6),
        "guard_two_stats": round(two_s, 6),
    },
    "guard_cost_as_fraction_of_glob": {
        "guard_all_dirs_scandir": round(all_s / glob_s, 4),
        "guard_two_stats": round(two_s / glob_s, 4),
    },
}
print(json.dumps(out, ensure_ascii=False, indent=2))
