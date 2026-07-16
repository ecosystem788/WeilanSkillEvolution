from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
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


def main() -> int:
    live_skills = configured_live_skills()
    live_before = {str(path): tree_hash(path) for path in live_skills}
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
        entry_results = {
            "install": run_entry(root, "install"),
            "start": run_entry(root, "start", "-Smoke"),
            "stop": run_entry(root, "stop", "-Smoke"),
            "status": run_entry(root, "status"),
            "open-dashboard": run_entry(root, "open-dashboard", "-Smoke"),
        }
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
    checks = {
        "manifest_hash_closure": closure,
        "five_entrypoints_smoke": all(
            result.get("status") in ("installed", "smoke_pass") or result.get("state") == "healthy"
            for result in entry_results.values()
        ),
        "status_explains_activation_boundary": bool(entry_results["status"].get("runtime_activation_boundary")),
        "setup_entry_succeeded": setup_rc == 0 and setup_repeat_rc == 0,
        "clean_uninstall": clean_uninstall_rc == 0 and clean_uninstall["status"] == "uninstalled",
        "uninstall_idempotent": repeated_uninstall["status"] == "already_absent",
        "sentinel_preserved": sentinel_after_clean and sentinel_after_drift,
        "drift_refused_with_nonzero_exit": drift_uninstall_rc != 0 and drift_uninstall["status"] == "conflict" and drift_relative.as_posix() in drift_uninstall["conflicts"],
        "drifted_file_preserved": drift_preserved,
        "live_skills_unchanged": live_before == live_after,
        "runtime_activation_not_claimed": all(
            not entry_results[name].get("runtime_activation_performed", False)
            for name in ("start", "stop", "open-dashboard")
        ),
    }
    receipt = {
        "schema": "weilan_install_ownership_acceptance_receipt_v0.1",
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "verdict": "PASS_WITH_RUNTIME_BOUNDARY" if all(checks.values()) else "FAIL",
        "source_manifest": str(HERE / "install-manifest.json"),
        "owned_file_count": installed["owned_file_count"],
        "checks": checks,
        "entry_results": entry_results,
        "drift_conflicts": drift_uninstall["conflicts"],
        "live_skills_before": live_before,
        "live_skills_after": live_after,
        "live_skill_guard": {
            "configured": bool(live_skills),
            "source": "WEILAN_LIVE_SKILL_PATHS",
        },
        "boundary": "Ownership/install/uninstall and five-entry smoke are closed. Real scheduler/dashboard activation is intentionally refused until machine-specific runtime paths are removed and independently reviewed.",
        "signature": None,
        "adopted": False,
        "deployed": False,
    }
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["verdict"] == "PASS_WITH_RUNTIME_BOUNDARY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
