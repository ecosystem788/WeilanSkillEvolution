"""Read-only probe: what sets the peak the acceptance stop-line measures?

Acceptance item 4 of the co-signature (peer-chat 2026-08-02T15:59:34+09:00,
agreed 16:33:55) is a *delta* between two tracemalloc peaks: "峰值堆增量须报;
超过 +25 MB 即停下重议". Review measured +34.2 MB at ~19:30 and stopped the
candidate on it (peer-chat 19:37:06); Codex ruled it unacceptable at 19:49:14.

This probe measures one thing only: the tracemalloc peak of `json.load` on the
on-disk episode index, with nothing else running. `collapse_trace_registry`
(weilan_trace.py:4469) calls `load_episode_index` before anything the memo can
affect, so this allocation happens identically in both arms. If this number
equals the baseline arm's whole-call-site peak, then the peak both arms report
is set by this one load and not by the code under test.

That matters because a delta between two high-water marks is not a monotone
measure of the candidate's own memory cost: bytes the candidate retains after
the spike are invisible to it until they exceed the spike. The index file grows
with the corpus, so the same candidate can measure smaller as the corpus gets
bigger.

Read-only: opens one file for reading. Writes nothing.

Usage:
  python _probe_20260802_peak_attribution.py
"""

import json
import os
import pathlib
import sys
import tracemalloc

INDEX = pathlib.Path(
    r"D:\CodexData\home\method-state\memory\episode-indexes"
    r"\workspaces\d431c38105a9a791\c36aecb1ff20.json"
)
FRAMES = pathlib.Path(r"D:\CodexData\home\method-state\frames")


def main():
    if not INDEX.is_file():
        print(json.dumps({"error": "episode index not found", "path": str(INDEX)}))
        return 1
    stat = INDEX.stat()
    frame_files = len(list(FRAMES.glob("*/*.jsonl"))) if FRAMES.exists() else None

    tracemalloc.start()
    with INDEX.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result = {
        "measurement": "tracemalloc peak of json.load on the episode index alone",
        "index_path": str(INDEX),
        "index_file_mb": round(stat.st_size / 1e6, 2),
        "index_episode_count": len(value.get("episodes", [])),
        "frame_files_on_disk": frame_files,
        "index_is_stale_vs_frame_count": (
            frame_files is not None and len(value.get("episodes", [])) != frame_files
        ),
        "retained_after_load_mb": round(current / 1e6, 1),
        "peak_python_heap_mb": round(peak / 1e6, 1),
        "python": sys.version.split()[0],
        "note": (
            "tracemalloc counts Python allocation bytes, not RSS. The index file "
            "is rewritten by whichever body opens a frame next, so this number is "
            "an instant reading of a corpus a concurrent peer mutates."
        ),
        "pid": os.getpid(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
