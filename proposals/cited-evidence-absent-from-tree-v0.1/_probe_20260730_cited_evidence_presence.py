"""Read-only census: do the repo paths cited by double-sign authorization lines
exist in the tree of the commit that transaction landed in?

Method (stated so a third party can re-run without trusting this output):

1. Source = proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl, read as raw bytes
   and framed on 0x0A (the current-record-minus-LF-v1 framing CHARTER 3 names).
2. A transaction = a record whose text contains an execution-receipt marker AND a
   bare 40-hex string that `git cat-file -t` reports as a commit. That commit is the
   landing commit.
3. Its authorization lines = records whose `time` value appears verbatim, quoted or
   bare, in the receipt text, excluding the receipt's own time.
4. Cited paths = repo-relative-looking paths extracted from the authorization lines'
   text by a conservative regex (segments of [A-Za-z0-9._-] joined by `/`, ending in a
   known artifact extension). Paths are reported, not filtered by "should be there".
5. For each cited path: `git cat-file -e <landing_commit>:<path>` -> present/absent in
   the landing tree; plus whether the path exists anywhere in history at all
   (`git log --all --diff-filter=A -- <path>`), and whether it exists on disk now.

Nothing here writes. `time` values are treated only as identity keys inside an
append-only file, never as clock readings (ledger-timestamp-authority-v0.1).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHAT = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.jsonl"

RECEIPT_MARKERS = ("执行收据",)  # 执行收据
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
ISO_TIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2})?")
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])"
    r"((?:[A-Za-z0-9][A-Za-z0-9._-]*/)+[A-Za-z0-9][A-Za-z0-9._-]*"
    r"\.(?:md|py|json|jsonl|tsv|txt|toml|yml|yaml))"
)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def records() -> list[tuple[int, dict]]:
    raw = CHAT.read_bytes()
    out = []
    for n, chunk in enumerate(raw.split(b"\n"), 1):
        if not chunk.strip():
            continue
        try:
            out.append((n, json.loads(chunk.decode("utf-8"))))
        except Exception:
            continue  # counted separately below
    return out


def main() -> int:
    rows = records()
    by_time: dict[str, list[tuple[int, dict]]] = {}
    for n, r in rows:
        t = r.get("time")
        if isinstance(t, str):
            by_time.setdefault(t, []).append((n, r))

    head = git("rev-parse", "HEAD").stdout.strip()
    print("repo=%s" % REPO)
    print("HEAD=%s" % head)
    print("chat records parsed=%d of %d raw frames" % (len(rows), len(CHAT.read_bytes().split(b"\n"))))
    print("=" * 72)

    transactions = []
    for n, r in rows:
        text = r.get("text") or ""
        if not any(m in text for m in RECEIPT_MARKERS):
            continue
        for oid in dict.fromkeys(HEX40.findall(text)):
            if git("cat-file", "-t", oid).stdout.strip() == "commit":
                transactions.append((n, r, oid))
                break

    print("execution receipts naming a real commit: %d" % len(transactions))
    print("=" * 72)

    totals = {"cited": 0, "present": 0, "absent": 0, "never_in_history": 0}
    detail_absent = []

    for n, r, oid in transactions:
        text = r.get("text") or ""
        own = r.get("time")
        stamps = [s for s in dict.fromkeys(ISO_TIME.findall(text)) if s != own]
        auth_lines = []
        for s in stamps:
            for m, rec in by_time.get(s, []):
                if m != n:
                    auth_lines.append((m, rec))
        if not auth_lines:
            print("[line %s] receipt %s -> commit %s : NO authorization lines resolved"
                  % (n, own, oid[:8]))
            print("-" * 72)
            continue

        cited: dict[str, list[int]] = {}
        for m, rec in auth_lines:
            for p in PATH_RE.findall(rec.get("text") or ""):
                cited.setdefault(p, []).append(m)

        print("[line %s] receipt %s -> commit %s" % (n, own, oid[:8]))
        print("  authorization lines: %s" % ", ".join(str(m) for m, _ in auth_lines))
        print("  distinct cited paths: %d" % len(cited))
        for p in sorted(cited):
            totals["cited"] += 1
            in_tree = git("cat-file", "-e", "%s:%s" % (oid, p)).returncode == 0
            if in_tree:
                totals["present"] += 1
                continue
            totals["absent"] += 1
            ever = git("log", "--all", "--diff-filter=A", "--format=%h", "--", p).stdout.strip()
            on_disk = (REPO / p).exists()
            if not ever:
                totals["never_in_history"] += 1
            print("    ABSENT-IN-TREE %s" % p)
            print("       cited by line(s) %s | ever added to history: %s | on disk now: %s"
                  % (cited[p], ever.splitlines()[:1] or "NEVER", on_disk))
            detail_absent.append((oid[:8], p, bool(ever), on_disk))
        print("-" * 72)

    print("=" * 72)
    print("TOTALS  cited=%(cited)d  present_in_landing_tree=%(present)d  "
          "absent=%(absent)d  of_which_never_in_any_commit=%(never_in_history)d" % totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
