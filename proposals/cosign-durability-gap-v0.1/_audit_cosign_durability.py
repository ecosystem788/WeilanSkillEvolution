"""Audit: for every co-signed precise-text execution, is the co-signed FINAL durable in git?

Reads each execution's preflight-state.json (target, base) and postcheck receipt
(final_expected/final_actual, ok), then compares three byte sources:
  - the co-signed final          (from the postcheck receipt)
  - the current worktree bytes   (what a reader sees today)
  - HEAD:<target> bytes          (what survives `git checkout -- <target>`)

Zero authority. Read-only. Prints a table; exits 0 always.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

EXECUTIONS = [
    ("cosign v0.6 (CHARTER §3)", "proposals/cosign-bytewise-binding-v0.1/execution-v0.6",
     "postcheck-rerun-after-archive.json"),
    ("cold-start scope kick", "proposals/codex-cold-start-scope-ambiguity-v0.1/execution",
     "postcheck-receipt.json"),
    ("cron wrapper portability", "proposals/cron-wrapper-portability-v0.1/execution",
     "postcheck-receipt.json"),
    ("CHARTER §6.1 daily push", "proposals/charter-daily-push-v0.1/execution",
     "postcheck-receipt.json"),
    ("cosign v0.7 (CONVENTION)", "proposals/cosign-bytewise-binding-v0.1/execution-v0.7",
     "postcheck-receipt.json"),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(path):
    with io.open(os.path.join(REPO, path), encoding="utf-8-sig") as fh:
        return json.load(fh)


def head_bytes(target):
    proc = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + target],
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def main():
    rows = []
    for label, execdir, receipt in EXECUTIONS:
        state = load(os.path.join(execdir, "preflight-state.json"))
        post = load(os.path.join(execdir, receipt))
        target = state["target"]
        final = post.get("final_expected")

        wt_path = os.path.join(REPO, target)
        wt = sha(open(wt_path, "rb").read()) if os.path.exists(wt_path) else "ABSENT"
        hb = head_bytes(target)
        head = sha(hb) if hb is not None else "ABSENT"

        if head == final:
            verdict = "DURABLE      "
        elif wt == final and head == state["base"]:
            verdict = "STRANDED@base"
        elif wt == final:
            verdict = "STRANDED     "
        elif head == final or wt == final:
            verdict = "MIXED        "
        else:
            verdict = "SUPERSEDED   "
        rows.append((verdict, label, target, post.get("ok"), final[:12],
                     wt[:12] if wt != "ABSENT" else wt,
                     head[:12] if head != "ABSENT" else head))

    print("verdict        postcheck.ok  final[:12]    worktree[:12] HEAD[:12]     target")
    for v, label, target, ok, f, w, h in rows:
        print("%s  %-12s  %-13s %-13s %-13s %s" % (v, ok, f, w, h, target))
        print("               (%s)" % label)
    stranded = [r for r in rows if r[0].startswith("STRANDED")]
    print("\n%d/%d co-signed finals are STRANDED (live only in the worktree)."
          % (len(stranded), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
