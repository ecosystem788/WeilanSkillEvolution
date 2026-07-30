#!/usr/bin/env python3
"""Push one explicitly authorized commit to one ref, then verify it.

All outcomes are emitted as a single JSON object on stdout.  The caller is
responsible for supplying values that have already passed the community's
authorization and publication-review process; this tool enforces only the
stated ref transition.

Every receipt reports whether this invocation called the push subprocess.
``push_performed`` is narrower: it appears only on the two successful
outcomes where this invocation's effect is settled.  Its absence on an error
means whether this invocation changed the remote is undetermined, not false.
The false value on ``already_at_authorized_head`` is scoped to this invocation
and does not claim that no earlier invocation performed the push.
"""

import argparse
import hashlib
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


def push_argv(origin, ref, base, authorized_oid):
    return (
        "push",
        "--porcelain",
        f"--force-with-lease={ref}:{base}",
        origin,
        f"{authorized_oid}:{ref}",
    )


def parse_push_porcelain(stdout, authorized_oid, ref):
    """Return one bounded ref-status report, or None when it is not exact."""
    status_lines = [
        line for line in stdout.splitlines() if line.count("\t") == 2
    ]
    if len(status_lines) != 1:
        return None
    flag, source_destination, summary = status_lines[0].split("\t")
    if len(flag) != 1:
        return None
    if source_destination != f"{authorized_oid}:{ref}":
        return None
    if len(summary.encode("utf-8")) > 512:
        return None
    return {
        "flag": flag,
        "source_oid": authorized_oid,
        "destination_ref": ref,
        "summary": summary,
        "summary_authority": "git_process_self_report_not_remote_observation",
    }


def replacement_decoded_stdout_fingerprint(stdout):
    """Describe the text returned by git(), not unavailable raw stdout bytes."""
    encoded = stdout.encode("utf-8")
    return {
        "push_report_status": "unparseable",
        "stdout_replacement_decoded_utf8_byte_count": len(encoded),
        "stdout_replacement_decoded_utf8_sha256": hashlib.sha256(
            encoded
        ).hexdigest(),
    }


def fail(
    reason,
    *,
    stage,
    push_attempted=False,
    returncode=None,
    returncode_field="git_returncode",
    **fields,
):
    receipt = {
        "ok": False,
        "status": "error",
        "stage": stage,
        "reason": reason,
        "push_attempted": push_attempted,
        **fields,
    }
    if returncode is not None:
        receipt[returncode_field] = returncode
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


def live_remote_oid(
    origin,
    ref,
    *,
    stage,
    push_attempted,
    failure_fields=None,
):
    failure_fields = dict(failure_fields or {})
    proc = git("ls-remote", "--refs", origin, ref)
    if proc.returncode != 0:
        return None, fail(
            "ls_remote_failed",
            stage=stage,
            push_attempted=push_attempted,
            returncode=proc.returncode,
            returncode_field="remote_read_returncode",
            ref=ref,
            **failure_fields,
        )
    matches = []
    for line in proc.stdout.splitlines():
        oid, separator, found_ref = line.partition("\t")
        if separator and found_ref == ref:
            matches.append(oid)
    if not matches:
        return None, fail(
            "remote_ref_missing",
            stage=stage,
            push_attempted=push_attempted,
            ref=ref,
            **failure_fields,
        )
    if len(matches) != 1:
        return None, fail(
            "remote_ref_ambiguous",
            stage=stage,
            push_attempted=push_attempted,
            ref=ref,
            match_count=len(matches),
            **failure_fields,
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

    remote_oid, error = live_remote_oid(
        args.origin,
        args.ref,
        stage="preflight_remote_read",
        push_attempted=False,
    )
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
                "push_attempted": False,
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

    push = git(*push_argv(args.origin, args.ref, base, authorized_oid))
    push_report = parse_push_porcelain(
        push.stdout, authorized_oid, args.ref
    )
    push_evidence = (
        {"push_report": push_report}
        if push_report is not None
        else replacement_decoded_stdout_fingerprint(push.stdout)
    )
    if push.returncode != 0:
        return fail(
            "git_push_failed",
            stage="push",
            push_attempted=True,
            returncode=push.returncode,
            ref=args.ref,
            base=base,
            authorized_oid=authorized_oid,
            preflight_remote_oid=remote_oid,
            push_returncode=push.returncode,
            **push_evidence,
        )

    verified_oid, error = live_remote_oid(
        args.origin,
        args.ref,
        stage="post_push_remote_read",
        push_attempted=True,
        failure_fields={
            "authorized_oid": authorized_oid,
            "preflight_remote_oid": remote_oid,
            "push_returncode": push.returncode,
            **push_evidence,
        },
    )
    if error is not None:
        return error
    if verified_oid != authorized_oid:
        return fail(
            "post_push_ref_mismatch",
            stage="post_verification",
            push_attempted=True,
            ref=args.ref,
            expected_authorized_oid=authorized_oid,
            observed_remote_oid=verified_oid,
            preflight_remote_oid=remote_oid,
            push_returncode=push.returncode,
            **push_evidence,
        )
    if push_report is None:
        return fail(
            "push_porcelain_unparseable",
            stage="post_verification",
            push_attempted=True,
            ref=args.ref,
            expected_authorized_oid=authorized_oid,
            observed_remote_oid=verified_oid,
            preflight_remote_oid=remote_oid,
            push_returncode=push.returncode,
            **replacement_decoded_stdout_fingerprint(push.stdout),
        )

    emit(
        {
            "ok": True,
            "status": "pushed_and_verified",
            "ref": args.ref,
            "base": base,
            "authorized_oid": authorized_oid,
            "preflight_remote_oid": remote_oid,
            "remote_oid": verified_oid,
            "push_attempted": True,
            "push_performed": True,
            "push_report": push_report,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
