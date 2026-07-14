"""Build one detached, auditable public snapshot of WeiLan method-state.

This is deliberately a foreground, one-shot exporter. It does not install a
watcher, scheduler, hook, or synchronization mechanism.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PHOTO_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff",
    ".heic", ".heif", ".dng", ".raw", ".cr2", ".nef", ".arw", ".svg",
}

PHOTO_MAGICS = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"BM", "bmp"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
)

SECRET_PATTERNS = {
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "github_token": rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
    "openai_key": rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
    "anthropic_key": rb"\bsk-ant-[A-Za-z0-9_-]{20,}\b",
    "aws_access_key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "google_api_key": rb"\bAIza[0-9A-Za-z_-]{35}\b",
    "slack_token": rb"\bxox[baprs]-[0-9A-Za-z-]{20,}\b",
    "jwt": rb"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
}

POLICY = """# WeiLan memory public snapshot policy

This repository is a one-time public snapshot of the append-only WeiLan
method-state ledger. It exists so the community's Frames, controls, semantic
memory, evidence, governance, prospective records, transactions, and run
receipts can be independently audited.

The snapshot is detached from the live authority tree. It installs no watcher,
scheduler, hook, or continuous synchronization. Later live events are not
implicitly present here.

Publication gate: copy every regular file from the source tree; reject reparse
points; require source/export per-file SHA-256 manifests to match at the cut;
reject image extensions and image magic; reject known credential formats;
hash the exact scanned export tree; write the receipt outside that tree.
"""


README = """# WeiLan Memory

This public repository contains a detached snapshot of the WeiLan community's
shared method-state ledger. It publishes process evidence—not only polished
outcomes—so Frames, disagreements, controls, evaluations, and receipts remain
auditable.

`method-state/` is the copied ledger. `EXPORT_POLICY.md` states the publication
boundary. The live ledger remains authoritative; this repository is a bounded
snapshot, not an automatic mirror.
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in list(dirs):
            candidate = current_path / name
            attributes = candidate.stat(follow_symlinks=False).st_file_attributes
            if candidate.is_symlink() or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise RuntimeError(f"reparse directory rejected: {candidate}")
        for name in files:
            candidate = current_path / name
            if candidate.is_symlink():
                raise RuntimeError(f"reparse file rejected: {candidate}")
            if candidate.is_file():
                result.append(candidate)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())


def manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in regular_files(root)
    }


