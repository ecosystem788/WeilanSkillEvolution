"""Independent review probe for frame_abandoned v3.1 (Claude, 2026-07-31).

Read-only against every real ledger: everything happens inside a throwaway
WEILAN_METHOD_HOME under tempfile.mkdtemp(). Nothing here touches
$CODEX_HOME/method-state or the repo working tree.

Question under test (NOT one Codex's receipt answers):

  v3.1 added `head_validation_markers` to build_self_projection's branch_heads.
  build_self_projection has TWO callers: command_self_project (the read surface
  Codex measured) and current_metabolic_contract, which embeds
  projection["projection_hash"] into the contract snapshot as
  `self_projection_hash` and hashes the whole snapshot into contract_hash.

  contract_hash is not a read surface. It is the anchor a metabolic proposal
  pins via --expected-contract-hash. So the question is:

    Does the marker -- which Codex itself calls a 瞬时量 (instantaneous,
    not-for-history quantity) -- now change contract_hash as a function of
    frame state, while remaining unreadable anywhere in the contract output?

Method: build one frame carrying a genuinely unmet obligation, abandon it via
the real CLI, then present the terminal event in two shapes that differ ONLY in
whether a marker fires (v3 current-basis vs v2 legacy no-fields). For each
shape, ask `metabolic-contract` for its hash and its readable body, under both
the live v3.1 script and the co-signed pre-3.1 rollback base.

Discriminating prediction, stated before running:
  - pre-3.1 base:  the two shapes yield the SAME contract_hash.
  - live v3.1:     the two shapes yield DIFFERENT contract_hash,
                   while `branches[<branch>]` is byte-identical in both
                   and the string "marker" appears nowhere in the output.
If instead v3.1 also yields the same hash, my reading of the coupling is wrong
and this probe refutes it.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

LIVE = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py")
BASE = Path(
    "D:/WeilanSkillEvolution/proposals/frame-abandon-validation-gap-v0.1/evidence/"
    "weilan_trace.py.live-"
    "31b75974525c554a659a8b2e8ccc7f8afcd347e3c4e290b12e5b1e47837f30d7.copy"
)
SCOPE = "v31-contract-coupling"


def run(script, args, env, check=False):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if check and result.returncode:
        raise AssertionError(f"command failed: {args}\n{result.stderr}")
    return result


def load_json(result):
    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def frame_path(home, frame_id):
    matches = list(Path(home).glob(f"frames/*/{frame_id}.jsonl"))
    if len(matches) != 1:
        raise AssertionError(f"expected one frame file: {matches}")
    return matches[0]


def read_events(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_events(path, events):
    path.write_text(
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


def build_case(tmp, script):
    """Return (env, workspace, frame_path, terminal_event) for a fresh home."""
    home = tmp / "method-state"
    workspace = tmp / "workspace"
    workspace.mkdir()
    env = os.environ.copy()
    env["WEILAN_METHOD_HOME"] = str(home)

    opened = load_json(
        run(
            script,
            [
                "open", "--level", "L2",
                "--workspace", str(workspace),
                "--problem", "v3.1 contract-hash coupling probe",
                "--success", "the marker's reach is keyed on what it claims",
                "--scope", SCOPE, "--branch", "main", "--relation", "root",
            ],
            env,
            check=True,
        )
    )
    frame_id = opened["frame_id"]

    run(
        script,
        [
            "event", "--frame-id", frame_id,
            "--type", "minimal_unit_collapsed",
            "--field", "scope=assumption",
            "--field", "former_holder=probe-holder",
            "--field", "invalidating_evidence=probe evidence",
        ],
        env,
        check=True,
    )

    path = frame_path(home, frame_id)
    events = read_events(path)
    events[-1]["timestamp_utc"] = (
        datetime.now(timezone.utc) - timedelta(seconds=10800)
    ).replace(microsecond=0).isoformat()
    write_events(path, events)

    run(
        script,
        [
            "frame-abandon", "--frame-id", frame_id,
            "--silence-threshold-seconds", "7200",
            "--evidence", json.dumps(
                {
                    "alert_id": "v31-coupling-probe",
                    "consecutive_count": 10,
                    "source_ref": "probe:claude-v31-review",
                }
            ),
            "--reason", "v3.1 coupling probe",
        ],
        env,
        check=True,
    )
    events = read_events(path)
    return env, workspace, path, events


def main():
    out = {
        "probe": "v31_contract_hash_coupling",
        "live_script": str(LIVE),
        "base_script": str(BASE),
        "results": {},
    }

    for label, script in (("base_pre_v31", BASE), ("live_v31", LIVE)):
        tmp = Path(tempfile.mkdtemp(prefix=f"v31-coupling-{label}-"))
        if script is BASE:
            # The base copy needs its sibling modules (runtime_core et al.).
            # Mirror the live scripts dir into temp and drop the co-signed
            # rollback base in as weilan_trace.py. The live tree is only read.
            staged = tmp / "scripts"
            shutil.copytree(LIVE.parent, staged)
            shutil.copyfile(BASE, staged / "weilan_trace.py")
            script = staged / "weilan_trace.py"
            out["base_staged_sha256"] = hashlib.sha256(
                script.read_bytes()
            ).hexdigest()
        env, workspace, path, events = build_case(tmp, script)
        terminal = events[-1]
        shapes = {
            "v3_current_basis": dict(terminal["data"]),
            "v2_no_fields": {
                key: value
                for key, value in terminal["data"].items()
                if key not in {"unmet_obligations", "unmet_obligations_basis"}
            },
        }
        per_shape = {}
        for shape_name, data in shapes.items():
            mutated = list(events)
            mutated[-1] = {**terminal, "data": data}
            write_events(path, mutated)

            contract = run(
                script,
                [
                    "metabolic-contract",
                    "--workspace", str(workspace),
                    "--scope", SCOPE,
                ],
                env,
            )
            contract_json = load_json(contract)
            proj = run(
                script,
                ["self-project", "--workspace", str(workspace), "--scope", SCOPE],
                env,
            )
            proj_json = load_json(proj)

            branches = (contract_json or {}).get("snapshot", {}).get("branches")
            if branches is None:
                branches = (contract_json or {}).get("branches")
            per_shape[shape_name] = {
                "contract_rc": contract.returncode,
                "contract_hash": (contract_json or {}).get("contract_hash"),
                # metabolism.build_contract puts the projection hash at
                # body["input_heads"]["self_projection"] and then hashes body.
                "input_heads_self_projection": _dig(
                    contract_json, "input_heads", "self_projection"
                ),
                "contract_branches_canonical": json.dumps(
                    branches, ensure_ascii=False, sort_keys=True
                ),
                "marker_substring_in_contract_stdout": "marker" in contract.stdout,
                "self_project_head_markers": _dig(
                    proj_json, "branch_heads", "main", "head_validation_markers"
                ),
                "self_projection_hash_from_self_project": (proj_json or {}).get(
                    "projection_hash"
                ),
            }
        per_shape["_verdict"] = {
            "contract_hash_differs_between_shapes": per_shape["v3_current_basis"][
                "contract_hash"
            ]
            != per_shape["v2_no_fields"]["contract_hash"],
            "contract_branches_identical_between_shapes": per_shape[
                "v3_current_basis"
            ]["contract_branches_canonical"]
            == per_shape["v2_no_fields"]["contract_branches_canonical"],
        }
        out["results"][label] = per_shape

    print(json.dumps(out, ensure_ascii=False, indent=2))


def _dig(obj, *keys):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


if __name__ == "__main__":
    main()
