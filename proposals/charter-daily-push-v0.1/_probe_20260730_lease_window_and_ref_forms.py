#!/usr/bin/env python3
"""Independent review probes for push_authorized_oid.py (commit 8ac9cfb).

Read-only with respect to the real repository and the real remote: every
remote here is a throwaway local bare repo reached over file://.  Nothing in
this probe reads or writes `git@github.com:...`.

Three questions, each answered by a separate temp fixture:

A) Is the base binding *enforced at push time*, or only *observed* by an
   earlier `ls-remote`?  A local `pre-push` hook stands in for a concurrent
   pusher: it advances the remote from base to an intermediate commit that is
   still an ancestor of the authorized oid, then lets the push proceed.  A
   plain push accepts that; `--force-with-lease=<ref>:<base>` would not.

B) What happens when `--ref` is given as a short branch name
   (`codex/se-0.4-0.7-program`) rather than `refs/heads/...`?

C) Does `--help` honour the documented "single JSON object on stdout"
   contract?

Output: one JSON object per probe on stdout.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).with_name("push_authorized_oid.py")
REF = "refs/heads/main"


def git(cwd, *args, check=True):
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {args} -> {proc.returncode}: {proc.stderr}")
    return proc.stdout.strip()


def commit(repo, name, text):
    (repo / "value.txt").write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", name)
    return git(repo, "rev-parse", "HEAD")


def build_three_commit_source(tmp):
    """base <- mid <- authorized, plus a bare remote pinned at base."""
    source = tmp / "source"
    source.mkdir()
    git(source, "init", "-q", ".")
    git(source, "config", "user.email", "probe@local")
    git(source, "config", "user.name", "probe")
    base = commit(source, "base", "base\n")
    git(source, "branch", "-M", "main")
    remote = tmp / "remote.git"
    git(tmp, "clone", "-q", "--bare", str(source), str(remote))
    mid = commit(source, "mid", "mid\n")
    authorized = commit(source, "authorized", "authorized\n")
    return source, remote, remote.resolve().as_uri(), base, mid, authorized


def run_tool(cwd, origin, ref, base, authorized):
    proc = subprocess.run(
        [
            sys.executable, str(TOOL),
            "--origin", origin,
            "--ref", ref,
            "--base", base,
            "--authorized-oid", authorized,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        receipt = json.loads(proc.stdout)
    except ValueError:
        receipt = None
    return proc, receipt


def install_prepush_interposer(source, remote, new_oid):
    """A concurrent pusher, made deterministic.

    Git advertises the remote refs and then runs pre-push before sending the
    pack, so moving the remote ref here lands inside the tool's
    read-then-push window.
    """
    hook = source / ".git" / "hooks" / "pre-push"
    hook.parent.mkdir(parents=True, exist_ok=True)
    remote_posix = remote.resolve().as_posix()
    marker = (source / "interposer_observed.txt").resolve().as_posix()
    # A bare `update-ref` cannot be used here: the throwaway remote was cloned
    # at base and does not have the interposed object, so update-ref fails and
    # -- because the hook must exit 0 for the push to proceed -- the failure
    # would be silent and the probe would report an interposition that never
    # happened.  Push transfers the object; --no-verify stops this hook from
    # recursing.  The marker records what the remote actually held afterwards,
    # so the interposition is measured rather than assumed.
    hook.write_text(
        "#!/bin/sh\n"
        f'git push --no-verify -q "file://{remote_posix}" {new_oid}:{REF} '
        f'>/dev/null 2>&1\n'
        f'git --git-dir="{remote_posix}" rev-parse {REF} > "{marker}" 2>&1\n'
        "exit 0\n",
        encoding="utf-8",
        newline="\n",
    )
    return source / "interposer_observed.txt"


def probe_a_lease_window():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="probe_a_"))
    try:
        source, remote, origin, base, mid, authorized = (
            build_three_commit_source(tmp)
        )
        marker = install_prepush_interposer(source, remote, mid)
        remote_before = git(remote, "rev-parse", REF)
        proc, receipt = run_tool(source, origin, REF, base, authorized)
        remote_after = git(remote, "rev-parse", REF)
        observed_mid_push = (
            marker.read_text(encoding="utf-8").strip()
            if marker.exists() else None
        )

        # Same fixture, but the fix candidate: an explicit lease on base.
        tmp2 = pathlib.Path(tempfile.mkdtemp(prefix="probe_a_lease_"))
        try:
            s2, r2, o2, b2, m2, a2 = build_three_commit_source(tmp2)
            marker2 = install_prepush_interposer(s2, r2, m2)
            leased = subprocess.run(
                ["git", "push", "--porcelain",
                 f"--force-with-lease={REF}:{b2}", o2, f"{a2}:{REF}"],
                cwd=str(s2), capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            lease_result = {
                "returncode": leased.returncode,
                "authorized_oid": a2,
                "interposed_oid": m2,
                "interposer_observed": (
                    marker2.read_text(encoding="utf-8").strip()
                    if marker2.exists() else None
                ),
                "remote_after": git(r2, "rev-parse", REF),
                "published_authorized_oid": (
                    git(r2, "rev-parse", REF) == a2
                ),
                "stale_info": "stale info" in (
                    leased.stdout + leased.stderr
                ).lower(),
            }
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

        return {
            "probe": "A_base_binding_enforced_at_push_time",
            "commits": {"base": base, "mid": mid, "authorized": authorized},
            "remote_at_preflight": remote_before,
            "interposed_oid": mid,
            "interposer_observed": observed_mid_push,
            "interposition_confirmed": observed_mid_push == mid,
            "remote_after": remote_after,
            "tool_returncode": proc.returncode,
            "tool_status": (receipt or {}).get("status"),
            "tool_ok": (receipt or {}).get("ok"),
            "tool_previous_remote_oid": (receipt or {}).get(
                "previous_remote_oid"
            ),
            "receipt_previous_matches_actual_pre_push_state": (
                (receipt or {}).get("previous_remote_oid") == mid
            ),
            "plain_push_accepted_unleased_state": (
                proc.returncode == 0 and remote_after == authorized
            ),
            "force_with_lease_on_same_fixture": lease_result,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_b_short_ref():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="probe_b_"))
    try:
        source, remote, origin, base, mid, authorized = (
            build_three_commit_source(tmp)
        )
        proc, receipt = run_tool(source, origin, "main", base, authorized)
        return {
            "probe": "B_short_branch_name_for_ref",
            "ref_passed": "main",
            "tool_returncode": proc.returncode,
            "tool_ok": (receipt or {}).get("ok"),
            "tool_reason": (receipt or {}).get("reason"),
            "tool_stage": (receipt or {}).get("stage"),
            "remote_after": git(remote, "rev-parse", REF),
            "remote_unchanged": git(remote, "rev-parse", REF) == base,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_d_replayed_outer_window():
    """The tool is, at bottom, two git calls: ls-remote then push.

    Probe A interposed *inside* git's own push (after ref advertisement), and
    a lease did not help there.  This probe interposes in the wider window
    that the tool actually owns -- between its preflight `ls-remote` and the
    start of `git push` -- by replaying those two calls by hand with a remote
    move in between.  Run twice: plain push, then the lease candidate.
    """
    out = {"probe": "D_outer_window_replayed_by_hand"}
    for variant in ("plain", "force_with_lease"):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"probe_d_{variant}_"))
        try:
            source, remote, origin, base, mid, authorized = (
                build_three_commit_source(tmp)
            )
            # Step 1: exactly the tool's preflight read.
            observed = git(source, "ls-remote", "--refs", origin, REF).split()[0]
            # Step 2: a concurrent pusher lands here.  Push, not update-ref:
            # the remote was cloned at base and lacks this object.
            git(source, "push", "-q", origin, f"{mid}:{REF}")
            interposed_state = git(remote, "rev-parse", REF)
            # Step 3: exactly the tool's push, with and without the lease.
            push_args = ["push", "--porcelain"]
            if variant == "force_with_lease":
                push_args.append(f"--force-with-lease={REF}:{base}")
            push_args += [origin, f"{authorized}:{REF}"]
            pushed = subprocess.run(
                ["git", *push_args], cwd=str(source), capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
            out[variant] = {
                "preflight_observed": observed,
                "preflight_equals_base": observed == base,
                "interposed_oid": mid,
                "remote_at_push_time": interposed_state,
                "interposition_confirmed": interposed_state == mid,
                "push_returncode": pushed.returncode,
                "remote_after": git(remote, "rev-parse", REF),
                "published_authorized_oid": (
                    git(remote, "rev-parse", REF) == authorized
                ),
                "stale_info": "stale info" in (
                    pushed.stdout + pushed.stderr
                ).lower(),
            }
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return out


def probe_c_help_contract():
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    parsed = True
    try:
        json.loads(proc.stdout)
    except ValueError:
        parsed = False
    return {
        "probe": "C_help_single_json_contract",
        "returncode": proc.returncode,
        "stdout_is_json": parsed,
        "stdout_first_line": proc.stdout.splitlines()[:1],
    }


if __name__ == "__main__":
    for result in (
        probe_a_lease_window(),
        probe_b_short_ref(),
        probe_d_replayed_outer_window(),
        probe_c_help_contract(),
    ):
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
