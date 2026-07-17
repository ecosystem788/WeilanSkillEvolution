from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_RC_ROOT = HERE.parents[1]
INSTALLER_RELATIVE = Path("proposals/public-release-consolidation-v0.1/release_installer.py")
MANIFEST_RELATIVE = Path("proposals/public-release-consolidation-v0.1/install-manifest.json")
HARD_KILL_PAYLOAD = 91
HARD_KILL_RECEIPT = 92


def load_installer(rc_root: Path):
    module_path = rc_root / INSTALLER_RELATIVE
    module_name = f"release_installer_r9_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load installer: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_command_finder(command: str) -> str:
    return rf"C:\fixture\{command}.exe"


def wait_for(path: Path, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for {path}")
        time.sleep(0.01)


def worker(args: argparse.Namespace) -> int:
    rc_root = Path(args.rc_root).resolve()
    install_root = Path(args.install_root).resolve()
    gate = Path(args.gate).resolve()
    installer = load_installer(rc_root)
    manifest = rc_root / MANIFEST_RELATIVE
    wait_for(gate)

    if args.action == "payload-kill":
        original_write = Path.write_bytes
        killed = False

        def partial_then_kill(path: Path, data: bytes) -> int:
            nonlocal killed
            if not killed and install_root in path.resolve().parents:
                killed = True
                partial = data[: max(1, len(data) // 2)]
                with path.open("wb") as stream:
                    stream.write(partial)
                    stream.flush()
                    os.fsync(stream.fileno())
                os._exit(HARD_KILL_PAYLOAD)
            return original_write(path, data)

        Path.write_bytes = partial_then_kill
    elif args.action == "receipt-kill":
        original_replace = installer.os.replace

        def kill_before_replace(source, destination):
            if Path(destination).name == installer.RECEIPT_NAME:
                os._exit(HARD_KILL_RECEIPT)
            return original_replace(source, destination)

        installer.os.replace = kill_before_replace
    elif args.action == "install-pause-before-receipt":
        reached = Path(args.reached).resolve()
        release = Path(args.release).resolve()
        original_receipt_write = installer._write_receipt_atomic

        def pause_before_receipt(path: Path, result: dict) -> None:
            reached.write_text("reached\n", encoding="utf-8")
            wait_for(release)
            original_receipt_write(path, result)

        installer._write_receipt_atomic = pause_before_receipt
    elif args.action == "hold-lock":
        reached = Path(args.reached).resolve()
        release = Path(args.release).resolve()
        with installer._InstallRootMutex(install_root):
            reached.write_text("reached\n", encoding="utf-8")
            wait_for(release)
        return 0

    if args.action == "uninstall":
        result = installer.uninstall(install_root)
    else:
        result = installer.install(
            rc_root,
            install_root,
            manifest,
            command_finder=fake_command_finder,
        )
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


class R9FaultInjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rc_root = Path(os.environ.get("WEILAN_R9_RC_ROOT", DEFAULT_RC_ROOT)).resolve()
        cls.installer = load_installer(cls.rc_root)
        cls.manifest = cls.rc_root / MANIFEST_RELATIVE
        if not (cls.rc_root / INSTALLER_RELATIVE).is_file():
            raise RuntimeError(f"missing frozen installer under {cls.rc_root}")

    def run_worker(
        self,
        action: str,
        install_root: Path,
        gate: Path,
        *,
        reached: Path | None = None,
        release: Path | None = None,
    ) -> subprocess.Popen[str]:
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--action",
            action,
            "--rc-root",
            str(self.rc_root),
            "--install-root",
            str(install_root),
            "--gate",
            str(gate),
        ]
        if reached is not None:
            command.extend(["--reached", str(reached)])
        if release is not None:
            command.extend(["--release", str(release)])
        return subprocess.Popen(command, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def collect(self, process: subprocess.Popen[str], expected: int = 0) -> dict | None:
        stdout, stderr = process.communicate(timeout=30)
        self.assertEqual(process.returncode, expected, stderr or stdout)
        return json.loads(stdout) if stdout.strip() else None

    def assert_healthy_receipt_matches_disk(self, install_root: Path) -> dict:
        receipt_path = install_root / self.installer.RECEIPT_NAME
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "installed")
        self.assertEqual(receipt["install_root"], str(install_root.resolve()))
        self.assertEqual(receipt["owned_file_count"], len(receipt["owned_files"]))
        for owned in receipt["owned_files"]:
            target = install_root.joinpath(*Path(owned["path"]).parts)
            self.assertTrue(target.is_file(), owned["path"])
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), owned["sha256"], owned["path"])
        self.assertEqual(self.installer.status(install_root)["state"], "healthy")
        return receipt

    def test_two_concurrent_installs_end_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "install"
            gate = base / "start"
            first = self.run_worker("install", root, gate)
            second = self.run_worker("install", root, gate)
            gate.write_text("go\n", encoding="utf-8")
            results = [self.collect(first), self.collect(second)]
            self.assertTrue(all(result and result["status"] == "installed" for result in results))
            self.assert_healthy_receipt_matches_disk(root)

    def test_install_uninstall_race_never_leaves_receipt_without_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "install"
            seeded = self.installer.install(
                self.rc_root,
                root,
                self.manifest,
                command_finder=fake_command_finder,
            )
            self.assertEqual(seeded["status"], "installed")
            gate = base / "start"
            reached = base / "install-reached-receipt"
            release = base / "resume-install"
            installing = self.run_worker(
                "install-pause-before-receipt",
                root,
                gate,
                reached=reached,
                release=release,
            )
            gate.write_text("go\n", encoding="utf-8")
            wait_for(reached)
            uninstalling = self.run_worker("uninstall", root, gate)
            release.write_text("go\n", encoding="utf-8")
            install_result = self.collect(installing)
            self.assertEqual(install_result["status"], "installed")
            uninstall_result = self.collect(uninstalling)
            self.assertEqual(uninstall_result["status"], "uninstalled")
            self.assertEqual(self.installer.status(root)["state"], "absent")

    def test_hard_kill_during_payload_write_refuses_with_exact_conflict_and_preserves_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "install"
            root.mkdir()
            sentinel = root / "outside-owner.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            gate = base / "start"
            process = self.run_worker("payload-kill", root, gate)
            gate.write_text("go\n", encoding="utf-8")
            self.collect(process, HARD_KILL_PAYLOAD)
            result = self.installer.install(
                self.rc_root,
                root,
                self.manifest,
                command_finder=fake_command_finder,
            )
            self.assertEqual(result["status"], "conflict")
            self.assertEqual(len(result["conflicts"]), 1)
            conflict = root.joinpath(*Path(result["conflicts"][0]).parts)
            self.assertTrue(conflict.is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse((root / self.installer.RECEIPT_NAME).exists())

    def test_hard_kill_before_receipt_replace_recovers_and_preserves_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "install"
            root.mkdir()
            sentinel = root / "outside-owner.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            gate = base / "start"
            process = self.run_worker("receipt-kill", root, gate)
            gate.write_text("go\n", encoding="utf-8")
            self.collect(process, HARD_KILL_RECEIPT)
            self.assertFalse((root / self.installer.RECEIPT_NAME).exists())
            recovered = self.installer.install(
                self.rc_root,
                root,
                self.manifest,
                command_finder=fake_command_finder,
            )
            self.assertEqual(recovered["status"], "installed")
            self.assert_healthy_receipt_matches_disk(root)
            uninstalled = self.installer.uninstall(root)
            self.assertEqual(uninstalled["status"], "uninstalled")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    @unittest.skipUnless(os.name == "nt", "Windows named-mutex contract")
    def test_mutex_identity_collapses_case_trailing_separator_and_junction_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "Target"
            target.mkdir()
            alias = base / "alias"
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(alias), str(target)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertEqual(self.installer._mutex_name(target), self.installer._mutex_name(alias))
            self.assertEqual(
                self.installer._mutex_name(Path(str(target).upper() + os.sep)),
                self.installer._mutex_name(target),
            )

    @unittest.skipUnless(os.name == "nt", "Windows named-mutex contract")
    def test_different_roots_do_not_share_one_global_mutex(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first_root, second_root = base / "first", base / "second"
            gate, reached, release = base / "start", base / "reached", base / "release"
            holder = self.run_worker("hold-lock", first_root, gate, reached=reached, release=release)
            gate.write_text("go\n", encoding="utf-8")
            wait_for(reached)
            result = self.installer.install(
                self.rc_root,
                second_root,
                self.manifest,
                command_finder=fake_command_finder,
            )
            self.assertEqual(result["status"], "installed")
            release.write_text("go\n", encoding="utf-8")
            self.collect(holder)

    @unittest.skipUnless(os.name == "nt", "Windows named-mutex contract")
    def test_bounded_wait_returns_actionable_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "install"
            gate, reached, release = base / "start", base / "reached", base / "release"
            holder = self.run_worker("hold-lock", root, gate, reached=reached, release=release)
            gate.write_text("go\n", encoding="utf-8")
            wait_for(reached)
            started = time.monotonic()
            try:
                result = self.installer.install(
                    self.rc_root,
                    root,
                    self.manifest,
                    command_finder=fake_command_finder,
                )
            finally:
                release.write_text("go\n", encoding="utf-8")
                self.collect(holder)
            elapsed = time.monotonic() - started
            self.assertEqual(result["status"], "conflict")
            self.assertEqual(result["code"], "install_root_busy")
            self.assertIn("retry", result["hint"].lower())
            self.assertLess(elapsed, 8.0, "bounded wait must remain well below the 30s harness timeout")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--action")
    parser.add_argument("--rc-root")
    parser.add_argument("--install-root")
    parser.add_argument("--gate")
    parser.add_argument("--reached")
    parser.add_argument("--release")
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments, remaining = parse_args(sys.argv[1:]), []
    if arguments.worker:
        raise SystemExit(worker(arguments))
    unittest.main(argv=[sys.argv[0], *remaining])
