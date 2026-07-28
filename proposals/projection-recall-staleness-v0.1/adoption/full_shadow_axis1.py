"""One-shot, fail-closed stage-3 shadow harness for projection freshness axis-1.

This harness is evaluation plumbing only.  It never adopts or deploys a Skill.
The authority tuple and finite budgets come from full-shadow-proposal.json.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROPOSAL_DIR = Path(__file__).resolve().parent
PROPOSAL = PROPOSAL_DIR / "full-shadow-proposal.json"
RESULT = PROPOSAL_DIR / "FULL_SHADOW_RESULT.json"
PRIOR_STOP_RESULT_HASH = "29f1e8b654151e62c99db6202156429f9b3d53de94cae4b18fdf998ac7048a5b"
SPEC = PROPOSAL_DIR.parent / "STAGE3_FULL_SHADOW_SPEC.md"
DEPLOYED_BUNDLE = Path(r"D:\CodexData\skills\solve-with-weilan")
MANIFEST = ROOT / "evals" / "fusion-dogfood-v0.1-manifest.json"
CASE_SET = ROOT / "evals" / "cases" / "fusion-dogfood-v0.1.json"
FIXTURES = ROOT / "evals" / "fixtures" / "fusion-dogfood-v0.1"
SCORER = ROOT / "evals" / "hidden" / "scorers" / "fusion-dogfood-v0.1" / "scorer.py"
TRACE_FIELDS = ("gate", "intended_action", "observable_failure", "cost")
EXCLUDED_TREE_PARTS = {"__pycache__", ".pytest_cache"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_obj(value) -> str:
    return sha_bytes(canonical(value).encode("utf-8"))


def tree_manifest(root: Path):
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_TREE_PARTS for part in path.parts) or path.suffix == ".pyc":
            continue
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha_file(path),
        })
    return rows


def tree_hash(root: Path) -> str:
    return sha_obj(tree_manifest(root))


def ephemera(root: Path):
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and (path.suffix == ".pyc" or any(part in EXCLUDED_TREE_PARTS for part in path.parts))
    )


def candidate_bundle(proposal):
    digest = proposal["candidate_artifact_hash"]
    return PROPOSAL_DIR / "frozen" / digest / "solve-with-weilan"


def assert_run_copy(path: Path, run_root: Path, frozen: Path) -> Path:
    resolved = path.resolve()
    root = run_root.resolve()
    frozen_root = frozen.resolve()
    if resolved == frozen_root or frozen_root in resolved.parents:
        raise ValueError(f"execution source resolves inside frozen artifact: {resolved}")
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"execution source is outside run_root: {resolved}")
    return resolved


def copy_method_bundle(source: Path, destination: Path, expected_hash: str, run_root: Path, frozen: Path) -> Path:
    if destination.exists():
        raise FileExistsError(f"method bundle copy already exists: {destination}")
    shutil.copytree(source, destination)
    resolved = assert_run_copy(destination, run_root, frozen)
    if tree_hash(resolved) != expected_hash:
        raise ValueError(f"copied method bundle hash mismatch: {resolved}")
    return resolved


def authority_artifact_state(proposal, stage: str):
    frozen = candidate_bundle(proposal)
    state = {
        "stage": stage,
        "baseline_tree_hash": tree_hash(DEPLOYED_BUNDLE),
        "candidate_tree_hash": tree_hash(frozen),
        "candidate_ephemera": ephemera(frozen),
    }
    if state["baseline_tree_hash"] != proposal["base_artifact_hash"]:
        raise ValueError(f"{stage}: deployed baseline artifact drift")
    if state["candidate_tree_hash"] != proposal["candidate_artifact_hash"]:
        raise ValueError(f"{stage}: frozen candidate artifact drift")
    if state["candidate_ephemera"]:
        raise ValueError(f"{stage}: frozen candidate contains ephemera: {state['candidate_ephemera']}")
    return state


def archive_previous_result():
    if not RESULT.is_file():
        raise FileNotFoundError("the prior fail-closed result is missing")
    prior = load(RESULT)
    claimed = prior.pop("result_hash", None)
    actual = sha_obj(prior)
    if claimed != PRIOR_STOP_RESULT_HASH or actual != PRIOR_STOP_RESULT_HASH:
        raise ValueError(f"unexpected prior result identity: claimed={claimed}, actual={actual}")
    archive = PROPOSAL_DIR / f"FULL_SHADOW_RESULT.stop-{PRIOR_STOP_RESULT_HASH[:12]}.json"
    if archive.exists():
        if archive.read_bytes() != RESULT.read_bytes():
            raise ValueError(f"immutable prior-result archive collision: {archive}")
    else:
        shutil.copy2(RESULT, archive)
    return {
        "path": archive.relative_to(ROOT).as_posix(),
        "result_hash": PRIOR_STOP_RESULT_HASH,
    }


def run(cmd, *, cwd=None, env=None, timeout=180, input_text=None):
    return subprocess.run(
        [str(item) for item in cmd],
        cwd=cwd,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=timeout,
    )


def verify_utf8_subprocess_contract():
    sentinel = "微澜-utf8-probe"
    script = f"import sys; sys.stdout.write({sentinel!r})"
    isolated_env = dict(os.environ)
    isolated_env.pop("PYTHONIOENCODING", None)
    isolated_env.pop("PYTHONUTF8", None)
    arms = [
        ("python_x_utf8", [sys.executable, "-X", "utf8", "-c", script], isolated_env),
        (
            "python_env_utf8_no_x",
            [sys.executable, "-c", script],
            {**isolated_env, "PYTHONUTF8": "1"},
        ),
    ]
    records = []
    for name, argv, env in arms:
        outcome = run(argv, env=env, timeout=30)
        passed = outcome.returncode == 0 and outcome.stdout == sentinel
        records.append({
            "arm": name,
            "passed": passed,
            "returncode": outcome.returncode,
            "stdout": outcome.stdout,
            "stderr": outcome.stderr,
        })
        if not passed:
            raise RuntimeError(
                f"UTF-8 subprocess contract failed for {name}: "
                f"returncode={outcome.returncode}, stdout={outcome.stdout!r}, "
                f"stderr={outcome.stderr!r}"
            )
    return records


def resolve_executor():
    if os.name != "nt":
        raise RuntimeError("this signed launcher contract requires Windows")
    resolved = shutil.which("codex.cmd")
    if not resolved:
        raise FileNotFoundError("shutil.which('codex.cmd') did not resolve an executor")
    path = Path(resolved)
    if not path.is_absolute() or path.suffix.lower() != ".cmd" or not path.is_file():
        raise ValueError(f"executor must be an existing absolute .cmd file: {path}")
    outcome = run([path, "--version"], timeout=30)
    version = outcome.stdout.strip()
    if outcome.returncode != 0 or not version.startswith("codex-cli "):
        raise RuntimeError(
            f"executor version probe failed: returncode={outcome.returncode}, "
            f"stdout={version!r}, stderr={outcome.stderr.strip()!r}"
        )
    return {
        "path": str(path.resolve()),
        "sha256": sha_file(path),
        "version_probe": {
            "argv": [str(path.resolve()), "--version"],
            "returncode": outcome.returncode,
            "stdout": version,
            "stderr": outcome.stderr.strip(),
        },
        "binding_rule": "windows_absolute_codex_cmd_only_no_ps1_no_extensionless_shim",
    }


def verify_executor_binding(binding):
    path = Path(binding["path"])
    if not path.is_absolute() or path.suffix.lower() != ".cmd" or not path.is_file():
        raise ValueError(f"bound executor is no longer an existing absolute .cmd file: {path}")
    actual = sha_file(path)
    if actual != binding["sha256"]:
        raise ValueError(f"bound executor hash drift: {actual} != {binding['sha256']}")
    return {"path": str(path.resolve()), "sha256": actual}


def snapshot_harness(run_root: Path):
    controller = run_root / "controller"
    controller.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve()
    destination = controller / "executed-harness.py"
    destination.write_bytes(source.read_bytes())
    record = {
        "path": destination.relative_to(run_root).as_posix(),
        "sha256": sha_file(destination),
        "provenance_claim": "recomputable launch-time byte snapshot, not instruction-level execution proof",
    }
    write(controller / "harness-snapshot.json", record)
    return record


def verify_harness_snapshot(run_root: Path, schedule):
    record = schedule["harness_snapshot"]
    path = run_root / record["path"]
    if not path.is_file():
        raise FileNotFoundError(f"executed harness snapshot is missing: {path}")
    actual = sha_file(path)
    if actual != record["sha256"]:
        raise ValueError(f"executed harness snapshot hash drift: {actual} != {record['sha256']}")
    return record


def assert_equal(checks, name, actual, expected):
    passed = actual == expected
    checks.append({"check": name, "passed": passed, "actual": actual, "expected": expected})
    if not passed:
        raise ValueError(f"{name}: expected {expected!r}, found {actual!r}")


def canonical_targeted_hash(path: Path) -> str:
    value = load(path)
    claimed = value.pop("result_hash", None)
    actual = sha_obj(value)
    if claimed != actual:
        raise ValueError(f"prior targeted result self-hash mismatch: {claimed} != {actual}")
    return actual


def preflight():
    proposal = load(PROPOSAL)
    binding = proposal["evaluation_binding"]
    checks = []
    utf8_subprocess_contract = verify_utf8_subprocess_contract()

    sys.path.insert(0, str(ROOT / "tools"))
    from evolution_core import validate_proposal, validate_eval_manifest  # noqa: E402

    proposal_validation = validate_proposal(proposal)
    assert_equal(checks, "proposal_validate", proposal_validation["valid"], True)
    manifest = load(MANIFEST)
    cases = load(CASE_SET)
    manifest_validation = validate_eval_manifest(manifest, require_approved=True, case_set=cases)
    assert_equal(checks, "manifest_approved_frozen", manifest_validation["valid"], True)
    assert_equal(checks, "manifest_file_sha256", sha_file(MANIFEST), binding["harder_suite_manifest"]["sha256"])
    assert_equal(checks, "case_file_sha256", sha_file(CASE_SET), binding["case_set"]["file_sha256"])
    assert_equal(checks, "case_canonical_hash", sha_obj(cases), binding["case_set"]["canonical_hash"])
    assert_equal(checks, "configuration_sha256", sha_file(ROOT / binding["configuration"]["path"]), binding["configuration"]["sha256"])
    for name, record in binding["evaluator_artifacts"].items():
        assert_equal(checks, f"evaluator_{name}_sha256", sha_file(ROOT / record["path"]), record["sha256"])

    targeted = ROOT / binding["prior_targeted_result"]["path"]
    assert_equal(checks, "prior_targeted_result_hash", canonical_targeted_hash(targeted), binding["prior_targeted_result"]["result_hash"])
    targeted_value = load(targeted)
    assert_equal(checks, "prior_targeted_base", targeted_value["baseline_artifact_hash"], proposal["base_artifact_hash"])
    assert_equal(checks, "prior_targeted_candidate", targeted_value["candidate_artifact_hash"], proposal["candidate_artifact_hash"])

    frozen = candidate_bundle(proposal)
    if not DEPLOYED_BUNDLE.is_dir() or not frozen.is_dir():
        raise FileNotFoundError("deployed or frozen candidate bundle is missing")
    assert_equal(checks, "deployed_tree_hash", tree_hash(DEPLOYED_BUNDLE), proposal["base_artifact_hash"])
    assert_equal(checks, "candidate_tree_hash", tree_hash(frozen), proposal["candidate_artifact_hash"])
    assert_equal(checks, "candidate_ephemera", ephemera(frozen), [])
    assert_equal(checks, "trial_budget", proposal["budgets"]["max_evaluation_trials"], 24)
    assert_equal(checks, "candidate_generation_budget", proposal["budgets"]["max_candidate_generations"], 0)
    assert_equal(checks, "targeted_check_budget", proposal["budgets"]["max_targeted_checks"], 0)
    assert_equal(checks, "migration_budget", proposal["budgets"]["max_migration_checks"], 2)
    assert_equal(checks, "deployment_budget", proposal["budgets"]["max_deployments"], 0)
    expected_trials = sum(item["trial_count"] for item in manifest["cases"]) * 2
    assert_equal(checks, "manifest_receipt_count", expected_trials, 24)
    requirement = proposal["method_impact_requirement"]
    assert_equal(checks, "impact_case", requirement["approved_case_id"], "fusion-memory-scope-recovery")
    assert_equal(checks, "impact_reproductions", requirement["required_reproductions"], 2)
    assert_equal(checks, "impact_trace_fields", requirement["required_trace_fields"], list(TRACE_FIELDS))
    assert_equal(checks, "migration_not_impact", requirement["migration_checks_count_as_approved_suite_method_impact"], False)
    authority_artifact_state(proposal, "preflight")
    executor_binding = resolve_executor()
    verify_executor_binding(executor_binding)
    return {
        "passed": True,
        "proposal_validation": proposal_validation,
        "manifest_validation": manifest_validation,
        "checks": checks,
        "pre_tree_hashes": {"baseline": tree_hash(DEPLOYED_BUNDLE), "candidate": tree_hash(frozen)},
        "authority_tuple": binding,
        "executor_binding": executor_binding,
        "utf8_subprocess_contract": utf8_subprocess_contract,
    }


def fixture_manifest_hash(case_id: str) -> str:
    return sha_file(FIXTURES / case_id / "fixture-manifest.json")


def prompt_for(execution, case, variant):
    sources = "\n".join(f"- {path}" for path in execution["fixture_sources_local"])
    impact = ""
    if case["case_id"] == "fusion-memory-scope-recovery":
        impact = """
