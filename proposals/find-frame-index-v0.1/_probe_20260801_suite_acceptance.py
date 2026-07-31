"""Run the skill's own test suite against the frozen baseline and the frozen
candidate under identical conditions, and report rc plus the collected node list.

Deliberately not reporting "all green": on this line the phrase has already been
wrong once. pytest prints "no tests collected" under rc 0, 2 and 5 alike, so the
acceptance signal here is (returncode, collected node count, per-node verdict).
The suite is mixed-style -- some files are pytest modules, some are argparse
scripts with a main() that pytest collects nothing from -- so both are run:
pytest over scripts/, then each main()-style file executed directly.

Emits JSON to stdout. Nothing outside temp dirs is written.
"""

import json
import os
import re
import subprocess
import sys

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b"
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")


def pytest_run(scripts_dir, timeout):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", ".", "-v", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=scripts_dir, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )
    nodes = {}
    for line in proc.stdout.splitlines():
        match = NODE_RE.match(line.strip())
        if match:
            nodes[match.group(1)] = match.group(2)
    verdicts = {}
    for verdict in nodes.values():
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    return {
        "returncode": proc.returncode,
        "collected_node_count": len(nodes),
        "verdict_counts": verdicts,
        "non_passing_nodes": sorted(
            node for node, verdict in nodes.items()
            if verdict not in ("PASSED", "SKIPPED", "XFAIL")
        ),
        "nodes": sorted(nodes),
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
    }


def main_style_files(scripts_dir):
    found = []
    for name in sorted(os.listdir(scripts_dir)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(scripts_dir, name), encoding="utf-8") as handle:
            text = handle.read()
        if "\ndef main(" in text and "__main__" in text:
            found.append(name)
    return found


def script_runs(scripts_dir, names, timeout):
    results = {}
    for name in names:
        try:
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", name],
                cwd=scripts_dir, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout,
            )
            results[name] = {
                "returncode": proc.returncode,
                "stderr_tail": proc.stderr.strip()[-300:] if proc.returncode else "",
            }
        except subprocess.TimeoutExpired:
            results[name] = {"returncode": None, "stderr_tail": "TIMEOUT"}
    return results


def main():
    timeout = int(os.environ.get("WEILAN_PROBE_TIMEOUT", "1800"))
    out = {"base_artifact_hash": BASE, "candidate_artifact_hash": CAND, "trees": {}}
    for label, digest in (("baseline", BASE), ("candidate", CAND)):
        scripts_dir = os.path.join(HERE, "artifacts", digest, "solve-with-weilan", "scripts")
        names = main_style_files(scripts_dir)
        out["trees"][label] = {
            "scripts_dir": scripts_dir,
            "pytest": pytest_run(scripts_dir, timeout),
            "main_style_file_count": len(names),
            "main_style_runs": script_runs(scripts_dir, names, timeout),
        }
    for label, tree in out["trees"].items():
        failing = [n for n, r in tree["main_style_runs"].items() if r["returncode"] != 0]
        tree["main_style_nonzero"] = sorted(failing)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
