"""Schema-layer tests for the scaffold export receipt.

Codex 20:04:40 【反对】 pointed out that draft-07 validation still accepted a
receipt with target_remote="" and visibility="unset", contradicting the
load-bearing claim "schema 上签不出没远端". These tests pin HOLE-1 as a schema
hard gate (minLength on target_remote; unset dropped from the visibility enum)
and freeze the earlier inline jsonschema cases into a persistent regression so
"签不出没远端" is closed evidence, not a one-off manual run.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator


SCHEMA_PATH = Path(__file__).with_name("export-receipt.schema.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft7Validator(SCHEMA)


def _valid_receipt() -> dict:
    """A fully-formed receipt that MUST validate; tests perturb copies of it."""
    return {
        "receipt_version": "export-receipt-v1",
        "built_at_utc": "2026-07-11T20:00:00+00:00",
        "template_hash": "sha256:template-a",
        "built_tree_hash": "sha256:tree-a",
        "scan_ruleset_hash": "sha256:ruleset-a",
        "scan_result": {
            "hits": 0,
            "clean": True,
            "scanned_tree_hash": "sha256:tree-a",
        },
        "file_hashes": [{"path": "README.md", "sha256": "sha256:readme"}],
        "test_result": {"passed": 4, "total": 4, "green": True},
        "target_remote": "git@github.com:ecosystem788/example.git",
        "visibility": "public",
        "rollback": "推前删临时导出目录；推后 git revert。",
    }


def _is_valid(receipt: dict) -> bool:
    return VALIDATOR.is_valid(receipt)


def test_fully_formed_receipt_validates():
    assert _is_valid(_valid_receipt())


# --- HOLE-1: the two gates Codex's 反对 demanded ---

def test_empty_target_remote_rejected():
    receipt = _valid_receipt()
    receipt["target_remote"] = ""
    assert not _is_valid(receipt), "empty target_remote must fail-closed (minLength:1)"


def test_unset_visibility_rejected():
    receipt = _valid_receipt()
    receipt["visibility"] = "unset"
    assert not _is_valid(receipt), "visibility=unset must fail-closed (dropped from enum)"


@pytest.mark.parametrize("visibility", ["public", "private"])
def test_declared_visibility_accepted(visibility):
    receipt = _valid_receipt()
    receipt["visibility"] = visibility
    assert _is_valid(receipt)


# --- Frozen from the earlier inline scan_result binding cases ---

def test_dirty_scan_with_clean_true_rejected():
    receipt = _valid_receipt()
    receipt["scan_result"] = {"hits": 1, "clean": True, "scanned_tree_hash": "sha256:tree-a"}
    assert not _is_valid(receipt), "hits>0 with clean:true must be rejected"


def test_zero_hits_with_clean_false_rejected():
    receipt = _valid_receipt()
    receipt["scan_result"] = {"hits": 0, "clean": False, "scanned_tree_hash": "sha256:tree-a"}
    assert not _is_valid(receipt), "hits==0 with clean:false must be rejected"


def test_honest_dirty_scan_is_legal():
    # fail-closed honesty: a dirty scan honestly reported (hits>0, clean:false)
    # is a legal receipt shape — it just won't pass the guard's sign gate.
    receipt = _valid_receipt()
    receipt["scan_result"] = {"hits": 3, "clean": False, "scanned_tree_hash": "sha256:tree-a"}
    assert _is_valid(receipt)


def test_missing_scanned_tree_hash_rejected():
    receipt = _valid_receipt()
    del receipt["scan_result"]["scanned_tree_hash"]
    assert not _is_valid(receipt), "scanned_tree_hash is required"
