"""Read-only probe: does scan_push_manifest.py currently pass an impostor object?

Independent review premise-check for Codex's 2026-07-29T04:57:50+09:00 proposal
(recompute OID from type+payload inside scan_push_manifest.py).

The proposal is only load-bearing if `git cat-file --batch` echoes the REQUESTED
object id when the bytes at that path recompute to a different id.  If git
instead echoed the recomputed name, the existing order check
(`object_id != expected_id` -> RuntimeError) would already be fail-closed and
the补强 would be redundant.

Builds a throwaway repo under TEMP, corrupts one loose object into a
well-formed impostor, then runs the LIVE scanner against it.  Never touches
WeilanSkillEvolution objects.  Deletes the temp repo unless --keep.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zlib

SCANNER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "charter-daily-push-v0.1", "scan_push_manifest.py")


def git(repo, *args, input=None, check=True):
    return subprocess.run(["git", "-C", repo, *args], input=input,
                          capture_output=True, check=check)


def build_repo(root):
    repo = os.path.join(root, "src")
    os.makedirs(repo)
    git(repo if os.path.isdir(os.path.join(repo, ".git")) else root,
        "init", "-q", "-b", "main", repo)
    git(repo, "config", "user.name", "probe")
    git(repo, "config", "user.email", "probe@local")
    git(repo, "config", "core.autocrlf", "false")
    env = {"GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
           "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00"}
    for key, value in env.items():
        os.environ[key] = value

    with open(os.path.join(repo, "A.txt"), "wb") as fh:
        fh.write(b"REAL-BASE\n")
    git(repo, "add", "A.txt")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "branch", "baseline")

    with open(os.path.join(repo, "B.txt"), "wb") as fh:
        fh.write(b"REAL-PAYLOAD\n")
    git(repo, "add", "B.txt")
    git(repo, "commit", "-q", "-m", "head")
    return repo


def loose_path(repo, oid):
    return os.path.join(repo, ".git", "objects", oid[:2], oid[2:])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)

    root = tempfile.mkdtemp(prefix="wl-impostor-")
    out = {"temp_root": root, "scanner": SCANNER}
    try:
        repo = build_repo(root)
        out["object_format"] = git(
            repo, "rev-parse", "--show-object-format").stdout.decode().strip()

        target = git(repo, "rev-parse", "HEAD:B.txt").stdout.decode().strip()
        out["target_oid"] = target
        out["target_is_loose"] = os.path.isfile(loose_path(repo, target))

        # Baseline: live scanner on the healthy repo.
        pre = subprocess.run([sys.executable, SCANNER, "--remote-ref", "baseline"],
                             cwd=repo, capture_output=True)
        out["healthy_scanner_rc"] = pre.returncode
        if pre.returncode == 0:
            receipt = json.loads(pre.stdout.decode("utf-8"))
            out["healthy_clean"] = receipt["clean"]
            out["healthy_manifest_digest"] = receipt["manifest_digest"]
            out["healthy_closure_objects"] = receipt["closure_objects"]

        # Swap the bytes at the target's path for a well-formed impostor.
        impostor_payload = b"IMPOSTOR-PAYLOAD\n"
        impostor_body = b"blob %d\x00" % len(impostor_payload) + impostor_payload
        out["impostor_true_oid"] = hashlib.sha1(impostor_body).hexdigest()
        victim = loose_path(repo, target)
        os.chmod(victim, 0o666)  # loose objects land read-only
        with open(victim, "wb") as fh:
            fh.write(zlib.compress(impostor_body))

        # Q1: what does cat-file --batch echo for the requested (now-wrong) oid?
        batch = git(repo, "cat-file", "--batch",
                    input=target.encode() + b"\n", check=False)
        out["batch_rc"] = batch.returncode
        out["batch_header"] = batch.stdout.split(b"\n", 1)[0].decode(
            "utf-8", "replace")
        out["batch_echoes_requested_oid"] = out["batch_header"].split(
            " ")[0] == target if batch.stdout else None

        # Cross-check with an independent authority.
        fsck = git(repo, "fsck", check=False)
        out["fsck_rc"] = fsck.returncode
        out["fsck_mentions_true_oid"] = out["impostor_true_oid"] in (
            fsck.stdout + fsck.stderr).decode("utf-8", "replace")

        # Q2: does the LIVE scanner still emit a clean receipt?
        post = subprocess.run([sys.executable, SCANNER, "--remote-ref", "baseline"],
                              cwd=repo, capture_output=True)
        out["impostor_scanner_rc"] = post.returncode
        out["impostor_scanner_stderr_tail"] = post.stderr.decode(
            "utf-8", "replace")[-300:]
        if post.returncode in (0, 1) and post.stdout:
            receipt = json.loads(post.stdout.decode("utf-8"))
            out["impostor_clean"] = receipt["clean"]
            out["impostor_manifest_digest"] = receipt["manifest_digest"]
            entry = [e for e in receipt["manifest"]
                     if e["object_id"] == target]
            out["impostor_entry"] = entry[0] if entry else None
            out["digest_changed_vs_healthy"] = (
                receipt["manifest_digest"] != out.get("healthy_manifest_digest"))

        # Q3: an EQUAL-LENGTH impostor.  `bytes` is the only payload-derived
        # field in the manifest, so if length is preserved the digest cannot
        # move at all -- that is the sharp form of "digest binds P_path".
        eq_payload = b"IMPOSTOR-PAY\n"          # 13 == len(b"REAL-PAYLOAD\n")
        eq_body = b"blob %d\x00" % len(eq_payload) + eq_payload
        out["equal_len_true_oid"] = hashlib.sha1(eq_body).hexdigest()
        os.chmod(victim, 0o666)
        with open(victim, "wb") as fh:
            fh.write(zlib.compress(eq_body))
        eq = subprocess.run([sys.executable, SCANNER, "--remote-ref", "baseline"],
                            cwd=repo, capture_output=True)
        out["equal_len_scanner_rc"] = eq.returncode
        if eq.returncode in (0, 1) and eq.stdout:
            receipt = json.loads(eq.stdout.decode("utf-8"))
            out["equal_len_clean"] = receipt["clean"]
            out["equal_len_manifest_digest"] = receipt["manifest_digest"]
            out["equal_len_digest_identical_to_healthy"] = (
                receipt["manifest_digest"] == out.get("healthy_manifest_digest"))

        out["verdict"] = {
            "existing_order_check_catches_impostor":
                out.get("batch_echoes_requested_oid") is False,
            "live_scanner_emits_receipt_over_impostor_bytes":
                out.get("impostor_scanner_rc") == 0,
        }
    finally:
        if args.keep:
            out["kept"] = True
        else:
            shutil.rmtree(root, ignore_errors=True)
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
