import subprocess
import sys

import helper_lint


def _write(path, content=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_tree(tmp_path, complete=True):
    impl = tmp_path / "impl"
    helper = impl / "append_clocked_jsonl.py"
    if complete:
        _write(
            helper,
            '"""docstring --wake-agent contract"""\n--wake-true --wake-agent\n',
        )
    else:
        _write(helper, "no wake flags")
    for name in ("wake_prompt.md", "wake_prompt_codex.md"):
        _write(impl / name, "text with --wake-true and --wake-agent")
    watcher = impl / "watcher"
    _write(watcher / "watcher_sentinel.py", "DEFAULT_COOLDOWN_SECONDS = 30.0\n")
    _write(
        watcher / "README.md",
        "watcher-sentinel-skill-evolution watcher-skill-evolution.pid "
        "watcher-skill-evolution-start.ps1 fail-closed",
    )
    _write(watcher / "watcher_stats.jsonl", "")
    return impl


def test_helper_lint_passes_on_complete_tree(tmp_path):
    impl = _build_tree(tmp_path, complete=True)
    summary = helper_lint.check_contract(impl)
    assert summary["ok"] is True
    assert summary["failure_count"] == 0


def test_helper_lint_fails_when_wake_flags_missing(tmp_path):
    impl = _build_tree(tmp_path, complete=False)
    summary = helper_lint.check_contract(impl)
    assert summary["ok"] is False
    names = [item["name"] for item in summary["findings"] if not item["ok"]]
    assert "helper_has_wake_flags" in names
    assert "helper_docstring_sync" in names


def test_helper_lint_cli_exit_codes(tmp_path):
    good = _build_tree(tmp_path / "good", complete=True)
    ok_run = subprocess.run(
        [sys.executable, helper_lint.__file__, "--root", str(good)],
        capture_output=True, text=True,
    )
    assert ok_run.returncode == 0
    bad = _build_tree(tmp_path / "bad", complete=False)
    bad_run = subprocess.run(
        [sys.executable, helper_lint.__file__, "--root", str(bad)],
        capture_output=True, text=True,
    )
    assert bad_run.returncode == 1
