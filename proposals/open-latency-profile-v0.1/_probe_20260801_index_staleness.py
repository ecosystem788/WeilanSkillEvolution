"""Read-only probe: is the on-disk episode index ever fresh at `open` time?

Claims under test (source: scripts/weilan_trace.py):
  (a) collapse_trace_registry() rebuilds in memory only and never persists;
      only the explicit `episode-index` command writes the file.
  (b) command_frame_open writes the new frame file BEFORE calling
      attach_trace_advisory_result.
Consequence: the persisted index is older than the newest frame file, so
episode_index_is_fresh() is false at open. This probe measures the gap.
No writes. No ledger appends.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
import weilan_trace as wt  # noqa: E402

WS = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"

idx_path = wt.episode_index_path(wt.canonical_workspace(WS), wt.normalize_scope(SCOPE))
out = {"index_path": str(idx_path), "index_exists": idx_path.is_file()}

if out["index_exists"]:
    with idx_path.open("r", encoding="utf-8") as fh:
        idx = json.load(fh)
    out["index_generated_at_utc"] = idx.get("generated_at_utc")
    out["index_schema_version"] = idx.get("schema_version")
    out["index_schema_current"] = idx.get("schema_version") == wt.EPISODE_INDEX_SCHEMA_VERSION
    out["index_episode_count"] = idx.get("episode_count")
    out["index_source_state_len"] = len(idx.get("source_state") or [])
    out["index_file_mtime_ns"] = idx_path.stat().st_mtime_ns
else:
    idx = None

root = wt.state_root() / "frames"
all_files = sorted(root.glob("*/*.jsonl"))
out["global_frame_file_count"] = len(all_files)
newest = max(all_files, key=lambda p: p.stat().st_mtime_ns) if all_files else None
if newest is not None:
    out["newest_frame_file"] = newest.name
    out["newest_frame_mtime_ns"] = newest.stat().st_mtime_ns
    if out["index_exists"]:
        gap_ns = out["newest_frame_mtime_ns"] - out["index_file_mtime_ns"]
        out["newest_frame_minus_index_seconds"] = round(gap_ns / 1e9, 3)

# Files that the scoped scan skips because they carry no events: these are the
# ones a name-set inventory + known-scoped stat would not cover.
empty_files = [p.name for p in all_files if p.stat().st_size == 0]
out["zero_byte_frame_files"] = empty_files[:20]
out["zero_byte_frame_file_count"] = len(empty_files)

# Does the persisted index know about the newest frame file?
if out["index_exists"] and newest is not None:
    known = {e.get("path") for e in (idx.get("source_state") or [])}
    try:
        rel = str(newest.relative_to(wt.state_root()))
    except ValueError:
        rel = str(newest)
    out["newest_frame_in_index_source_state"] = rel in known

print(json.dumps(out, ensure_ascii=False, indent=2))
