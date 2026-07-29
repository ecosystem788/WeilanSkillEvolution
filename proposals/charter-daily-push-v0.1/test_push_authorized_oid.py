"""Local end-to-end tests for push_authorized_oid.py.

Every remote is a temporary file:// bare repository.
"""

import json
import pathlib
import runpy
import subprocess
import sys


TOOL = pathlib.Path(__file__).with_name("push_authorized_oid.py")
REF = "refs/heads/main"


def git(repo, *args, input=None):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input,
        check=True,
        capture_output=True,
    ).stdout


def write(repo, relative_path, text):
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").decode().strip()


def configure_identity(repo):
    git(repo, "config", "user.email", "push-test@local")
    git(repo, "config", "user.name", "push-test")


def initialize(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-q", ".")
    configure_identity(source)
    write(source, "value.txt", "base\n")
    base = commit(source, "base")
    git(source, "branch", "-M", "main")

    remote = tmp_path / "remote.git"
    git(tmp_path, "clone", "-q", "--bare", str(source), str(remote))
    origin = remote.resolve().as_uri()

    write(source, "value.txt", "authorized\n")
    authorized_oid = commit(source, "authorized")
    return source, remote, origin, base, authorized_oid


def run_tool(source, origin, base, authorized_oid):
    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--origin",
            origin,
            "--ref",
            REF,
            "--base",
            base,
            "--authorized-oid",
            authorized_oid,
        ],
        cwd=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc, json.loads(proc.stdout)


def remote_head(remote):
    return git(remote, "rev-parse", REF).decode().strip()


def test_normal_fast_forward_push(tmp_path):
    source, remote, origin, base, authorized_oid = initialize(tmp_path)

    proc, receipt = run_tool(source, origin, base, authorized_oid)

    assert proc.returncode == 0
    assert proc.stderr == ""
    assert receipt["ok"] is True
    assert receipt["status"] == "pushed_and_verified"
    assert receipt["push_performed"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["remote_oid"] == authorized_oid
    assert remote_head(remote) == authorized_oid


def test_push_argv_binds_exact_preflight_base():
    push_argv = runpy.run_path(str(TOOL))["push_argv"]

    assert push_argv("origin", REF, "base", "authorized") == (
        "push",
        "--porcelain",
        f"--force-with-lease={REF}:base",
        "origin",
        f"authorized:{REF}",
    )


def test_remote_base_drift_refuses_push(tmp_path):
    source, remote, origin, base, authorized_oid = initialize(tmp_path)
    drifter = tmp_path / "drifter"
    git(tmp_path, "clone", "-q", origin, str(drifter))
    configure_identity(drifter)
    write(drifter, "drift.txt", "remote drift\n")
    drift_oid = commit(drifter, "remote drift")
    git(drifter, "push", "-q", "origin", f"HEAD:{REF}")

    proc, receipt = run_tool(source, origin, base, authorized_oid)

    assert proc.returncode == 1
    assert receipt["ok"] is False
    assert receipt["reason"] == "remote_base_mismatch"
    assert receipt["observed_remote_oid"] == drift_oid
    assert remote_head(remote) == drift_oid


def test_repeat_call_is_idempotent(tmp_path):
    source, remote, origin, base, authorized_oid = initialize(tmp_path)
    first_proc, first_receipt = run_tool(
        source, origin, base, authorized_oid
    )

    second_proc, second_receipt = run_tool(
        source, origin, base, authorized_oid
    )

    assert first_proc.returncode == 0
    assert first_receipt["status"] == "pushed_and_verified"
    assert second_proc.returncode == 0
    assert second_proc.stderr == ""
    assert second_receipt["ok"] is True
    assert second_receipt["status"] == "already_at_authorized_head"
    assert second_receipt["push_performed"] is False
    assert second_receipt["remote_oid"] == authorized_oid
    assert remote_head(remote) == authorized_oid


def test_non_fast_forward_refuses_push(tmp_path):
    source, remote, origin, base, _ = initialize(tmp_path)
    tree = git(source, "rev-parse", f"{base}^{{tree}}").decode().strip()
    sibling_oid = git(
        source,
        "commit-tree",
        tree,
        input=b"sibling without base parent\n",
    ).decode().strip()

    proc, receipt = run_tool(source, origin, base, sibling_oid)

    assert proc.returncode == 1
    assert receipt["ok"] is False
    assert receipt["reason"] == "non_fast_forward"
    assert receipt["base"] == base
    assert receipt["authorized_oid"] == sibling_oid
    assert remote_head(remote) == base
