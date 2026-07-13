"""Builder-side guard for scaffold export receipts.

The JSON schema can require both hashes to exist, but draft-07 cannot express
that scan_result.scanned_tree_hash must equal built_tree_hash. Keep that
identity check in the export builder path and test it directly.
"""

from __future__ import annotations

from typing import Any, Mapping


class ExportReceiptGuardError(ValueError):
    """Raised when a receipt is not safe to sign or publish."""


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExportReceiptGuardError(f"{field} must be an object")
    return value


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExportReceiptGuardError(f"{field} must be a non-empty string")
    return value


def validate_export_receipt_guard(receipt: Mapping[str, Any]) -> None:
    """Validate non-schema invariants before an export receipt is signed.

    This is intentionally narrow. It does not replace JSON-schema validation;
    it adds the builder-only scan/hash identity check plus the clean/hits
    consistency gate that the export process relies on before publication.
    """

    receipt_obj = _require_mapping(receipt, "receipt")
    built_tree_hash = _require_string(
        receipt_obj.get("built_tree_hash"), "built_tree_hash"
    )
    scan_result = _require_mapping(receipt_obj.get("scan_result"), "scan_result")
    scanned_tree_hash = _require_string(
        scan_result.get("scanned_tree_hash"), "scan_result.scanned_tree_hash"
    )

    if scanned_tree_hash != built_tree_hash:
        raise ExportReceiptGuardError(
            "scan_result.scanned_tree_hash must equal built_tree_hash"
        )

    hits = scan_result.get("hits")
    clean = scan_result.get("clean")
    if not isinstance(hits, int) or hits < 0:
        raise ExportReceiptGuardError("scan_result.hits must be a non-negative integer")
    if not isinstance(clean, bool):
        raise ExportReceiptGuardError("scan_result.clean must be a boolean")
    if clean != (hits == 0):
        raise ExportReceiptGuardError("scan_result.clean must be true iff hits == 0")

    if hits != 0:
        raise ExportReceiptGuardError("redaction scan must be clean before signing")
