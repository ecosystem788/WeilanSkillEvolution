"""Read-only probe: where does the wake-path time actually go?

Times the three candidate cost centres separately, in one fresh process each
component measured before the module memoizes it. Writes nothing.
"""
import json
import sys
import time

sys.path.insert(0, r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
import weilan_trace as wt  # noqa: E402

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
out = {}

path = wt.episode_index_path(WORKSPACE, SCOPE)
out["episode_index_bytes"] = path.stat().st_size

t = time.perf_counter()
index = wt.load_episode_index(WORKSPACE, SCOPE)
out["load_episode_index_s"] = round(time.perf_counter() - t, 3)
out["episode_count"] = index and index.get("episode_count")

t = time.perf_counter()
paths = wt.scoped_frame_paths(WORKSPACE, SCOPE)
out["scoped_frame_paths_s"] = round(time.perf_counter() - t, 3)
out["scoped_frame_count"] = len(paths)

t = time.perf_counter()
state = wt.frame_source_state(paths)
out["frame_source_state_s"] = round(time.perf_counter() - t, 3)

t = time.perf_counter()
fresh = wt.episode_index_is_fresh(index, WORKSPACE, SCOPE)
out["episode_index_is_fresh_s_warm"] = round(time.perf_counter() - t, 3)
out["episode_index_fresh"] = fresh

t = time.perf_counter()
registry = wt.collapse_trace_registry(WORKSPACE, SCOPE)
out["collapse_trace_registry_s_warm"] = round(time.perf_counter() - t, 3)
out["registry_entries"] = len(registry)

print(json.dumps(out, ensure_ascii=False, indent=2))
