"""Manifest-owned, proposal-local release installer candidate.

This module deliberately owns installation and rollback only.  The generated
start/stop/open-dashboard commands expose a smoke contract but refuse real
runtime activation until the scheduler's machine-specific paths are removed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "install-manifest.json"
RECEIPT_NAME = "install-receipt.json"
REQUIRED_COMMANDS = {
    "python": "Install Python 3 and ensure 'python' is available on PATH.",
    "codex": "Install Codex and ensure 'codex' is available on PATH.",
    "claude": "Install Claude Code and ensure 'claude' is available on PATH.",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> Path:
    pure = PurePosixPath(value.replace("\\", "/"))
    windows = PureWindowsPath(value)
    if (
        pure.is_absolute()
        or windows.drive
        or windows.root
        or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise ValueError(f"unsafe relative path: {value!r}")
    return Path(*pure.parts)


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "weilan_release_install_manifest_v0.1":
        raise ValueError("unsupported install manifest schema")
    entries = data.get("entrypoints")
    if entries != ["install", "start", "stop", "status", "open-dashboard"]:
        raise ValueError("manifest must declare the five release entrypoints in canonical order")
    if not data.get("payloads"):
        raise ValueError("manifest has no payloads")
    for payload in data["payloads"]:
        _safe_relative(payload["source"])
        _safe_relative(payload["target"])
    return data


def _excluded(relative: Path, manifest: dict) -> bool:
    if any(part in set(manifest.get("exclude_segments", [])) for part in relative.parts):
        return True
    return relative.suffix.lower() in set(manifest.get("exclude_suffixes", []))


def _is_reparse_point(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _iter_payload(repo_root: Path, manifest: dict) -> Iterable[tuple[Path, Path]]:
    for payload in manifest["payloads"]:
        source_root = repo_root / _safe_relative(payload["source"])
        target_root = _safe_relative(payload["target"])
        if not source_root.is_dir():
            raise FileNotFoundError(f"payload source missing: {source_root}")
        resolved_root = source_root.resolve()
        for current, names, files in os.walk(source_root, topdown=True, followlinks=False):
            current_path = Path(current)
            contained_names = []
            for name in sorted(names):
                directory = current_path / name
                try:
                    directory.resolve(strict=False).relative_to(resolved_root)
                except ValueError:
                    continue
                if _is_reparse_point(directory):
                    raise ValueError(f"symlink/reparse payload entry is not admitted: {directory}")
                contained_names.append(name)
            names[:] = contained_names

            for name in sorted(files):
                source = current_path / name
                if _is_reparse_point(source):
                    raise ValueError(f"symlink/reparse payload entry is not admitted: {source}")
                try:
                    source.resolve(strict=False).relative_to(resolved_root)
                except ValueError as exc:
                    raise ValueError(
                        f"payload file resolves outside its source root: {source}"
                    ) from exc
                relative = source.relative_to(source_root)
                if not _excluded(relative, manifest):
                    yield source, target_root / relative


def preflight(
    repo_root: Path,
    install_root: Path,
    manifest_path: Path,
    command_finder: Callable[[str], str | None] = shutil.which,
) -> dict:
    """Discover proposal prerequisites without changing the target filesystem."""
    issues: list[dict[str, str]] = []
    discoveries: dict[str, object] = {"commands": {}, "skill_payloads": []}

    if not repo_root.is_dir():
        issues.append({
            "code": "repository_root_missing",
            "message": f"Repository root is not a directory: {repo_root}",
            "hint": "Run setup.ps1 from a complete WeilanSkillEvolution checkout.",
        })
    if install_root.exists() and not install_root.is_dir():
        issues.append({
            "code": "install_root_not_directory",
            "message": f"Install root exists and is not a directory: {install_root}",
            "hint": "Choose a missing path or an existing directory for --install-root.",
        })

    manifest = None
    if not manifest_path.is_file():
        issues.append({
            "code": "install_manifest_missing",
            "message": f"Install manifest was not found: {manifest_path}",
            "hint": "Restore install-manifest.json or pass --manifest with its path.",
        })
    else:
        try:
            manifest = load_manifest(manifest_path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            issues.append({
                "code": "install_manifest_invalid",
                "message": f"Install manifest is invalid: {exc}",
                "hint": "Use a manifest that satisfies weilan_release_install_manifest_v0.1.",
            })

    for command, hint in REQUIRED_COMMANDS.items():
        discovered = command_finder(command)
        discoveries["commands"][command] = discovered
        if not discovered:
            issues.append({
                "code": f"prerequisite_{command}_missing",
                "message": f"Required command '{command}' was not found on PATH.",
                "hint": hint,
            })

    if manifest is not None and repo_root.is_dir():
        for payload in manifest["payloads"]:
            source = repo_root / _safe_relative(payload["source"])
            discoveries["skill_payloads"].append(str(source))
            if not source.is_dir():
                issues.append({
                    "code": "skill_payload_missing",
                    "message": f"Skill payload source is not a directory: {source}",
                    "hint": "Use a complete checkout containing the manifest-declared Skill payload.",
                })
                continue
            skill_manifest = source / "SKILL.md"
            if not skill_manifest.is_file() or skill_manifest.is_symlink():
                issues.append({
                    "code": "skill_manifest_missing",
                    "message": f"Skill payload has no ordinary SKILL.md file: {skill_manifest}",
                    "hint": "Restore the manifest-declared Skill root and its SKILL.md file.",
                })
            elif skill_manifest.stat().st_size == 0:
                issues.append({
                    "code": "skill_manifest_empty",
                    "message": f"Skill payload SKILL.md is empty: {skill_manifest}",
                    "hint": "Restore a non-empty SKILL.md from the release candidate source.",
                })

    return {
        "schema": "weilan_release_preflight_v0.1",
        "status": "blocked" if issues else "ready",
        "issues": issues,
        "discoveries": discoveries,
    }


def _wrapper(name: str) -> bytes:
    manager = "$PSScriptRoot\\..\\lib\\release_installer.py"
    receipt = "$PSScriptRoot\\..\\install-receipt.json"
    common = (
        "$ErrorActionPreference = 'Stop'\n"
        "$manager = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\\lib\\release_installer.py'))\n"
        "$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))\n"
        "$receipt = Join-Path $root 'install-receipt.json'\n"
    )
    if name == "install":
        body = (
            "param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)\n"
            + common
            + "$installed = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json\n"
            + "$repo = [string]$installed.repo_root\n"
            + "& python $manager install --repo-root $repo --install-root $root --receipt $receipt @Rest\n"
            + "exit $LASTEXITCODE\n"
        )
    elif name == "status":
        body = (
            "param()\n" + common
            + "& python $manager status --install-root $root --receipt $receipt\n"
            + "exit $LASTEXITCODE\n"
        )
    elif name == "uninstall":
        body = (
            "param()\n" + common
            + "& python $manager uninstall --install-root $root --receipt $receipt\n"
            + "exit $LASTEXITCODE\n"
        )
    else:
        body = (
            "param([switch]$Smoke)\n" + common
            + f"$argsList = @('entry', '--name', '{name}', '--install-root', $root, '--receipt', $receipt)\n"
            + "if ($Smoke) { $argsList += '--smoke' }\n"
            + "& python $manager @argsList\n"
            + "exit $LASTEXITCODE\n"
        )
    return body.encode("utf-8-sig")


def build_plan(repo_root: Path, install_root: Path, manifest_path: Path) -> dict[Path, bytes]:
    manifest = load_manifest(manifest_path)
    plan: dict[Path, bytes] = {}
    for source, relative in _iter_payload(repo_root, manifest):
        plan[relative] = source.read_bytes()
    plan[Path("lib/release_installer.py")] = Path(__file__).read_bytes()
    plan[Path("lib/install-manifest.json")] = manifest_path.read_bytes()
    for name in manifest["entrypoints"]:
        plan[Path("bin") / f"{name}.ps1"] = _wrapper(name)
    plan[Path("bin/uninstall.ps1")] = _wrapper("uninstall")
    return plan


def _receipt_path(install_root: Path, receipt: Path | None) -> Path:
    resolved_root = install_root.resolve()
    path = receipt.resolve() if receipt else resolved_root / RECEIPT_NAME
    try:
        relative = path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("receipt path must be inside the install root") from exc
    if not relative.parts:
        raise ValueError("receipt path must name a file inside the install root")
    return path


def _contained_target(install_root: Path, relative: Path) -> Path:
    """Resolve an owned path without following an existing link outside root."""
    target = install_root / relative
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(install_root)
    except ValueError as exc:
        raise ValueError(f"owned path resolves outside the install root: {relative.as_posix()}") from exc
    return target


def _existing_receipt_matches(path: Path, expected: dict) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return existing == expected


def _missing_parents(path: Path) -> list[Path]:
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    return missing


def _remove_created(created_files: list[Path], created_directories: set[Path]) -> None:
    for path in reversed(created_files):
        path.unlink(missing_ok=True)
    for directory in sorted(created_directories, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass


def _contained_directories_bottom_up(install_root: Path) -> list[Path]:
    """List directories without descending through links that resolve outside root."""
    directories: list[Path] = []
    for current, names, _ in os.walk(install_root, topdown=True, followlinks=False):
        current_path = Path(current)
        contained_names = []
        for name in names:
            directory = current_path / name
            if _is_reparse_point(directory):
                continue
            relative = directory.relative_to(install_root)
            try:
                _contained_target(install_root, relative)
            except ValueError:
                continue
            contained_names.append(name)
            directories.append(directory)
        names[:] = contained_names
    return sorted(directories, key=lambda path: len(path.parts), reverse=True)


def _write_receipt_atomic(path: Path, result: dict) -> None:
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def install(
    repo_root: Path,
    install_root: Path,
    manifest_path: Path,
    receipt: Path | None = None,
    command_finder: Callable[[str], str | None] = shutil.which,
) -> dict:
    repo_root = repo_root.resolve()
    install_root = install_root.resolve()
    manifest_path = manifest_path.resolve()
    receipt_path = _receipt_path(install_root, receipt)
    preflight_result = preflight(repo_root, install_root, manifest_path, command_finder)
    if preflight_result["status"] != "ready":
        return {
            "schema": "weilan_release_install_result_v0.1",
            "status": "preflight_failed",
            "preflight": preflight_result,
        }
    plan = build_plan(repo_root, install_root, manifest_path)
    conflicts = []
    for relative, data in plan.items():
        target = _contained_target(install_root, relative)
        if target.exists() and (not target.is_file() or sha256_file(target) != sha256_bytes(data)):
            conflicts.append(relative.as_posix())
    if conflicts:
        return {"schema": "weilan_release_install_result_v0.1", "status": "conflict", "conflicts": conflicts}

    owned = [
        {"path": relative.as_posix(), "sha256": sha256_bytes(data)}
        for relative, data in sorted(plan.items(), key=lambda item: item[0].as_posix())
    ]
    result = {
        "schema": "weilan_release_install_receipt_v0.1",
        "status": "installed",
        "repo_root": str(repo_root),
        "install_root": str(install_root),
        "manifest_sha256": sha256_file(manifest_path),
        "owned_files": owned,
        "owned_file_count": len(owned),
        "runtime_activation_ready": False,
        "runtime_activation_boundary": "scheduler/dashboard sources still contain machine-specific paths; real start/stop/open-dashboard refuse activation",
    }
    try:
        receipt_relative = receipt_path.relative_to(install_root).as_posix()
    except ValueError as exc:
        raise ValueError("receipt path must be inside the install root") from exc
    if Path(*PurePosixPath(receipt_relative).parts) in plan:
        return {
            "schema": "weilan_release_install_result_v0.1",
            "status": "conflict",
            "conflicts": [receipt_relative],
        }
    if receipt_path.exists() and not _existing_receipt_matches(receipt_path, result):
        return {
            "schema": "weilan_release_install_result_v0.1",
            "status": "conflict",
            "conflicts": [receipt_relative],
        }
    created_files: list[Path] = []
    created_directories: set[Path] = set()
    try:
        for relative, data in plan.items():
            target = _contained_target(install_root, relative)
            if not target.exists():
                created_directories.update(_missing_parents(target.parent))
                target.parent.mkdir(parents=True, exist_ok=True)
                created_files.append(target)
                target.write_bytes(data)
        created_directories.update(_missing_parents(receipt_path.parent))
        _write_receipt_atomic(receipt_path, result)
    except OSError:
        _remove_created(created_files, created_directories)
        raise
    return result


def load_receipt(install_root: Path, receipt: Path | None = None) -> tuple[Path, dict | None]:
    path = _receipt_path(install_root, receipt)
    if not path.exists():
        return path, None
    return path, json.loads(path.read_text(encoding="utf-8"))


def status(install_root: Path, receipt: Path | None = None) -> dict:
    install_root = install_root.resolve()
    _, data = load_receipt(install_root, receipt)
    if data is None:
        return {"schema": "weilan_release_status_v0.1", "state": "absent", "ok": True}
    missing, drifted = [], []
    for owned in data.get("owned_files", []):
        relative = _safe_relative(owned["path"])
        target = _contained_target(install_root, relative)
        if not target.is_file():
            missing.append(owned["path"])
        elif sha256_file(target) != owned["sha256"]:
            drifted.append(owned["path"])
    state = "healthy" if not missing and not drifted else "drifted"
    return {
        "schema": "weilan_release_status_v0.1",
        "state": state,
        "ok": state == "healthy",
        "owned_file_count": len(data.get("owned_files", [])),
        "missing": missing,
        "drifted": drifted,
        "runtime_activation_ready": bool(data.get("runtime_activation_ready", False)),
        "runtime_activation_boundary": data.get("runtime_activation_boundary"),
    }


def uninstall(install_root: Path, receipt: Path | None = None) -> dict:
    install_root = install_root.resolve()
    receipt_path, data = load_receipt(install_root, receipt)
    if data is None:
        return {"schema": "weilan_release_uninstall_result_v0.1", "status": "already_absent", "conflicts": []}
    conflicts, removed = [], []
    for owned in reversed(data.get("owned_files", [])):
        relative = _safe_relative(owned["path"])
        target = _contained_target(install_root, relative)
        if not target.exists():
            continue
        if not target.is_file() or sha256_file(target) != owned["sha256"]:
            conflicts.append(owned["path"])
            continue
        target.unlink()
        removed.append(owned["path"])
    for directory in _contained_directories_bottom_up(install_root):
        try:
            directory.rmdir()
        except OSError:
            pass
    if not conflicts:
        receipt_path.unlink(missing_ok=True)
        try:
            install_root.rmdir()
        except OSError:
            pass
    return {
        "schema": "weilan_release_uninstall_result_v0.1",
        "status": "conflict" if conflicts else "uninstalled",
        "removed": removed,
        "conflicts": sorted(conflicts),
    }


def entry(name: str, install_root: Path, receipt: Path | None, smoke: bool) -> tuple[int, dict]:
    report = status(install_root, receipt)
    if not report["ok"] or report["state"] != "healthy":
        return 2, {"entry": name, "status": "installation_not_healthy", "installation": report}
    if smoke:
        return 0, {
            "entry": name,
            "status": "smoke_pass",
            "runtime_activation_performed": False,
            "boundary": report["runtime_activation_boundary"],
        }
    return 3, {
        "entry": name,
        "status": "activation_refused",
        "runtime_activation_performed": False,
        "boundary": report["runtime_activation_boundary"],
    }


def _print(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_install = sub.add_parser("install")
    p_install.add_argument("--repo-root", type=Path, required=True)
    p_install.add_argument("--install-root", type=Path, required=True)
    p_install.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p_install.add_argument("--receipt", type=Path)
    for command in ("status", "uninstall"):
        child = sub.add_parser(command)
        child.add_argument("--install-root", type=Path, required=True)
        child.add_argument("--receipt", type=Path)
    p_entry = sub.add_parser("entry")
    p_entry.add_argument("--name", choices=("start", "stop", "open-dashboard"), required=True)
    p_entry.add_argument("--install-root", type=Path, required=True)
    p_entry.add_argument("--receipt", type=Path)
    p_entry.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            result = install(args.repo_root, args.install_root, args.manifest, args.receipt)
            _print(result)
            return 0 if result["status"] == "installed" else 2
        if args.command == "status":
            result = status(args.install_root, args.receipt)
            _print(result)
            return 0 if result["ok"] else 2
        if args.command == "uninstall":
            result = uninstall(args.install_root, args.receipt)
            _print(result)
            return 0 if result["status"] in ("uninstalled", "already_absent") else 2
        code, result = entry(args.name, args.install_root, args.receipt, args.smoke)
        _print(result)
        return code
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _print({"schema": "weilan_release_installer_error_v0.1", "status": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
