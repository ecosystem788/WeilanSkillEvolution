"""Command-line entrypoint for the external WeiLan Skill Evolution plane."""

import argparse
import json
from pathlib import Path

from evolution_core import (
    compare_trials,
    freeze_candidate,
    validate_eval_manifest,
    validate_proposal,
)
from evolution_runner import run_evolution_manifest, validate_evolution_manifest
from release_core import (
    compare_shadow,
    deploy_candidate,
    evaluate_canary,
    rollback_deployment,
    validate_decision,
    validate_shadow_plan,
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def command_proposal_validate(args):
    result = validate_proposal(load_json(args.proposal))
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_candidate_freeze(args):
    print(json.dumps(freeze_candidate(args.source, args.artifact_root), indent=2))


def command_eval_validate(args):
    manifest_path = Path(args.manifest).resolve()
    manifest = load_json(manifest_path)
    case_set = None
    if manifest.get("case_spec"):
        case_path = manifest_path.parent.parent / manifest["case_spec"]
        case_set = load_json(case_path)
    result = validate_eval_manifest(
        manifest,
        require_approved=not args.allow_draft,
        case_set=case_set,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_eval_compare(args):
    result = compare_trials(load_json(args.manifest), load_jsonl(args.receipts))
    print(json.dumps(result, indent=2))


def command_shadow_validate(args):
    result = validate_shadow_plan(
        load_json(args.plan),
        load_json(args.manifest),
        load_json(args.case_set),
    )
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_shadow_compare(args):
    result = compare_shadow(
        load_json(args.plan),
        load_json(args.manifest),
        load_jsonl(args.receipts),
        case_set=load_json(args.case_set),
    )
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def command_decision_validate(args):
    result = validate_decision(load_json(args.decision), load_json(args.shadow_result))
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_deploy(args):
    if not args.confirm_deployment:
        raise ValueError("deployment requires --confirm-deployment")
    result = deploy_candidate(
        args.candidate,
        args.target,
        load_json(args.decision),
        load_json(args.shadow_result),
        args.receipt_root,
    )
    print(json.dumps(result, indent=2))


def command_canary(args):
    result = evaluate_canary(load_json(args.deployment_receipt), load_json(args.observations))
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_rollback(args):
    if not args.confirm_rollback:
        raise ValueError("rollback requires --confirm-rollback")
    result = rollback_deployment(args.deployment_receipt, args.authority_source)
    print(json.dumps(result, indent=2))


def command_evolution_validate(args):
    result = validate_evolution_manifest(load_json(args.manifest))
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_evolution_run(args):
    result = run_evolution_manifest(
        load_json(args.manifest),
        args.root,
        args.receipt,
        allow_deployment=args.allow_deployment,
    )
    print(json.dumps(result, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    proposal = commands.add_parser("proposal-validate")
    proposal.add_argument("--proposal", required=True)
    proposal.set_defaults(func=command_proposal_validate)

    freeze = commands.add_parser("candidate-freeze")
    freeze.add_argument("--source", required=True)
    freeze.add_argument("--artifact-root", required=True)
    freeze.set_defaults(func=command_candidate_freeze)

    validate = commands.add_parser("eval-validate")
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--allow-draft", action="store_true")
    validate.set_defaults(func=command_eval_validate)

    compare = commands.add_parser("eval-compare")
    compare.add_argument("--manifest", required=True)
    compare.add_argument("--receipts", required=True)
    compare.set_defaults(func=command_eval_compare)

    shadow_validate = commands.add_parser("shadow-validate")
    shadow_validate.add_argument("--plan", required=True)
    shadow_validate.add_argument("--manifest", required=True)
    shadow_validate.add_argument("--case-set", required=True)
    shadow_validate.set_defaults(func=command_shadow_validate)

    shadow_compare = commands.add_parser("shadow-compare")
    shadow_compare.add_argument("--plan", required=True)
    shadow_compare.add_argument("--manifest", required=True)
    shadow_compare.add_argument("--case-set", required=True)
    shadow_compare.add_argument("--receipts", required=True)
    shadow_compare.add_argument("--output")
    shadow_compare.set_defaults(func=command_shadow_compare)

    decision = commands.add_parser("decision-validate")
    decision.add_argument("--decision", required=True)
    decision.add_argument("--shadow-result", required=True)
    decision.set_defaults(func=command_decision_validate)

    deploy = commands.add_parser("deploy")
    deploy.add_argument("--candidate", required=True)
    deploy.add_argument("--target", required=True)
    deploy.add_argument("--decision", required=True)
    deploy.add_argument("--shadow-result", required=True)
    deploy.add_argument("--receipt-root", required=True)
    deploy.add_argument("--confirm-deployment", action="store_true")
    deploy.set_defaults(func=command_deploy)

    canary = commands.add_parser("canary")
    canary.add_argument("--deployment-receipt", required=True)
    canary.add_argument("--observations", required=True)
    canary.set_defaults(func=command_canary)

    rollback = commands.add_parser("rollback")
    rollback.add_argument("--deployment-receipt", required=True)
    rollback.add_argument("--authority-source", required=True)
    rollback.add_argument("--confirm-rollback", action="store_true")
    rollback.set_defaults(func=command_rollback)

    evolution_validate = commands.add_parser("evolution-validate")
    evolution_validate.add_argument("--manifest", required=True)
    evolution_validate.set_defaults(func=command_evolution_validate)

    evolution_run = commands.add_parser("evolution-run")
    evolution_run.add_argument("--manifest", required=True)
    evolution_run.add_argument("--root", required=True)
    evolution_run.add_argument("--receipt", required=True)
    evolution_run.add_argument("--allow-deployment", action="store_true")
    evolution_run.set_defaults(func=command_evolution_run)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        return int(args.func(args) or 0)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
