#!/usr/bin/env python3
"""Push one explicitly authorized commit to one ref, then verify it.

All outcomes are emitted as a single JSON object on stdout.  The caller is
responsible for supplying values that have already passed the community's
authorization and publication-review process; this tool enforces only the
stated ref transition.
"""

import argparse
import json
import subprocess
import sys


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def emit(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def git(*args):
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def fail(reason, *, stage, returncode=None, **fields):
    receipt = {
        "ok": False,
        "status": "error",
        "stage": stage,
        "reason": reason,
        **fields,
    }
    if returncode is not None:
        receipt["git_returncode"] = returncode
    emit(receipt)
    return 1


def canonical_commit(value, label):
    proc = git("rev-parse", "--verify", f"{value}^{{commit}}")
    if proc.returncode != 0:
        return None, fail(
            f"{label}_is_not_a_local_commit",
            stage="local_validation",
            returncode=proc.returncode,
        )
    canonical = proc.stdout.strip()
    if canonical != value:
        return None, fail(
            f"{label}_is_not_a_canonical_oid",
            stage="local_validation",
        )
    return canonical, None


def live_remote_oid(origin, ref):
    proc = git("ls-remote", "--refs", origin, ref)
    if proc.returncode != 0:
        return None, fail(
            "ls_remote_failed",
            stage="remote_read",
            returncode=proc.returncode,
        )
    matches = []
    for line in proc.stdout.splitlines():
        oid, separator, found_ref = line.partition("\t")
        if separator and found_ref == ref:
            matches.append(oid)
    if not matches:
        return None, fail("remote_ref_missing", stage="remote_read", ref=ref)
    if len(matches) != 1:
        return None, fail(
            "remote_ref_ambiguous",
            stage="remote_read",
            ref=ref,
            match_count=len(matches),
        )
    return matches[0], None


def build_parser():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--authorized-oid", required=True)
    return parser


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
    except ValueError:
        return fail("invalid_arguments", stage="argument_validation")
    except SystemExit as exc:
        return int(exc.code or 0)

    base, error = canonical_commit(args.base, "base")
    if error is not None:
        return error
    authorized_oid, error = canonical_commit(
        args.authorized_oid, "authorized_oid"
    )
    if error is not None:
        return error

    ancestry = git("merge-base", "--is-ancestor", base, authorized_oid)
    if ancestry.returncode == 1:
        return fail(
            "non_fast_forward",
            stage="local_validation",
            base=base,
            authorized_oid=authorized_oid,
            ref=args.ref,
        )
    if ancestry.returncode != 0:
        return fail(
            "ancestry_check_failed",
            stage="local_validation",
            returncode=ancestry.returncode,
        )

    remote_oid, error = live_remote_oid(args.origin, args.ref)
    if error is not None:
        return error
    if remote_oid == authorized_oid:
        emit(
            {
                "ok": True,
                "status": "already_at_authorized_head",
                "ref": args.ref,
                "base": base,
                "authorized_oid": authorized_oid,
                "remote_oid": remote_oid,
                "push_performed": False,
            }
        )
        return 0
    if remote_oid != base:
        return fail(
            "remote_base_mismatch",
            stage="preflight",
            ref=args.ref,
            expected_base=base,
            observed_remote_oid=remote_oid,
            authorized_oid=authorized_oid,
        )

    push = git(
        "push",
        "--porcelain",
        args.origin,
        f"{authorized_oid}:{args.ref}",
    )
    if push.returncode != 0:
        return fail(
            "git_push_failed",
            stage="push",
            returncode=push.returncode,
            ref=args.ref,
            base=base,
            authorized_oid=authorized_oid,
        )

    verified_oid, error = live_remote_oid(args.origin, args.ref)
    if error is not None:
        return error
    if verified_oid != authorized_oid:
        return fail(
            "post_push_ref_mismatch",
            stage="post_verification",
            ref=args.ref,
            expected_authorized_oid=authorized_oid,
            observed_remote_oid=verified_oid,
        )

    emit(
        {
            "ok": True,
            "status": "pushed_and_verified",
            "ref": args.ref,
            "base": base,
            "authorized_oid": authorized_oid,
            "previous_remote_oid": remote_oid,
            "remote_oid": verified_oid,
            "push_performed": True,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
