"""Manifest-owned, proposal-local release installer candidate.

This module deliberately owns installation and rollback only.  The generated
start/stop/open-dashboard commands expose a smoke contract but refuse real
runtime activation until the scheduler's machine-specific paths are removed.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import stat
import tempfile
import types
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "install-manifest.json"
RECEIPT_NAME = "install-receipt.json"
MUTEX_WAIT_SECONDS = 5.0
WAIT_OBJECT_0 = 0x00000000
WAIT_ABANDONED = 0x00000080
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
REQUIRED_COMMANDS = {
    "python": "Install Python 3 and ensure 'python' is available on PATH.",
    "codex": "Install Codex and ensure 'codex' is available on PATH.",
    "claude": "Install Claude Code and ensure 'claude' is available on PATH.",
}


class InstallRootBusyError(RuntimeError):
    """The bounded wait for another installer operating on this root expired."""


def _mutex_name(install_root: Path) -> str:
    """Return one session-local mutex name for every spelling of a final root."""
    final_root = str(install_root.resolve(strict=False)).replace("/", "\\").rstrip("\\").casefold()
    identity = hashlib.sha256(final_root.encode("utf-8")).hexdigest()
    # Local\ is deliberate: installation is an interactive per-session operation,
    # and unrelated Windows sessions must not be serialized globally.
    return f"Local\\WeiLanReleaseInstaller-{identity}"


class _InstallRootMutex:
    def __init__(self, install_root: Path, wait_seconds: float = MUTEX_WAIT_SECONDS) -> None:
        self.name = _mutex_name(install_root)
        self.wait_seconds = wait_seconds
        self.handle = None
        self.abandoned = False

    def __enter__(self) -> "_InstallRootMutex":
        if os.name != "nt":
            return self
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise OSError(ctypes.get_last_error(), f"CreateMutexW failed for {self.name}")
        wait_ms = max(0, min(round(self.wait_seconds * 1000), 0xFFFFFFFE))
        result = kernel32.WaitForSingleObject(handle, wait_ms)
        if result in (WAIT_OBJECT_0, WAIT_ABANDONED):
            self.handle = handle
            self.abandoned = result == WAIT_ABANDONED
            return self
        kernel32.CloseHandle(handle)
        if result == WAIT_TIMEOUT:
            raise InstallRootBusyError(
                f"another install or uninstall still owns {self.name}; retry after it finishes"
            )
        if result == WAIT_FAILED:
            raise OSError(ctypes.get_last_error(), f"WaitForSingleObject failed for {self.name}")
        raise OSError(f"unexpected mutex wait result {result} for {self.name}")

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        try:
            if not kernel32.ReleaseMutex(self.handle):
                raise OSError(ctypes.get_last_error(), f"ReleaseMutex failed for {self.name}")
        finally:
            kernel32.CloseHandle(self.handle)
            self.handle = None


def _busy_result(schema: str, error: InstallRootBusyError) -> dict:
    return {
        "schema": schema,
        "status": "conflict",
        "code": "install_root_busy",
        "message": str(error),
        "hint": "Wait for the competing install or uninstall to finish, then retry.",
        "conflicts": ["install_root_busy"],
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
    elif name == "start":
        body = (
            "param([switch]$Smoke,[switch]$TickOnly,[string]$TaskName)\n" + common
            + "$argsList = @('entry', '--name', 'start', '--install-root', $root, '--receipt', $receipt)\n"
            + "if ($Smoke) { $argsList += '--smoke' }\n"
            + "if ($TickOnly) { $argsList += '--tick-only' }\n"
            + "if ($TaskName) { $argsList += @('--task-name', $TaskName) }\n"
            + "& python $manager @argsList\nexit $LASTEXITCODE\n"
        )
    elif name == "open-dashboard":
        body = (
            "param([switch]$Smoke,[int]$Port=8765,[string]$Bind='127.0.0.1',[switch]$AcknowledgeNetworkExposure)\n" + common
            + "$argsList = @('entry', '--name', 'open-dashboard', '--install-root', $root, '--receipt', $receipt, '--port', [string]$Port, '--bind', $Bind)\n"
            + "if ($Smoke) { $argsList += '--smoke' }\n"
            + "if ($AcknowledgeNetworkExposure) { $argsList += '--acknowledge-network-exposure' }\n"
            + "& python $manager @argsList\nexit $LASTEXITCODE\n"
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


def _install_locked(
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
        "install_id": hashlib.sha256(str(install_root).encode("utf-8")).hexdigest()[:12],
        "runtime_activation_ready": True,
        "runtime_activation_boundary": None,
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


def install(
    repo_root: Path,
    install_root: Path,
    manifest_path: Path,
    receipt: Path | None = None,
    command_finder: Callable[[str], str | None] = shutil.which,
) -> dict:
    try:
        with _InstallRootMutex(install_root):
            # WAIT_ABANDONED is still ownership: the ordinary disk/receipt checks
            # below decide whether to repair or return an exact conflict.
            return _install_locked(repo_root, install_root, manifest_path, receipt, command_finder)
    except InstallRootBusyError as error:
        return _busy_result("weilan_release_install_result_v0.1", error)


def load_receipt(install_root: Path, receipt: Path | None = None) -> tuple[Path, dict | None]:
    path = _receipt_path(install_root, receipt)
    if not path.exists():
        return path, None
    return path, json.loads(path.read_text(encoding="utf-8"))


def _runtime_module(install_root: Path):
    path = install_root / "skills" / "solve-with-weilan" / "runtime" / "lifecycle.py"
    if not path.is_file():
        raise FileNotFoundError(f"portable runtime lifecycle missing: {path}")
    name = f"weilan_runtime_lifecycle_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


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
    result = {
        "schema": "weilan_release_status_v0.1",
        "state": state,
        "ok": state == "healthy",
        "owned_file_count": len(data.get("owned_files", [])),
        "missing": missing,
        "drifted": drifted,
        "runtime_activation_ready": bool(data.get("runtime_activation_ready", False)),
        "runtime_activation_boundary": data.get("runtime_activation_boundary"),
    }
    if state == "healthy" and data.get("runtime_activation_ready"):
        result["runtime"] = _runtime_module(install_root).status(install_root)
    return result


def _uninstall_locked(install_root: Path, receipt: Path | None = None) -> dict:
    install_root = install_root.resolve()
    receipt_path, data = load_receipt(install_root, receipt)
    if data is None:
        return {"schema": "weilan_release_uninstall_result_v0.1", "status": "already_absent", "conflicts": []}
    if data.get("runtime_activation_ready"):
        runtime = _runtime_module(install_root)
        try:
            runtime.stop(install_root)
            runtime_state = runtime.status(install_root)
            if runtime_state.get("task_registered") or runtime_state.get("dashboard", {}).get("live"):
                return {"schema": "weilan_release_uninstall_result_v0.1", "status": "conflict", "conflicts": ["runtime_residue"]}
            runtime.remove_runtime_residue(install_root)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            return {"schema": "weilan_release_uninstall_result_v0.1", "status": "conflict", "conflicts": ["runtime_residue"], "error": str(exc)}
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


def uninstall(install_root: Path, receipt: Path | None = None) -> dict:
    try:
        with _InstallRootMutex(install_root):
            return _uninstall_locked(install_root, receipt)
    except InstallRootBusyError as error:
        return _busy_result("weilan_release_uninstall_result_v0.1", error)


def entry(
    name: str,
    install_root: Path,
    receipt: Path | None,
    smoke: bool,
    *,
    tick_only: bool = False,
    task_name: str | None = None,
    port: int = 8765,
    bind: str = "127.0.0.1",
    acknowledge_network_exposure: bool = False,
) -> tuple[int, dict]:
    report = status(install_root, receipt)
    if (not report["ok"] or report["state"] != "healthy") and name != "stop":
        return 2, {"entry": name, "status": "installation_not_healthy", "installation": report}
    if smoke:
        return 0, {
            "entry": name,
            "status": "smoke_pass",
            "runtime_activation_performed": False,
            "boundary": report.get("runtime_activation_boundary"),
        }
    _, receipt_data = load_receipt(install_root, receipt)
    if receipt_data is None:
        return 2, {"entry": name, "status": "installation_absent"}
    runtime = _runtime_module(install_root.resolve())
    if name == "start":
        result = runtime.start(install_root, receipt_data, tick_only=tick_only, task_name=task_name)
    elif name == "stop":
        result = runtime.stop(install_root)
    else:
        result = runtime.open_dashboard(
            install_root, receipt_data, port=port, bind=bind,
            acknowledge=acknowledge_network_exposure,
        )
    result["runtime_activation_performed"] = True
    return 0, result


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
    p_entry.add_argument("--tick-only", action="store_true")
    p_entry.add_argument("--task-name")
    p_entry.add_argument("--port", type=int, default=8765)
    p_entry.add_argument("--bind", default="127.0.0.1")
    p_entry.add_argument("--acknowledge-network-exposure", action="store_true")
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
        code, result = entry(
            args.name, args.install_root, args.receipt, args.smoke,
            tick_only=args.tick_only, task_name=args.task_name, port=args.port,
            bind=args.bind, acknowledge_network_exposure=args.acknowledge_network_exposure,
        )
        _print(result)
        return code
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _print({"schema": "weilan_release_installer_error_v0.1", "status": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
