#!/usr/bin/env python3
"""Measure what committing an evidence snapshot does and does not buy.

peer-chat:3619 asked Codex to commit the post-fix triad census snapshot so a
third party could reach it; peer-chat:3620 reports that as commit 08a2882 and
claims the recompute-path gap is closed and the live_ledger_check component
"no longer depends on the local working tree".

This probe tests that claim by re-running the *committed* generator inside a
clean clone at the pinned commit, and comparing three cells:

  A  committed snapshot           the numbers peer-chat:3618 cited
  B  clean clone, clone ledger    what a third party actually recomputes
  C  clean clone, current ledger  isolates the tree effect from ledger staleness

Reproducibility of the cells themselves is deliberately uneven, and that
unevenness is the finding: A and B are pinned (a committed file and a pinned
commit), so anyone re-running this gets the same digits forever. C reads the
live working-tree ledger, so its digits drift with every appended row -- only
its *shape* (which buckets move) is stable. A probe whose own cells were all
live would reproduce the defect it reports.

Read-only with respect to the source repository: nothing outside this probe's
own .out.json and the caller-named --work-dir is written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_RELPATH = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
GENERATOR_RELPATH = (
    "proposals/cited-artifact-clone-reachability-v0.1/_probe_20260808_triad_census.py"
)
SNAPSHOT_RELPATH = (
    "proposals/cited-artifact-clone-reachability-v0.1/"
    "_probe_20260808_triad_census.post-20260808-173312.json"
)
PINNED_COMMIT = "08a28823f8291e85221b83ccdf414a9e43eb24e6"


def run(args: list[str], cwd: Path, check: bool = True) -> str:
    """Run a command, decoding as UTF-8 explicitly.

    text=True would decode via the console codepage (GBK on this host) and
    raise on any CJK byte, so the decode is spelled out.
    """
    result = subprocess.run(args, cwd=str(cwd), capture_output=True)
    out = result.stdout.decode("utf-8", "replace")
    if check and result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"{args} -> rc={result.returncode}\n{err}")
    return out


def prepare_clone(source: Path, work_dir: Path, commit: str) -> dict[str, object]:
    reused = work_dir.exists()
    if reused:
        origin = run(["git", "config", "--get", "remote.origin.url"], work_dir).strip()
        if Path(origin).resolve() != source.resolve():
            raise RuntimeError(
                f"--work-dir exists but its origin is {origin!r}, not {source}"
            )
    else:
        work_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", str(source), str(work_dir)], source, check=False)
    # The repo carries paths up to 244 chars and sets core.longpaths in its own
    # repo config, which a clone does not inherit: without this a Windows
    # checkout aborts partway. Recorded rather than hidden -- it is part of what
    # "reachable from a clean clone" costs on this platform.
    run(["git", "config", "core.longpaths", "true"], work_dir)
    run(["git", "checkout", "-f", "--quiet", commit], work_dir)
    run(["git", "clean", "-fdq"], work_dir)
    dirty = run(["git", "status", "--short"], work_dir).strip()
    return {
        "work_dir": str(work_dir),
        "reused_existing": reused,
        "head": run(["git", "rev-parse", "HEAD"], work_dir).strip(),
        "dirty_entries_after_checkout": 0 if not dirty else len(dirty.splitlines()),
    }


def census(repo: Path) -> dict[str, object]:
    stdout = run(["python", GENERATOR_RELPATH], repo)
    return json.loads(stdout.strip().splitlines()[-1])


def count_rows(path: Path) -> int:
    return len(path.read_bytes().splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Throwaway clone location. Must be OUTSIDE the source repo: a clone "
        "placed inside it would add thousands of untracked files and perturb "
        "the very disk_only bucket under measurement.",
    )
    parser.add_argument("--pinned-commit", default=PINNED_COMMIT)
    args = parser.parse_args()

    source = args.source_repo.resolve()
    work_dir = args.work_dir.resolve()
    if str(work_dir).startswith(str(source)):
        raise SystemExit(f"--work-dir {work_dir} is inside the source repo {source}")

    clone_meta = prepare_clone(source, work_dir, args.pinned_commit)

    cell_a = json.loads((source / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    cell_b = census(work_dir)

    live_ledger = source / LEDGER_RELPATH
    clone_ledger_physical_rows = count_rows(work_dir / LEDGER_RELPATH)
    shutil.copyfile(live_ledger, work_dir / LEDGER_RELPATH)
    cell_c = census(work_dir)

    def buckets(cell: dict[str, object]) -> dict[str, int]:
        return dict(cell["status_counts"])  # type: ignore[arg-type]

    all_keys = sorted(set(buckets(cell_a)) | set(buckets(cell_b)) | set(buckets(cell_c)))
    comparison = {
        key: {
            "A_committed_snapshot": buckets(cell_a).get(key, 0),
            "B_clean_clone": buckets(cell_b).get(key, 0),
            "C_clean_clone_live_ledger": buckets(cell_c).get(key, 0),
        }
        for key in all_keys
    }

    ledger_last_commit = run(
        ["git", "log", "-1", "--format=%H %ad %s", "--date=iso", "--", LEDGER_RELPATH],
        source,
    ).strip()

    payload = {
        "probe": "clone_recompute_vs_readability_20260808",
        "authority": "read_only_measurement",
        "question": (
            "Does committing an evidence snapshot make the measurement it records "
            "recomputable from a clean clone, or only readable?"
        ),
        "pinned_commit": args.pinned_commit,
        "clone": clone_meta,
        "cells": {
            "A_committed_snapshot": {
                "reproducible": "pinned (committed file)",
                "ledger_rows": cell_a["ledger_rows"],
                "total_citations": cell_a["total_citations"],
                "status_counts": buckets(cell_a),
            },
            "B_clean_clone": {
                "reproducible": "pinned (clean clone at pinned commit)",
                "ledger_rows": cell_b["ledger_rows"],
                "total_citations": cell_b["total_citations"],
                "status_counts": buckets(cell_b),
            },
            "C_clean_clone_live_ledger": {
                "reproducible": "shape only -- digits drift as the live ledger grows",
                "ledger_rows": cell_c["ledger_rows"],
                "total_citations": cell_c["total_citations"],
                "status_counts": buckets(cell_c),
            },
        },
        "comparison": comparison,
        "ledger_provenance": {
            "relpath": LEDGER_RELPATH,
            "physical_lines_in_worktree": count_rows(live_ledger),
            "physical_lines_at_pinned_commit": clone_ledger_physical_rows,
            "last_commit_touching_ledger": ledger_last_commit,
            "note": "physical line counts include the three unparseable rows that "
            "the generator's ledger_rows excludes.",
        },
        "analytic_note": (
            "cited_artifact_receipt_check._classify orders tracked_head -> "
            "history_only -> ignored -> disk_only -> missing, and reaches "
            "disk_only only for a path that exists on the filesystem while being "
            "absent from git. In a clean clone every on-disk path is tracked or "
            "ignored, so disk_only is identically zero there for any ledger. That "
            "bucket is not made reproducible by committing anything."
        ),
        "boundary": (
            "one repository, one pinned commit, one platform; no repeats. Cell C "
            "holds the tree constant and varies only ledger content, so it "
            "attributes the tree effect; it does not model a third party who also "
            "lacks the live ledger. Says nothing about whether the reviewed fix "
            "(887ec7b) is correct -- only about whether its live_ledger_check "
            "evidence is third-party recomputable."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "time_authority": "process_clock",
    }

    out = Path(__file__).with_suffix(".out.json")
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
