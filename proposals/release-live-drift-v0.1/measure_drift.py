"""Read-only measurement of LIVE (installed skill) vs TARGET (repo publish payload).

Writes nothing. Mirrors verify_inclusion.py's live/target comparison only, so the
numbers here can be checked against that verifier without letting it overwrite the
un-receipted working-tree state in proposals/public-release-consolidation-v0.1/.

Usage: python measure_drift.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan")
TARGET = ROOT / "skill" / "solve-with-weilan"


def collect(base: Path) -> dict[str, Path]:
    files = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if ".pytest_cache" in path.parts or ".git" in path.parts:
            continue
        files[path.relative_to(base).as_posix()] = path
    return files


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
