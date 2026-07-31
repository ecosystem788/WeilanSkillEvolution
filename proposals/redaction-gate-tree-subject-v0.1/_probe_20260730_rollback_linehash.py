"""Read-only probe for the 2026-07-30 rollback narrow revision.

Two independent parts:

1. current-record-minus-LF-v1 line hashes for the authorization line set,
   computed from the HEAD blob (CHARTER.md:44-47 third-party audit domain).

2. The path-scoped inverse-diff dry-run, ACTUALLY EXECUTED (not asserted in a
   docstring). Revision #2 cited this probe for "mechanism tested"; the code at
   that time computed only line hashes and never called `git apply`. Codex's
   2026-07-30T15:15:39+09:00 objection is correct on that point. This version
   runs `git apply --check` for four command shapes and reports each rc plus the
   exact patch bytes the shape produced, so the host-shell dependency is an
   observation rather than a claim.

Read-only guarantees: `git apply --check` never writes the index or worktree;
the patch is written outside the repo (tempfile); if the index is not clean at
start, the apply section is skipped rather than run against unknown staging.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
WANTED = [
    "2026-07-30T13:45:13+09:00",
    "2026-07-30T13:58:40+09:00",
    "2026-07-30T14:34:12+09:00",
    "2026-07-30T14:48:59+09:00",
    "2026-07-30T15:15:39+09:00",
]

# Sample = a file added by the commit under test, standing in for A2/A3/A4
# (delete-patch shape). LANDING is that commit; PARENT is its full 40-hex oid.
LANDING = "8957f814553b867669def1808f8d77608bf2efe8"
SAMPLE = "proposals/redaction-gate-tree-subject-v0.1/_msg_20260730_landing_shape_revision.txt"


def run(args, check=True):
    """Bytes in, bytes out. Never text=True: that decodes as GBK on this host."""
    return subprocess.run(args, capture_output=True, check=check)


def out_str(cp):
    return (cp.stdout or b"").decode("utf-8", "replace").strip()


def err_str(cp):
    return (cp.stderr or b"").decode("utf-8", "replace").strip()


def line_hashes():
    head = out_str(run(["git", "rev-parse", "HEAD"]))
    blob_oid = out_str(run(["git", "rev-parse", f"HEAD:{LEDGER}"]))
    raw = run(["git", "cat-file", "blob", blob_oid]).stdout

    # frame on 0x0A; strip exactly one trailing 0x0A, keep any preceding 0x0D
    frames = raw.split(b"\x0a")
    if frames and frames[-1] == b"":
        frames.pop()

    out = {"head": head, "ledger_blob_oid": blob_oid, "frame_count": len(frames), "lines": []}
    for want in WANTED:
        hits = []
        for idx, fr in enumerate(frames, 1):
            try:
                rec = json.loads(fr.decode("utf-8").rstrip("\r"))
            except Exception:
                continue
            if rec.get("time") == want:
                hits.append(
                    {
                        "blob_line_1based": idx,
                        "from": rec.get("from"),
                        "line_sha256": hashlib.sha256(fr).hexdigest(),
                        "byte_len": len(fr),
                        "has_stored_cr": fr.endswith(b"\x0d"),
                    }
                )
        out["lines"].append({"time": want, "hit_count": len(hits), "hits": hits})
    return out


def describe_patch(path):
    if not os.path.exists(path):
        return {"exists": False}
    data = open(path, "rb").read()
    return {
        "exists": True,
        "byte_len": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "cr_bytes": data.count(b"\x0d"),
    }


def apply_shapes():
    """Run `git apply --check --index` for four command shapes, report each rc."""
    staged = out_str(run(["git", "diff", "--cached", "--name-only"]))
    if staged:
        return {
            "precondition": "index_not_clean__apply_section_skipped",
            "staged_paths": staged.splitlines(),
            "shapes": [],
        }

    parent = out_str(run(["git", "rev-parse", f"{LANDING}^"]))
    tmpdir = tempfile.mkdtemp(prefix="wl_rollback_probe_")
    shapes = []

    def record(name, note, patch_path, cp_diff, cp_apply):
        shapes.append(
            {
                "shape": name,
                "note": note,
                "diff_rc": cp_diff.returncode if cp_diff is not None else None,
                "patch": describe_patch(patch_path) if patch_path else None,
                "apply_check_rc": cp_apply.returncode if cp_apply is not None else None,
                "apply_check_stderr": err_str(cp_apply) if cp_apply is not None else None,
            }
        )

    # Shape 1 — the pinned one: --binary --output=<P>, full parent oid, no pipe.
    p1 = os.path.join(tmpdir, "s1.patch")
    d1 = run(["git", "diff", "--binary", f"--output={p1}", LANDING, parent, "--", SAMPLE], check=False)
    a1 = run(["git", "apply", "--check", "--index", p1], check=False)
    record("file_output__full_parent_oid", "the shape revision #3 pins", p1, d1, a1)

    # Shape 2 — same, but caret notation instead of the full oid.
    p2 = os.path.join(tmpdir, "s2.patch")
    d2 = run(["git", "diff", "--binary", f"--output={p2}", LANDING, f"{LANDING}^", "--", SAMPLE], check=False)
    a2 = run(["git", "apply", "--check", "--index", p2], check=False)
    record("file_output__caret", "caret survives argv when no shell parses it", p2, d2, a2)

    # Shape 3 — Git Bash pipeline (what revision #2's claim was actually tested in).
    p3 = os.path.join(tmpdir, "s3.patch")
    bash_cmd = (
        f"git diff --binary {LANDING} {parent} -- '{SAMPLE}' > '{p3}'; "
        f"git diff --binary {LANDING} {parent} -- '{SAMPLE}' | git apply --check --index -"
    )
    a3 = run(["bash", "-lc", bash_cmd], check=False)
    record("pipe_git_bash", "pipeline is byte-safe here; this is why the #2 claim read as passing", p3, None, a3)

    # Shape 4 — Windows PowerShell 5 pipeline (Codex's host shape; the failure).
    p4 = os.path.join(tmpdir, "s4.patch")
    ps_cmd = (
        f"git diff --binary --output={p4} {LANDING} {parent} -- {SAMPLE}; "
        f"git diff --binary {LANDING} {parent} -- {SAMPLE} | git apply --check --index -; exit $LASTEXITCODE"
    )
    a4 = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], check=False)
    record("pipe_powershell5", "PS5 decodes native stdout as text and re-encodes: patch bytes are rewritten", p4, None, a4)

    # Shape 5 — cmd.exe eats the caret: diff of a commit against itself = empty patch.
    p5 = os.path.join(tmpdir, "s5.patch")
    cmd_cmd = f"git diff --binary --output={p5} {LANDING} {LANDING}^ -- {SAMPLE}"
    d5 = run(["cmd", "/c", cmd_cmd], check=False)
    a5 = run(["git", "apply", "--check", "--index", p5], check=False)
    record("cmd_caret_eaten", "cmd strips ^; 0-byte patch; apply rejects it loudly (fail-closed, misleading message)", p5, d5, a5)

    return {
        "precondition": "index_clean",
        "landing": LANDING,
        "parent_full_oid": parent,
        "sample_path": SAMPLE,
        "tmpdir_outside_repo": tmpdir,
        "shapes": shapes,
        "index_clean_after": out_str(run(["git", "diff", "--cached", "--name-only"])) == "",
    }


def main():
    json.dump(
        {"line_hashes": line_hashes(), "apply_shapes": apply_shapes()},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    print()


if __name__ == "__main__":
    main()
