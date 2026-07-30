#!/usr/bin/env python3
"""Read-only independent review of Codex's 2026-07-30 porcelain landing receipt.

Checks, against commit a592eef only (no network, no writes):
  1. the ledger blob oid Codex named is the blob actually at that commit;
  2. lines 3039/3040 of that blob are the cited proposal/cosign records,
     and their current-record-minus-LF-v1 sha256 match the claimed digests;
  3. neither authorization line carries a trailing CR;
  4. each file-type citation's blob oid is the oid at that commit.
"""

import hashlib
import subprocess

COMMIT = "a592eef5db2af7698b48a2fe9a5394401a499981"
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
CLAIMED_LEDGER_BLOB = "e3377bb8fe3a5b2116c56c8c58ff0f6c7df6d06c"
CLAIMED = {
    3039: "2f3c07b080cf3e8cd7c94f0cf06f75764ebef5ff1835943800e3384c2294f030",
    3040: "297688a0374f07bdbd3ac03b57c35db88c351f638046d6dae6501b96de6482b5",
}
CLAIMED_FILE_BLOBS = {
    "proposals/charter-daily-push-v0.1/push_authorized_oid.py":
        "6c108248704aa50928bb7b1ff606a723293de800",
    "proposals/charter-daily-push-v0.1/test_push_authorized_oid.py":
        "e713db871b528e4b650cab5748b9306d7531bdc9",
    "proposals/charter-daily-push-v0.1/_probe_20260730_porcelain_shapes.py":
        "9554b213c1c7fc0db71b56388a04a883b409b17b",
    "proposals/charter-daily-push-v0.1/_probe_20260730_porcelain_shapes.out.json":
        "191d07d320458841943848584f3c187f5c5412d4",
}


def run(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, cwd="D:/WeilanSkillEvolution"
    )


def blob_oid_at_commit(path):
    proc = run("rev-parse", f"{COMMIT}:{path}")
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("ascii").strip()


def record_minus_lf_sha256(raw_line):
    """Convention: the record bytes with exactly one trailing LF removed."""
    body = raw_line[:-1] if raw_line.endswith(b"\n") else raw_line
    return hashlib.sha256(body).hexdigest(), body.endswith(b"\r")


def main():
    print("== 1. ledger blob identity ==")
    actual_blob = blob_oid_at_commit(LEDGER)
    print(f"claimed={CLAIMED_LEDGER_BLOB}")
    print(f"actual ={actual_blob}")
    print(f"match  ={actual_blob == CLAIMED_LEDGER_BLOB}")

    raw = run("cat-file", "blob", CLAIMED_LEDGER_BLOB).stdout
    lines = raw.split(b"\n")
    # split on LF keeps trailing empty element for a LF-terminated file
    print(f"blob bytes={len(raw)} records={len(lines) - 1}")

    print("\n== 2/3. authorization lines ==")
    for lineno, claimed_hash in CLAIMED.items():
        raw_line = lines[lineno - 1] + b"\n"
        digest, has_cr = record_minus_lf_sha256(raw_line)
        print(f"line {lineno}: sha256_match={digest == claimed_hash} "
              f"trailing_cr={has_cr}")
        print(f"  claimed={claimed_hash}")
        print(f"  actual ={digest}")
        head = raw_line[:110].decode("utf-8", "replace").replace("\n", "")
        print(f"  head   ={head}")

    print("\n== 4. file-type citations ==")
    for path, claimed in CLAIMED_FILE_BLOBS.items():
        actual = blob_oid_at_commit(path)
        print(f"{'OK ' if actual == claimed else 'BAD'} {path}")
        if actual != claimed:
            print(f"    claimed={claimed} actual={actual}")


if __name__ == "__main__":
    main()
