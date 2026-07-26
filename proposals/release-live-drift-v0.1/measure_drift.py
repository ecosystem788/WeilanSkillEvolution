"""Read-only measurement of LIVE (installed skill) vs TARGET (repo publish payload).

Writes nothing. Mirrors verify_inclusion.py's live/target comparison only, so the
numbers here can be checked against that verifier without letting it overwrite the
un-receipted working-tree state in proposals/public-release-consolidation-v0.1/.

Usage: python measure_drift.py
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
import sys
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


def _probe_case_insensitive(base: Path) -> object:
    """Ask this filesystem rather than infer it from the OS name.

    Case behaviour is load-bearing for the visible set: two names differing only
    in case are two keys in collect() on a case-sensitive filesystem and one on a
    case-insensitive one.  The probe is a pure existence check on the case-swapped
    name of a file that is already there -- no writes.  A tree with no letters in
    any filename, or an unreadable base, yields unknown rather than a guess.
    """
    try:
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            swapped = path.name.swapcase()
            if swapped == path.name:
                continue
            return (path.parent / swapped).exists()
    except OSError:
        return "unknown"
    return "unknown"


def _rglob_recurse_symlinks_default() -> object:
    """The link-traversal rule of the exact call collect() makes, read from the API.

    Reported as a fact about this runtime's signature, not as a remembered version
    table: "absent" is what pre-3.13 pathlib looks like from here, and it is kept
    distinct from an explicit False.  Two runtimes that disagree on this string are
    then treated as different dimensions even if they would in fact walk alike --
    the conservative direction, since the cost is a withheld comparison rather
    than a false one.
    """
    param = inspect.signature(Path.rglob).parameters.get("recurse_symlinks")
    if param is None:
        return "absent"
    if param.default is inspect.Parameter.empty:
        return "required"
    return param.default


def runtime_semantics() -> dict:
    """The execution-semantics half of comparability, which sha256 cannot supply.

    measurer.sha256 pins the source text; it does not pin what that text does.
    collect() reaches its file set through Path.rglob and Path.resolve, whose
    result depends on the interpreter's link rules and on the filesystem's case
    behaviour -- so the same source can yield a different visible set on a
    different runtime.  Kept deliberately narrow: only rules that can change this
    script's own set.  Patch version, platform release, CPU and hostname are
    excluded on purpose; they would mint environment noise into a dimension.
    """
    return {
        "implementation": sys.implementation.name,
        "version_boundary": f"{sys.version_info.major}.{sys.version_info.minor}",
        "os_name": os.name,
        "path_case_insensitive": _probe_case_insensitive(TARGET),
        "rglob_recurse_symlinks_default": _rglob_recurse_symlinks_default(),
    }


def provenance() -> dict:
    """What would have to match for another report's numbers to be comparable.

    Four orthogonal conditions, none of which content-addressing supplies:
    subject (which bytes, via which name), criteria (what was excluded), measurer
    (which code -- identified by its own sha256, not by repo HEAD), and runtime
    semantics (what that code does when executed here).  The host clock says when,
    and is context, not a comparability condition.  LIVE is reached through a
    filesystem junction on this machine, so the nominal path alone does not
    identify the subject; resolved is what was read.
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
    runtime = runtime_semantics()
    key_material = {
        "live_resolved": subject["live_resolved"],
        "target_resolved": subject["target_resolved"],
        "criteria": criteria,
        "measurer_sha256": measurer["sha256"],
        "runtime_semantics": runtime,
    }
    return {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "time_authority": "clock",
        "subject": subject,
        "criteria": criteria,
        "measurer": measurer,
        "runtime_semantics": runtime,
        "comparison_key": {
            "value": hashlib.sha256(
                json.dumps(key_material, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "over": ["subject.live_resolved", "subject.target_resolved",
                     "criteria", "measurer.sha256", "runtime_semantics"],
            "note": "A matching value is sufficient for two reports' counts to be "
                    "same-dimension; it is not necessary. The key is deliberately "
                    "over-split (version_boundary, rglob rule), so a mismatch means "
                    "comparability is not established -- not that the measurements "
                    "differ. measured_at and measurer.repo_context are context only.",
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
