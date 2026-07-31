"""Read-only probe: is lineage-show's cost find_frame's per-id glob?

Runs command_lineage_show twice in two fresh subprocess-free passes is not
possible (module-level memoization), so this probe runs the baseline in one
process and the indexed variant in another, then compares stdout byte-for-byte.

Writes nothing outside its own stdout. Pass a mode argument:
    python _probe_20260801_find_frame_index.py baseline
    python _probe_20260801_find_frame_index.py indexed
"""
import io
import json
import os
import pathlib
import sys
import time
import types

SKILL = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts"
sys.path.insert(0, SKILL)
import weilan_trace as wt  # noqa: E402

WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"


def build_index():
    """id -> [paths], from one sweep of frames/*/ instead of one glob per id."""
    root = wt.state_root() / "frames"
    index = {}
    if not root.is_dir():
        return index
    for date_dir in os.scandir(root):
        if not date_dir.is_dir():
            continue
        for entry in os.scandir(date_dir.path):
            if not entry.is_file() or not entry.name.endswith(".jsonl"):
                continue
            index.setdefault(entry.name[: -len(".jsonl")], []).append(
                pathlib.Path(entry.path)
            )
    return index


def indexed_find_frame(frame_id, _cache={}):
    if not _cache:
        _cache["index"] = build_index()
    candidates = _cache["index"].get(frame_id, [])
    matches = [path for path in candidates if wt.read_events(path)]
    if not matches:
        raise FileNotFoundError(f"frame not found: {frame_id}")
    if len(matches) > 1:
        raise RuntimeError(f"multiple frame files found: {frame_id}")
    return matches[0]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if mode == "indexed":
        wt.find_frame = indexed_find_frame
    args = types.SimpleNamespace(workspace=WORKSPACE, scope=SCOPE)
    buffer = io.StringIO()
    real_stdout, sys.stdout = sys.stdout, buffer
    started = time.perf_counter()
    try:
        rc = wt.command_lineage_show(args)
    finally:
        sys.stdout = real_stdout
    elapsed = time.perf_counter() - started
    payload = buffer.getvalue()
    import hashlib

    print(json.dumps({
        "mode": mode,
        "rc": rc,
        "elapsed_s": round(elapsed, 3),
        "stdout_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "stdout_bytes": len(payload.encode("utf-8")),
        "record_count": json.loads(payload).get("record_count"),
        "valid": json.loads(payload).get("valid"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