Pre-registered observable method-impact check (not a hidden answer): report whether projection
freshness changed the activation gate.  If it did, method_impact_trace must be a single-line JSON
array with one object containing gate, intended_action, observable_failure, and cost.  The cost
object must contain non-negative integer tool_calls, elapsed_ms, and context_tokens.  Also include
observable_effect, changed_action, and source so the external v0.5 method-impact validator can
check it.  If it did not fire, write method_impact_trace: [].  Do not invent an impact.
"""
    fields = ", ".join(case["expected_receipt_fields"])
    return f"""Evaluation execution ID: {execution['execution_id']}

This is one isolated trial in an externally approved frozen shadow. Work only inside:
{execution['trial_root']}

Candidate-visible public workspace: {execution['public_root']}
Method bundle under test ({variant}): {execution['method_bundle']}
Set WEILAN_METHOD_HOME to: {execution['method_home']}

Mandatory bootstrap: read the method bundle SKILL.md completely, then follow it proportionally.
Do not inspect D:\\WeilanSkillEvolution, any evals/hidden or private evaluator directory, or any
other trial. Do not use network access. Do not modify the method bundle. Absolute live paths in
the frozen task mean their isolated equivalents inside the public workspace.

Frozen case id: {case['case_id']}
Frozen task: {case['task']}
Frozen success criteria: {json.dumps(case['success'], ensure_ascii=False)}
Frozen guardrails: {json.dumps(case['guardrails'], ensure_ascii=False)}
Candidate-visible sources:\n{sources}
Expected receipt fields: {fields}
Budget after bootstrap: at most {execution['budget']['tool_calls']} task tool calls and
{execution['budget']['context_tokens']} task context tokens.
{impact}
Write the final factual receipt to {execution['final_path']}. It must begin exactly with
`{execution['execution_id']}` and expose each expected field as `field: value`. Do not assign
scores, reveal hidden reasoning, approve, adopt, deploy, or edit frozen evaluation authority.
After the receipt is complete, compute SHA-256 from the exact final.md bytes and write only the
lowercase 64-hex digest plus a newline to {execution['final_sha256_path']}. This sidecar must be
written by you before exit; the controller will independently hash final.md after the process
returns, and missing or mismatched digests fail closed.
"""


def prepare(run_root: Path, seed=20260724):
    if run_root.exists():
        raise FileExistsError(f"run root already exists: {run_root}")
    pf = preflight()
    if run_root.exists():
        raise FileExistsError(f"run root appeared during preflight: {run_root}")
    harness_snapshot = snapshot_harness(run_root)
    proposal = load(PROPOSAL)
    manifest = load(MANIFEST)
    case_set = load(CASE_SET)
    cases = {item["case_id"]: item for item in case_set["cases"]}
    frozen = candidate_bundle(proposal)
    rng = random.Random(seed)
    executions = []
    sequence = 0
    for entry in manifest["cases"]:
        case = cases[entry["case_id"]]
        for trial in range(1, entry["trial_count"] + 1):
            variants = ["baseline", "candidate"]
            rng.shuffle(variants)
            for order, variant in enumerate(variants, 1):
                sequence += 1
                execution_id = f"axis1-{sequence:02d}-{rng.randrange(16**6):06x}"
                trial_root = run_root / "trials" / execution_id
                public_root = trial_root / "public"
                bundle = trial_root / "method-bundle"
                method_home = trial_root / "method-state"
                output = trial_root / "agent-output"
                shutil.copytree(FIXTURES / case["case_id"] / "public", public_root)
                copy_method_bundle(
                    DEPLOYED_BUNDLE if variant == "baseline" else frozen,
                    bundle,
                    proposal[f"{'base' if variant == 'baseline' else 'candidate'}_artifact_hash"],
                    run_root,
                    frozen,
                )
                snapshot = public_root / "method-state-snapshot"
                if snapshot.exists():
                    shutil.copytree(snapshot, method_home)
                else:
                    method_home.mkdir(parents=True)
                output.mkdir(parents=True)
                prefix = Path("evals") / "fixtures" / "fusion-dogfood-v0.1" / case["case_id"] / "public"
                local_sources = []
                for item in case.get("fixture_sources", []):
                    local_sources.append(str(public_root / Path(item).relative_to(prefix)))
                execution = {
                    "execution_id": execution_id,
                    "run_root": str(run_root),
                    "case_id": case["case_id"],
                    "trial": trial,
                    "variant": variant,
                    "pair_order": order,
                    "artifact_hash": proposal[f"{'base' if variant == 'baseline' else 'candidate'}_artifact_hash"],
                    "budget": entry["budget"],
                    "trial_root": str(trial_root),
                    "public_root": str(public_root),
                    "method_bundle": str(bundle),
                    "method_home": str(method_home),
                    "final_path": str(output / "final.md"),
                    "final_sha256_path": str(output / "final.sha256"),
                    "last_message_path": str(output / "last-message.md"),
                    "expected_receipt_fields": list(case["expected_receipt_fields"]),
                    "fixture_sources_local": local_sources,
                    "fixture_manifest_hash": fixture_manifest_hash(case["case_id"]),
                    "public_tree_before": tree_hash(public_root),
                    "bundle_tree_before": tree_hash(bundle),
                    "executor_binding": pf["executor_binding"],
                }
                prompt = prompt_for(execution, case, variant)
                (trial_root / "controller").mkdir()
                write(trial_root / "controller" / "execution.json", execution)
                (trial_root / "controller" / "prompt.txt").write_text(prompt, encoding="utf-8", newline="\n")
                executions.append(execution)
    schedule = {
        "schema_version": "axis1_full_shadow_schedule_v0.1",
        "seed": seed,
        "execution_count": len(executions),
        "proposal_id": proposal["proposal_id"],
        "authority_tuple": proposal["evaluation_binding"],
        "preflight": pf,
        "harness_snapshot": harness_snapshot,
        "executions": executions,
    }
    write(run_root / "controller" / "schedule.json", schedule)
    return schedule


def count_tool_calls(events):
    count = 0
    for event in events:
        kind = str(event.get("type", ""))
        item_type = str((event.get("item") or {}).get("type", ""))
        if "tool" in kind or item_type in {"command_execution", "mcp_tool_call"}:
            count += 1
    return count


def extract_context_usage(events):
    for event in reversed(events):
        if event.get("type") != "turn.completed":
            continue
        raw = event.get("usage")
        if not isinstance(raw, dict):
            continue
        context_tokens = raw.get("input_tokens")
        if isinstance(context_tokens, bool) or not isinstance(context_tokens, int) or context_tokens < 0:
            continue
        return context_tokens, {
            "context_tokens_source": "json_event.turn.completed.usage.input_tokens",
            "event_usage": {
                key: value for key, value in raw.items()
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0
            },
        }
    return None, {
        "context_tokens_source": "unavailable",
        "event_usage": None,
    }


def receipt_survival_observation(execution):
    final_path = Path(execution["final_path"])
    digest_path = Path(execution["final_sha256_path"])
    last_message_path = Path(execution["last_message_path"])
    executor_digest = None
    if digest_path.is_file():
        candidate = digest_path.read_text(encoding="utf-8", errors="strict").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", candidate):
            executor_digest = candidate
    controller_digest = sha_file(final_path) if final_path.is_file() else None
    return {
        "executor_digest_path": str(digest_path),
        "executor_digest": executor_digest,
        "controller_digest_path": str(final_path),
        "controller_digest": controller_digest,
        "digests_match": (
            executor_digest is not None
            and controller_digest is not None
            and executor_digest == controller_digest
        ),
        "last_message_path": str(last_message_path),
        "last_message_exists": last_message_path.is_file(),
    }


def receipt_contract_failures(execution, record):
    failures = []
    final_path = Path(execution["final_path"])
    if record.get("returncode") != 0:
        failures.append("executor_nonzero")
    if not final_path.is_file():
        failures.append("final_missing")
        text = ""
    else:
        text = final_path.read_text(encoding="utf-8", errors="replace")
    if not text.lstrip().startswith(execution["execution_id"]):
        failures.append("receipt_identity_mismatch")
    missing_fields = [
        field for field in execution["expected_receipt_fields"]
        if not re.search(rf"(?mi)^\s*{re.escape(field)}\s*:\s*\S", text)
    ]
    if missing_fields:
        failures.append("receipt_fields_missing:" + ",".join(missing_fields))
    survival = record["receipt_survival"]
    if survival["executor_digest"] is None:
        failures.append("executor_receipt_digest_unavailable")
    elif not survival["digests_match"]:
        failures.append("receipt_digest_mismatch")
    if not survival["last_message_exists"]:
        failures.append("last_message_missing")
    return failures


def budget_guardrail_failures(execution, executor):
    failures = []
    actual = executor.get("actual_usage") or {}
    for key, allowed in execution["budget"].items():
        used = actual.get(key)
        if isinstance(used, bool) or not isinstance(used, int) or used < 0:
            failures.append("budget_unverifiable")
        elif key == "tool_calls" and used > allowed:
            failures.append("budget_exceeded")
    return list(dict.fromkeys(failures))


def budget_guardrail_annotations(execution, executor):
    actual = executor.get("actual_usage") or {}
    context_tokens = actual.get("context_tokens")
    if (
        "context_tokens" in execution["budget"]
        and isinstance(context_tokens, int)
        and not isinstance(context_tokens, bool)
        and context_tokens >= 0
    ):
        return [
            "context_budget_uncalibrated:"
            "frozen threshold unit != observed whole-context input_tokens"
        ]
    return []


def execute_one(execution):
    trial_root = Path(execution["trial_root"])
    prompt = (trial_root / "controller" / "prompt.txt").read_text(encoding="utf-8")
    final_path = Path(execution["final_path"])
    last_message_path = Path(execution["last_message_path"])
    env = dict(os.environ)
    env["WEILAN_METHOD_HOME"] = execution["method_home"]
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    launcher_before = verify_executor_binding(execution["executor_binding"])
    started = time.monotonic()
    result = run(
        [
            execution["executor_binding"]["path"], "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--skip-git-repo-check", "--sandbox", "danger-full-access", "--json",
            "--cd", trial_root, "--output-last-message", last_message_path, "-",
        ],
        cwd=trial_root,
        env=env,
        timeout=1800,
        input_text=prompt,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    launcher_after = verify_executor_binding(execution["executor_binding"])
    events = []
    for line in result.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    tool_calls = count_tool_calls(events)
    context_tokens, usage_details = extract_context_usage(events)
    usage = {
        "tool_calls": tool_calls,
        "context_tokens": context_tokens,
    }
    receipt_survival = receipt_survival_observation(execution)
    record = {
        "execution_id": execution["execution_id"],
        "returncode": result.returncode,
        "elapsed_ms": elapsed_ms,
        "actual_usage": usage,
        "usage": usage_details,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
        "final_exists": final_path.exists(),
        "last_message_path": str(last_message_path),
        "last_message_exists": last_message_path.exists(),
        "receipt_survival": receipt_survival,
        "executor_binding": execution["executor_binding"],
        "launcher_before": launcher_before,
        "launcher_after": launcher_after,
        "authority_artifacts_after_trial": authority_artifact_state(
            load(PROPOSAL), f"trial:{execution['execution_id']}"
        ),
    }
    write(trial_root / "controller" / "executor-result.json", record)
    return record


def execute(run_root: Path, workers=1):
    schedule = load(run_root / "controller" / "schedule.json")
    smoke_execution = schedule["executions"][0]
    smoke_path = run_root / "controller" / "smoke-result.json"
    results = []
    if smoke_path.is_file():
        smoke = load(smoke_path)
        if not smoke.get("passed") or smoke.get("execution_id") != smoke_execution["execution_id"]:
            raise RuntimeError("stored smoke gate is not a passing result for the designated first trial")
        smoke_record = load(Path(smoke_execution["trial_root"]) / "controller" / "executor-result.json")
        smoke_record["receipt_survival"] = receipt_survival_observation(smoke_execution)
        smoke_failures = receipt_contract_failures(smoke_execution, smoke_record)
        smoke_budget_failures = budget_guardrail_failures(smoke_execution, smoke_record)
        smoke_failures.extend(
            failure for failure in smoke_budget_failures
            if failure in {"budget_unverifiable", "budget_exceeded"}
            and failure not in smoke_failures
        )
        if smoke_failures:
            raise RuntimeError("stored smoke gate no longer reproduces: " + ";".join(smoke_failures))
    else:
        smoke_record_path = Path(smoke_execution["trial_root"]) / "controller" / "executor-result.json"
        if Path(smoke_execution["final_path"]).exists() and smoke_record_path.is_file():
            smoke_record = load(smoke_record_path)
            smoke_record["receipt_survival"] = receipt_survival_observation(smoke_execution)
        else:
            smoke_record = execute_one(smoke_execution)
            results.append(smoke_record)
        smoke_failures = receipt_contract_failures(smoke_execution, smoke_record)
        smoke_budget_failures = budget_guardrail_failures(smoke_execution, smoke_record)
        smoke_failures.extend(
            failure for failure in smoke_budget_failures
            if failure in {"budget_unverifiable", "budget_exceeded"}
            and failure not in smoke_failures
        )
        smoke = {
            "execution_id": smoke_execution["execution_id"],
            "passed": not smoke_failures,
            "failures": smoke_failures,
            "guardrail_annotations": budget_guardrail_annotations(smoke_execution, smoke_record),
            "receipt_survival": smoke_record["receipt_survival"],
        }
        write(smoke_path, smoke)
        if smoke_failures:
            raise RuntimeError("end-to-end smoke failed: " + ";".join(smoke_failures))
    pending = [
        item for item in schedule["executions"][1:]
        if not Path(item["final_path"]).exists()
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(execute_one, item): item["execution_id"] for item in pending}
        for future in concurrent.futures.as_completed(future_map):
            record = future.result()
            print(json.dumps({"completed": record["execution_id"], "returncode": record["returncode"]}), flush=True)
            results.append(record)
            if record["returncode"] != 0 or not record["final_exists"]:
                raise RuntimeError(f"trial failed: {record['execution_id']}")
    return results


def load_scorer():
    spec = importlib.util.spec_from_file_location("axis1_frozen_scorer", SCORER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.verify_hidden_checks()
    return module


def parse_impact(text: str, execution, executor):
    match = re.search(r"(?mi)^\s*method_impact_trace\s*:\s*(\[[^\r\n]*\])\s*$", text)
    if not match:
        return []
    try:
        values = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(values, list):
        return []
    records = []
    for value in values:
        if not isinstance(value, dict) or any(field not in value for field in TRACE_FIELDS):
            continue
        cost = value.get("cost")
        if not isinstance(cost, dict):
            continue
        context_tokens = cost.get("context_tokens", executor["actual_usage"]["context_tokens"])
        if isinstance(context_tokens, bool) or not isinstance(context_tokens, int) or context_tokens < 0:
            continue
        record = {
            "schema_version": "weilan_method_impact_v0.5",
            "gate": value["gate"],
            "changed_action": bool(value.get("changed_action", True)),
            "observable_effect": value.get("observable_effect") or value["observable_failure"],
            "source": value.get("source") or f"trial:{execution['execution_id']}",
            "cost": {
                "tool_calls": int(cost.get("tool_calls", executor["actual_usage"]["tool_calls"])),
                "elapsed_ms": int(cost.get("elapsed_ms", executor["elapsed_ms"])),
                "context_tokens": context_tokens,
            },
            "intended_action": value["intended_action"],
            "observable_failure": value["observable_failure"],
        }
        records.append(record)
    return records


def frozen_public_unchanged(execution):
    public = Path(execution["public_root"])
    manifest = load(FIXTURES / execution["case_id"] / "fixture-manifest.json")
    rows = manifest.get("public_files") or {
        key.removeprefix("public/"): value
        for key, value in manifest.get("files", {}).items()
        if key.startswith("public/")
    }
    changed = []
    for rel, expected in rows.items():
        path = public / rel
        if not path.is_file() or sha_file(path) != expected:
            changed.append(rel)
    return changed


def score(run_root: Path):
    pf = preflight()
    proposal = load(PROPOSAL)
    manifest = load(MANIFEST)
    schedule = load(run_root / "controller" / "schedule.json")
    scorer = load_scorer()
    rubric = scorer.load_frozen_rubric()
    sys.path.insert(0, str(ROOT / "tools"))
    from evolution_core import compare_trials, validate_method_impact  # noqa: E402

    receipts = []
    for execution in schedule["executions"]:
        trial_root = Path(execution["trial_root"])
        final_path = Path(execution["final_path"])
        executor = load(trial_root / "controller" / "executor-result.json")
        if executor["returncode"] != 0 or not final_path.is_file():
            raise RuntimeError(f"incomplete trial {execution['execution_id']}")
        text = final_path.read_text(encoding="utf-8", errors="replace")
        failures = []
        if not text.lstrip().startswith(execution["execution_id"]):
            failures.append("receipt_identity_mismatch")
        survival = receipt_survival_observation(execution)
        if survival["executor_digest"] is None:
            failures.append("executor_receipt_digest_unavailable")
        elif not survival["digests_match"]:
            failures.append("receipt_digest_mismatch")
        if tree_hash(Path(execution["method_bundle"])) != execution["bundle_tree_before"]:
            failures.append("method_bundle_mutated")
        changed_public = frozen_public_unchanged(execution)
        if changed_public:
            failures.append("frozen_fixture_mutated:" + ",".join(changed_public))
        failures.extend(item for item in budget_guardrail_failures(execution, executor) if item not in failures)
        guardrail_annotations = budget_guardrail_annotations(execution, executor)
        impacts = []
        if execution["case_id"] == proposal["method_impact_requirement"]["approved_case_id"] and execution["variant"] == "candidate":
            impacts = parse_impact(text, execution, executor)
            impact_issues = [issue for record in impacts for issue in validate_method_impact(record)]
            if impact_issues:
                failures.append("invalid_method_impact:" + ";".join(impact_issues))
        base_receipt = {"budget": execution["budget"], "actual_usage": executor["actual_usage"], "guardrail_failures": failures}
        metrics, breakdown = scorer.score_trial(execution["case_id"], text, base_receipt)
        receipt = {
            "schema_version": "weilan_skill_trial_receipt_v0.5",
            "case_id": execution["case_id"],
            "trial": execution["trial"],
            "variant": execution["variant"],
            "artifact_hash": execution["artifact_hash"],
            "evaluation_manifest_hash": sha_obj(manifest),
            "case_spec_hash": manifest["case_spec_hash"],
            "fixture_manifest_hash": execution["fixture_manifest_hash"],
            "configuration_hash": proposal["evaluation_binding"]["configuration"]["sha256"],
            "environment_id": "codex-windows-shared-host-2026-07-24-axis1-full-shadow",
            "scoring_version": manifest["scoring_version"],
            "budget": execution["budget"],
            "actual_usage": executor["actual_usage"],
            "termination_status": "completed",
            "raw_output_hash": sha_file(final_path),
            "grader_id": scorer.SCORER_VERSION,
            "grader_provenance": {
                "authority_source": "evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py",
                "evaluator_artifact_hash": sha_file(SCORER),
                "evidence_hash": sha_obj({"checks": breakdown, "raw_output_hash": sha_file(final_path)}),
            },
            "metrics": metrics,
            "guardrail_failures": failures,
            "guardrail_annotations": guardrail_annotations,
            "method_impacts": impacts,
            "executor_ids": [execution["execution_id"]],
        }
        receipt["receipt_hash"] = sha_obj(receipt)
        write(run_root / "receipts" / f"{execution['execution_id']}.json", receipt)
        receipts.append(receipt)
    if len(receipts) > proposal["budgets"]["max_evaluation_trials"]:
        raise ValueError("trial receipt budget exceeded")
    comparison = compare_trials(manifest, receipts)
    write(run_root / "controller" / "comparison.json", comparison)
    write(run_root / "controller" / "receipt-index.json", {
        "receipt_count": len(receipts),
        "receipt_hashes": [item["receipt_hash"] for item in receipts],
    })
    return pf, receipts, comparison


def trace_cli(bundle: Path, method_home: Path, run_root: Path, *args):
    proposal = load(PROPOSAL)
    frozen = candidate_bundle(proposal)
    assert_run_copy(bundle, run_root, frozen)
    env = dict(os.environ)
    env["WEILAN_METHOD_HOME"] = str(method_home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    result = run([sys.executable, bundle / "scripts" / "weilan_trace.py", *args], env=env, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def one_migration(run_root: Path, name: str, degrade):
    root = run_root / "migrations" / name
    proposal = load(PROPOSAL)
    frozen = candidate_bundle(proposal)
    deployed_copy = copy_method_bundle(
        DEPLOYED_BUNDLE,
        root / "deployed-writer-bundle",
        proposal["base_artifact_hash"],
        run_root,
        frozen,
    )
    candidate_copy = copy_method_bundle(
        frozen,
        root / "candidate-bundle",
        proposal["candidate_artifact_hash"],
        run_root,
        frozen,
    )
    workspace = root / "public"
    method_home = root / "method-state"
    workspace.mkdir(parents=True)
    method_home.mkdir(parents=True)
    source = workspace / "source.txt"
    source.write_text("deployed-writer migration fixture\n", encoding="utf-8")
    scope = f"axis1-{name.lower()}"
    trace_cli(deployed_copy, method_home, run_root, "memory-control", "--workspace", str(workspace), "--scope", scope, "--state", "active", "--directive", "Generate a deployed-writer migration fixture")
    opened = trace_cli(
        deployed_copy,
        method_home,
        run_root,
        "open",
        "--level",
        "L1",
        "--workspace",
        str(workspace),
        "--scope",
        scope,
        "--branch",
        "main",
        "--relation",
        "root",
        "--problem",
        "Generate a real deployed-writer migration fixture",
        "--success",
        "Leave one closed main lineage head",
    )
    trace_cli(
        deployed_copy,
        method_home,
        run_root,
        "close",
        "--frame-id",
        opened["frame_id"],
        "--outcome",
        "success",
        "--verdict",
        "deployed writer fixture head created",
    )
    trace_cli(deployed_copy, method_home, run_root, "memory-update", "--workspace", str(workspace), "--scope", scope, "--focus", name, "--status", "active", "--next", "migration check", "--source", str(source))
    projections = list((method_home / "memory" / "projections").rglob("*.json"))
    if len(projections) != 1:
        raise RuntimeError(f"{name}: expected one deployed-writer projection, found {len(projections)}")
    projection_path = projections[0]
    original = load(projection_path)
    if original.get("schema_version") != "weilan_workspace_projection_v0.2":
        raise RuntimeError(f"{name}: deployed writer did not produce v0.2")
    degraded = dict(original)
    degrade(degraded)
    write(projection_path, degraded)
    first = trace_cli(candidate_copy, method_home, run_root, "memory-recall", "--workspace", str(workspace), "--scope", scope)
    trace_cli(candidate_copy, method_home, run_root, "projection-rebuild", "--workspace", str(workspace), "--scope", scope, "--branch", "main")
    after = trace_cli(candidate_copy, method_home, run_root, "memory-recall", "--workspace", str(workspace), "--scope", scope)
    second = trace_cli(candidate_copy, method_home, run_root, "memory-recall", "--workspace", str(workspace), "--scope", scope)
    rebuilt = load(projection_path)
    expected_reason = "semantic-stale" if name == "M1" else "legacy_projection_schema"
    passed = (
        first.get("activation", {}).get("state") == "STALE"
        and expected_reason in first.get("activation", {}).get("reason_codes", [])
        and after.get("activation", {}).get("state") == "ACTIVE"
        and second.get("activation", {}).get("state") == "ACTIVE"
        and "semantic_dependency_vector" in rebuilt
    )
    return {
        "fixture": name,
        "passed": passed,
        "writer_source": str(DEPLOYED_BUNDLE / "scripts" / "weilan_trace.py"),
        "writer_execution_source": str(deployed_copy / "scripts" / "weilan_trace.py"),
        "candidate_execution_source": str(candidate_copy / "scripts" / "weilan_trace.py"),
        "writer_tree_hash": tree_hash(DEPLOYED_BUNDLE),
        "degradation": "remove semantic_dependency_vector" if name == "M1" else "set schema_version to weilan_workspace_projection_v0.1",
        "first_state": first.get("activation", {}),
        "rebuild_count": 1,
        "after_rebuild_state": after.get("activation", {}),
        "second_state": second.get("activation", {}),
        "rebuilt_has_semantic_dependency_vector": "semantic_dependency_vector" in rebuilt,
        "authority_artifacts_after_migration": authority_artifact_state(proposal, f"migration:{name}"),
    }


def migrations(run_root: Path):
    migration_root = run_root / "migrations"
    if migration_root.exists():
        shutil.rmtree(migration_root)
    m1 = one_migration(run_root, "M1", lambda value: value.pop("semantic_dependency_vector", None))
    m2 = one_migration(run_root, "M2", lambda value: value.__setitem__("schema_version", "weilan_workspace_projection_v0.1"))
    result = [m1, m2]
    write(run_root / "controller" / "migration-results.json", result)
    return result


def finalize(run_root: Path):
    schedule = load(run_root / "controller" / "schedule.json")
    harness_snapshot = verify_harness_snapshot(run_root, schedule)
    executor_verification = verify_executor_binding(schedule["preflight"]["executor_binding"])
    pf, receipts, comparison = score(run_root)
    migration_results = migrations(run_root)
    proposal = load(PROPOSAL)
    previous_result = archive_previous_result()
    frozen = candidate_bundle(proposal)
    post = {"baseline": tree_hash(DEPLOYED_BUNDLE), "candidate": tree_hash(frozen)}
    tree_stable = post == pf["pre_tree_hashes"]
    impact_case = proposal["method_impact_requirement"]["approved_case_id"]
    impact_trials = [
        item for item in receipts
        if item["case_id"] == impact_case and item["variant"] == "candidate" and item["method_impacts"]
    ]
    impact_pass = len(impact_trials) == proposal["method_impact_requirement"]["required_reproductions"]
    candidate_guardrails = comparison["candidate_guardrail_failures"]
    unrelated = [item for item in comparison["comparisons"] if item["case_id"] != impact_case]
    gate = {
        "a_no_safety_authorization_privacy_cross_workspace_regression": not candidate_guardrails,
        "b_l0_l1_overhead_no_material_degradation": all(item["delta"] >= 0 for item in comparison["comparisons"] if item["case_id"] == "fusion-hidden-evidence-boundary"),
        "c_declared_target_metrics_improve": impact_pass and comparison["mean_delta"] >= 0,
        "d_no_unacceptable_regression_on_unrelated_fixed_cases": all(item["delta"] >= 0 for item in unrelated),
    }
    migration_pass = len(migration_results) == 2 and all(item["passed"] for item in migration_results)
    adoption_eligible = all(gate.values()) and migration_pass and tree_stable and len(receipts) == 24
    result = {
        "schema_version": "axis1_full_shadow_result_v0.1",
        "proposal_id": proposal["proposal_id"],
        "double_sign": {
            "proposal": "peer-chat 2026-07-25 10:23:30 codex",
            "agreement": "peer-chat 2026-07-25 21:33:44 claude",
        },
        "previous_result": previous_result,
        "executed_harness_snapshot": harness_snapshot,
        "executed_harness_sha256": harness_snapshot["sha256"],
        "receipt_writer_harness_sha256": sha_file(Path(__file__)),
        "executor_binding": schedule["preflight"]["executor_binding"],
        "executor_verification_after_run": executor_verification,
        "authority_tuple": proposal["evaluation_binding"],
        "budgets": proposal["budgets"],
        "run_root": str(run_root.relative_to(ROOT)),
        "receipt_count": len(receipts),
        "receipt_hashes": [item["receipt_hash"] for item in receipts],
        "comparison": comparison,
        "gate_a_evidence": gate,
        "method_impact": {
            "approved_case_id": impact_case,
            "required_reproductions": proposal["method_impact_requirement"]["required_reproductions"],
            "observed_reproductions": len(impact_trials),
            "passed": impact_pass,
            "traces": [item["method_impacts"] for item in impact_trials],
        },
        "migration_checks": migration_results,
        "pre_tree_hashes": pf["pre_tree_hashes"],
        "post_tree_hashes": post,
        "tree_hashes_stable": tree_stable,
        "shadow_gate_failures": [
            name for name, failed in {
                "migration_not_converged_in_one_rebuild": not migration_pass,
                "method_impact_not_2_of_2": not impact_pass,
                "candidate_guardrail_failure": bool(candidate_guardrails),
                "authority_tree_drift": not tree_stable,
                "receipt_count_not_24": len(receipts) != 24,
            }.items() if failed
        ],
        "adoption_eligible": adoption_eligible,
        "authority": "evaluation_evidence_only_never_adopts_deploys_or_advances_gate_b",
        "negative_confirmation": {
            "candidate_generations": 0,
            "targeted_checks_rerun": 0,
            "deployments": 0,
            "adoption_decision_written": False,
            "gate_b_advanced": False,
        },
    }
    body = dict(result)
    result["result_hash"] = sha_obj(body)
    write(RESULT, result)
    return result


def record_launch_failure(run_root: Path):
    schedule = load(run_root / "controller" / "schedule.json")
    harness_snapshot = verify_harness_snapshot(run_root, schedule)
    finals = list((run_root / "trials").rglob("final.md"))
    executor_results = list((run_root / "trials").rglob("executor-result.json"))
    receipts = list((run_root / "receipts").glob("*.json")) if (run_root / "receipts").exists() else []
    migrations_found = list((run_root / "migrations").iterdir()) if (run_root / "migrations").exists() else []
    if schedule["execution_count"] != 24 or finals or executor_results or receipts or migrations_found:
        raise ValueError("launch-failure receipt requires 24 scheduled and zero executed artifacts")
    proposal = load(PROPOSAL)
    restoration = authority_artifact_state(proposal, "launch-failure:verified-stop")
    previous_result = archive_previous_result()
    result = {
        "schema_version": "axis1_full_shadow_result_v0.1",
        "proposal_id": proposal["proposal_id"],
        "double_sign": {
            "proposal": "peer-chat 2026-07-25 10:23:30 codex",
            "agreement": "peer-chat 2026-07-25 21:33:44 claude",
        },
        "previous_result": previous_result,
        "run_root": str(run_root.relative_to(ROOT)),
        "executed_harness_snapshot": harness_snapshot,
        "executed_harness_sha256": harness_snapshot["sha256"],
        "receipt_writer_harness_sha256": sha_file(Path(__file__)),
        "executor_binding": schedule["preflight"]["executor_binding"],
        "phase": "approved_suite_trial_launch",
        "preflight_passed": True,
        "schedule_prepared": True,
        "scheduled_receipt_count": schedule["execution_count"],
        "executed_receipt_count": 0,
        "migration_checks_completed": 0,
        "failure": {
            "code": "trial_executor_command_not_found",
            "observable": "Python subprocess could not resolve the PowerShell-only codex.ps1 launcher and raised WinError 2 before the first trial process was created",
            "disposition": "fail_closed_stop_no_trial_execution_no_rerun",
        },
        "restoration": restoration,
        "shadow_gate_failures": ["approved_suite_executor_unavailable"],
        "adoption_eligible": False,
        "authority": "evaluation_evidence_only_never_adopts_deploys_or_advances_gate_b",
        "negative_confirmation": {
            "candidate_generations": 0,
            "targeted_checks_rerun": 0,
            "approved_suite_trials_executed": 0,
            "deployments": 0,
            "adoption_decision_written": False,
            "gate_b_advanced": False,
        },
    }
    result["result_hash"] = sha_obj(result)
    write(RESULT, result)
    return result


def record_runtime_failure(run_root: Path):
    schedule = load(run_root / "controller" / "schedule.json")
    harness_snapshot = verify_harness_snapshot(run_root, schedule)
    finals = list((run_root / "trials").rglob("final.md"))
    executor_results = list((run_root / "trials").rglob("executor-result.json"))
    receipts = list((run_root / "receipts").glob("*.json")) if (run_root / "receipts").exists() else []
    migrations_found = list((run_root / "migrations").iterdir()) if (run_root / "migrations").exists() else []
    if (
        schedule["execution_count"] != 24
        or len(finals) != 24
        or executor_results
        or receipts
        or migrations_found
    ):
        raise ValueError(
            "runtime-failure receipt requires 24 scheduled/final outputs and zero "
            "executor records, receipts, and migrations"
        )
    proposal = load(PROPOSAL)
    restoration = authority_artifact_state(proposal, "runtime-failure:verified-stop")
    executor_verification = verify_executor_binding(schedule["preflight"]["executor_binding"])
    previous_result = archive_previous_result()
    result = {
        "schema_version": "axis1_full_shadow_result_v0.1",
        "proposal_id": proposal["proposal_id"],
        "double_sign": {
            "proposal": "peer-chat 2026-07-25 10:23:30 codex",
            "agreement": "peer-chat 2026-07-25 21:33:44 claude",
        },
        "previous_result": previous_result,
        "run_root": str(run_root.relative_to(ROOT)),
        "executed_harness_snapshot": harness_snapshot,
        "executed_harness_sha256": harness_snapshot["sha256"],
        "receipt_writer_harness_sha256": sha_file(Path(__file__)),
        "executor_binding": schedule["preflight"]["executor_binding"],
        "executor_verification_after_stop": executor_verification,
        "phase": "approved_suite_executor_output_capture",
        "preflight_passed": True,
        "schedule_prepared": True,
        "scheduled_execution_count": schedule["execution_count"],
        "final_outputs_observed": len(finals),
        "executor_records_written": 0,
        "evaluation_receipts_written": 0,
        "migration_checks_completed": 0,
        "failure": {
            "code": "executor_stdout_decode_failure",
            "observable": (
                "Python subprocess text readers used the Windows GBK locale for UTF-8 Codex "
                "JSON output; UnicodeDecodeError left stdout=None, so no trustworthy executor "
                "records or evaluation receipts could be produced"
            ),
            "disposition": "fail_closed_stop_no_rerun_no_threshold_change",
        },
        "restoration": restoration,
        "shadow_gate_failures": ["approved_suite_receipts_unavailable"],
        "adoption_eligible": False,
        "authority": "evaluation_evidence_only_never_adopts_deploys_or_advances_gate_b",
        "negative_confirmation": {
            "candidate_generations": 0,
            "targeted_checks_rerun": 0,
            "approved_suite_process_outputs": len(finals),
            "approved_suite_evaluation_receipts": 0,
            "deployments": 0,
            "adoption_decision_written": False,
            "gate_b_advanced": False,
        },
    }
    result["result_hash"] = sha_obj(result)
    write(RESULT, result)
    return result


def capture_smoke_fixture(write_receipt: bool):
    with tempfile.TemporaryDirectory(prefix="axis1-capture-smoke-") as temporary:
        output = Path(temporary) / "agent-output"
        output.mkdir()
        execution_id = "axis1-01-0b555f"
        final_path = output / "final.md"
        digest_path = output / "final.sha256"
        last_message_path = output / "last-message.md"
        execution = {
            "execution_id": execution_id,
            "final_path": str(final_path),
            "final_sha256_path": str(digest_path),
            "last_message_path": str(last_message_path),
            "expected_receipt_fields": ["case_id", "verdict"],
        }
        if write_receipt:
            prefix = f"{execution_id}\ncase_id: substrate-probe-review\nverdict: "
            receipt = prefix + ("x" * (5031 - len(prefix.encode("utf-8"))))
            final_path.write_text(receipt, encoding="utf-8", newline="")
            digest_path.write_text(sha_file(final_path) + "\n", encoding="utf-8", newline="\n")
        legacy_last_message = "[final.md](agent-output/final.md)"
        legacy_last_message += "x" * (325 - len(legacy_last_message.encode("utf-8")))
        last_message_path.write_text(legacy_last_message, encoding="utf-8", newline="")
        observation = receipt_survival_observation(execution)
        record = {
            "returncode": 0,
            "receipt_survival": observation,
        }
        failures = receipt_contract_failures(execution, record)
        return {
            "passed": not failures,
            "failures": failures,
            "final_bytes": final_path.stat().st_size if final_path.is_file() else 0,
            "last_message_bytes": last_message_path.stat().st_size,
            "startswith_execution_id": (
                final_path.read_text(encoding="utf-8").startswith(execution_id)
                if final_path.is_file() else False
            ),
            "executor_digest_source": str(digest_path),
            "controller_digest_source": str(final_path),
            "executor_digest": observation["executor_digest"],
            "controller_digest": observation["controller_digest"],
            "digests_match": observation["digests_match"],
        }


def capture_regression_test():
    positive = capture_smoke_fixture(write_receipt=True)
    negative = capture_smoke_fixture(write_receipt=False)
    if not positive["passed"]:
        raise AssertionError(f"positive capture smoke failed: {positive['failures']}")
    if positive["final_bytes"] != 5031 or positive["last_message_bytes"] != 325:
        raise AssertionError("r4 5031-byte receipt / 325-byte last-message fixture drift")
    if negative["passed"]:
        raise AssertionError("missing-receipt negative fixture was accepted")
    required_negative = {
        "final_missing",
        "receipt_identity_mismatch",
        "executor_receipt_digest_unavailable",
    }
    if not required_negative.issubset(set(negative["failures"])):
        raise AssertionError(f"negative fixture lacks readable failures: {negative['failures']}")
    context_tokens, usage = extract_context_usage([
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 312994,
                "cached_input_tokens": 269312,
                "output_tokens": 3151,
            },
        },
    ])
    if context_tokens != 312994 or usage["context_tokens_source"] != "json_event.turn.completed.usage.input_tokens":
        raise AssertionError(f"real JSON-event usage was not preserved: {context_tokens}, {usage}")
    unavailable_tokens, unavailable_usage = extract_context_usage([{"type": "turn.completed"}])
    unavailable_guardrails = budget_guardrail_failures(
        {"budget": {"tool_calls": 10, "context_tokens": 7000}},
        {"actual_usage": {"tool_calls": 1, "context_tokens": unavailable_tokens}},
    )
    if unavailable_usage["context_tokens_source"] != "unavailable" or unavailable_guardrails != ["budget_unverifiable"]:
        raise AssertionError(
            f"unavailable usage did not fail closed: {unavailable_usage}, {unavailable_guardrails}"
        )
    calibrated_budget = {"budget": {"tool_calls": 10, "context_tokens": 14000}}
    compliant_usage = {"actual_usage": {"tool_calls": 9, "context_tokens": context_tokens}}
    compliant_guardrails = budget_guardrail_failures(calibrated_budget, compliant_usage)
    compliant_annotations = budget_guardrail_annotations(calibrated_budget, compliant_usage)
    expected_annotation = (
        "context_budget_uncalibrated:"
        "frozen threshold unit != observed whole-context input_tokens"
    )
    if compliant_guardrails or compliant_annotations != [expected_annotation]:
        raise AssertionError(
            "unit-mismatched context usage was not separated from guardrail failures: "
            f"{compliant_guardrails}, {compliant_annotations}"
        )
    excessive_usage = {"actual_usage": {"tool_calls": 11, "context_tokens": context_tokens}}
    excessive_guardrails = budget_guardrail_failures(calibrated_budget, excessive_usage)
    if excessive_guardrails != ["budget_exceeded"]:
        raise AssertionError(f"excessive tool calls did not fail the guardrail: {excessive_guardrails}")
    scorer = load_scorer()
    rubric = scorer.load_frozen_rubric()
    scorer_receipt = {
        "budget": calibrated_budget["budget"],
        "actual_usage": compliant_usage["actual_usage"],
        "guardrail_failures": compliant_guardrails,
        "guardrail_annotations": compliant_annotations,
    }
    scorer_case = "fusion-s0-spec-review-boundary"
    metrics, _ = scorer.score_trial(scorer_case, "", scorer_receipt)
    compliant_weighted_score = scorer.weighted_score(
        scorer_case, metrics, rubric, scorer_receipt
    )
    if compliant_weighted_score == 0.0:
        raise AssertionError("uncalibrated context annotation zeroed the real frozen scorer")
    return {
        "passed": True,
        "positive": positive,
        "negative": negative,
        "usage_positive": {
            "context_tokens": context_tokens,
            "context_tokens_source": usage["context_tokens_source"],
            "compliant_guardrail_failures": compliant_guardrails,
            "guardrail_annotations": compliant_annotations,
            "weighted_score": compliant_weighted_score,
        },
        "tool_calls_exceeded": {
            "tool_calls": excessive_usage["actual_usage"]["tool_calls"],
            "guardrail_failures": excessive_guardrails,
        },
        "usage_negative": {
            "context_tokens": unavailable_tokens,
            "context_tokens_source": unavailable_usage["context_tokens_source"],
            "guardrail_failures": unavailable_guardrails,
        },
    }


def self_test():
    pf = preflight()
    assert pf["passed"]
    assert len(pf["utf8_subprocess_contract"]) == 2
    assert all(item["passed"] for item in pf["utf8_subprocess_contract"])
    assert sha_obj({"b": 2, "a": 1}) == sha_obj({"a": 1, "b": 2})
    assert canonical_targeted_hash(ROOT / load(PROPOSAL)["evaluation_binding"]["prior_targeted_result"]["path"])
    proposal = load(PROPOSAL)
    frozen = candidate_bundle(proposal)
    frozen_before = authority_artifact_state(proposal, "boundary-probe:before")
    with tempfile.TemporaryDirectory(prefix="axis1-boundary-probe-") as temporary:
        run_root = Path(temporary)
        copied = copy_method_bundle(
            frozen,
            run_root / "candidate-bundle",
            proposal["candidate_artifact_hash"],
            run_root,
            frozen,
        )
        probe = copied / "scripts" / "_source_side_effect_probe.py"
        marker = probe.with_suffix(".sidecar")
        probe.write_text(
            "from pathlib import Path\nPath(__file__).with_suffix('.sidecar').write_text('copy-only', encoding='utf-8')\n",
            encoding="utf-8",
            newline="\n",
        )
        outcome = run([sys.executable, probe], cwd=run_root, timeout=30)
        if outcome.returncode != 0 or not marker.is_file():
            raise RuntimeError("source-side-effect boundary probe did not execute in the run copy")
        if (frozen / "scripts" / marker.name).exists():
            raise RuntimeError("source-side-effect boundary probe escaped into the frozen artifact")
    frozen_after = authority_artifact_state(proposal, "boundary-probe:after")
    assert frozen_before == {**frozen_after, "stage": "boundary-probe:before"}
    return {
        "passed": True,
        "tests": 6,
        "utf8_subprocess_contract": pf["utf8_subprocess_contract"],
        "boundary_probe": "side effect confined to run_root copy",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("self-test")
    sub.add_parser("capture-regression")
    sub.add_parser("smoke-test")
    prepare_p = sub.add_parser("prepare")
    prepare_p.add_argument("--run-root", required=True)
    prepare_p.add_argument("--seed", type=int, default=20260724)
    execute_p = sub.add_parser("execute")
    execute_p.add_argument("--run-root", required=True)
    execute_p.add_argument("--workers", type=int, default=1)
    score_p = sub.add_parser("score")
    score_p.add_argument("--run-root", required=True)
    migrate_p = sub.add_parser("migrate")
    migrate_p.add_argument("--run-root", required=True)
    final_p = sub.add_parser("finalize")
    final_p.add_argument("--run-root", required=True)
    failure_p = sub.add_parser("record-launch-failure")
    failure_p.add_argument("--run-root", required=True)
    runtime_failure_p = sub.add_parser("record-runtime-failure")
    runtime_failure_p.add_argument("--run-root", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--run-root", required=True)
    run_p.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    run_root = Path(getattr(args, "run_root", "")).resolve() if hasattr(args, "run_root") else None
    if args.command == "preflight":
        value = preflight()
    elif args.command == "self-test":
        value = self_test()
    elif args.command == "capture-regression":
        value = capture_regression_test()
    elif args.command == "smoke-test":
        value = capture_smoke_fixture(write_receipt=True)
        if not value["passed"]:
            raise RuntimeError("capture smoke failed: " + ";".join(value["failures"]))
    elif args.command == "prepare":
        value = {"prepared": True, "execution_count": prepare(run_root, args.seed)["execution_count"], "run_root": str(run_root)}
    elif args.command == "execute":
        value = {"executed": len(execute(run_root, args.workers))}
    elif args.command == "score":
        _, receipts, comparison = score(run_root)
        value = {"receipt_count": len(receipts), "comparison": comparison}
    elif args.command == "migrate":
        value = {"migration_checks": migrations(run_root)}
    elif args.command == "finalize":
        value = finalize(run_root)
    elif args.command == "record-launch-failure":
        value = record_launch_failure(run_root)
    elif args.command == "record-runtime-failure":
        value = record_runtime_failure(run_root)
    else:
        schedule = prepare(run_root)
        execute(run_root, args.workers)
        value = finalize(run_root)
        value["prepared_execution_count"] = schedule["execution_count"]
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
