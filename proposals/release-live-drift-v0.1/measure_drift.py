"""Read-only measurement of LIVE (installed skill) vs TARGET (repo publish payload).

Writes nothing. Mirrors verify_inclusion.py's live/target comparison only, so the
numbers here can be checked against that verifier without letting it overwrite the
un-receipted working-tree state in proposals/public-release-consolidation-v0.1/.

Usage: python measure_drift.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan")
TARGET = ROOT / "skill" / "solve-with-weilan"

# Declared as data, not buried in the filter, so a report can be compared with
# another measurement only when both criteria sets match.  Note this set is NOT
# identical to tools/evolution_core.tree_manifest's (that one does not exclude
# ".git"); two point values from the two measurers are not same-dimension.
EXCLUDE_DIR_PARTS = ["__pycache__", ".pytest_cache", ".git"]
EXCLUDE_SUFFIXES = [".pyc"]


def collect(base: Path) -> dict[str, Path]:
    files = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix in EXCLUDE_SUFFIXES:
            continue
        if any(part in EXCLUDE_DIR_PARTS for part in path.parts):
            continue
        files[path.relative_to(base).as_posix()] = path
    return files


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return None


def repo_context(rel_path: str) -> dict:
    """Repo HEAD, plus a measurement of how little it says about these bytes.

    repo_head names the commit checked out while the script ran; it does not by
    itself establish that this file's bytes are that commit's.  Git's own test
    for that is blob-id equality, so it is computed here rather than asserted:
    head_blob is the id recorded at HEAD, worktree_blob is hash-object over the
    file as it exists now (both go through the configured filters, so a pure
    line-ending difference does not read as drift).  dirty_path_count is the
    number of paths that already differ from repo_head -- the gap, in one number.
    """
    head_blob = _git("rev-parse", f"HEAD:{rel_path}")
    worktree_blob = _git("hash-object", "--", str(ROOT / rel_path))
    status = _git("status", "--porcelain")
    matches = None
    if head_blob and worktree_blob:
        matches = head_blob == worktree_blob
    return {
        "repo_head": _git("rev-parse", "HEAD") or "unknown",
        "repo_head_authority": "runtime repo context only; does not bind these bytes",
        "head_blob": head_blob or "unknown",
        "worktree_blob": worktree_blob or "unknown",
        "worktree_matches_head": matches if matches is not None else "unknown",
        "dirty_path_count": len(status.splitlines()) if status is not None else "unknown",
    }


def provenance() -> dict:
    """What would have to match for another report's numbers to be comparable.

    Three orthogonal conditions, none of which content-addressing supplies:
    subject (which bytes, via which name), criteria (what was excluded), and
    measurer (which code -- identified by its own sha256, not by repo HEAD).
    The host clock says when, and is context, not a comparability condition.
    LIVE is reached through a filesystem junction on this machine, so the
    nominal path alone does not identify the subject; resolved is what was read.
    """
    rel_path = str(Path(__file__).resolve().relative_to(ROOT).as_posix())
    subject = {
        "live_nominal": str(LIVE),
        "live_resolved": str(Path(LIVE).resolve()),
        "target_nominal": str(TARGET),
        "target_resolved": str(Path(TARGET).resolve()),
    }
    criteria = {
        "exclude_dir_parts": EXCLUDE_DIR_PARTS,
        "exclude_suffixes": EXCLUDE_SUFFIXES,
        "hash": "sha256 of whole file bytes",
    }
    measurer = {
        "path": rel_path,
        "sha256": sha256(Path(__file__).resolve()),
        "repo_context": repo_context(rel_path),
    }
    key_material = {
        "live_resolved": subject["live_resolved"],
        "target_resolved": subject["target_resolved"],
        "criteria": criteria,
        "measurer_sha256": measurer["sha256"],
    }
    return {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "time_authority": "clock",
        "subject": subject,
        "criteria": criteria,
        "measurer": measurer,
        "comparison_key": {
            "value": hashlib.sha256(
                json.dumps(key_material, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "over": ["subject.live_resolved", "subject.target_resolved",
                     "criteria", "measurer.sha256"],
            "note": "Two reports' counts are same-dimension iff this value matches. "
                    "measured_at and measurer.repo_context are context, not key members.",
        },
    }


def main() -> int:
    live = collect(LIVE)
    target = collect(TARGET)
    shared = sorted(set(live) & set(target))
    mismatches = []
    for rel in shared:
        lh, th = sha256(live[rel]), sha256(target[rel])
        if lh != th:
            mismatches.append(
                {
                    "path": rel,
                    "live_sha256": lh,
                    "target_sha256": th,
                    "live_bytes": live[rel].stat().st_size,
                    "target_bytes": target[rel].stat().st_size,
                }
            )
    report = {
        "provenance": provenance(),
        "live_file_count": len(live),
        "target_file_count": len(target),
        "shared_count": len(shared),
        "live_only": sorted(set(live) - set(target)),
        "target_only": sorted(set(target) - set(live)),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
