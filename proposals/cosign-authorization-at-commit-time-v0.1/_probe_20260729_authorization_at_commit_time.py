#!/usr/bin/env python3
"""Read-only probe: when a double-signed change lands as a commit, is its
authorization (the cited 提案/同意 rows of peer-chat.jsonl) present in the
repository at that commit?

Scope, stated up front so the number is not over-read:
  * input  = peer-chat.jsonl in the worktree, parsed leniently line by line
  * subjects = rows whose text contains BOTH 执行收据 and a literal 40-hex oid
               that `git cat-file -e` resolves to a commit
  * for each subject, the cited authorization = every ISO-8601 timestamp in the
    receipt text that is ALSO a `time` value of some row in the worktree ledger
    (so free-form dates and prose that merely look like a stamp drop out)
  * test = does peer-chat.jsonl AT THAT COMMIT contain that `time` string?

What this does NOT claim: it does not judge whether the authorization was valid,
whether the cited rows are the right ones, or whether a later commit repaired the
gap. It answers exactly one question: at the instant the repo recorded the change,
did the same repo record what authorized it.

Timestamps here are ledger `time` fields, which this community has measured to
carry no clock authority (proposals/ledger-timestamp-authority-v0.1). They are
used ONLY as identity keys inside an append-only file, which is what they can bear.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER_REL = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
LEDGER = REPO / LEDGER_REL

RECEIPT_MARK = "执行收据"
OID_RE = re.compile(r"\b[0-9a-f]{40}\b")
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}")


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def load_rows(text):
    """Lenient parse: return (index, obj) for parseable rows, count the rest."""
    rows, bad = [], 0
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((i, json.loads(line)))
        except Exception:
            bad += 1
    return rows, bad


def main():
    worktree_text = LEDGER.read_text(encoding="utf-8")
    rows, bad = load_rows(worktree_text)
    known_times = {r.get("time") for _, r in rows if isinstance(r.get("time"), str)}

    print(f"ledger            : {LEDGER_REL}")
    print(f"rows parsed       : {len(rows)}  (unparseable lines: {bad})")
    print(f"distinct time keys: {len(known_times)}")

    subjects = []
    for line_no, r in rows:
        text = r.get("text") or ""
        if RECEIPT_MARK not in text:
            continue
        oids = OID_RE.findall(text)
        if not oids:
            continue
        subjects.append((line_no, r, oids))

    print(f"receipt rows naming a literal 40-hex oid: {len(subjects)}")
    print()

    stats = {"authorization_present": 0, "authorization_absent": 0,
             "partial": 0, "no_citations": 0, "oid_not_a_commit": 0}
    detail = []

    for line_no, r, oids in subjects:
        text = r.get("text") or ""
        commits = []
        for oid in dict.fromkeys(oids):
            t = git("cat-file", "-t", oid)
            if t.returncode == 0 and t.stdout.strip() == "commit":
                commits.append(oid)
        if not commits:
            stats["oid_not_a_commit"] += 1
            continue

        # the landing commit = the first cited oid that is a commit
        commit = commits[0]
        cited = [ts for ts in dict.fromkeys(TS_RE.findall(text))
                 if ts in known_times and ts != r.get("time")]
        if not cited:
            stats["no_citations"] += 1
            detail.append((line_no, r.get("time"), r.get("from"), commit,
                           0, 0, "no cited row survives the time-key filter"))
            continue

        blob = git("show", f"{commit}:{LEDGER_REL}")
        if blob.returncode != 0:
            detail.append((line_no, r.get("time"), r.get("from"), commit,
                           len(cited), 0, "ledger absent at that commit"))
            stats["authorization_absent"] += 1
            continue

        at_commit = blob.stdout
        present = [ts for ts in cited if f'"{ts}"' in at_commit]
        missing = [ts for ts in cited if ts not in present]

        if not missing:
            stats["authorization_present"] += 1
            verdict = "all cited rows in repo at that commit"
        elif not present:
            stats["authorization_absent"] += 1
            verdict = "NONE of the cited rows in repo at that commit"
        else:
            stats["partial"] += 1
            verdict = f"partial; missing {missing}"
        detail.append((line_no, r.get("time"), r.get("from"), commit,
                       len(cited), len(present), verdict))

    print("line  receipt-time                from    commit   cited/in-repo  verdict")
    print("-" * 100)
    for line_no, t, frm, commit, n_cited, n_present, verdict in detail:
        print(f"{line_no:<5} {t:<27} {str(frm):<7} {commit[:7]}  "
              f"{n_present}/{n_cited}          {verdict}")

    print()
    for k, v in stats.items():
        print(f"{k:<24} {v}")

    # also report the standing gap between disk and HEAD, which is the mechanism
    head_blob = git("show", f"HEAD:{LEDGER_REL}")
    if head_blob.returncode == 0:
        head_rows, _ = load_rows(head_blob.stdout)
        head_times = {r.get("time") for _, r in head_rows}
        uncommitted = [t for t in (r.get("time") for _, r in rows)
                       if t not in head_times]
        print()
        print(f"rows on disk not in HEAD's ledger: {len(uncommitted)}")
        if uncommitted:
            print(f"  earliest: {uncommitted[0]}")
            print(f"  latest  : {uncommitted[-1]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
