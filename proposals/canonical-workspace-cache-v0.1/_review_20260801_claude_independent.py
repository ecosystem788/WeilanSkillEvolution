"""Claude's independent review probe for canonical-workspace-cache-v0.1.

Read-only. Does not re-use Codex's probe code. Answers four questions the
review actually turns on:

  1. Are both install trees byte-identical to this package's baseline/ tree?
     (If not, "baseline" in the package is not the deployed baseline and the
     equivalence + latency evidence is measured against the wrong thing.)
  2. Is find-frame-index-v0.1 deployed? The observer's queue order puts it
     first; the canonical-workspace-cache work is the "remaining 50-110s"
     step that comes after.
  3. Does the candidate's contract test discriminate for the stated reason --
     i.e. does it FAIL by assertion on baseline, not error out?
  4. Do the reported latency samples separate cleanly, or only at the median?

Writes only its own .out.json next to itself.
"""

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
INSTALLS = {
    "claude_home": r"C:\Users\zy\.claude\skills\solve-with-weilan",
    "repo_skill": os.path.join(REPO, "skill", "solve-with-weilan"),
}
BASELINE = os.path.join(HERE, "baseline", "solve-with-weilan")
CANDIDATE = os.path.join(HERE, "candidate", "solve-with-weilan")
FFI = os.path.join(REPO, "proposals", "find-frame-index-v0.1")


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_map(root):
    """relpath (posix, lowercased separators kept) -> sha256 of raw bytes."""
    out = {}
    if not os.path.isdir(root):
        return None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            out[rel] = file_sha(full)
    return out


def compare(a, b):
    if a is None or b is None:
        return {"comparable": False}
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    differing = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    return {
        "comparable": True,
        "identical": not (only_a or only_b or differing),
        "file_count_a": len(a),
        "file_count_b": len(b),
        "only_in_a": only_a,
        "only_in_b": only_b,
        "differing_content": differing,
    }


result = {"probe": "claude_independent_review_canonical_workspace_cache_v0_1"}

# ---- Q1: install trees vs package baseline -------------------------------
base_map = tree_map(BASELINE)
cand_map = tree_map(CANDIDATE)
result["baseline_vs_candidate"] = compare(base_map, cand_map)
result["installs_vs_package_baseline"] = {
    name: compare(tree_map(path), base_map) for name, path in INSTALLS.items()
}

# ---- Q2: is find-frame-index deployed? -----------------------------------
ffi = {"package_present": os.path.isdir(FFI)}
if ffi["package_present"]:
    ffi_base = tree_map(os.path.join(FFI, "baseline", "solve-with-weilan"))
    ffi_cand = tree_map(os.path.join(FFI, "candidate", "solve-with-weilan"))
    ffi["candidate_vs_its_baseline"] = compare(ffi_cand, ffi_base)
    ffi["its_baseline_equals_this_baseline"] = compare(ffi_base, base_map)
    ffi["installs_vs_ffi_candidate"] = {
        name: compare(tree_map(path), ffi_cand) for name, path in INSTALLS.items()
    }
result["find_frame_index"] = ffi

# ---- Q3: contract test discriminates by assertion, independently ---------
disc = {}
try:
    test_src = os.path.join(CANDIDATE, "scripts", "test_canonical_workspace_cache.py")
    disc["test_exists"] = os.path.isfile(test_src)
    if disc["test_exists"]:
        with io.open(test_src, encoding="utf-8") as fh:
            disc["test_body"] = fh.read()
        for arm, tree in (("baseline", BASELINE), ("candidate", CANDIDATE)):
            with tempfile.TemporaryDirectory() as tmp:
                import shutil

                staged = os.path.join(tmp, "solve-with-weilan")
                shutil.copytree(tree, staged)
                dest = os.path.join(staged, "scripts", "test_canonical_workspace_cache.py")
                shutil.copyfile(test_src, dest)
                proc = subprocess.run(
                    [sys.executable, "-X", "utf8", "-m", "pytest", dest, "-v", "--no-header", "-p", "no:cacheprovider"],
                    capture_output=True,
                    cwd=os.path.join(staged, "scripts"),
                )
                out = proc.stdout.decode("utf-8", "replace")
                err = proc.stderr.decode("utf-8", "replace")
                disc[arm] = {
                    "returncode": proc.returncode,
                    "passed": out.count(" PASSED"),
                    "failed": out.count(" FAILED"),
                    "errors": out.count(" ERROR"),
                    "has_assertion_error": "AssertionError" in out,
                    "has_collection_error": "ERROR collecting" in out or "ImportError" in out,
                    "tail": out[-1500:],
                    "stderr_tail": err[-400:],
                }
except Exception as exc:  # noqa: BLE001
    disc["exception"] = repr(exc)
result["contract_discrimination_independent"] = disc

# ---- Q4: latency separation, not just medians ----------------------------
lat = {}
try:
    p = os.path.join(HERE, "_probe_real_open_latency.out.json")
    with io.open(p, encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    lat["raw_keys"] = sorted(raw.keys())

    def collect(node):
        found = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("samples", "wall_seconds", "durations", "seconds") and isinstance(v, list):
                    found.extend(x for x in v if isinstance(x, (int, float)))
                else:
                    found.extend(collect(v))
        elif isinstance(node, list):
            for v in node:
                found.extend(collect(v))
        return found

    arms = {}
    for key in ("baseline", "candidate"):
        node = raw.get(key)
        if node is None and isinstance(raw.get("arms"), dict):
            node = raw["arms"].get(key)
        if node is not None:
            vals = collect(node)
            if vals:
                arms[key] = sorted(vals)
    lat["arms"] = arms
    if "baseline" in arms and "candidate" in arms:
        lat["baseline_min"] = min(arms["baseline"])
        lat["candidate_max"] = max(arms["candidate"])
        lat["ranges_disjoint"] = min(arms["baseline"]) > max(arms["candidate"])
        lat["worst_case_ratio"] = min(arms["baseline"]) / max(arms["candidate"])
except Exception as exc:  # noqa: BLE001
    lat["exception"] = repr(exc)
result["latency_separation"] = lat

out_path = os.path.join(HERE, "_review_20260801_claude_independent.out.json")
with io.open(out_path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=1, ensure_ascii=False, sort_keys=True)

summary = {
    "installs_identical_to_package_baseline": {
        k: v.get("identical") for k, v in result["installs_vs_package_baseline"].items()
    },
    "ffi_installed": {
        k: v.get("identical")
        for k, v in result["find_frame_index"].get("installs_vs_ffi_candidate", {}).items()
    },
    "ffi_baseline_same_as_ours": result["find_frame_index"]
    .get("its_baseline_equals_this_baseline", {})
    .get("identical"),
    "disc_baseline_rc": disc.get("baseline", {}).get("returncode"),
    "disc_baseline_assertion": disc.get("baseline", {}).get("has_assertion_error"),
    "disc_baseline_collection_error": disc.get("baseline", {}).get("has_collection_error"),
    "disc_candidate_rc": disc.get("candidate", {}).get("returncode"),
    "disc_candidate_passed": disc.get("candidate", {}).get("passed"),
    "latency_ranges_disjoint": lat.get("ranges_disjoint"),
    "latency_worst_case_ratio": lat.get("worst_case_ratio"),
}
print(json.dumps(summary, indent=1, ensure_ascii=False))
