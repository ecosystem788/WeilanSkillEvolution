"""Census: enumerate the FULL set of co-signed precise-text executions from the
governance source of record (peer-chat.jsonl), not from a hand-written list.

Why: `_audit_cosign_durability.py` iterates a hard-coded EXECUTIONS list of 5.
Seven `execution/preflight-state.json` exist on disk. And at least one co-signed
precise-text execution (wake_prompt_codex.md, 2026-07-28) left NO execution
artifact at all, so it is invisible to any enumeration anchored on that artifact.
The denominator has therefore never been verified.

Enumeration rule (mechanical, stated so recall is visible rather than assumed):
  a co-sign event = a peer-chat message that
    (a) carries an agreement marker  -- 同意 in the leading header segment, and
    (b) contains at least one 64-hex sha256 digest.
CONVENTION's five-binding rule requires a precise-text 【同意】 to name the
signed final digest, so (b) is a structural consequence of the contract, not a
stylistic guess.

Recall is reported, not assumed: every 同意 message WITHOUT a digest is printed
as a near-miss so a reader can see exactly what the rule drops.

Zero authority. Read-only. Never writes git objects. Exits 0 always.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CHAT = os.path.join(REPO, "proposals", "bounded-scheduler-v0.1", "impl",
                    "peer-chat.jsonl")

SHA256 = re.compile(r"\b[0-9a-f]{64}\b")
# a truncated digest as the ledger habitually prints them: 8+ hex then an ellipsis
SHA_TRUNC = re.compile(r"\b[0-9a-f]{8,63}(?=[.…])")
AGREE = re.compile(r"同意")          # 同意
OPPOSE = re.compile(r"反对")         # 反对
STRONG = re.compile(r"强绑定")   # 强绑定
EXACT = re.compile(r"精确文本")  # 精确文本


def header(text):
    """The leading bracketed segment, where the speech act is declared."""
    m = re.match(r"\s*【([^】]{0,120})】", text)
    return m.group(1) if m else text[:60]


def load_rows():
    rows = []
    with io.open(CHAT, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((i, json.loads(line)))
            except ValueError:
                rows.append((i, {"from": "PARSE_ERROR", "text": "", "time": ""}))
    return rows


def on_disk_executions():
    found = []
    for root, dirs, files in os.walk(os.path.join(REPO, "proposals")):
        if ".git" in root.split(os.sep):
            continue
        if "preflight-state.json" in files:
            rel = os.path.relpath(root, REPO).replace("\\", "/")
            try:
                with io.open(os.path.join(root, "preflight-state.json"),
                             encoding="utf-8-sig") as fh:
                    st = json.load(fh)
            except Exception as exc:          # noqa: BLE001 - report, never raise
                st = {"_load_error": str(exc)}
            found.append((rel, st))
    return sorted(found)


def main():
    rows = load_rows()
    agree_hits, agree_misses = [], []
    for ln, r in rows:
        text = r.get("text", "") or ""
        head = header(text)
        if not AGREE.search(head) or OPPOSE.search(head):
            continue
        digests = SHA256.findall(text)
        trunc = SHA_TRUNC.findall(text)
        rec = {
            "line": ln,
            "from": r.get("from"),
            "time": r.get("time"),
            "header": head,
            "strong": bool(STRONG.search(text)),
            "exact": bool(EXACT.search(text)),
            "full_digests": sorted(set(digests)),
            "trunc_digests": sorted(set(trunc)),
        }
        if digests or trunc:
            agree_hits.append(rec)
        else:
            agree_misses.append(rec)

    print("== source ==")
    print("peer-chat rows parsed: %d" % len(rows))
    proc = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                          capture_output=True)
    print("repo HEAD: %s" % proc.stdout.decode().strip())

    print("\n== A. co-sign candidates (agreement header + at least one digest) : %d =="
          % len(agree_hits))
    for rec in agree_hits:
        print("  L%-5d %-6s %s  strong=%-5s exact=%-5s full=%d trunc=%d"
              % (rec["line"], rec["from"], rec["time"], rec["strong"],
                 rec["exact"], len(rec["full_digests"]), len(rec["trunc_digests"])))
        print("         %s" % rec["header"])

    print("\n== B. near-misses (agreement header, NO digest at all) : %d =="
          % len(agree_misses))
    print("   (printed so the rule's recall is inspectable, not assumed)")
    for rec in agree_misses:
        print("  L%-5d %-6s %s  %s"
              % (rec["line"], rec["from"], rec["time"], rec["header"]))

    disk = on_disk_executions()
    print("\n== C. execution dirs holding preflight-state.json on disk : %d =="
          % len(disk))
    for rel, st in disk:
        print("  %-64s target=%s" % (rel, st.get("target", st.get("_load_error"))))

    print("\n== D. denominator comparison ==")
    print("  hand-written list inside _audit_cosign_durability.py : 5")
    print("  execution dirs on disk                               : %d" % len(disk))
    print("  co-sign candidates in the governance ledger          : %d" % len(agree_hits))
    print("\n  A >= C is the finding: the ledger records co-signs that left no artifact.")
    print("  This script does NOT claim A is the true full set -- it claims the")
    print("  full set is unbounded from below by A, and that 5 was never derived")
    print("  from any of these sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
