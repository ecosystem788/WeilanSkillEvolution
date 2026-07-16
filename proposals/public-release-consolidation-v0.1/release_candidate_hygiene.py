"""Offline hygiene verification for the allowlisted Windows release candidate.

The verifier reads only the proposal files explicitly named in its code-owned
allowlist and the payload roots in install-manifest.json. The inventory records
the same surface for human review. It never discovers or scans user HOME
directories, live ledgers, or runtime state outside the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


PROPOSAL_ALLOWLIST = frozenset(
    {
        "proposals/public-release-consolidation-v0.1/INSTALL_OWNERSHIP_RECEIPT.json",
        "proposals/public-release-consolidation-v0.1/OPERATION_CARD.md",
        "proposals/public-release-consolidation-v0.1/README.md",
        "proposals/public-release-consolidation-v0.1/RUNTIME_DEPLOYABILITY_RECEIPT.json",
        "proposals/public-release-consolidation-v0.1/TROUBLESHOOTING.md",
        "proposals/public-release-consolidation-v0.1/clean_home_rehearsal.py",
        "proposals/public-release-consolidation-v0.1/install-manifest.json",
        "proposals/public-release-consolidation-v0.1/release_candidate_hygiene.py",
        "proposals/public-release-consolidation-v0.1/release_installer.py",
        "proposals/public-release-consolidation-v0.1/setup.ps1",
        "proposals/public-release-consolidation-v0.1/test_clean_home_rehearsal.py",
        "proposals/public-release-consolidation-v0.1/test_release_candidate_hygiene.py",
        "proposals/public-release-consolidation-v0.1/test_release_installer.py",
        "proposals/public-release-consolidation-v0.1/verify_release_candidate.py",
    }
)

# RELEASE_WORKTREE_INVENTORY.md classifies these as host/community state or
# local runtime output. Matching is on candidate paths, not harmless source
# references to fresh runtime filenames.
FORBIDDEN_PATH_SEGMENTS = frozenset({"wake-agent-runs", "tmp", "agent-output"})
FORBIDDEN_PATH_NAMES = frozenset(
    {
        "PAUSED",
        "codex-inbox-processed.jsonl",
        "codex-inbox-replies.jsonl",
        "codex-inbox.jsonl",
        "concurrent-receipts.jsonl",
        "peer-chat.jsonl",
        "wake-cursor.json",
        "wake-cursor.prev.json",
        "observe-server.log",
        "wake-agent.log",
        "wake-codex.log",
        "wake-cron.log",
    }
)

CONTENT_RULES = (
    (
        "absolute_user_or_machine_path",
        re.compile(
            rb"(?i)(?:[A-Z]:[\\/](?:Users[\\/][^\\/\s'\"]+|CodexData|\xe5\xbe\xae\xe6\xbe\x9c)(?:[\\/][^\r\n'\"]*)?|/(?:home|Users)/[^/\s'\"]+(?:/[^\r\n'\"]*)?)"
        ),
    ),
    (
        "private_key_material",
        re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    ),
    (
        "credential_assignment",
        re.compile(
            rb"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"
        ),
    ),
    (
        "known_token_format",
        re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})"),
    ),
)


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"rule": self.rule, "path": self.path}
        if self.line is not None:
            result["line"] = self.line
        return result


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(repo_root: Path, manifest_path: Path | None = None) -> dict:
    path = manifest_path or (
        repo_root
        / "proposals"
        / "public-release-consolidation-v0.1"
        / "install-manifest.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def expected_candidate_paths(
    repo_root: Path, manifest_path: Path | None = None
) -> tuple[str, ...]:
    """Return the exact allowlist without looking outside declared payload roots."""

    manifest = _manifest(repo_root, manifest_path)
    excluded_segments = set(manifest.get("exclude_segments", []))
    excluded_suffixes = tuple(manifest.get("exclude_suffixes", []))
    paths = set(PROPOSAL_ALLOWLIST)
    for payload in manifest["payloads"]:
        source = PurePosixPath(payload["source"])
        source_root = repo_root.joinpath(*source.parts)
        if not source_root.is_dir():
            raise FileNotFoundError(f"manifest payload source is missing: {source}")
        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(repo_root).as_posix()
            relative_parts = PurePosixPath(relative).parts
            if excluded_segments.intersection(relative_parts):
                continue
            if excluded_suffixes and relative.endswith(excluded_suffixes):
                continue
            paths.add(relative)
    return tuple(sorted(paths))


def path_findings(relative_paths: Iterable[str]) -> list[Finding]:
    findings: list[Finding] = []
    for relative in sorted(relative_paths):
        path = PurePosixPath(relative)
        if FORBIDDEN_PATH_SEGMENTS.intersection(path.parts):
            findings.append(Finding("forbidden_runtime_segment", relative))
        if path.name in FORBIDDEN_PATH_NAMES or path.suffix.lower() == ".log":
            findings.append(Finding("forbidden_runtime_state", relative))
    return findings


def content_findings(root: Path, relative_paths: Iterable[str]) -> list[Finding]:
    findings: list[Finding] = []
    for relative in sorted(relative_paths):
        content = root.joinpath(*PurePosixPath(relative).parts).read_bytes()
        for rule, pattern in CONTENT_RULES:
            for match in pattern.finditer(content):
                line = content.count(b"\n", 0, match.start()) + 1
                findings.append(Finding(rule, relative, line))
    return findings


def candidate_hashes(root: Path, relative_paths: Iterable[str]) -> dict[str, str]:
    return {
        relative: sha256_file(root.joinpath(*PurePosixPath(relative).parts))
        for relative in sorted(relative_paths)
    }


def tree_hash(hashes: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, file_hash in sorted(hashes.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_hash))
    return digest.hexdigest()


def verify_repository_candidate(repo_root: Path) -> dict[str, object]:
    relative_paths = expected_candidate_paths(repo_root)
    missing = [
        relative
        for relative in relative_paths
        if not repo_root.joinpath(*PurePosixPath(relative).parts).is_file()
    ]
    findings = path_findings(relative_paths)
    if not missing:
        findings.extend(content_findings(repo_root, relative_paths))
        hashes = candidate_hashes(repo_root, relative_paths)
    else:
        hashes = {}
    return {
        "schema": "weilan_release_candidate_hygiene_v0.1",
        "scope": "explicit proposal allowlist plus install-manifest payloads",
        "file_count": len(relative_paths),
        "allowlist": list(relative_paths),
        "missing": missing,
        "files": hashes,
        "tree_sha256": tree_hash(hashes) if hashes else None,
        "findings": [finding.as_dict() for finding in findings],
        "verdict": "PASS" if not missing and not findings else "FAIL",
        "boundary": "Repository candidate only; no HOME, live ledger, scheduler, dashboard, or external runtime path was scanned.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = verify_repository_candidate(args.repo_root.resolve())
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
