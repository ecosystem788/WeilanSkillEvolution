from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import release_installer as installer


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LIFECYCLE_PATH = REPO / "skill" / "solve-with-weilan" / "runtime" / "lifecycle.py"
SCHEDULER_PATH = REPO / "skill" / "solve-with-weilan" / "runtime" / "scheduler_cli.py"


def _load_lifecycle():
    spec = importlib.util.spec_from_file_location("portable_runtime_test_lifecycle", LIFECYCLE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


lifecycle = _load_lifecycle()


def _product_tasks() -> set[str]:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "@(Get-ScheduledTask -TaskName 'WeilanScheduler-*' -ErrorAction SilentlyContinue | ForEach-Object TaskName)|ConvertTo-Json -Compress"],
        text=True, encoding="utf-8", capture_output=True, timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    value = json.loads(completed.stdout.strip().lstrip("\ufeff") or "[]")
    return {value} if isinstance(value, str) else set(value or [])


def _tree_hash(root: Path | None) -> str | None:
    if root is None or not root.is_dir():
        return None
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big")); digest.update(relative)
        try:
            digest.update(b"content\0" + hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            stat = path.stat()
            digest.update(f"metadata\0{stat.st_size}\0{stat.st_mtime_ns}".encode("ascii"))
    return digest.hexdigest()


class PortableRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows path identity contract")
    def test_action_hash_domain_equivalence_distinction_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            component = root / "AsciiCase"
            component.mkdir()
            script = component / "runner.py"
            script.write_text("pass\n", encoding="utf-8")
            triple = {
                "execute": sys.executable,
                "arguments": [str(script), "tick", "--install-root", str(root), "--tick-only"],
                "working_directory": str(root),
            }
            expected = lifecycle.action_normalize(triple)
            variants = [
                {**triple, "working_directory": "\\\\?\\" + str(root)},
                {**triple, "arguments": [str(root / "asciicase" / "runner.py"), "tick", "--install-root", str(root), "--tick-only"]},
            ]
            for variant in variants:
                path = variant["working_directory"] if variant is variants[0] else variant["arguments"][0]
                original = str(root) if variant is variants[0] else str(script)
                self.assertTrue(os.path.samefile(path, original))
                self.assertEqual(lifecycle.action_normalize(variant), expected)
                self.assertEqual(lifecycle.action_sha256(variant), lifecycle.action_sha256(triple))

            sharp = root / "straße.txt"
            plain = root / "strasse.txt"
            sharp.write_text("sharp", encoding="utf-8")
            plain.write_text("plain", encoding="utf-8")
            self.assertTrue(sharp.exists() and plain.exists())
            self.assertFalse(os.path.samefile(sharp, plain))
            sharp_triple = {**triple, "arguments": [str(sharp), "tick", "--install-root", str(root)]}
            plain_triple = {**triple, "arguments": [str(plain), "tick", "--install-root", str(root)]}
            self.assertNotEqual(lifecycle.action_sha256(sharp_triple), lifecycle.action_sha256(plain_triple))

            raw = hashlib.sha256(json.dumps(variants[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.assertNotEqual(raw, lifecycle.action_sha256(variants[0]))
            missing = {**triple, "arguments": [str(root / "missing.py"), "tick", "--install-root", str(root)]}
            with self.assertRaisesRegex(ValueError, "missing.py"):
                lifecycle.action_normalize(missing)

    def test_tick_receipts_and_agent_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "data" / "runtime"
            runtime.mkdir(parents=True)
            side_effect = root / "agent-ran.txt"
            stub = root / "stub.py"
            stub.write_text(f"from pathlib import Path\nPath({str(side_effect)!r}).write_text('ran', encoding='utf-8')\n", encoding="utf-8")
            (runtime / "runtime.json").write_text(json.dumps({"agent_command": [sys.executable, str(stub)]}), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCHEDULER_PATH), "tick", "--install-root", str(root)],
                text=True, encoding="utf-8", capture_output=True, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["outcome"], "agent_invoked")
            self.assertEqual(side_effect.read_text(encoding="utf-8"), "ran")
            receipt = json.loads((runtime / "scheduler-ticks.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(receipt["outcome"], "agent_invoked")

    @unittest.skipUnless(os.name == "nt", "real Task Scheduler acceptance")
    def test_isolated_real_lifecycle_and_ownership_guards(self):
        baseline = _product_tasks()
        ledger_raw = os.environ.get("WEILAN_TEST_COMMUNITY_LEDGER")
        ledger = Path(ledger_raw) if ledger_raw else None
        ledger_before = _tree_hash(ledger)
        name = f"WeilanReleaseTest-{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "install"
            installed = installer.install(
                REPO, root, HERE / "install-manifest.json",
                command_finder=lambda command: rf"C:\fixture\{command}.exe",
            )
            self.assertEqual(installed["status"], "installed")
            try:
                with self.assertRaisesRegex(ValueError, "agent_command"):
                    lifecycle.start(root, installed, tick_only=False, task_name=name)
                with self.assertRaisesRegex(ValueError, "WeilanReleaseTest-"):
                    lifecycle.start(root, installed, tick_only=True, task_name="Foo")
                result = lifecycle.start(root, installed, tick_only=True, task_name=name)
                registration = result["registration"]
                self.assertEqual(registration["task_name"], name)
                live = lifecycle._task_query(name)
                self.assertIsNotNone(live)
                live_triple = lifecycle._live_triple(live)
                self.assertEqual(lifecycle.action_sha256(live_triple), registration["action_sha256"])
                self.assertTrue(Path(registration["action"]["execute"]).is_absolute())
                self.assertTrue(Path(registration["action"]["arguments"][0]).is_absolute())

                # Reproduce the registered action by argv from a foreign cwd and PATH.
                ticks = root / "data" / "runtime" / "scheduler-ticks.jsonl"
                before = ticks.stat().st_size if ticks.exists() else 0
                env = os.environ.copy(); env["PATH"] = str(root / "empty-path")
                direct = subprocess.run(
                    [registration["action"]["execute"], *registration["action"]["arguments"]],
                    cwd=HERE, env=env, text=True, encoding="utf-8", capture_output=True, timeout=30,
                )
                self.assertEqual(direct.returncode, 0, direct.stderr)
                self.assertTrue(ticks.stat().st_size > before)

                # Corrupt a non-path token and prove re-entrant start re-pins it.
                corrupt = json.loads(json.dumps(registration["action"]))
                corrupt["arguments"][1] = "tock"
                lifecycle._register(name, corrupt)
                lifecycle.start(root, installed, tick_only=True, task_name=name)
                repaired = lifecycle._live_triple(lifecycle._task_query(name))
                self.assertEqual(repaired["arguments"][1], "tick")
                events = (root / "data" / "runtime" / "runtime-events.jsonl").read_text(encoding="utf-8")
                self.assertIn("task_repinned", events)

                before = ticks.stat().st_size if ticks.exists() else 0
                lifecycle.trigger_task(name)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and (not ticks.exists() or ticks.stat().st_size <= before):
                    time.sleep(0.25)
                self.assertTrue(ticks.exists() and ticks.stat().st_size > before, "real task produced no tick receipt")
                self.assertIn(json.loads(ticks.read_text(encoding="utf-8").splitlines()[-1])["outcome"], {"nothing_due", "no_agent_configured"})

                dashboard = lifecycle.open_dashboard(root, installed, port=0, bind="127.0.0.1", acknowledge=False)
                self.assertEqual(dashboard["status"], "running")
                url = dashboard["url"]
                with urllib.request.urlopen(url, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                request = urllib.request.Request(url, method="POST")
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(caught.exception.code, 405)
                with self.assertRaisesRegex(ValueError, "acknowledge"):
                    lifecycle.open_dashboard(root, installed, port=0, bind="0.0.0.0", acknowledge=False)

                both = lifecycle.status(root)
                self.assertTrue(both["task_registered"] and both["dashboard"]["live"])
                dash_pid = both["dashboard"]["pid"]
                env = os.environ.copy(); env["WEILAN_RUNTIME_PID"] = str(dash_pid)
                killed = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Stop-Process -Id $env:WEILAN_RUNTIME_PID -Force"],
                    env=env, capture_output=True, timeout=15,
                )
                self.assertEqual(killed.returncode, 0)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and lifecycle._pid_status(root, clean_stale=False).get("live"):
                    time.sleep(0.1)
                task_only = lifecycle.status(root)
                self.assertTrue(task_only["task_registered"])
                self.assertFalse(task_only["dashboard"]["live"])
                self.assertFalse((root / "data" / "runtime" / "dashboard.pid").exists())

                lifecycle.open_dashboard(root, installed, port=0, bind="127.0.0.1", acknowledge=False)
                lifecycle._unregister(name)
                (root / "data" / "runtime" / "task-registration.json").unlink()
                dashboard_only = lifecycle.status(root)
                self.assertFalse(dashboard_only["task_registered"])
                self.assertTrue(dashboard_only["dashboard"]["live"])

                self.assertEqual(lifecycle.stop(root)["status"], "stopped")
                self.assertEqual(lifecycle.stop(root)["status"], "stopped")
                state = lifecycle.status(root)
                self.assertFalse(state["task_registered"])
                self.assertFalse(state["dashboard"]["live"])
            finally:
                if root.exists():
                    lifecycle.stop(root)
            removed = installer.uninstall(root)
            self.assertEqual(removed["status"], "uninstalled", removed)
            self.assertFalse(root.exists())
        self.assertEqual(_product_tasks(), baseline)
        self.assertEqual(_tree_hash(ledger), ledger_before)

    def test_dashboard_source_is_read_only_surface(self):
        text = (REPO / "skill" / "solve-with-weilan" / "runtime" / "dashboard.py").read_text(encoding="utf-8")
        for forbidden in ("wake_agent", "owner-inbox", "codex-inbox", "peer-chat"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
