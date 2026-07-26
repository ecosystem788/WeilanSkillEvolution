"""Verify the fixed object-level landing of the source-authenticity candidate."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


COMMIT = "f267f4a85d786f7cc83f3945c0b2ae549640894c"
PARENT = "cf6f4b3767b07fe004bbaac73c381f5ebac52dc7"
TARGET = "proposals/capture-contract-source-authenticity-v0.1/candidate/solve-with-weilan"
EXPECTED_ENTRIES = 47
EXPECTED_BYTES = 903_000
EXPECTED_PARENT_COVERED = 46
EXPECTED_PARENT_ORPHAN = 1
EXPECTED_ORPHAN_BLOB = "64bf3ab7eb719817c8b1895e40f164c782a32d07"
EXPECTED_SUBTREE = "c91ff506e3a0995205ba662750f1f5322a7602af"
EXPECTED_MANIFEST = "d5789a6e35348b51391ca9f8e72c308788b3a66858363d7014e00c12043e6286"
EXPECTED_TREE_HASH = "c393bc3916a9276f2dddfda6973790d3738acd0bd756ec8259f4d87463c60d6c"

REPO_ROOT = Path(__file__).resolve().parents[2]


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        stderr=subprocess.STDOUT,
    )


def git_text(*args: str) -> str:
    return git_bytes(*args).decode("utf-8").strip()


def target_entries() -> list[tuple[str, str, bytes]]:
    prefix = f"{TARGET}/"
    entries: list[tuple[str, str, bytes]] = []
    raw = git_bytes("ls-tree", "-r", "-z", COMMIT, "--", TARGET)
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        _mode, object_type, encoded_oid = metadata.split()
        path = encoded_path.decode("utf-8")
        if object_type != b"blob" or not path.startswith(prefix):
            raise ValueError(f"unexpected target entry: {record!r}")
        oid = encoded_oid.decode("ascii")
        entries.append((path[len(prefix) :], oid, git_bytes("cat-file", "blob", oid)))
    return sorted(entries)


def commit_changes() -> list[tuple[str, str]]:
    fields = [
        field
        for field in git_bytes(
            "diff-tree", "--no-commit-id", "--name-status", "-r", "-z", COMMIT
        ).split(b"\0")
        if field
    ]
    if len(fields) % 2:
        raise ValueError(f"unexpected diff-tree field count: {len(fields)}")
    return [
        (fields[index].decode("ascii"), fields[index + 1].decode("utf-8"))
        for index in range(0, len(fields), 2)
    ]


def manifest_sha256(entries: list[tuple[str, str, bytes]]) -> str:
    payload = b"".join(
        relpath.encode("utf-8")
        + b"\0"
        + hashlib.sha256(blob).hexdigest().encode("ascii")
        + b"\n"
        for relpath, _oid, blob in entries
    )
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    landing_errors: list[str] = []

    def require(actual: object, expected: object, label: str) -> None:
        if actual != expected:
            landing_errors.append(f"{label}: expected {expected!r}, got {actual!r}")

    try:
        require(git_text("rev-parse", f"{COMMIT}~1"), PARENT, "parent")
        subtree = git_text("rev-parse", f"{COMMIT}:{TARGET}")
        require(subtree, EXPECTED_SUBTREE, "subtree")

        entries = target_entries()
        paths = {f"{TARGET}/{relpath}" for relpath, _oid, _blob in entries}
        changes = commit_changes()
        require(len(changes), EXPECTED_ENTRIES, "commit entry count")
        require({status for status, _path in changes}, {"A"}, "commit statuses")
        require({path for _status, path in changes}, paths, "commit paths")

        reachable = {
            line.split(b" ", 1)[0].decode("ascii")
            for line in git_bytes("rev-list", "--objects", PARENT).splitlines()
            if line
        }
        covered = sum(oid in reachable for _path, oid, _blob in entries)
        orphan_oids = [oid for _path, oid, _blob in entries if oid not in reachable]
        require(len(entries), EXPECTED_ENTRIES, "target entries")
        require(sum(len(blob) for _path, _oid, blob in entries), EXPECTED_BYTES, "target bytes")
        require(covered, EXPECTED_PARENT_COVERED, "parent covered")
        require(len(orphan_oids), EXPECTED_PARENT_ORPHAN, "parent orphan")
        require(orphan_oids, [EXPECTED_ORPHAN_BLOB], "orphan blob")

        manifest = manifest_sha256(entries)
        require(manifest, EXPECTED_MANIFEST, "manifest")
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as error:
        landing_errors.append(f"object inspection failed: {error}")
        entries = []
        subtree = "<unavailable>"
        covered = 0
        orphan_oids = []
        manifest = "<unavailable>"

    if landing_errors:
        for error in landing_errors:
            print(f"LANDING_DRIFT: {error}", file=sys.stderr)
        return 1

    module_path = REPO_ROOT / "tools" / "evolution_core.py"
    try:
        evolution_core_blob = git_text("hash-object", str(module_path))
        sys.path.insert(0, str(REPO_ROOT))
        from tools.evolution_core import tree_hash

        with tempfile.TemporaryDirectory(prefix="weilan-landing-") as temp_dir:
            extracted_root = Path(temp_dir)
            for relpath, _oid, blob in entries:
                destination = extracted_root / Path(relpath)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(blob)
            actual_tree_hash = tree_hash(extracted_root)
    except (OSError, subprocess.CalledProcessError, ImportError) as error:
        print(
            f"HASHER_DRIFT: bridge execution failed: {error}; "
            f"evolution_core_blob={locals().get('evolution_core_blob', '<unavailable>')}",
            file=sys.stderr,
        )
        return 1

    if actual_tree_hash != EXPECTED_TREE_HASH:
        print(
            f"HASHER_DRIFT: expected tree_hash={EXPECTED_TREE_HASH}, "
            f"got {actual_tree_hash}; evolution_core_blob={evolution_core_blob}",
            file=sys.stderr,
        )
        return 1

    print(
        "PASS "
        f"entries={len(entries)} "
        f"bytes={sum(len(blob) for _path, _oid, blob in entries)} "
        f"parent_covered={covered} "
        f"parent_orphan={len(orphan_oids)} "
        f"subtree={subtree} "
        f"manifest={manifest} "
        f"tree_hash={actual_tree_hash} "
        f"evolution_core_blob={evolution_core_blob}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
