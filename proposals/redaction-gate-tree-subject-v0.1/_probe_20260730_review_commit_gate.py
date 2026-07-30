"""Read-only review probe for the landed commit-scoped redaction gate.

Two questions, both about whether the gate's receipt says what it scanned.

Q1 (undecodable blobs): make_occurrences scans content only when the blob
decodes as utf-8 or utf-16; otherwise content is silently skipped and only the
path is scanned. Count how many blobs in the landed commit tree fall in that
class, and how many bytes they hold. The receipt has no field for this.

Q2 (repository binding): the ruleset and the registry come from hardcoded
absolute paths, but every git invocation inherits the ambient cwd. Build a
throwaway repo in a temp dir, run the gate from there, and see whether the
receipt is distinguishable from one produced against this repository.

Nothing here writes to the repository under review.
"""
import hashlib
import importlib.util
import io
import json
import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution")
GATE_PATH = ROOT / "proposals" / "scaffold-opensource-export-v0.1" / "scan_only_gate.py"
LANDED = "8ef57756a7c5a31e0c73385e4dca02e08a6bcbeb"

SPEC = importlib.util.spec_from_file_location("gate_under_review", GATE_PATH)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def q1_undecodable_blobs():
    os.chdir(ROOT)
    entries = GATE.parse_ls_tree(GATE.resolve_commit(LANDED))
    blobs = GATE.read_blobs(entries)
    undecodable = []
    total_blob_bytes = 0
    for entry in entries:
        if entry["type"] != "blob":
            continue
        raw = blobs[entry["oid"]]
        total_blob_bytes += len(raw)
        try:
            raw.decode("utf-8")
            continue
        except UnicodeDecodeError:
            pass
        try:
            raw.decode("utf-16")
            framing = "utf-16"
        except UnicodeDecodeError:
            framing = "undecodable"
        if framing == "undecodable":
            undecodable.append({"path": entry["path"], "bytes": len(raw)})
    return {
        "tree_entries": len(entries),
        "blob_count": sum(e["type"] == "blob" for e in entries),
        "total_blob_bytes": total_blob_bytes,
        "undecodable_blob_count": len(undecodable),
        "undecodable_bytes": sum(u["bytes"] for u in undecodable),
        "undecodable_share_of_bytes": (
            round(sum(u["bytes"] for u in undecodable) / total_blob_bytes, 6)
            if total_blob_bytes else None
        ),
        "sample_paths": [u["path"] for u in undecodable[:8]],
        "receipt_has_field_for_this": (
            "undecodable_blob_count" in GATE.scan_commit.__doc__ if
            GATE.scan_commit.__doc__ else False
        ),
    }


def q1b_synthetic_miss():
    """Does an undecodable blob holding the token really scan CLEAN?"""
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        repo = base / "repo"
        repo.mkdir()
        patterns = base / "patterns.txt"
        registry = base / "registry.jsonl"
        token = "fixture-private-token"
        patterns.write_text(token + "\n", encoding="utf-8")
        registry.write_bytes(b"")
        run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        run("init", "-q")
        run("config", "user.email", "probe@example.invalid")
        run("config", "user.name", "Probe")
        # token in plain utf-8 preceded by a lone 0x80 -> not utf-8, odd length
        # so not utf-16 either.
        (repo / "leak.bin").write_bytes(b"\x80" + token.encode("utf-8"))
        run("add", "-A")
        run("commit", "-q", "-m", "undecodable blob carrying the token")
        previous_cwd = os.getcwd()
        previous_registry = GATE.DEFAULT_REGISTRY
        os.chdir(repo)
        GATE.DEFAULT_REGISTRY = str(registry)
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = GATE.main(["--commit", "HEAD",
                                "--private-strings", str(patterns)])
            payload = json.loads(out.getvalue()) if out.getvalue() else None
            # control: the same bytes as plain utf-8
            (repo / "leak.txt").write_bytes(token.encode("utf-8"))
            run("add", "-A")
            run("commit", "-q", "-m", "same token as utf-8")
            out2, err2 = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out2), contextlib.redirect_stderr(err2):
                rc2 = GATE.main(["--commit", "HEAD",
                                 "--private-strings", str(patterns)])
            payload2 = json.loads(out2.getvalue()) if out2.getvalue() else None
        finally:
            GATE.DEFAULT_REGISTRY = previous_registry
            os.chdir(previous_cwd)
    return {
        "undecodable_carrier_rc": rc,
        "undecodable_carrier_state": payload["state"] if payload else None,
        "undecodable_carrier_occurrences": payload["occurrence_count"] if payload else None,
        "undecodable_carrier_files_scanned": payload["files_scanned"] if payload else None,
        "utf8_control_rc": rc2,
        "utf8_control_state": payload2["state"] if payload2 else None,
        "utf8_control_occurrences": payload2["occurrence_count"] if payload2 else None,
    }


def q2_repo_binding():
    """Run the gate from a foreign repo; is the receipt distinguishable?"""
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        repo = base / "foreign"
        repo.mkdir()
        run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        run("init", "-q")
        run("config", "user.email", "probe@example.invalid")
        run("config", "user.name", "Probe")
        (repo / "unrelated.txt").write_text("nothing to do with WeilanSkillEvolution\n",
                                            encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "-m", "foreign repo")
        previous_cwd = os.getcwd()
        os.chdir(repo)
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = GATE.main(["--commit", "HEAD"])
            payload = json.loads(out.getvalue()) if out.getvalue() else None
            stderr_text = err.getvalue()
            # and: does the real repo's oid resolve here?
            landed_here = subprocess.run(
                ["git", "rev-parse", "--verify", LANDED + "^{commit}"],
                cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).returncode
        finally:
            os.chdir(previous_cwd)
    return {
        "foreign_repo_rc": rc,
        "foreign_repo_state": payload["state"] if payload else None,
        "foreign_repo_resolved_oid": payload["resolved_oid"] if payload else None,
        "foreign_repo_entries_scanned": payload["entries_scanned"] if payload else None,
        "foreign_repo_used_home_registry": GATE.DEFAULT_REGISTRY,
        "foreign_repo_used_home_patterns": GATE.DEFAULT_PRIVATE,
        "receipt_fields": sorted(payload.keys()) if payload else None,
        "receipt_names_a_repository": (
            any("repo" in k or "root" in k or "dir" in k
                for k in payload.keys()) if payload else None
        ),
        "landed_oid_resolves_in_foreign_repo_rc": landed_here,
        "stderr": stderr_text.strip(),
    }


if __name__ == "__main__":
    report = {
        "gate_path": str(GATE_PATH),
        "gate_sha256": hashlib.sha256(GATE_PATH.read_bytes()).hexdigest(),
        "landed_commit": LANDED,
        "q1_undecodable_blobs_in_landed_tree": q1_undecodable_blobs(),
        "q1b_synthetic_undecodable_carrier": q1b_synthetic_miss(),
        "q2_repository_binding": q2_repo_binding(),
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()
