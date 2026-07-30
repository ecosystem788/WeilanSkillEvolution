#!/usr/bin/env python3
"""Read-only: does any failure receipt record that the remote was mutated?

No network. Reuses the landed test file's scripted-git stub so the tool runs
against a fake git; nothing is pushed and no file is written.

Question under test: for the three failure shapes that occur *after* the push
subprocess has run, can a third party reading the receipt alone tell whether
the remote was mutated by this invocation?
"""

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = "refs/heads/codex/se-0.4-0.7-program"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fresh_tool():
    return load("tool_probe", "push_authorized_oid.py")


def scripted(module, post_oid, push_stdout, push_rc=0):
    base = "a" * 40
    authorized_oid = "b" * 40
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify"):
            return type("P", (), {"returncode": 0,
                                  "stdout": args[2].removesuffix("^{commit}") + "\n"})()
        if args[:2] == ("merge-base", "--is-ancestor"):
            return type("P", (), {"returncode": 0, "stdout": ""})()
        if args[0] == "ls-remote":
            seen = len([c for c in calls if c[0] == "ls-remote"])
            observed = base if seen == 1 else post_oid
            return type("P", (), {"returncode": 0,
                                  "stdout": f"{observed}\t{REF}\n"})()
        if args[0] == "push":
            return type("P", (), {"returncode": push_rc,
                                  "stdout": push_stdout})()
        raise AssertionError(args)

    module.git = fake_git
    return base, authorized_oid


def receipt_for(post_oid, push_stdout, push_rc=0):
    module = fresh_tool()
    base, authorized_oid = scripted(module, post_oid, push_stdout, push_rc)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        rc = module.main([
            "--origin", "redacted-origin", "--ref", REF,
            "--base", base, "--authorized-oid", authorized_oid,
        ])
    return rc, json.loads(buffer.getvalue())


AUTHORIZED = "b" * 40
DRIFT = "c" * 40
GOOD = f" \t{AUTHORIZED}:{REF}\t1234567..abcdef0\n"
JUNK = "To redacted-origin\nDone\n"

CASES = [
    # label, post-push ls-remote oid, push stdout, push rc, did remote mutate?
    ("pushed_and_verified", AUTHORIZED, GOOD, 0, True),
    ("push_porcelain_unparseable", AUTHORIZED, JUNK, 0, True),
    ("post_push_ref_mismatch (accepted report)", DRIFT, GOOD, 0, "unknown"),
    ("git_push_failed", DRIFT, JUNK, 1, "unknown"),
]


def main():
    for label, post_oid, stdout, rc_in, mutated in CASES:
        rc, receipt = receipt_for(post_oid, stdout, rc_in)
        print(f"--- {label}")
        print(f"    exit={rc} reason={receipt.get('reason', receipt.get('status'))}")
        print(f"    push_performed present? {'push_performed' in receipt}"
              f"  preflight_remote_oid present? "
              f"{'preflight_remote_oid' in receipt}")
        print(f"    ground truth: remote mutated by this call = {mutated}")
        print(f"    keys={sorted(receipt)}")


if __name__ == "__main__":
    main()
