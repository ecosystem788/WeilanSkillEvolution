"""Read-only CLI byte-equivalence bound to the REVISED candidate 8602bb0f.

The author's `_probe_cli_equivalence.out.json` names the previous candidate ec236760. This
run adds two things that receipt cannot give:

1. the revised content address is the one actually executed, so target metric #5 stops
   being inherited evidence;
2. a third arm runs the prior candidate in the same session, so the claim "the two
   candidate trees differ only in a test file, therefore CLI behaviour is unchanged" is
   measured rather than inferred.

All three commands are read-only. Nothing is written to the production ledger.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = {
    "baseline": "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad",
    "revised_candidate": "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a",
    "prior_candidate": "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f",
}
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
OUT = HERE / "_shadow_20260801_claude_cli_equivalence_revised.out.json"
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
        capture_output=True, env=env, timeout=300,
    )
    return {
        "returncode": proc.returncode,
        "stdout_bytes": len(proc.stdout),
        "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest(),
        "stderr_tail": proc.stderr.decode("utf-8", errors="replace")[-300:],
    }


def main():
    commands = {}
    all_equivalent = True
    revised_matches_prior = True
    for name, argv in COMMANDS.items():
        rows = {arm: run(digest, argv) for arm, digest in ARMS.items()}
        base = rows["baseline"]
        revised = rows["revised_candidate"]
        prior = rows["prior_candidate"]
        equivalent = (
            base["returncode"] == revised["returncode"] == 0
            and base["stdout_sha256"] == revised["stdout_sha256"]
        )
        same_across_candidates = (
            prior["returncode"] == revised["returncode"]
            and prior["stdout_sha256"] == revised["stdout_sha256"]
        )
        commands[name] = {
            "argv": argv,
            "arms": rows,
            "baseline_vs_revised_byte_identical": equivalent,
            "prior_vs_revised_byte_identical": same_across_candidates,
        }
        all_equivalent = all_equivalent and equivalent
        revised_matches_prior = revised_matches_prior and same_across_candidates
    result = {
        "probe": "claude independent read-only CLI equivalence, three arms",
        "arms": ARMS,
        "workspace": WORKSPACE,
        "scope": SCOPE,
        "commands": commands,
        "baseline_and_revised_candidate_byte_identical": all_equivalent,
        "prior_and_revised_candidate_byte_identical": revised_matches_prior,
        "boundary": (
            "Read-only command equivalence on one current ledger is not a proof over all "
            "inputs. Byte identity across the two candidate content addresses is evidence "
            "for these three commands only, not a general statement about the test file "
            "being unreachable from every entry point."
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
