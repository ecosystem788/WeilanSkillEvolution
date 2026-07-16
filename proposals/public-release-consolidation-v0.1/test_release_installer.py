from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import release_installer as installer


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


class ReleaseInstallerTests(unittest.TestCase):
    def test_missing_skill_payload_fails_preflight_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            repo = temporary_path / "repository"
            repo.mkdir()
            root = temporary_path / "install"
            result = installer.install(
                repo,
                root,
                HERE / "install-manifest.json",
                command_finder=lambda command: rf"C:\fixture\{command}.exe",
            )
            self.assertEqual(result["status"], "preflight_failed")
            issues = result["preflight"]["issues"]
            self.assertEqual([item["code"] for item in issues], ["skill_payload_missing"])
            self.assertIn("skill\\solve-with-weilan", issues[0]["message"])
            self.assertIn("complete checkout", issues[0]["hint"])
            self.assertFalse(root.exists())

    def test_skill_payload_requires_an_ordinary_nonempty_skill_manifest(self):
        fixtures = (
            ("empty-directory", None, "skill_manifest_missing"),
            ("missing-skill-manifest", {"README.md": "not a Skill manifest"}, "skill_manifest_missing"),
            ("empty-skill-manifest", {"SKILL.md": ""}, "skill_manifest_empty"),
        )
        for name, files, expected_code in fixtures:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                temporary_path = Path(temporary)
                repo = temporary_path / "repository"
                skill = repo / "skill" / "solve-with-weilan"
                skill.mkdir(parents=True)
                for relative, content in (files or {}).items():
                    (skill / relative).write_text(content, encoding="utf-8")
                root = temporary_path / "install"
                result = installer.install(
                    repo,
                    root,
                    HERE / "install-manifest.json",
                    command_finder=lambda command: rf"C:\fixture\{command}.exe",
                )
                self.assertEqual(result["status"], "preflight_failed")
                self.assertEqual(
                    [item["code"] for item in result["preflight"]["issues"]],
                    [expected_code],
                )
                self.assertFalse(root.exists())

    def test_external_or_unknown_receipt_is_preserved_without_payload_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            root = temporary_path / "install"
            external = temporary_path / "external-receipt.json"
            external.write_text("external owner", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inside the install root"):
                installer.install(REPO, root, HERE / "install-manifest.json", receipt=external)
            self.assertEqual(external.read_text(encoding="utf-8"), "external owner")
            self.assertFalse(root.exists())

            root.mkdir()
            unknown = root / "custom-receipt.json"
            unknown.write_text("unknown owner", encoding="utf-8")
            result = installer.install(REPO, root, HERE / "install-manifest.json", receipt=unknown)
            self.assertEqual(result["status"], "conflict")
            self.assertEqual(result["conflicts"], ["custom-receipt.json"])
            self.assertEqual(unknown.read_text(encoding="utf-8"), "unknown owner")
            self.assertEqual(list(root.iterdir()), [unknown])

    def test_missing_codex_and_claude_fail_preflight_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            available = {"python": r"C:\Python\python.exe"}
            result = installer.install(
                REPO,
                root,
                HERE / "install-manifest.json",
                command_finder=available.get,
            )
            self.assertEqual(result["status"], "preflight_failed")
            issues = {item["code"]: item for item in result["preflight"]["issues"]}
            self.assertEqual(
                set(issues),
                {"prerequisite_codex_missing", "prerequisite_claude_missing"},
            )
            self.assertIn("PATH", issues["prerequisite_codex_missing"]["message"])
            self.assertIn("Install Claude Code", issues["prerequisite_claude_missing"]["hint"])
            self.assertFalse(root.exists())

    def test_invalid_repository_manifest_and_install_paths_are_actionable(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            install_root = temporary_path / "not-a-directory"
            install_root.write_text("occupied", encoding="utf-8")
            result = installer.preflight(
                temporary_path / "missing-repository",
                install_root,
                temporary_path / "missing-manifest.json",
                command_finder=lambda _: r"C:\fixture\command.exe",
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                {item["code"] for item in result["issues"]},
                {"repository_root_missing", "install_root_not_directory", "install_manifest_missing"},
            )
            self.assertTrue(all(item["message"] and item["hint"] for item in result["issues"]))

    def test_windows_drive_and_rooted_manifest_targets_fail_before_writes(self):
        unsafe_targets = (
            r"C:\escape",
            r"C:escape",
            r"\\server\share\escape",
            r"\escape",
            "/escape",
            r"..\escape",
        )
        source_manifest = json.loads((HERE / "install-manifest.json").read_text(encoding="utf-8"))
        for unsafe_target in unsafe_targets:
            with self.subTest(target=unsafe_target), tempfile.TemporaryDirectory() as temporary:
                temporary_path = Path(temporary)
                root = temporary_path / "install"
                manifest = temporary_path / "unsafe-manifest.json"
                candidate = json.loads(json.dumps(source_manifest))
                candidate["payloads"][0]["target"] = unsafe_target
                manifest.write_text(json.dumps(candidate), encoding="utf-8")

                result = installer.install(
                    REPO,
                    root,
                    manifest,
                    command_finder=lambda command: rf"C:\fixture\{command}.exe",
                )

                self.assertEqual(result["status"], "preflight_failed")
                self.assertEqual(
                    [item["code"] for item in result["preflight"]["issues"]],
                    ["install_manifest_invalid"],
                )
                self.assertFalse(root.exists())

    def test_existing_link_parent_cannot_redirect_owned_writes_outside_install_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            root = temporary_path / "install"
            outside = temporary_path / "outside"
            root.mkdir()
            outside.mkdir()
            try:
                (root / "skills").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                if os.name != "nt":
                    self.skipTest(f"directory links unavailable: {exc}")
                completed = subprocess.run(
                    ["cmd", "/d", "/c", "mklink", "/J", str(root / "skills"), str(outside)],
                    text=True,
                    encoding="oem",
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            with self.assertRaisesRegex(ValueError, "resolves outside the install root"):
                installer.install(REPO, root, HERE / "install-manifest.json")

            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((root / installer.RECEIPT_NAME).exists())

    def test_payload_walk_does_not_descend_through_junction_outside_source_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            repo = temporary_path / "repository"
            payload = repo / "payload"
            outside = temporary_path / "outside"
            link = payload / "foreign-link"
            payload.mkdir(parents=True)
            outside.mkdir()
            ordinary = payload / "ordinary.txt"
            secret = outside / "secret.txt"
            ordinary.write_text("admitted", encoding="utf-8")
            secret.write_text("outside", encoding="utf-8")
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                if os.name != "nt":
                    self.skipTest(f"directory links unavailable: {exc}")
                completed = subprocess.run(
                    ["cmd", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                    text=True,
                    encoding="oem",
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            manifest = {
                "payloads": [{"source": "payload", "target": "installed"}],
                "exclude_segments": [],
                "exclude_suffixes": [],
            }
            enumerated = list(installer._iter_payload(repo, manifest))

            self.assertEqual(enumerated, [(ordinary, Path("installed") / "ordinary.txt")])
            self.assertNotIn(secret, [source for source, _ in enumerated])
            self.assertTrue(link.exists())
            if os.name == "nt" and not link.is_symlink():
                link.rmdir()

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_payload_walk_rejects_in_root_junction_before_recursing(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            repo = temporary_path / "repository"
            payload = repo / "payload"
            link = payload / "loop"
            payload.mkdir(parents=True)
            (payload / "ordinary.txt").write_text("admitted", encoding="utf-8")
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(link), str(payload)],
                text=True,
                encoding="oem",
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            manifest = {
                "payloads": [{"source": "payload", "target": "installed"}],
                "exclude_segments": [],
                "exclude_suffixes": [],
            }
            try:
                with self.assertRaisesRegex(ValueError, "symlink/reparse payload entry"):
                    list(installer._iter_payload(repo, manifest))
            finally:
                link.rmdir()

    def test_setup_reports_missing_python_as_json_before_install(self):
        powershell = shutil.which("powershell")
        self.assertIsNotNone(powershell)
        with tempfile.TemporaryDirectory() as temporary:
            env = os.environ.copy()
            env["PATH"] = str(Path(temporary) / "empty-path")
            completed = subprocess.run(
                [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "setup.ps1"), "-InstallRoot", str(Path(temporary) / "install")],
                text=True,
                encoding="utf-8",
                capture_output=True,
                env=env,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 4, completed.stderr)
            result = json.loads(completed.stdout.lstrip("\ufeff"))
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["issues"][0]["code"], "prerequisite_python_missing")
            self.assertFalse((Path(temporary) / "install").exists())

    def test_install_status_idempotence_and_clean_uninstall(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            sentinel = root / "outside-owner.txt"
            root.mkdir()
            sentinel.write_text("keep", encoding="utf-8")
            first = installer.install(REPO, root, HERE / "install-manifest.json")
            second = installer.install(REPO, root, HERE / "install-manifest.json")
            self.assertEqual(first["status"], "installed")
            self.assertEqual(first["owned_files"], second["owned_files"])
            self.assertEqual(installer.status(root)["state"], "healthy")
            result = installer.uninstall(root)
            self.assertEqual(result["status"], "uninstalled")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual(installer.uninstall(root)["status"], "already_absent")

    def test_uninstall_cleanup_does_not_descend_through_junction_outside_install_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            root = temporary_path / "install"
            outside = temporary_path / "outside"
            victim = outside / "victim-empty-directory"
            link = root / "foreign-link"
            installer.install(REPO, root, HERE / "install-manifest.json")
            victim.mkdir(parents=True)
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                if os.name != "nt":
                    self.skipTest(f"directory links unavailable: {exc}")
                completed = subprocess.run(
                    ["cmd", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                    text=True,
                    encoding="oem",
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            result = installer.uninstall(root)

            self.assertEqual(result["status"], "uninstalled")
            self.assertTrue(victim.is_dir())
            self.assertTrue(link.exists())
            link.rmdir()

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_uninstall_cleanup_does_not_descend_through_in_root_junction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            link = root / "loop"
            installer.install(REPO, root, HERE / "install-manifest.json")
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(link), str(root)],
                text=True,
                encoding="oem",
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            result = installer.uninstall(root)

            self.assertEqual(result["status"], "uninstalled")
            self.assertTrue(link.exists())
            link.rmdir()

    def test_failed_install_write_rolls_back_only_files_created_by_that_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            sentinel = root / "outside-owner.txt"
            root.mkdir()
            sentinel.write_text("keep", encoding="utf-8")
            original_write = Path.write_bytes
            writes = 0

            def fail_second_write(path, data):
                nonlocal writes
                writes += 1
                if writes == 2:
                    raise OSError("injected write failure")
                return original_write(path, data)

            with mock.patch.object(Path, "write_bytes", fail_second_write):
                with self.assertRaisesRegex(OSError, "injected write failure"):
                    installer.install(REPO, root, HERE / "install-manifest.json")

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual(list(root.iterdir()), [sentinel])

    def test_receipt_replace_failure_preserves_old_receipt_and_rolls_back_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            receipt = installer.install(REPO, root, HERE / "install-manifest.json")
            receipt_path = root / installer.RECEIPT_NAME
            old_receipt = receipt_path.read_bytes()
            missing_relative = Path(receipt["owned_files"][0]["path"])
            missing_target = root / missing_relative
            missing_target.unlink()

            with mock.patch.object(installer.os, "replace", side_effect=OSError("injected replace failure")):
                with self.assertRaisesRegex(OSError, "injected replace failure"):
                    installer.install(REPO, root, HERE / "install-manifest.json")

            self.assertEqual(receipt_path.read_bytes(), old_receipt)
            self.assertFalse(missing_target.exists())
            self.assertEqual(list(receipt_path.parent.glob(f".{receipt_path.name}.*.tmp")), [])

    def test_drifted_owned_file_is_preserved_and_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            receipt = installer.install(REPO, root, HERE / "install-manifest.json")
            relative = Path(receipt["owned_files"][0]["path"])
            target = root / relative
            target.write_bytes(target.read_bytes() + b"\nuser drift\n")
            result = installer.uninstall(root)
            self.assertEqual(result["status"], "conflict")
            self.assertIn(relative.as_posix(), result["conflicts"])
            self.assertTrue(target.exists())

    def test_five_generated_entrypoints_have_honest_smoke_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            installer.install(REPO, root, HERE / "install-manifest.json")
            install_wrapper = (root / "bin" / "install.ps1").read_text(encoding="utf-8-sig")
            self.assertNotIn(str(REPO), install_wrapper)
            self.assertIn("$installed.repo_root", install_wrapper)
            commands = {
                "install": [],
                "start": ["-Smoke"],
                "stop": ["-Smoke"],
                "status": [],
                "open-dashboard": ["-Smoke"],
            }
            for name, extra in commands.items():
                completed = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "bin" / f"{name}.ps1"), *extra],
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(completed.returncode, 0, f"{name}: {completed.stdout}\n{completed.stderr}")
                parsed = json.loads(completed.stdout.lstrip("\ufeff"))
                if name in {"start", "stop", "open-dashboard"}:
                    self.assertFalse(parsed["runtime_activation_performed"])
                    self.assertEqual(parsed["status"], "smoke_pass")


if __name__ == "__main__":
    unittest.main()
