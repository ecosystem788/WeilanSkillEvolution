#!/usr/bin/env python3
"""Read-only probe: how many pre/post ls-remote exit pairs are byte-identical?

Context: Codex's 2026-07-30T09:43:09+09:00 proposal scopes the fix to "four
post-invocation failure exits" and lists six test cells.  live_remote_oid has
THREE failure returns (ls_remote_failed / remote_ref_missing /
remote_ref_ambiguous), all hardcoding stage="remote_read", and it is called
from both the preflight and the post-verification site.  This probe asks
whether the other two returns also produce pre/post receipts that cannot be
told apart -- i.e. whether threading `stage` must cover all three returns
rather than only the ls_remote_failed one named in the proposal.

No remote is touched: module.git is replaced by a scripted stub.
"""

import contextlib
import importlib.util
import io
import json
import pathlib


TOOL = pathlib.Path(__file__).with_name("push_authorized_oid.py")
REF = "refs/heads/main"
BASE = "a" * 40
AUTHORIZED = "b" * 40


def load_tool_module():
    spec = importlib.util.spec_from_file_location(
        "push_authorized_oid_probe", TOOL
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def completed(args, returncode, stdout):
    import subprocess

    return subprocess.CompletedProcess(args, returncode, stdout, "")


def run_case(ls_remote_outputs, push_returncode=0, push_stdout=""):
    """Run main() with ls-remote answers taken in order from the list."""
    module = load_tool_module()
    calls = []
    pushed = []

    def fake_git(*args):
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify"):
            return completed(args, 0, args[2].removesuffix("^{commit}") + "\n")
        if args[:2] == ("merge-base", "--is-ancestor"):
            return completed(args, 0, "")
        if args[0] == "ls-remote":
            index = len([c for c in calls if c[0] == "ls-remote"]) - 1
            if index >= len(ls_remote_outputs):
                raise AssertionError("unexpected extra ls-remote call")
            returncode, stdout = ls_remote_outputs[index]
            return completed(args, returncode, stdout)
        if args[0] == "push":
            pushed.append(args)
            return completed(args, push_returncode, push_stdout)
        raise AssertionError(args)

    module.git = fake_git
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        exit_code = module.main(
            [
                "--origin",
                "redacted-origin",
                "--ref",
                REF,
                "--base",
                BASE,
                "--authorized-oid",
                AUTHORIZED,
            ]
        )
    return {
        "exit_code": exit_code,
        "receipt_bytes": buffer.getvalue(),
        "push_subprocess_invoked": bool(pushed),
        "ls_remote_calls": len([c for c in calls if c[0] == "ls-remote"]),
    }


GOOD_PREFLIGHT = (0, BASE + "\t" + REF + "\n")
ACCEPTED_PUSH = " \t" + AUTHORIZED + ":" + REF + "\t1234567..abcdef0\n"

FAILURE_SHAPES = {
    "ls_remote_failed": (128, ""),
    "remote_ref_missing": (0, ""),
    "remote_ref_ambiguous": (
        0,
        BASE + "\t" + REF + "\n" + AUTHORIZED + "\t" + REF + "\n",
    ),
}


def main():
    report = {"tool": str(TOOL), "pairs": []}
    for name, shape in FAILURE_SHAPES.items():
        pre = run_case([shape])
        post = run_case(
            [GOOD_PREFLIGHT, shape],
            push_returncode=0,
            push_stdout=ACCEPTED_PUSH,
        )
        pre_receipt = json.loads(pre["receipt_bytes"])
        post_receipt = json.loads(post["receipt_bytes"])
        report["pairs"].append(
            {
                "failure_shape": name,
                "preflight_push_invoked": pre["push_subprocess_invoked"],
                "post_push_push_invoked": post["push_subprocess_invoked"],
                "preflight_reason": pre_receipt.get("reason"),
                "post_push_reason": post_receipt.get("reason"),
                "receipts_byte_identical": (
                    pre["receipt_bytes"] == post["receipt_bytes"]
                ),
                "receipt_bytes": pre["receipt_bytes"].rstrip("\n"),
                "post_records_push_invoked": any(
                    key in post_receipt
                    for key in (
                        "push_performed",
                        "push_attempted",
                        "push_report",
                        "preflight_remote_oid",
                    )
                ),
            }
        )
    report["identical_pair_count"] = sum(
        1 for pair in report["pairs"] if pair["receipts_byte_identical"]
    )
    report["named_in_proposal_test_list"] = ["ls_remote_failed"]
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
