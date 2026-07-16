from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import clean_home_rehearsal as rehearsal


HERE = Path(__file__).resolve().parent


class CleanHomeRehearsalTests(unittest.TestCase):
    def test_path_guard_rejects_sibling_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            sibling = Path(temporary) / "root-sibling"
            root.mkdir()
            sibling.mkdir()
            self.assertTrue(rehearsal._inside(root / "child", root))
            self.assertFalse(rehearsal._inside(sibling, root))

    def test_rehearsal_is_isolated_nonactivating_and_self_cleaning(self):
        result = rehearsal.rehearse()
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertEqual(result["claim_level"], "LOCAL_CLEAN_HOME_ONLY")
        self.assertFalse(result["clean_machine_acceptance"])
        self.assertFalse(result["runtime_activation_performed"])
        self.assertTrue(result["all_state_paths_inside_temporary_root"])
        self.assertTrue(result["temporary_install_removed"])

    def test_cli_writes_same_labeled_receipt_it_prints(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            completed = subprocess.run(
                [sys.executable, str(HERE / "clean_home_rehearsal.py"), "--receipt", str(receipt)],
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            printed = json.loads(completed.stdout)
            written = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(printed, written)
            self.assertEqual(written["claim_level"], "LOCAL_CLEAN_HOME_ONLY")


if __name__ == "__main__":
    unittest.main()
