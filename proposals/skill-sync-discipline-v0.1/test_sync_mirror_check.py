#!/usr/bin/env python3
"""Tests for sync_mirror_check.py.

Run from the proposal directory:
    python -m pytest test_sync_mirror_check.py -v

Or directly:
    python test_sync_mirror_check.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import sync_mirror_check as smc


def test_sha256_bytes():
    assert smc.sha256_bytes(b"hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_classify_live_only():
    assert smc.classify_live_only("__pycache__")[0] is True
    assert smc.classify_live_only(".pytest_cache")[0] is True
    assert smc.classify_live_only("foo.pyc")[0] is True
    assert smc.classify_live_only("weilan_trace.py.pre-three-state-v1.bak")[0] is True
    assert smc.classify_live_only("foo.tmp")[0] is True
    assert smc.classify_live_only("weilan_trace.py")[0] is False
    assert smc.classify_live_only("test_extra.py")[0] is False


def _setup_repo_and_live(tmpdir, files_in_repo, files_in_live):
    """Create a temp git repo and a temp live dir with the given files.

    files_in_*: dict {basename: bytes_content}
    Returns (repo_root, live_root).
    """
    repo_root = os.path.join(tmpdir, "repo")
    live_root = os.path.join(tmpdir, "live")
    os.makedirs(repo_root)
    os.makedirs(live_root)
    # git init
    subprocess.run(["git", "init", "-q", repo_root], check=True)
    subprocess.run(
        ["git", "-C", repo_root, "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", repo_root, "config", "user.name", "test"], check=True
    )
    subtree = "skill/scripts"
    os.makedirs(os.path.join(repo_root, subtree))
    for name, content in files_in_repo.items():
        path = os.path.join(repo_root, subtree, name)
        with open(path, "wb") as f:
            f.write(content)
    # commit
    subprocess.run(["git", "-C", repo_root, "add", subtree], check=True)
    subprocess.run(
        ["git", "-C", repo_root, "commit", "-q", "-m", "init"], check=True
    )
    # populate live
    for name, content in files_in_live.items():
        path = os.path.join(live_root, name)
        with open(path, "wb") as f:
            f.write(content)
    return repo_root, live_root, subtree


def test_check_ok():
    with tempfile.TemporaryDirectory() as tmp:
        content = b"hello world\n"
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": content, "b.py": content}, {"a.py": content, "b.py": content}
        )
        result = smc.check(repo, live, subtree)
        assert result["ok"] is True
        assert sorted(result["matches"]) == ["a.py", "b.py"]
        assert result["mismatches"] == []
        assert result["head_only"] == []
        assert result["live_only_unexpected"] == []


def test_check_byte_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp,
            {"a.py": b"from-mirror\n"},
            {"a.py": b"from-live\n"},
        )
        result = smc.check(repo, live, subtree)
        assert result["ok"] is False
        assert result["mismatches"] == ["a.py"]
        assert result["matches"] == []


def test_check_head_only():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": b"x\n", "extra.py": b"y\n"}, {"a.py": b"x\n"}
        )
        result = smc.check(repo, live, subtree)
        assert result["ok"] is False
        assert result["head_only"] == ["extra.py"]


def test_check_live_only_whitelisted():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": b"x\n"}, {"a.py": b"x\n", "__pycache__": b"", "foo.pyc": b""}
        )
        # Create __pycache__ as a directory in live; the checker only looks at files,
        # so we need to instead create the file entries.
        # Remove the bogus "__pycache__" file and ".pyc" file entries:
        os.remove(os.path.join(live, "__pycache__"))
        os.remove(os.path.join(live, "foo.pyc"))
        result = smc.check(repo, live, subtree)
        assert result["ok"] is True
        assert result["live_only_whitelisted"] == []
        # The whitelist path needs files (not dirs) — make a real file with that name
        # to verify suffix whitelist:
        with open(os.path.join(live, "x.bak"), "wb") as f:
            f.write(b"backup")
        result = smc.check(repo, live, subtree)
        assert result["ok"] is True
        assert any(
            e["path"] == "x.bak" for e in result["live_only_whitelisted"]
        )


def test_check_live_only_unexpected():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": b"x\n"}, {"a.py": b"x\n", "drift.py": b"y\n"}
        )
        result = smc.check(repo, live, subtree)
        assert result["ok"] is False
        assert result["live_only_unexpected"] == ["drift.py"]


def test_main_returns_1_on_drift():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": b"mirror\n"}, {"a.py": b"live\n"}
        )
        rc = subprocess.run(
            [
                sys.executable,
                os.path.join(HERE, "sync_mirror_check.py"),
                "--repo-root",
                repo,
                "--live-root",
                live,
                "--subtree",
                subtree,
            ],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        assert rc == 1, f"expected rc=1 on drift, got {rc}"


def test_main_returns_0_on_ok():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": b"same\n"}, {"a.py": b"same\n"}
        )
        rc = subprocess.run(
            [
                sys.executable,
                os.path.join(HERE, "sync_mirror_check.py"),
                "--repo-root",
                repo,
                "--live-root",
                live,
                "--subtree",
                subtree,
            ],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        assert rc == 0, f"expected rc=0 on ok, got {rc}; stderr: see output"


def test_main_json_output_is_valid():
    with tempfile.TemporaryDirectory() as tmp:
        repo, live, subtree = _setup_repo_and_live(
            tmp, {"a.py": b"same\n"}, {"a.py": b"same\n"}
        )
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(HERE, "sync_mirror_check.py"),
                "--repo-root",
                repo,
                "--live-root",
                live,
                "--subtree",
                subtree,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        parsed = json.loads(proc.stdout)
        assert "ok" in parsed
        assert "matches" in parsed
        assert "mismatches" in parsed
        assert "head_only" in parsed
        assert "live_only_unexpected" in parsed


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
