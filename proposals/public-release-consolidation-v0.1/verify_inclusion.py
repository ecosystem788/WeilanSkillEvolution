"""Verify the dual-signed solve-with-weilan inclusion without deploying it."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
LIVE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan")
TARGET = ROOT / "skill" / "solve-with-weilan"
PUBLIC = ROOT / "tmp" / "solve-with-weilan-cc4ae8c"
EXPECTED_LIVE_TREE = "0d1e94b23703b014a50b9950ffec479c2859b5041128aab11527def668e77155"
EXPECTED_PUBLIC_HEAD = "cc4ae8c8cd893b3795c540b5030a3fb971d61b4c"
EXPECTED_PUBLIC_BLOBS = 84
STALE_SUPERSEDED = {
    ".gitattributes",
    ".gitignore",
    "README.md",
    "theory/无我.md",
    "scripts/prospective.py",
    "scripts/runtime_core.py",
    "scripts/weilan_trace.py",
    "scripts/test_episode_memory.py",
    "scripts/test_memory.py",
    "scripts/test_prospective.py",
    "scripts/test_semantic_memory.py",
}


def run(*args: str, cwd: Path | None = None) -> bytes:
    return subprocess.check_output(args, cwd=cwd)


def files_under(root: Path) -> dict[str, Path]:
    result = {}
    for path in root.rglob("*"):
        if not path.is_file() or {"__pycache__", ".pytest_cache"} & set(path.parts):
            continue
        result[path.relative_to(root).as_posix()] = path
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    relative = path.relative_to(ROOT)
    return run("git", "hash-object", "--", str(relative), cwd=ROOT).decode().strip()


def public_blobs() -> list[tuple[str, str]]:
    records = run("git", "ls-tree", "-r", "-z", "HEAD", cwd=PUBLIC).split(b"\0")
    result = []
    for record in records:
        if not record:
            continue
        meta, raw_path = record.split(b"\t", 1)
        result.append((raw_path.decode("utf-8"), meta.split()[2].decode("ascii")))
    return result


def mapped_target(public_path: str) -> Path:
    if public_path == "LICENSE":
        return ROOT / "LICENSE"
    if public_path == "README.md":
        return TARGET / "README.md"
    if public_path in {".gitattributes", ".gitignore"}:
        return ROOT / public_path
    if public_path.startswith("theory/"):
        return ROOT / public_path
    return TARGET / public_path


def main() -> int:
    live = files_under(LIVE)
    target = files_under(TARGET)
    payload_target = {key: value for key, value in target.items() if key != "README.md"}
    rows = [f"{path}\t{sha256(live[path])}" for path in sorted(live)]
    tree_text = "\n".join(rows) + "\n"
    tree_hash = hashlib.sha256(tree_text.encode("utf-8")).hexdigest()

    errors: list[str] = []
    if len(live) != 46 or tree_hash != EXPECTED_LIVE_TREE:
        errors.append(f"live anchor drift: count={len(live)} tree={tree_hash}")
    if set(payload_target) != set(live):
        errors.append("target payload file set differs from live file set")
    mismatches = [path for path in live if path in payload_target and sha256(live[path]) != sha256(payload_target[path])]
    if mismatches:
        errors.append("source-target SHA256 mismatch: " + ", ".join(mismatches))

    head = run("git", "rev-parse", "HEAD", cwd=PUBLIC).decode().strip()
    if head != EXPECTED_PUBLIC_HEAD:
        errors.append(f"public source drift: {head}")
    blobs = public_blobs()
    if len(blobs) != EXPECTED_PUBLIC_BLOBS:
        errors.append(f"public blob count drift: {len(blobs)}")

    accounting = []
    for public_path, expected_blob in blobs:
        if public_path.startswith("examples/bounded-autonomy-scaffold/"):
            accounting.append((public_path, expected_blob, "examples_pointer", "proposals/bounded-scheduler-v0.1/impl/", "-"))
            continue
        target_path = mapped_target(public_path)
        actual_blob = git_blob(target_path) if target_path.is_file() else "MISSING"
        target_ref = target_path.relative_to(ROOT).as_posix() if target_path.is_relative_to(ROOT) else str(target_path)
        if actual_blob == expected_blob:
            category = "hash_identical"
        elif public_path in STALE_SUPERSEDED and target_path.is_file():
            category = "stale_superseded"
        else:
            errors.append(f"unaccounted public blob: {public_path} -> {target_ref} ({actual_blob})")
            category = "unaccounted"
        accounting.append((public_path, expected_blob, category, target_ref, actual_blob))

    readme = (TARGET / "README.md").read_text(encoding="utf-8")
    if "WeilanSkillEvolution" not in readme or "proposals/bounded-scheduler-v0.1/impl/" not in readme:
        errors.append("Skill README lacks installation or scaffold-source pointer")

    out = Path(__file__).resolve().parent
    (out / "LIVE_SKILL_SHA256.tsv").write_text(tree_text, encoding="utf-8", newline="\n")
    accounting_text = "public_path\tpublic_blob\tcategory\ttarget\ttarget_blob\n" + "\n".join(
        "\t".join(row) for row in accounting
    ) + "\n"
    (out / "PUBLIC_BLOB_ACCOUNTING.tsv").write_text(accounting_text, encoding="utf-8", newline="\n")
    counts = {name: sum(row[2] == name for row in accounting) for name in ("hash_identical", "stale_superseded", "examples_pointer", "unaccounted")}
    receipt = {
        "schema": "weilan_public_release_inclusion_v0.1",
        "live_file_count": len(live),
        "live_tree_sha256": tree_hash,
        "target_payload_file_count": len(payload_target),
        "source_target_mismatch_count": len(mismatches),
        "public_head": head,
        "public_blob_count": len(blobs),
        "accounting_counts": counts,
        "errors": errors,
        "verified": not errors,
    }
    (out / "INCLUSION_RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
