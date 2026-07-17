from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

import release_installer as installer


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUTPUT = HERE / "INSTALL_OWNERSHIP_RECEIPT.json"


def configured_live_skills() -> tuple[Path, ...]:
    """Return only caller-declared live trees; never embed machine paths."""
    raw = os.environ.get("WEILAN_LIVE_SKILL_PATHS", "")
    return tuple(Path(item) for item in raw.split(os.pathsep) if item)


def tree_hash(root: Path) -> dict:
    if not root.is_dir():
        return {"exists": False, "file_count": 0, "sha256": None}
    digest = hashlib.sha256()
    count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content_hash = bytes.fromhex(installer.sha256_file(path))
        digest.update(content_hash)
        count += 1
    return {"exists": True, "file_count": count, "sha256": digest.hexdigest()}


def run_entry(root: Path, name: str, *extra: str) -> dict:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "bin" / f"{name}.ps1"), *extra],
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{name} rc={completed.returncode}: {completed.stdout}\n{completed.stderr}")
    return json.loads(completed.stdout.lstrip("\ufeff"))


def run_script(script: Path, *arguments: str) -> tuple[int, dict]:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *arguments],
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    return completed.returncode, json.loads(completed.stdout.lstrip("\ufeff"))


def product_tasks() -> set[str]:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "@(Get-ScheduledTask -TaskName 'WeilanScheduler-*' -ErrorAction SilentlyContinue | ForEach-Object TaskName)|ConvertTo-Json -Compress"],
        text=True, encoding="utf-8", capture_output=True, timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    value = json.loads(completed.stdout.strip().lstrip("\ufeff") or "[]")
    return {value} if isinstance(value, str) else set(value or [])


def redact_paths(value, replacements: tuple[tuple[str, str], ...]):
    if isinstance(value, dict):
        return {key: redact_paths(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_paths(item, replacements) for item in value]
    if isinstance(value, str):
        for source, replacement in replacements:
            value = value.replace(source, replacement)
        return value
    return value


def main() -> int:
    live_skills = configured_live_skills()
    live_before = {str(path): tree_hash(path) for path in live_skills}
    product_tasks_before = product_tasks()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "fake-home"
        root.mkdir()
        sentinel = root / "outside-owner.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        setup_rc, installed = run_script(HERE / "setup.ps1", "-InstallRoot", str(root))
        if setup_rc != 0:
            raise RuntimeError(f"setup.ps1 rc={setup_rc}: {installed}")
        if installed["status"] != "installed":
            raise RuntimeError(str(installed))
        closure = all(
            installer.sha256_file(root / Path(item["path"])) == item["sha256"]
            for item in installed["owned_files"]
        )
        runtime = installer._runtime_module(root)
        task_name = f"WeilanReleaseTest-{uuid.uuid4().hex}"
        ticks = root / "data" / "runtime" / "scheduler-ticks.jsonl"
        try:
            entry_results = {
                "install": run_entry(root, "install"),
                "start": run_entry(root, "start", "-TickOnly", "-TaskName", task_name),
            }
            runtime.trigger_task(task_name)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not ticks.is_file():
                time.sleep(0.25)
            entry_results["open-dashboard"] = run_entry(root, "open-dashboard", "-Port", "0")
            entry_results["status"] = run_entry(root, "status")
            entry_results["stop"] = run_entry(root, "stop")
            entry_results["stop_again"] = run_entry(root, "stop")
        finally:
            runtime.stop(root)
        tick_receipt = json.loads(ticks.read_text(encoding="utf-8").splitlines()[-1]) if ticks.is_file() else None
        clean_uninstall_rc, clean_uninstall = run_script(root / "bin" / "uninstall.ps1")
        sentinel_after_clean = sentinel.read_text(encoding="utf-8") == "preserve"
        repeated_uninstall = installer.uninstall(root)

        setup_repeat_rc, reinstalled = run_script(HERE / "setup.ps1", "-InstallRoot", str(root))
        drift_relative = Path(reinstalled["owned_files"][0]["path"])
        drift_target = root / drift_relative
        drift_target.write_bytes(drift_target.read_bytes() + b"\nuser drift\n")
        drift_uninstall_rc, drift_uninstall = run_script(root / "bin" / "uninstall.ps1")
        drift_preserved = drift_target.exists()
        sentinel_after_drift = sentinel.read_text(encoding="utf-8") == "preserve"

    live_after = {str(path): tree_hash(path) for path in live_skills}
    product_tasks_after = product_tasks()
    checks = {
        "manifest_hash_closure": closure,
        "five_entrypoints_real_lifecycle": (
            entry_results["start"].get("status") == "running"
            and entry_results["open-dashboard"].get("status") == "running"
            and entry_results["status"].get("runtime", {}).get("task_registered")
            and entry_results["status"].get("runtime", {}).get("dashboard", {}).get("live")
            and entry_results["stop"].get("status") == "stopped"
            and entry_results["stop_again"].get("status") == "stopped"
        ),
        "real_task_tick_receipt": bool(tick_receipt and tick_receipt.get("outcome") in ("nothing_due", "no_agent_configured")),
        "product_task_baseline_unchanged": product_tasks_before == product_tasks_after,
        "setup_entry_succeeded": setup_rc == 0 and setup_repeat_rc == 0,
        "clean_uninstall": clean_uninstall_rc == 0 and clean_uninstall["status"] == "uninstalled",
        "uninstall_idempotent": repeated_uninstall["status"] == "already_absent",
        "sentinel_preserved": sentinel_after_clean and sentinel_after_drift,
        "drift_refused_with_nonzero_exit": drift_uninstall_rc != 0 and drift_uninstall["status"] == "conflict" and drift_relative.as_posix() in drift_uninstall["conflicts"],
        "drifted_file_preserved": drift_preserved,
        "live_skills_unchanged": live_before == live_after,
        "runtime_activation_verified": all(
            entry_results[name].get("runtime_activation_performed", False)
            for name in ("start", "stop", "open-dashboard")
        ),
    }
    replacements = (
        (str(root), "<isolated-install>"),
        (str(REPO), "<repo-root>"),
        (str(Path(sys.executable)), "<python-executable>"),
    )
    receipt = {
        "schema": "weilan_install_ownership_acceptance_receipt_v0.1",
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "source_manifest": "proposals/public-release-consolidation-v0.1/install-manifest.json",
        "owned_file_count": installed["owned_file_count"],
        "checks": checks,
        "entry_results": redact_paths(entry_results, replacements),
        "tick_receipt": tick_receipt,
        "drift_conflicts": drift_uninstall["conflicts"],
        "live_skills_before": live_before,
        "live_skills_after": live_after,
        "live_skill_guard": {
            "configured": bool(live_skills),
            "source": "WEILAN_LIVE_SKILL_PATHS",
        },
        "boundary": "Current-host isolated lifecycle evidence only; clean-machine timing, adoption, deployment, publication, and R15 independent final audit remain open.",
        "signature": None,
        "adopted": False,
        "deployed": False,
    }
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
