"""Run a local clean-HOME rehearsal without activating host runtime services."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANAGER = HERE / "release_installer.py"
MANIFEST = HERE / "install-manifest.json"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _run(arguments: list[str], env: dict[str, str]) -> dict:
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, str(MANAGER), *arguments],
        cwd=REPO,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
    )
    try:
        payload = json.loads(completed.stdout.lstrip("\ufeff"))
    except json.JSONDecodeError:
        payload = {"status": "invalid_json", "stdout": completed.stdout}
    return {
        "arguments": arguments,
        "exit_code": completed.returncode,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "payload": payload,
        "stderr": completed.stderr,
    }


def rehearse() -> dict:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="weilan-clean-home-") as temporary:
        root = Path(temporary).resolve()
        home = root / "home"
        codex_home = root / "codex-home"
        method_home = root / "method-state"
        install_root = root / "install"
        for directory in (home, codex_home, method_home):
            directory.mkdir(parents=True)

        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(codex_home),
                "WEILAN_METHOD_HOME": str(method_home),
            }
        )
        common = ["--install-root", str(install_root)]
        steps = [
            _run(
                [
                    "install",
                    "--repo-root",
                    str(REPO),
                    *common,
                    "--manifest",
                    str(MANIFEST),
                ],
                env,
            ),
            _run(["status", *common], env),
            _run(["entry", "--name", "start", *common, "--smoke"], env),
            _run(["entry", "--name", "open-dashboard", *common, "--smoke"], env),
            _run(["entry", "--name", "stop", *common, "--smoke"], env),
            _run(["uninstall", *common], env),
            _run(["uninstall", *common], env),
        ]
        expected = ["installed", "healthy", "smoke_pass", "smoke_pass", "smoke_pass", "uninstalled", "already_absent"]
        observed = [
            step["payload"].get("status", step["payload"].get("state"))
            for step in steps
        ]
        all_paths_isolated = all(
            _inside(path, root)
            for path in (home, codex_home, method_home, install_root)
        )
        no_runtime_activation = all(
            step["payload"].get("runtime_activation_performed") is False
            for step in steps[2:5]
        )
        passed = (
            all(step["exit_code"] == 0 for step in steps)
            and observed == expected
            and all_paths_isolated
            and no_runtime_activation
            and not install_root.exists()
        )
        return {
            "schema": "weilan_local_clean_home_rehearsal_v0.1",
            "verdict": "PASS" if passed else "FAIL",
            "claim_level": "LOCAL_CLEAN_HOME_ONLY",
            "clean_machine_acceptance": False,
            "boundary": "Current-host isolated HOME rehearsal only; not a clean Windows account or clean machine, not a timed release acceptance result.",
            "runtime_activation_performed": False,
            "all_state_paths_inside_temporary_root": all_paths_isolated,
            "temporary_install_removed": not install_root.exists(),
            "observed_statuses": observed,
            "expected_statuses": expected,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "steps": steps,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, help="Optional path for the labeled JSON receipt")
    args = parser.parse_args(argv)
    result = rehearse()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

