"""Executable contract for process-local canonical workspace resolution."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import runtime_core


def test_same_expanded_path_is_resolved_once_per_process(monkeypatch, tmp_path):
    """Behavioral discriminator that does not depend on cache-control symbols."""

    key = str(tmp_path / "contract-input")
    calls = []

    def parent_resolve(path):
        calls.append(str(path))
        return Path(f"{path}-parent-resolution-{len(calls)}")

    monkeypatch.setattr(runtime_core.Path, "resolve", parent_resolve)

    first = runtime_core.canonical_workspace(key)
    second = runtime_core.canonical_workspace(key)

    assert first == second, (
        "the same expanded path must retain its first resolution within one process"
    )
    assert calls == [key]


@pytest.mark.skipif(
    not hasattr(runtime_core, "clear_canonical_workspace_cache"),
    reason="the no-contract baseline has no explicit cache-clear boundary",
)
def test_explicit_clear_and_new_process_resolution(monkeypatch, tmp_path):
    key = str(tmp_path / "clear-and-child-input")
    calls = []

    def parent_resolve(path):
        calls.append(str(path))
        return Path(f"{path}-parent-resolution-{len(calls)}")

    runtime_core.clear_canonical_workspace_cache()
    monkeypatch.setattr(runtime_core.Path, "resolve", parent_resolve)

    first = runtime_core.canonical_workspace(key)
    assert "A new process resolves it again" in runtime_core.CANONICAL_WORKSPACE_CACHE_CONTRACT

    runtime_core.clear_canonical_workspace_cache()
    after_explicit_clear = runtime_core.canonical_workspace(key)
    assert after_explicit_clear != first
    assert calls == [key, key]

    child_code = textwrap.dedent(
        """
        import sys
        from pathlib import Path

        def child_resolve(path):
            return Path(f"{path}-child-resolution")

        Path.resolve = child_resolve
        sys.path.insert(0, sys.argv[1])
        import runtime_core
        print(runtime_core.canonical_workspace(sys.argv[2]))
        """
    )
    child = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", child_code, str(Path(__file__).parent), key],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == f"{key}-child-resolution"