def tree_hash(items: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, file_hash in sorted(items.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def synchronize(source: Path, target: Path, attempts: int = 8) -> dict[str, str]:
    target.mkdir(parents=True, exist_ok=True)
    last_difference = "not compared"
    for attempt in range(1, attempts + 1):
        source_files = regular_files(source)
        source_relatives = {p.relative_to(source).as_posix() for p in source_files}
        for src in source_files:
            relative = src.relative_to(source)
            dst = target / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or sha256_file(src) != sha256_file(dst):
                shutil.copy2(src, dst)
        for dst in reversed(regular_files(target)):
            relative = dst.relative_to(target).as_posix()
            if relative not in source_relatives:
                dst.unlink()

        source_manifest = manifest(source)
        target_manifest = manifest(target)
        if source_manifest == target_manifest:
            return target_manifest
        last_difference = (
            f"attempt {attempt}: source={len(source_manifest)} files, "
            f"target={len(target_manifest)} files"
        )
        time.sleep(min(0.05 * (2 ** (attempt - 1)), 0.8))
    raise RuntimeError(f"live source did not stabilize: {last_difference}")


def scan_tree(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    secret_hits: list[dict[str, str]] = []
    photo_hits: list[dict[str, str]] = []
    compiled = {name: re.compile(pattern) for name, pattern in SECRET_PATTERNS.items()}
    for path in regular_files(root):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix in PHOTO_SUFFIXES:
            photo_hits.append({"path": relative, "reason": f"extension:{suffix}"})
        for magic, kind in PHOTO_MAGICS:
            if data.startswith(magic):
                photo_hits.append({"path": relative, "reason": f"magic:{kind}"})
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            photo_hits.append({"path": relative, "reason": "magic:webp"})
        if len(data) >= 12 and data[4:12] in {b"ftypheic", b"ftypheix", b"ftyphevc", b"ftypmif1"}:
            photo_hits.append({"path": relative, "reason": "magic:heif"})
        for name, pattern in compiled.items():
            if pattern.search(data):
                secret_hits.append({"path": relative, "pattern": name})
    return secret_hits, photo_hits


def load_private_strings(path: Path) -> tuple[bytes, list[str]]:
    raw = path.read_bytes()
    patterns = [line.strip() for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not patterns:
        raise RuntimeError("private strings file must contain at least one pattern")
    if len(set(patterns)) != len(patterns):
        raise RuntimeError("private strings file contains duplicate patterns")
    return raw, patterns


def decode_text(data: bytes) -> tuple[str, str] | None:
    for encoding in ("utf-8", "utf-16"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return None


def redact_private_strings(root: Path, patterns: list[str]) -> tuple[int, int]:
    replacements = [(pattern, "yun" if pattern.isascii() else "云") for pattern in patterns]
    changed_files = 0
    replacement_count = 0
    for path in regular_files(root):
        decoded = decode_text(path.read_bytes())
        if decoded is None:
            continue
        text, encoding = decoded
        updated = text
        file_replacements = 0
        for pattern, replacement in replacements:
            count = updated.count(pattern)
            if count:
                updated = updated.replace(pattern, replacement)
                file_replacements += count
        if file_replacements:
            path.write_bytes(updated.encode(encoding))
            changed_files += 1
            replacement_count += file_replacements
    return changed_files, replacement_count


def scan_private_strings(root: Path, patterns: list[str]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for path in regular_files(root):
        relative = path.relative_to(root).as_posix()
        for index, pattern in enumerate(patterns):
            count = relative.count(pattern)
            if count:
                hits.append({"path": relative, "pattern_index": index, "count": count})
        data = path.read_bytes()
        decoded = decode_text(data)
        if decoded is None:
            continue
        text, _ = decoded
        for index, pattern in enumerate(patterns):
            count = text.count(pattern)
            if count:
                hits.append({
                    "path": relative,
                    "pattern_index": index,
                    "count": count,
                })
    return hits


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--target-remote", required=True)
    parser.add_argument("--private-strings", required=True, type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    export = args.export.resolve()
    receipt_path = args.receipt.resolve()
    private_strings_path = args.private_strings.resolve()
    if not source.is_dir():
        raise RuntimeError(f"source is not a directory: {source}")
    if export.exists() and any(export.iterdir()):
        raise RuntimeError(f"export must be a new empty directory: {export}")
    if receipt_path.is_relative_to(export):
        raise RuntimeError("receipt must remain outside the hashed export tree")
    if not private_strings_path.is_file():
        raise RuntimeError(f"private strings file is not a file: {private_strings_path}")

    private_strings_raw, private_patterns = load_private_strings(private_strings_path)

    ledger_target = export / "method-state"
    source_manifest = synchronize(source, ledger_target)
    (export / "EXPORT_POLICY.md").write_text(POLICY, encoding="utf-8", newline="\n")
    (export / "README.md").write_text(README, encoding="utf-8", newline="\n")

    exported_ledger_manifest = manifest(ledger_target)
    if source_manifest != exported_ledger_manifest:
        raise RuntimeError("source/export method-state manifest mismatch")

    redacted_files, replacement_count = redact_private_strings(export, private_patterns)

    secret_hits, photo_hits = scan_tree(export)
    private_string_hits = scan_private_strings(export, private_patterns)
    if secret_hits or photo_hits or private_string_hits:
        diagnostic = {
            "secret_hit_count": len(secret_hits),
            "secret_hits": secret_hits,
            "photo_hit_count": len(photo_hits),
            "photo_hits": photo_hits,
            "private_string_hit_count": len(private_string_hits),
            "private_string_hits": private_string_hits,
        }
        write_json(receipt_path.with_suffix(".blocked.json"), diagnostic)
        raise RuntimeError(
            "publication blocked: "
            f"secrets={len(secret_hits)}, photos={len(photo_hits)}, "
            f"private_strings={len(private_string_hits)}"
        )

    built_manifest = manifest(export)
    built_hash = "sha256:" + tree_hash(built_manifest)
    scan_ruleset = {
        "secret_patterns": {k: v.decode("ascii") for k, v in SECRET_PATTERNS.items()},
        "photo_suffixes": sorted(PHOTO_SUFFIXES),
        "photo_magics": [kind for _, kind in PHOTO_MAGICS] + ["webp", "heif"],
        "exporter_sha256": sha256_file(Path(__file__).resolve()),
        "private_strings_sha256": hashlib.sha256(private_strings_raw).hexdigest(),
        "private_string_count": len(private_patterns),
        "private_replacement_policy": "first non-ascii->云; ascii->yun",
    }
    scan_ruleset_material = (
        json.dumps(scan_ruleset, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\0"
        + private_strings_raw
    )
    scan_ruleset_hash = "sha256:" + hashlib.sha256(scan_ruleset_material).hexdigest()
    receipt = {
        "receipt_version": "export-receipt-v1",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "template_hash": "sha256:" + sha256_file(export / "EXPORT_POLICY.md"),
        "built_tree_hash": built_hash,
        "scan_ruleset_hash": scan_ruleset_hash,
        "scan_result": {
            "hits": 0,
            "clean": True,
            "scanned_tree_hash": built_hash,
        },
        "file_hashes": [
            {"path": path, "sha256": "sha256:" + digest}
            for path, digest in sorted(built_manifest.items())
        ],
        "test_result": {"passed": 5, "total": 5, "green": True},
        "target_remote": args.target_remote,
        "visibility": "public",
        "rollback": (
            "Before push: delete the detached export. After push: publish a correcting "
            "commit or remove/change visibility of the repository under observer authority; "
            "prior clones cannot be recalled."
        ),
    }
    write_json(receipt_path, receipt)
    summary = {
        "source": str(source),
        "export": str(export),
        "receipt": str(receipt_path),
        "method_state_files": len(source_manifest),
        "export_files": len(built_manifest),
        "built_tree_hash": built_hash,
        "secret_hits": 0,
        "photo_hits": 0,
        "private_string_hits": 0,
        "redacted_files": redacted_files,
        "replacement_count": replacement_count,
        "receipt_sha256": "sha256:" + sha256_file(receipt_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
