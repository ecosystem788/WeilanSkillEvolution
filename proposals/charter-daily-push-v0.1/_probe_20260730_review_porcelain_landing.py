#!/usr/bin/env python3
"""Read-only review probe for the 2026-07-30 push-porcelain landing.

Touches no remote at all: `git` inside the tool module is replaced by a
scripted stub, so nothing outside this process is read or written.  Two
questions, both about receipt shapes the landed tests do not assert:

A. rc=0 + PARSEABLE porcelain + post read sees a third-party oid.
   The proposal's own verification list promised a case asserting
   `post_push_ref_mismatch` carries an *accepted* `push_report` plus the
   observed remote.  The landed suite covers this path only with
   UNPARSEABLE stdout, so the accepted-report branch is unexercised.

B. Is a failed POST ls-remote receipt distinguishable from a failed
   PREFLIGHT ls-remote receipt?  Both call sites share one hardcoded
   stage label, so a receipt written after the irreversible push may be
   byte-identical to one written before any push happened.

Usage: python _probe_20260730_review_porcelain_landing.py
Writes its findings to stdout as JSON; no files, no network, no remotes.
"""

import importlib.util
import io
import json
import pathlib
import subprocess
import sys

TOOL = pathlib.Path(__file__).with_name("push_authorized_oid.py")
REF = "refs/heads/main"
BASE = "a" * 40
AUTHORIZED = "b" * 40
DRIFT = "c" * 40


def load_tool_module():
    spec = importlib.util.spec_from_file_location("tool_under_probe", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scripted_git(*, push_stdout, push_rc, ls_remote_results):
    """ls_remote_results: list of (returncode, stdout) consumed in order."""
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify"):
            value = args[2].removesuffix("^{commit}")
            return subprocess.CompletedProcess(args, 0, value + "\n", "")
        if args[:2] == ("merge-base", "--is-ancestor"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "ls-remote":
            seen = len([c for c in calls if c[0] == "ls-remote"])
            rc, out = ls_remote_results[seen - 1]
            return subprocess.CompletedProcess(args, rc, out, "")
        if args[0] == "push":
            return subprocess.CompletedProcess(args, push_rc, push_stdout, "")
        raise AssertionError(args)

    return fake_git, calls


def run(module, fake_git):
    module.git = fake_git
    buffer = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = buffer
    try:
        rc = module.main(
            [
                "--origin", "probe-origin-placeholder",
                "--ref", REF,
                "--base", BASE,
                "--authorized-oid", AUTHORIZED,
            ]
        )
    finally:
        sys.stdout = real_stdout
    return rc, buffer.getvalue()


def case_a():
    """rc=0, parseable porcelain, post read sees a third-party oid."""
    module = load_tool_module()
    porcelain = (
        "To probe-origin-placeholder\n"
        f" \t{AUTHORIZED}:{REF}\t1234567..abcdef0\n"
        "Done\n"
    )
    fake_git, calls = scripted_git(
        push_stdout=porcelain,
        push_rc=0,
        ls_remote_results=[(0, f"{BASE}\t{REF}\n"), (0, f"{DRIFT}\t{REF}\n")],
    )
    rc, out = run(module, fake_git)
    receipt = json.loads(out)
    return {
        "returncode": rc,
        "receipt": receipt,
        "ls_remote_call_count": len([c for c in calls if c[0] == "ls-remote"]),
        "checks": {
            "reason_is_post_push_ref_mismatch":
                receipt.get("reason") == "post_push_ref_mismatch",
            "carries_accepted_push_report":
                isinstance(receipt.get("push_report"), dict),
            "push_report_flag_is_accepted":
                (receipt.get("push_report") or {}).get("flag") == " ",
            "carries_observed_remote":
                receipt.get("observed_remote_oid") == DRIFT,
            "no_unparseable_status_leaked":
                "push_report_status" not in receipt,
        },
    }


def case_b_preflight_read_fails():
    module = load_tool_module()
    fake_git, calls = scripted_git(
        push_stdout="", push_rc=0, ls_remote_results=[(128, "")]
    )
    rc, out = run(module, fake_git)
    return {
        "returncode": rc,
        "receipt": json.loads(out),
        "push_attempted": any(c[0] == "push" for c in calls),
    }


def case_c_post_read_fails():
    module = load_tool_module()
    porcelain = f" \t{AUTHORIZED}:{REF}\t1234567..abcdef0\n"
    fake_git, calls = scripted_git(
        push_stdout=porcelain,
        push_rc=0,
        ls_remote_results=[(0, f"{BASE}\t{REF}\n"), (128, "")],
    )
    rc, out = run(module, fake_git)
    return {
        "returncode": rc,
        "receipt": json.loads(out),
        "push_attempted": any(c[0] == "push" for c in calls),
    }


def main():
    a = case_a()
    b = case_b_preflight_read_fails()
    c = case_c_post_read_fails()
    report = {
        "probe": "review_porcelain_landing",
        "tool": str(TOOL),
        "case_a_parseable_report_plus_post_drift": a,
        "case_b_preflight_ls_remote_failure": b,
        "case_c_post_ls_remote_failure": c,
        "case_bc_receipts_identical":
            b["receipt"] == c["receipt"],
        "case_c_receipt_records_push_performed":
            "push_performed" in c["receipt"]
            or "push_report" in c["receipt"]
            or "authorized_oid" in c["receipt"],
        "case_bc_push_attempted": {
            "preflight_case": b["push_attempted"],
            "post_case": c["push_attempted"],
        },
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
