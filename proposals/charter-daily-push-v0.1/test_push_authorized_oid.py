"""Local end-to-end tests for push_authorized_oid.py.

Every remote is a temporary file:// bare repository.
"""

import json
import importlib.util
import pathlib
import runpy
import subprocess
import sys

import pytest


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


def load_tool_module():
    spec = importlib.util.spec_from_file_location(
        "push_authorized_oid_under_test", TOOL
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normal_fast_forward_push(tmp_path):
    source, remote, origin, base, authorized_oid = initialize(tmp_path)

    proc, receipt = run_tool(source, origin, base, authorized_oid)

    assert proc.returncode == 0
    assert proc.stderr == ""
    assert receipt["ok"] is True
    assert receipt["status"] == "pushed_and_verified"
    assert receipt["push_attempted"] is True
    assert receipt["push_performed"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["remote_oid"] == authorized_oid
    assert receipt["push_report"] == {
        "flag": " ",
        "source_oid": authorized_oid,
        "destination_ref": REF,
        "summary": receipt["push_report"]["summary"],
        "summary_authority": (
            "git_process_self_report_not_remote_observation"
        ),
    }
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


def test_fail_requires_explicit_push_attempted_without_emitting(capsys):
    fail = runpy.run_path(str(TOOL))["fail"]

    with pytest.raises(TypeError):
        fail("missing_push_attempted", stage="test")

    assert capsys.readouterr().out == ""


def test_parse_push_porcelain_accepts_exact_safe_status_shapes():
    parse = runpy.run_path(str(TOOL))["parse_push_porcelain"]
    oid = "a" * 40

    success = parse(
        f"To file://credential@example.invalid/repo\n"
        f" \t{oid}:{REF}\t1234567..abcdef0\nDone\n",
        oid,
        REF,
    )
    rejected = parse(
        f"!\t{oid}:{REF}\t[rejected] (stale info)\n", oid, REF
    )

    assert success == {
        "flag": " ",
        "source_oid": oid,
        "destination_ref": REF,
        "summary": "1234567..abcdef0",
        "summary_authority": (
            "git_process_self_report_not_remote_observation"
        ),
    }
    assert "credential" not in json.dumps(success)
    assert rejected["flag"] == "!"
    assert rejected["summary"] == "[rejected] (stale info)"


def test_parse_push_porcelain_rejects_missing_ambiguous_or_wrong_records():
    parse = runpy.run_path(str(TOOL))["parse_push_porcelain"]
    oid = "a" * 40
    exact = f" \t{oid}:{REF}\told..new"

    assert parse("To origin\nDone\n", oid, REF) is None
    assert parse(f"{exact}\n{exact}\n", oid, REF) is None
    assert parse(
        f" \t{'b' * 40}:{REF}\told..new\n", oid, REF
    ) is None
    assert parse(
        f" \t{oid}:refs/heads/other\told..new\n", oid, REF
    ) is None


def scripted_git(module, post_oid, push_stdout):
    base = "a" * 40
    authorized_oid = "b" * 40
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify"):
            value = args[2].removesuffix("^{commit}")
            return subprocess.CompletedProcess(args, 0, value + "\n", "")
        if args[:2] == ("merge-base", "--is-ancestor"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "ls-remote":
            observed = base if len(
                [call for call in calls if call[0] == "ls-remote"]
            ) == 1 else post_oid
            return subprocess.CompletedProcess(
                args, 0, f"{observed}\t{REF}\n", ""
            )
        if args[0] == "push":
            return subprocess.CompletedProcess(args, 0, push_stdout, "")
        raise AssertionError(args)

    module.git = fake_git
    return base, authorized_oid, calls


def scripted_receipt(
    module,
    capsys,
    ls_remote_outputs,
    *,
    push_returncode=0,
    push_stdout="",
):
    base = "a" * 40
    authorized_oid = "b" * 40
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify"):
            value = args[2].removesuffix("^{commit}")
            return subprocess.CompletedProcess(args, 0, value + "\n", "")
        if args[:2] == ("merge-base", "--is-ancestor"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "ls-remote":
            index = len(
                [call for call in calls if call[0] == "ls-remote"]
            ) - 1
            returncode, stdout = ls_remote_outputs[index]
            return subprocess.CompletedProcess(
                args, returncode, stdout, ""
            )
        if args[0] == "push":
            return subprocess.CompletedProcess(
                args, push_returncode, push_stdout, ""
            )
        raise AssertionError(args)

    module.git = fake_git
    returncode = module.main(
        [
            "--origin",
            "redacted-origin",
            "--ref",
            REF,
            "--base",
            base,
            "--authorized-oid",
            authorized_oid,
        ]
    )
    receipt = json.loads(capsys.readouterr().out)
    return returncode, receipt, calls, base, authorized_oid


def test_preflight_remote_read_failure_is_before_push(capsys):
    module = load_tool_module()

    returncode, receipt, calls, _, _ = scripted_receipt(
        module, capsys, [(128, "")]
    )

    assert returncode == 1
    assert receipt["reason"] == "ls_remote_failed"
    assert receipt["stage"] == "preflight_remote_read"
    assert receipt["push_attempted"] is False
    assert receipt["remote_read_returncode"] == 128
    assert "git_returncode" not in receipt
    assert "push_performed" not in receipt
    assert not [call for call in calls if call[0] == "push"]


@pytest.mark.parametrize(
    ("reason", "post_returncode", "post_stdout"),
    [
        ("ls_remote_failed", 128, ""),
        ("remote_ref_missing", 0, ""),
        (
            "remote_ref_ambiguous",
            0,
            f"{'a' * 40}\t{REF}\n{'b' * 40}\t{REF}\n",
        ),
    ],
)
def test_post_push_remote_read_failures_preserve_push_context(
    capsys, reason, post_returncode, post_stdout
):
    accepted_push = f" \t{'b' * 40}:{REF}\t1234567..abcdef0\n"

    pre_module = load_tool_module()
    _, pre_receipt, _, base, authorized_oid = scripted_receipt(
        pre_module, capsys, [(post_returncode, post_stdout)]
    )
    post_module = load_tool_module()
    returncode, receipt, calls, _, _ = scripted_receipt(
        post_module,
        capsys,
        [
            (0, f"{base}\t{REF}\n"),
            (post_returncode, post_stdout),
        ],
        push_stdout=accepted_push,
    )

    assert returncode == 1
    assert receipt["reason"] == reason
    assert receipt["stage"] == "post_push_remote_read"
    assert receipt["push_attempted"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["authorized_oid"] == authorized_oid
    assert receipt["push_returncode"] == 0
    assert receipt["push_report"]["source_oid"] == authorized_oid
    assert "push_performed" not in receipt
    assert receipt != pre_receipt
    assert len([call for call in calls if call[0] == "push"]) == 1
    if reason == "ls_remote_failed":
        assert receipt["remote_read_returncode"] == 128
        assert "git_returncode" not in receipt
    if reason == "remote_ref_ambiguous":
        assert receipt["match_count"] == 2


def test_git_push_failure_records_attempt_and_preflight(capsys):
    module = load_tool_module()
    rejected_push = f"!\t{'b' * 40}:{REF}\t[rejected] (stale info)\n"

    returncode, receipt, calls, base, _ = scripted_receipt(
        module,
        capsys,
        [(0, f"{'a' * 40}\t{REF}\n")],
        push_returncode=1,
        push_stdout=rejected_push,
    )

    assert returncode == 1
    assert receipt["reason"] == "git_push_failed"
    assert receipt["stage"] == "push"
    assert receipt["push_attempted"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["push_returncode"] == 1
    assert receipt["git_returncode"] == 1
    assert "push_performed" not in receipt
    assert len([call for call in calls if call[0] == "push"]) == 1


def test_post_mismatch_outranks_unparseable_push_report(capsys):
    module = load_tool_module()
    drift_oid = "c" * 40
    base, authorized_oid, calls = scripted_git(
        module, drift_oid, "To credential@example.invalid/repo\nDone\n"
    )

    returncode = module.main(
        [
            "--origin",
            "redacted-origin",
            "--ref",
            REF,
            "--base",
            base,
            "--authorized-oid",
            authorized_oid,
        ]
    )
    receipt = json.loads(capsys.readouterr().out)

    assert returncode == 1
    assert receipt["reason"] == "post_push_ref_mismatch"
    assert receipt["push_attempted"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["push_returncode"] == 0
    assert "push_performed" not in receipt
    assert receipt["observed_remote_oid"] == drift_oid
    assert receipt["push_report_status"] == "unparseable"
    assert "stdout_replacement_decoded_utf8_sha256" in receipt
    assert "credential" not in json.dumps(receipt)
    assert len([call for call in calls if call[0] == "ls-remote"]) == 2


def test_post_mismatch_preserves_accepted_push_report(capsys):
    module = load_tool_module()
    drift_oid = "c" * 40
    expected_authorized_oid = "b" * 40
    push_stdout = (
        f" \t{expected_authorized_oid}:{REF}\t1234567..abcdef0\n"
    )
    base, authorized_oid, calls = scripted_git(
        module, drift_oid, push_stdout
    )

    returncode = module.main(
        [
            "--origin",
            "redacted-origin",
            "--ref",
            REF,
            "--base",
            base,
            "--authorized-oid",
            authorized_oid,
        ]
    )
    receipt = json.loads(capsys.readouterr().out)

    assert returncode == 1
    assert receipt["reason"] == "post_push_ref_mismatch"
    assert receipt["push_attempted"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["push_returncode"] == 0
    assert "push_performed" not in receipt
    assert receipt["observed_remote_oid"] == drift_oid
    assert receipt["push_report"] == {
        "flag": " ",
        "source_oid": authorized_oid,
        "destination_ref": REF,
        "summary": "1234567..abcdef0",
        "summary_authority": (
            "git_process_self_report_not_remote_observation"
        ),
    }
    assert "push_report_status" not in receipt
    assert len([call for call in calls if call[0] == "ls-remote"]) == 2


def test_unparseable_report_fails_after_matching_post_read(capsys):
    module = load_tool_module()
    authorized_oid = "b" * 40
    base, authorized_oid, calls = scripted_git(
        module, authorized_oid, "To redacted-origin\nDone\n"
    )

    returncode = module.main(
        [
            "--origin",
            "redacted-origin",
            "--ref",
            REF,
            "--base",
            base,
            "--authorized-oid",
            authorized_oid,
        ]
    )
    receipt = json.loads(capsys.readouterr().out)

    assert returncode == 1
    assert receipt["reason"] == "push_porcelain_unparseable"
    assert receipt["push_attempted"] is True
    assert receipt["preflight_remote_oid"] == base
    assert receipt["push_returncode"] == 0
    assert "push_performed" not in receipt
    assert receipt["observed_remote_oid"] == authorized_oid
    assert receipt["push_report_status"] == "unparseable"
    assert len([call for call in calls if call[0] == "ls-remote"]) == 2


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
    assert receipt["push_attempted"] is False
    assert "push_performed" not in receipt
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
    assert second_receipt["push_attempted"] is False
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
    assert receipt["push_attempted"] is False
    assert "push_performed" not in receipt
    assert receipt["base"] == base
    assert receipt["authorized_oid"] == sibling_oid
    assert remote_head(remote) == base
