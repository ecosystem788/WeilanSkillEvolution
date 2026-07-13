from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("export_receipt_guard.py")
SPEC = importlib.util.spec_from_file_location("export_receipt_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(guard)


def _receipt(**scan_overrides):
    scan_result = {
        "hits": 0,
        "clean": True,
        "scanned_tree_hash": "sha256:tree-a",
    }
    scan_result.update(scan_overrides)
    return {
        "built_tree_hash": "sha256:tree-a",
        "scan_result": scan_result,
    }


def test_guard_accepts_receipt_when_scanned_tree_is_built_tree():
    guard.validate_export_receipt_guard(_receipt())


def test_guard_rejects_scanned_tree_hash_mismatch():
    with pytest.raises(guard.ExportReceiptGuardError, match="must equal"):
        guard.validate_export_receipt_guard(
            _receipt(scanned_tree_hash="sha256:other-tree")
        )


def test_guard_rejects_dirty_scan_before_signing():
    with pytest.raises(guard.ExportReceiptGuardError, match="must be clean"):
        guard.validate_export_receipt_guard(_receipt(hits=1, clean=False))


def test_guard_rejects_clean_hits_contradiction():
    with pytest.raises(guard.ExportReceiptGuardError, match="true iff"):
        guard.validate_export_receipt_guard(_receipt(hits=1, clean=True))
