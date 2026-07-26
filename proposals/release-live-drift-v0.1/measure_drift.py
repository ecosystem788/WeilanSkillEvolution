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


def provenance() -> dict:
    """What would have to match for another report's numbers to be comparable.

    Three orthogonal conditions, none of which content-addressing supplies:
    subject (which bytes, via which name), criteria (what was excluded), and
    measurer (which code, at which commit) -- plus the host clock for when.
    LIVE is reached through a filesystem junction on this machine, so the
    nominal path alone does not identify the subject; resolved is what was read.
    """
    try:
        commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        commit = "unknown"
    return {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "time_authority": "clock",
        "subject": {
            "live_nominal": str(LIVE),
            "live_resolved": str(Path(LIVE).resolve()),
            "target_nominal": str(TARGET),
            "target_resolved": str(Path(TARGET).resolve()),
        },
        "criteria": {
            "exclude_dir_parts": EXCLUDE_DIR_PARTS,
            "exclude_suffixes": EXCLUDE_SUFFIXES,
            "hash": "sha256 of whole file bytes",
        },
        "measurer": {
            "path": str(Path(__file__).resolve().relative_to(ROOT).as_posix()),
            "sha256": sha256(Path(__file__).resolve()),
            "repo_head": commit,
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
