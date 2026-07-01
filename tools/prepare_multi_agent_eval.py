"""Prepare isolated, opaque workspaces for the approved SE multi-agent evaluation."""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path


BASELINE_HASH = "a40521f88e93b61262c6e24edd52c636efc02a732dacee3e7e2edccf16659170"
CANDIDATE_HASH = "45e7699ecfa9d4e588acf3cf3b27e11efcc5dbe1889acaf7d0d83dd82ae99ce6"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cli(script, method_home, *arguments):
    env = dict(os.environ)
    env["WEILAN_METHOD_HOME"] = str(method_home)
    result = subprocess.run(
        [sys.executable, str(script), *arguments],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def initialize_method_state(case_id, fixture, workspace, bundle, method_home, controller):
    seed_script = fixture / "seed_state.py"
    if seed_script.exists():
        subprocess.run(
            [sys.executable, str(seed_script), str(workspace), str(controller / "seed.json")],
            check=True,
        )
    trace = bundle / "scripts" / "weilan_trace.py"
    workspace_text = str(workspace)
    if case_id == "memory-cross-window-continuation":
        run_cli(trace, method_home, "memory-control", "--workspace", workspace_text, "--scope", "checkout-implementation", "--state", "active", "--directive", "Continue prepared checkout implementation")
        run_cli(trace, method_home, "memory-control", "--workspace", workspace_text, "--scope", "docs-redesign", "--state", "paused", "--directive", "Keep unrelated docs redesign paused")
        run_cli(trace, method_home, "memory-update", "--workspace", workspace_text, "--scope", "checkout-implementation", "--focus", "finish checkout total v2", "--status", "unfinished", "--next", "implement and verify checkout_total", "--source", str(workspace / "requirements" / "checkout.md"))
    elif case_id == "source-staleness-recovery":
        source = workspace / "requirements" / "release-channel.md"
        current = source.read_bytes()
        source.write_bytes((fixture / "private" / "previous-source.md").read_bytes())
        try:
            run_cli(trace, method_home, "memory-control", "--workspace", workspace_text, "--scope", "release-configuration", "--state", "active", "--directive", "Resume prepared release configuration")
            run_cli(trace, method_home, "memory-update", "--workspace", workspace_text, "--scope", "release-configuration", "--focus", "apply release channel", "--status", "cached blue conclusion", "--next", "implement cached blue channel", "--source", str(source))
        finally:
            source.write_bytes(current)
    elif case_id == "long-horizon-package-evolution":
        run_cli(trace, method_home, "memory-control", "--workspace", workspace_text, "--scope", "parcel-route-evolution", "--state", "active", "--directive", "Execute three bounded parcel-route milestones across fresh windows")
        run_cli(trace, method_home, "memory-update", "--workspace", workspace_text, "--scope", "parcel-route-evolution", "--focus", "complete parcel-route milestones", "--status", "milestone 1 pending", "--next", "implement and verify milestone 1", "--source", str(workspace / "requirements" / "milestone-1.md"))


def build_prompt(execution, case, stages, stage, workspace, bundle, method_home):
    stage_prompt = stage.get("prompt", "")
    requirement = stage.get("requirement")
    if requirement:
        stage_prompt += f"\nCurrent frozen requirement: {requirement}."
    completion = (
        "Output only the requested Chinese translation; do not include the execution ID, a receipt, or any explanation."
        if execution["case_id"] == "l0-proportional-exit"
        else f"Finish with a compact factual receipt beginning exactly with `{execution['execution_id']}`. Do not assign yourself metric scores."
    )
    return f"""Evaluation execution ID: {execution['execution_id']}

This is an isolated Skill evaluation. Work only in:
{workspace}

Mandatory bootstrap: read {bundle / 'SKILL.md'} completely and follow that method bundle for this task. Read only task-relevant references named by it. Bootstrap reads under the method-bundle directory are evaluator setup and do not count against the task tool budget.

Set WEILAN_METHOD_HOME to:
{method_home}

Frozen task:
{case['task']}

Frozen success criteria:
{json.dumps(case['success'], ensure_ascii=False)}

Frozen guardrails:
{json.dumps(case['guardrails'], ensure_ascii=False)}

Current stage instruction:
{stage_prompt}

Task budget for this stage: at most {stage.get('max_tool_calls', execution['budget']['tool_calls'])} task tool calls and {stage.get('max_context_tokens', execution['budget']['context_tokens'])} task context tokens. Do not use network access. Do not inspect D:\\WeilanSkillEvolution or any evaluator/private directory. Do not change requirements, tests, AGENTS.md, or the method bundle. Use apply_patch for edits. {completion}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--seed", type=int, default=20260630)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    run_root = Path(args.run_root).resolve()
    if run_root.exists():
        raise SystemExit(f"run root already exists: {run_root}")
    run_root.mkdir(parents=True)
    manifest = load_json(project / "evals" / "manifest.json")
    case_set = load_json(project / "evals" / "cases" / "seed-v0.1.json")
    cases = {item["case_id"]: item for item in case_set["cases"]}
    eval_cases = {item["case_id"]: item for item in manifest["cases"]}
    rng = random.Random(args.seed)
    schedule = []
    sequence = 0
    for case_entry in manifest["cases"]:
        case_id = case_entry["case_id"]
        fixture = project / "evals" / "fixtures" / "seed-v0.1" / case_id
        stages = load_json(fixture / "stages.json")
        for trial in range(1, case_entry["trial_count"] + 1):
            variants = ["baseline", "candidate"]
            rng.shuffle(variants)
            pair_id = f"{case_id}-t{trial}"
            for order, variant in enumerate(variants, 1):
                sequence += 1
                artifact_hash = BASELINE_HASH if variant == "baseline" else CANDIDATE_HASH
                execution_id = f"se06-{sequence:02d}-{rng.randrange(16**6):06x}"
                trial_root = run_root / "trials" / execution_id
                workspace = trial_root / "public"
                bundle = trial_root / "method-bundle"
                method_home = trial_root / "method-state"
                controller = trial_root / "controller"
                shutil.copytree(fixture / "public", workspace)
                shutil.copytree(project / "artifacts" / artifact_hash / "solve-with-weilan", bundle)
                method_home.mkdir()
                controller.mkdir()
                execution = {
                    "execution_id": execution_id,
                    "pair_id": pair_id,
                    "case_id": case_id,
                    "trial": trial,
                    "variant": variant,
                    "artifact_hash": artifact_hash,
                    "pair_order": order,
                    "budget": case_entry["budget"],
                    "trial_root": str(trial_root),
                    "workspace": str(workspace),
                    "bundle": str(bundle),
                    "method_home": str(method_home),
                    "stage_count": len(stages["stages"]),
                }
                initialize_method_state(case_id, fixture, workspace, bundle, method_home, controller)
                for stage_index, stage in enumerate(stages["stages"], 1):
                    (controller / f"prompt-stage-{stage_index}.txt").write_text(
                        build_prompt(execution, cases[case_id], stages, stage, workspace, bundle, method_home),
                        encoding="utf-8",
                    )
                write_json(controller / "execution.json", execution)
                schedule.append(execution)
    write_json(run_root / "controller" / "schedule.json", {
        "schema_version": "weilan_multi_agent_eval_schedule_v0.1",
        "seed": args.seed,
        "manifest_hash": load_json(project / "evals" / "shadow" / "se-0.6-v0.1-plan.json")["evaluation_manifest_hash"],
        "execution_count": len(schedule),
        "executions": schedule,
    })
    print(json.dumps({"prepared": True, "run_root": str(run_root), "execution_count": len(schedule)}, indent=2))


if __name__ == "__main__":
    main()
