#!/usr/bin/env python3
"""Read-only: can the preflight witness prove consent PRECEDED execution?

Motivation. `proposals/ledger-timestamp-authority-v0.1/` established that the
`time` field in our append-only ledgers has no clock authority -- agents hand-write
it. So "consent 18:01:25 preceded execution 18:06:17" is, today, a self-declaration
by the same party that executed. Nothing machine-checkable backs the ordering.

But verify_binding.py's preflight witness fingerprints the working-tree bytes of
every non-target path at a moment that is provably before the target was mutated
(the sidecar/base capture happens in the same preflight call). If the ledger is
append-only, the witnessed content is a PREFIX of the ledger as it stands now.
Locating that prefix dates the ledger: every record inside it existed at preflight.

This probe locates the prefix by hashing every prefix boundary of the current
working-tree ledger and matching the witness fingerprint, then reports which
signature records fall inside it.
"""
import hashlib
import json
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
WITNESS_BLOB = "874e7bd02576846365cb34ad4bbf54a6fad74d5d"
PROPOSAL_TIME = "2026-07-31T17:50:11+09:00"
CONSENT_TIME = "2026-07-31T18:01:25+09:00"
RECEIPT_TIME = "2026-07-31T18:06:17+09:00"


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, check=True).stdout


def main():
    wit = git("cat-file", "blob", WITNESS_BLOB)
    want = None
    for line in wit.split(b"\n"):
        if line.startswith(b"S\t") and LEDGER.encode() in line:
            want = line.split(b"\t")[3].decode()
    out = {"witness_fingerprint_of_ledger": want}

    with open(rf"{REPO}\{LEDGER}".replace("/", "\\"), "rb") as fh:
        cur = fh.read()
    out["current_worktree"] = {"bytes": len(cur), "sha256": sha256(cur), "records": cur.count(b"\n")}

    # append-only => witnessed content should be a record-boundary prefix of cur
    h = hashlib.sha256()
    match_at = None
    consumed = 0
    for i, rec in enumerate(cur.split(b"\n")[:-1], start=1):
        h.update(rec + b"\n")
        consumed += len(rec) + 1
        if h.hexdigest() == want:
            match_at = i
            break
    out["prefix_match"] = {
        "found": match_at is not None,
        "records_in_prefix": match_at,
        "bytes_in_prefix": consumed if match_at else None,
    }

    if match_at is None:
        out["verdict"] = "witnessed bytes are NOT a record-boundary prefix of the current ledger"
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    # which of the three signature records are inside the witnessed prefix?
    inside = {}
    for i, rec in enumerate(cur.split(b"\n")[:-1], start=1):
        try:
            o = json.loads(rec.decode("utf-8"))
        except Exception:
            continue
        t = o.get("time")
        if t in (PROPOSAL_TIME, CONSENT_TIME, RECEIPT_TIME):
            inside[t] = {"line": i, "from": o.get("from"), "within_witnessed_prefix": i <= match_at}
    out["signature_records"] = inside
    out["verdict"] = {
        "proposal_predates_preflight": inside.get(PROPOSAL_TIME, {}).get("within_witnessed_prefix"),
        "consent_predates_preflight": inside.get(CONSENT_TIME, {}).get("within_witnessed_prefix"),
        "receipt_predates_preflight": inside.get(RECEIPT_TIME, {}).get("within_witnessed_prefix"),
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
