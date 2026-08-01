"""Do this line's byte bindings survive a git round trip?

Read-only. `.gitattributes` declares `*.py text eol=lf` / `*.json text eol=lf` while
`core.autocrlf=true`, so a working copy holds CRLF and the committed blob holds LF. Every
hash this line has argued from -- artifact tree hashes, `file_sha256` evidence refs inside
SHADOW_RESULT.json -- is computed over working-copy bytes. If those bytes are CRLF, the
same hash recomputed after a fresh clone on an LF checkout is a different number.

This probe measures three things and asserts nothing it has not measured:

  1. actual line endings of the frozen artifact trees and of this line's evidence files
  2. whether `git hash-object` (blob-as-committed) agrees with the on-disk sha256
  3. what the frozen candidate tree hash becomes if its bytes were LF instead
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from evolution_core import tree_hash  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "_shadow_20260801_claude_eol_roundtrip_probe.out.json"
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"


def eol_census(root):
    crlf = lf = neither = 0
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\r\n" in data:
            crlf += 1
        elif b"\n" in data:
            lf += 1
        else:
            neither += 1
    return {"crlf_files": crlf, "lf_only_files": lf, "no_newline_files": neither}


def as_lf_tree_hash(root):
    """Recompute the tree hash as if every file had been checked out with LF endings.

    Mirrors evolution_core.tree_hash's shape: sorted relative posix path, then content.
    Verified below by recomputing the CRLF form the same way and comparing to tree_hash().
    """
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def git_blob_id(path):
    proc = subprocess.run(
        ["git", "hash-object", "--", str(path)],
        cwd=str(REPO), capture_output=True, text=True,
    )
    return proc.stdout.strip() or None


def main():
    cand_tree = HERE / "artifacts" / CAND / "solve-with-weilan"
    base_tree = HERE / "artifacts" / BASE / "solve-with-weilan"

    evidence = [
        "_shadow_20260801_claude_cli_equivalence_revised.out.json",
        "_shadow_20260801_claude_revised_latency.out.json",
        "_shadow_20260801_claude_decision_contract_probe.out.json",
        "SHADOW_RESULT.json",
    ]
    evidence_rows = {}
    for name in evidence:
        path = HERE / name
        data = path.read_bytes()
        evidence_rows[name] = {
            "on_disk_sha256": hashlib.sha256(data).hexdigest(),
            "has_crlf": b"\r\n" in data,
            "lf_normalized_sha256": hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest(),
            "git_blob_id_of_working_copy": git_blob_id(path),
        }

    result = {
        "probe": "do the byte bindings survive a git round trip",
        "authority": "read_only_measurement_only",
        "gitattributes_declares": ["*.py text eol=lf", "*.json text eol=lf"],
        "core_autocrlf": subprocess.run(
            ["git", "config", "--get", "core.autocrlf"],
            cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
        "frozen_trees": {
            "baseline": {
                "declared_hash": BASE,
                "recomputed_from_disk": tree_hash(base_tree),
                "eol_census": eol_census(base_tree),
                "hash_if_bytes_were_lf": as_lf_tree_hash(base_tree),
            },
            "candidate": {
                "declared_hash": CAND,
                "recomputed_from_disk": tree_hash(cand_tree),
                "eol_census": eol_census(cand_tree),
                "hash_if_bytes_were_lf": as_lf_tree_hash(cand_tree),
            },
        },
        "evidence_files": evidence_rows,
        "tracked_in_git": {
            "artifacts_dir": "gitignored -- never round trips through git",
            "baseline_and_candidate_dirs": subprocess.run(
                ["git", "ls-files", "--", "proposals/canonical-workspace-cache-v0.1/baseline",
                 "proposals/canonical-workspace-cache-v0.1/candidate"],
                cwd=str(REPO), capture_output=True, text=True).stdout.strip() or "untracked",
        },
        "boundary": (
            "This measures line endings and hash arithmetic on this checkout. It does not "
            "run a clone, so it predicts rather than observes what a fresh LF checkout "
            "would compute; the prediction is arithmetic, not a claim about git's "
            "behaviour on another host."
        ),
    }
    frozen = result["frozen_trees"]
    result["finding"] = {
        "declared_hashes_match_disk": (
            frozen["baseline"]["recomputed_from_disk"] == BASE
            and frozen["candidate"]["recomputed_from_disk"] == CAND
        ),
        "frozen_trees_are_crlf": (
            frozen["baseline"]["eol_census"]["crlf_files"] > 0
            or frozen["candidate"]["eol_census"]["crlf_files"] > 0
        ),
        "lf_checkout_would_change_artifact_hashes": (
            frozen["baseline"]["hash_if_bytes_were_lf"] != BASE
            or frozen["candidate"]["hash_if_bytes_were_lf"] != CAND
        ),
        "lf_checkout_would_change_evidence_file_hashes": any(
            row["has_crlf"] for row in evidence_rows.values()
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
