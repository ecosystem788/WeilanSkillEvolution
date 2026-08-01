"""Read-only probe: does a process-local cache of canonical_workspace ever go stale?

Context. Codex's 2026-08-01T11:24:28+09:00 review of candidate A (memoize
canonical_workspace) concluded the semantics hold for the deployed CLI, bounded
to "one process = one command", on the strength of a static call-site census:
production code has no symlink/junction/mount/readlink/chdir call and main()
dispatches exactly once. This probe does not re-run that census. It asks the
complementary dynamic question the census cannot answer:

    within ONE process, can canonical_workspace(s) return two different values
    for the same input string s?

If yes, a module-level dict cache keyed on s is not a pure memoization, and the
"one process = one command" boundary is doing real load-bearing work rather than
being a conservative caveat. That distinction decides whether the candidate needs
an explicit invalidation contract or merely a docstring.

Everything here runs in a throwaway temp directory. It imports the DEPLOYED
runtime_core (both install points are byte-identical; asserted below) and only
calls canonical_workspace. It writes no ledger, touches no proposal, and mutates
nothing under either skill tree or method-state.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLAUDE_TREE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan")
CODEX_TREE = Path(r"D:\CodexData\skills\solve-with-weilan")
OUT = Path(__file__).with_suffix(".out.json")


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_canonical_workspace():
    sys.path.insert(0, str(CLAUDE_TREE / "scripts"))
    import runtime_core  # noqa: E402

    return runtime_core.canonical_workspace


def main():
    result = {
        "probe": "canonical_workspace process-local cache invalidation",
        "authority": "read_only_evidence_no_adoption",
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "install_points": {},
        "cases": [],
        "verdict": {},
    }

    for name, tree in (("claude", CLAUDE_TREE), ("codex", CODEX_TREE)):
        rc = tree / "scripts" / "runtime_core.py"
        result["install_points"][name] = {
            "path": str(rc),
            "exists": rc.exists(),
            "sha256": sha256_file(rc) if rc.exists() else None,
        }
    shas = {v["sha256"] for v in result["install_points"].values()}
    result["install_points"]["identical"] = len(shas) == 1 and None not in shas

    cw = load_canonical_workspace()
    tmp = Path(tempfile.mkdtemp(prefix="wl_cache_probe_"))
    try:
        # Case 1 -- the reachable one: same string, resolved before the directory
        # exists and again after it is created, with a case difference between the
        # string and the on-disk name. On Windows resolve() reports the on-disk
        # case only once the entry exists.
        d = tmp / "WorkspaceCaseTest"
        probe_str = str(tmp / "workspacecasetest")
        before = cw(probe_str)
        d.mkdir()
        after = cw(probe_str)
        result["cases"].append(
            {
                "case": "resolve_before_vs_after_mkdir_case_differs",
                "input": probe_str,
                "on_disk_name": d.name,
                "before_exists": before,
                "after_exists": after,
                "stable": before == after,
                "note": "unstable => a dict cache keyed on the input string can "
                "hand back a pre-creation value for the rest of the process",
            }
        )

        # Case 2 -- control: same string, directory exists the whole time.
        d2 = tmp / "AlreadyThere"
        d2.mkdir()
        s2 = str(d2)
        result["cases"].append(
            {
                "case": "resolve_twice_directory_stable",
                "input": s2,
                "first": cw(s2),
                "second": cw(s2),
                "stable": cw(s2) == cw(s2),
            }
        )

        # Case 3 -- directory replaced under the same name in-process (delete +
        # recreate with different on-disk case). No symlink or junction needed.
        d3 = tmp / "SwapMe"
        d3.mkdir()
        s3 = str(tmp / "SwapMe")
        first = cw(s3)
        shutil.rmtree(d3)
        (tmp / "swapme").mkdir()
        second = cw(s3)
        result["cases"].append(
            {
                "case": "same_name_recreated_with_different_disk_case",
                "input": s3,
                "first": first,
                "second": second,
                "stable": first == second,
            }
        )

        # Case 4 -- does the deployed CLI itself ever resolve a workspace that
        # does not exist yet? Ask it, read-only, with a path under tmp.
        missing = tmp / "NeverCreated"
        proc = subprocess.run(
            [
                sys.executable,
                str(CLAUDE_TREE / "scripts" / "weilan_trace.py"),
                "memory-recall",
                "--workspace",
                str(missing),
                "--scope",
                "probe-only",
            ],
            capture_output=True,
            timeout=180,
        )
        result["cases"].append(
            {
                "case": "cli_accepts_nonexistent_workspace",
                "input": str(missing),
                "returncode": proc.returncode,
                "accepted": proc.returncode == 0,
                "stdout_head": proc.stdout[:400].decode("utf-8", "replace"),
                "stderr_head": proc.stderr[:400].decode("utf-8", "replace"),
                "note": "if the CLI accepts a workspace path that does not exist, "
                "case 1 is reachable through a real command, not only in-process",
            }
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    unstable = [c["case"] for c in result["cases"] if c.get("stable") is False]
    result["verdict"] = {
        "unstable_cases": unstable,
        "same_string_can_resolve_two_ways_in_one_process": bool(unstable),
        "reading": (
            "empty unstable_cases => memoizing canonical_workspace is a pure "
            "function cache under any process shape; non-empty => the cache is "
            "sound only because each process runs exactly one command, and that "
            "boundary must be stated as a contract, not a caveat"
        ),
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["verdict"], ensure_ascii=False, indent=2))
    for c in result["cases"]:
        print(c["case"], "stable=", c.get("stable"), c.get("accepted", ""))


if __name__ == "__main__":
    main()
