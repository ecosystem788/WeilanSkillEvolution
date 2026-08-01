"""Compare read-only CLI output bytes from the two frozen trees."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f"
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
OUT = HERE / "_probe_cli_equivalence.out.json"
COMMANDS = {
    "memory-recall": ["memory-recall", "--workspace", WORKSPACE, "--scope", SCOPE],
    "prospective-show": ["prospective-show", "--workspace", WORKSPACE, "--scope", SCOPE],
    "lineage-show": ["lineage-show", "--workspace", WORKSPACE, "--scope", SCOPE],
}


def run(digest, argv):
    script = HERE / "artifacts" / digest / "solve-with-weilan" / "scripts" / "weilan_trace.py"
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), *argv],
        capture_output=True,
        env=env,
        timeout=300,
    )
    return {
        "returncode": proc.returncode,
        "stdout_bytes": len(proc.stdout),
        "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
        "stderr_tail": proc.stderr.decode("utf-8", errors="replace")[-300:],
    }, proc.stdout


def main():
    commands = {}
    all_equivalent = True
    for name, argv in COMMANDS.items():
        baseline, baseline_stdout = run(BASE, argv)
        candidate, candidate_stdout = run(CAND, argv)
        equivalent = (
            baseline["returncode"] == candidate["returncode"] == 0
            and baseline_stdout == candidate_stdout
        )
        commands[name] = {
            "argv": argv,
            "baseline": baseline,
            "candidate": candidate,
            "stdout_byte_identical": equivalent,
        }
        all_equivalent = all_equivalent and equivalent
    result = {
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "workspace": WORKSPACE,
        "scope": SCOPE,
        "commands": commands,
        "all_commands_byte_identical": all_equivalent,
        "boundary": "Read-only command equivalence on one current ledger is not a proof over all inputs.",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
