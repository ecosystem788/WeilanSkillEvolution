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
    result = validate_eval_manifest(load_json(args.manifest), require_approved=not args.allow_draft)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def command_eval_compare(args):
    result = compare_trials(load_json(args.manifest), load_jsonl(args.receipts))
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
