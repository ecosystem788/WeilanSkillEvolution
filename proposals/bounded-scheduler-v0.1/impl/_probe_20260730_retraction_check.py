"""Read-only probe: independently verify Codex's 2026-07-30T03:17:03+09:00 retraction.

Checks, all from git objects / disk bytes, no writes:
  1. In commit 0c9c068's blob of peer-chat.jsonl, locate the 同意 line whose `time`
     is 2026-07-30T02:46:00+09:00 and extract every repo-relative-looking path
     that mentions `_probe_20260730_citation_forms_review`.
  2. For both the claimed-correct path and the receipt's recorded path, ask
     `git cat-file -e 0c9c068:<path>` -> in_tree / not_in_tree.
  3. Locate receipt line (time 2026-07-30T02:58:26+09:00) on disk and print its
     disclosure-table row that mentions that probe name.
  4. Report whether the receipt line is contained in commit 0c9c068's blob.
"""
import json
import re
import subprocess
import sys

REPO = "D:/WeilanSkillEvolution"
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
COMMIT = "0c9c0688c7289e0cd0006bba1e342cf927a1cd4c"
NAME = "_probe_20260730_citation_forms_review"
COSIGN_TIME = "2026-07-30T02:46:00+09:00"
RECEIPT_TIME = "2026-07-30T02:58:26+09:00"


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True)


def blob_lines(rev, path):
    p = git("cat-file", "blob", "%s:%s" % (rev, path))
    if p.returncode != 0:
        sys.exit("cat-file failed: %s" % p.stderr.decode("utf-8", "replace"))
    return p.stdout.decode("utf-8").splitlines()


def find_row(lines, stamp):
    for n, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if obj.get("time") == stamp:
            return n, obj, raw
    return None, None, None


out = {"commit": COMMIT}

lines = blob_lines(COMMIT, LEDGER)
out["blob_line_count"] = len(lines)

n, obj, raw = find_row(lines, COSIGN_TIME)
out["cosign_line_in_blob"] = n
if obj is None:
    out["cosign_found"] = False
else:
    text = obj.get("text", "")
    # every token containing the probe stem, bounded by whitespace/backtick/quote
    toks = re.findall(r"[0-9A-Za-z_./\\-]*" + NAME + r"[0-9A-Za-z_./\\-]*", text)
    out["cosign_citation_tokens"] = sorted(set(toks))

candidates = sorted(set(out.get("cosign_citation_tokens", []))) + [
    "proposals/cited-evidence-absent-from-tree-v0.1/%s.py" % NAME,
    "%s.py" % NAME,
]
tree = {}
for c in sorted(set(candidates)):
    p = git("cat-file", "-e", "%s:%s" % (COMMIT, c))
    tree[c] = "in_tree" if p.returncode == 0 else "not_in_tree"
out["at_landing_commit"] = tree

# does that path exist in ANY commit?
for c in sorted(tree):
    p = git("log", "--all", "--diff-filter=A", "--format=%H", "--", c)
    out.setdefault("ever_added_anywhere", {})[c] = \
        p.stdout.decode().split() or "never"

# receipt row: on disk
disk = open("%s/%s" % (REPO, LEDGER), encoding="utf-8").read().splitlines()
rn, robj, rraw = find_row(disk, RECEIPT_TIME)
out["receipt_line_on_disk"] = rn
if robj is not None:
    rtext = robj.get("text", "")
    rows = [ln.strip() for ln in rtext.split("\n") if NAME in ln]
    out["receipt_rows_mentioning_probe"] = rows
    out["receipt_in_landing_blob"] = any(rraw == b for b in lines)

# is the receipt in ANY commit yet?
p = git("log", "--all", "--format=%H", "-S", RECEIPT_TIME, "--", LEDGER)
out["commits_introducing_receipt_stamp"] = p.stdout.decode().split() or "none"
p = git("log", "--all", "--format=%H", "-S", "2026-07-30T03:17:03+09:00", "--", LEDGER)
out["commits_introducing_retraction_stamp"] = p.stdout.decode().split() or "none"

print(json.dumps(out, ensure_ascii=False, indent=1))
