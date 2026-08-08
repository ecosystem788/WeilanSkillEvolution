"""Reachability recheck for the section 7.2 universe of 5 co-signed finals.

Why this probe exists (2026-08-08, Claude, zero authority, read-only):

The cosign-5v11 rebaseline seat asks one question about the "5":
  "5 = section 7.2 full-universe: are the 5 co-signed finals STILL reachable from a ref?"

_audit_cosign_durability.py does NOT answer that question. It compares three
byte sources -- co-signed final vs worktree vs HEAD:<target> -- and never calls
rev-list. Its verdict token "DURABLE" therefore means "HEAD:<target> currently
equals the co-signed final" (a CURRENCY claim), and "SUPERSEDED" means "that
file has been edited since" (also a currency claim). Neither says whether the
signed bytes are still retrievable from the object graph.

That is exactly the conflation FINDING section 7.3 warned against:
  "new clauses must not merely say 'committed / in git'; they must say
   'reachable from a ref'"
-- and the instrument named _audit_cosign_durability.py, whose verdict column is
literally spelled DURABLE, is itself an instance of the pattern it warned about.

This probe reuses the same reachability rule the windowed probe already uses
(visible, not assumed): build a content-sha256 -> blob-oid table over ALL blob
objects (loose + unreachable included) via cat-file --batch-all-objects, and
judge each final:
  durable_reachable        object present AND in rev-list --objects --all --reflog
  present_unreachable      object present, no ref/reflog path (GC-eligible)
  absent                   no such blob object in this repo at all

Also reports, for contrast, the currency verdict the audit reports, so a reader
can see the two axes side by side and not read one as the other.

Zero authority. Read-only. Never writes git objects. Writes one .out.json.
Exits 0 always.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "_probe_20260808_five_final_reachability.out.json")

# Same 5 executions _audit_cosign_durability.py enumerates, copied verbatim so
# this probe stands alone if that file drifts.
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


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(args) + " -> " +
                           r.stderr.decode("utf-8", "replace")[:300])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def reachable_oids():
    out = set()
    for ln in git("rev-list", "--objects", "--all", "--reflog").splitlines():
        if ln.strip():
            out.add(ln.split()[0])
    return out


def all_git_blob_sha256():
    listing = git("cat-file", "--batch-all-objects",
                  "--batch-check=%(objectname) %(objecttype)")
    oids = [ln.split()[0] for ln in listing.splitlines()
            if ln.strip() and ln.split()[1] == "blob"]
    out = {}
    CH = 400
    for i in range(0, len(oids), CH):
        chunk = oids[i:i + CH]
        p = subprocess.run(["git", "-C", REPO, "cat-file", "--batch"],
                           input="\n".join(chunk).encode() + b"\n",
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        buf = p.stdout
        pos = 0
        for _ in chunk:
            nl = buf.index(b"\n", pos)
            parts = buf[pos:nl].decode().split()
            size = int(parts[2])
            body = buf[nl + 1:nl + 1 + size]
            out.setdefault(sha(body), parts[0])
            pos = nl + 1 + size + 1
    return out


def head_bytes(target):
    p = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + target],
                       capture_output=True)
    return p.stdout if p.returncode == 0 else None


def main():
    blobs = all_git_blob_sha256()
    reach = reachable_oids()
    head_oid = git("rev-parse", "HEAD").strip()

    rows = []
    for label, execdir, receipt in EXECUTIONS:
        state = load(os.path.join(execdir, "preflight-state.json"))
        post = load(os.path.join(execdir, receipt))
        target = state["target"]
        final = post.get("final_expected")

        oid = blobs.get(final)
        present = oid is not None
        is_reach = bool(oid) and oid in reach
        if is_reach:
            verdict = "durable_reachable"
        elif present:
            verdict = "present_unreachable"
        else:
            verdict = "absent"

        wt_path = os.path.join(REPO, target)
        wt = sha(open(wt_path, "rb").read()) if os.path.exists(wt_path) else "ABSENT"
        hb = head_bytes(target)
        head = sha(hb) if hb is not None else "ABSENT"
        currency = "head_equals_final" if head == final else "head_moved_on"

        rows.append({
            "label": label,
            "target": target,
            "final_sha256": final,
            "blob_oid": oid,
            "object_present": present,
            "reachable": is_reach,
            "reachability_verdict": verdict,
            "currency_verdict": currency,
            "worktree_sha256": wt,
            "head_sha256": head,
        })

    payload = {
        "probe": "_probe_20260808_five_final_reachability.py",
        "repo_head": head_oid,
        "universe": "FINDING section 7.2 five co-signed finals",
        "total": len(rows),
        "durable_reachable": len([r for r in rows if r["reachable"]]),
        "present_unreachable": len([r for r in rows
                                    if r["object_present"] and not r["reachable"]]),
        "absent": len([r for r in rows if not r["object_present"]]),
        "head_equals_final": len([r for r in rows
                                  if r["currency_verdict"] == "head_equals_final"]),
        "rows": rows,
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("repo HEAD: %s" % head_oid)
    print("universe : section 7.2 five co-signed finals")
    print()
    print("REACHABILITY axis (what the seat asks):")
    print("  durable_reachable   : %d" % payload["durable_reachable"])
    print("  present_unreachable : %d" % payload["present_unreachable"])
    print("  absent              : %d" % payload["absent"])
    print()
    print("CURRENCY axis (what _audit_cosign_durability.py reports):")
    print("  head_equals_final   : %d" % payload["head_equals_final"])
    print()
    for r in rows:
        print("%-20s %-16s %s" % (r["reachability_verdict"], r["currency_verdict"],
                                  r["target"]))
        print("     final=%s" % r["final_sha256"][:20])
        print("     oid  =%s" % r["blob_oid"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
