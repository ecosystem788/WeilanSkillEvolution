"""Read-only: ground-truth evaluation of episode_index_is_fresh() right now,
plus the scope of the newest frame file. Confirms whether the persisted index
is actually stale for THIS scope (not merely missing a foreign-scope frame)."""
import json
import sys
import time

sys.path.insert(0, r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
import weilan_trace as wt  # noqa: E402

WS = wt.canonical_workspace(r"D:\WeilanSkillEvolution")
SCOPE = wt.normalize_scope("skill-evolution")

root = wt.state_root() / "frames"
newest = max(root.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime_ns)
ev = wt.read_events(newest)
out = {
    "newest_frame_file": newest.name,
    "newest_frame_scope": wt.frame_scope(ev),
    "newest_frame_workspace": ev[0].get("workspace") if ev else None,
    "newest_frame_is_ours": bool(ev)
    and wt.normalized_workspace(ev[0].get("workspace", "")) == wt.normalized_workspace(WS)
    and wt.frame_scope(ev).casefold() == SCOPE.casefold(),
}

idx = wt.load_episode_index(WS, SCOPE)
t0 = time.perf_counter()
fresh = wt.episode_index_is_fresh(idx, WS, SCOPE)
out["episode_index_is_fresh_now"] = bool(fresh)
out["freshness_check_seconds"] = round(time.perf_counter() - t0, 3)
out["scoped_path_count_now"] = len(wt.scoped_frame_paths(WS, SCOPE))
out["index_source_state_len"] = len(idx.get("source_state") or []) if idx else None
print(json.dumps(out, ensure_ascii=False, indent=2))
