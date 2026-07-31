"""Independent post-landing verification of ROADMAP North Star commit 18a16d0.

Read-only. Verifies acceptance item 5 of Claude's consent 2026-07-31T20:43:47+09:00:
new section position + verbatim text, non-scope byte conservation, authorization
visibility inside the landing commit, and the disclosure table blobs.
"""
import hashlib
import json
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
COMMIT = "18a16d0e241094fb2458e916dc570890c3ede4e0"
PARENT = "6bc3ea86ac40878b5821813392399c9d1aa07f41"


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(" ".join(args) + " -> " + p.stderr.decode("utf-8", "replace"))
    return p.stdout


def sha256(b):
    return hashlib.sha256(b).hexdigest()


out = []


def chk(name, ok, detail=""):
    out.append({"check": name, "ok": bool(ok), "detail": detail})


# --- 1. commit identity ------------------------------------------------------
parent_actual = git("rev-parse", COMMIT + "^").decode().strip()
chk("parent == 6bc3ea8", parent_actual == PARENT, parent_actual)

name_status = git("diff", "--name-status", PARENT, COMMIT).decode("utf-8").strip()
chk("changed paths", True, name_status.replace("\n", " ; "))

numstat = git("diff", "--numstat", PARENT, COMMIT, "--", "ROADMAP.md").decode().strip()
chk("ROADMAP numstat == 8 additions / 0 deletions", numstat.split("\t")[:2] == ["8", "0"], numstat)

# --- 2. base / final blobs ---------------------------------------------------
base_blob = git("rev-parse", PARENT + ":ROADMAP.md").decode().strip()
final_blob = git("rev-parse", COMMIT + ":ROADMAP.md").decode().strip()
base_bytes = git("cat-file", "blob", PARENT + ":ROADMAP.md")
final_bytes = git("cat-file", "blob", COMMIT + ":ROADMAP.md")
chk("base blob c226ac8a...", base_blob == "c226ac8ab18803bcbe8f3d3f5ddf7113d6b56219", base_blob)
chk("final blob 9e8e9544...", final_blob == "9e8e9544e7f6558388d100ff9e1940dddc3ff9fc", final_blob)
chk("base sha256 bd32917c...",
    sha256(base_bytes) == "bd32917c74701e672187d3270b57ee9124e09238949609536d69048623ba5031",
    sha256(base_bytes) + " / %d bytes" % len(base_bytes))
chk("final sha256 7ac491da...",
    sha256(final_bytes) == "7ac491da805a940bd61030e9952e873e85683e20398f0f3e2fb21fc8aec8d274",
    sha256(final_bytes) + " / %d bytes" % len(final_bytes))

# --- 3. conservation: final minus the inserted block == base -----------------
base_lines = base_bytes.split(b"\n")
final_lines = final_bytes.split(b"\n")
# locate the contiguous inserted run
import difflib

sm = difflib.SequenceMatcher(None, base_lines, final_lines, autojunk=False)
ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
chk("exactly one non-equal diff hunk", len(ops) == 1, str(ops))
if len(ops) == 1:
    tag, i1, i2, j1, j2 = ops[0]
    chk("hunk is pure insertion", tag == "insert" and i1 == i2, "%s base[%d:%d] final[%d:%d]" % (tag, i1, i2, j1, j2))
    inserted = final_lines[j1:j2]
    chk("inserted line count == 8", len(inserted) == 8, str(len(inserted)))
    residue = final_lines[:j1] + final_lines[j2:]
    chk("final minus inserted == base byte-for-byte", residue == base_lines,
        "residue sha256=" + sha256(b"\n".join(residue)))
    chk("insertion point: preceding line is blank & following is '## Version namespaces'",
        final_lines[j1 - 1] == b"" and final_lines[j2] == b"## Version namespaces",
        repr(final_lines[j1 - 1])[:40] + " | " + repr(final_lines[j2])[:60])
    inserted_text = b"\n".join(inserted).decode("utf-8")
else:
    inserted_text = ""

chk("'## North Star' occurs exactly once in final",
    final_bytes.count(b"## North Star") == 1, str(final_bytes.count(b"## North Star")))
chk("'## Version namespaces' occurs exactly once in final",
    final_bytes.count(b"## Version namespaces") == 1, str(final_bytes.count(b"## Version namespaces")))

# --- 4. inserted text vs the quoted section in the signed proposal -----------
LEDGER = REPO + r"\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl"
ledger_commit_bytes = git("cat-file", "blob", COMMIT + ":proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl")
ledger_blob = git("rev-parse", COMMIT + ":proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl").decode().strip()
chk("peer-chat blob in commit e4259e31...",
    ledger_blob == "e4259e3114b4df407d758aa99c06054c5b6773d7", ledger_blob)

raw_rows = ledger_commit_bytes.split(b"\n")
if raw_rows and raw_rows[-1] == b"":
    raw_rows = raw_rows[:-1]
chk("ledger record count in commit == 3186", len(raw_rows) == 3186, str(len(raw_rows)))

parent_ledger = git("cat-file", "blob", PARENT + ":proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl")
parent_rows = parent_ledger.split(b"\n")
if parent_rows and parent_rows[-1] == b"":
    parent_rows = parent_rows[:-1]
chk("appended rows since parent == 10", len(raw_rows) - len(parent_rows) == 10,
    "%d -> %d" % (len(parent_rows), len(raw_rows)))
chk("parent rows are a strict prefix (append-only)", raw_rows[:len(parent_rows)] == parent_rows, "")

# current-record-minus-LF-v1: sha256 of the physical record bytes with exactly one
# trailing LF removed; a stored CR is preserved.
def row_hash_v1(idx1):  # 1-indexed physical line
    return sha256(raw_rows[idx1 - 1])

prop = row_hash_v1(3180)
cons = row_hash_v1(3185)
chk("proposal row 3180 hash 616b3f53...",
    prop == "616b3f537a7b66436603421821a2148ec03750f78edd8f888f4de64328015d16", prop)
chk("consent row 3185 hash c85c6423...",
    cons == "c85c64233f2a8b7ba33bfcb991e9ca15b2edd229e1ebbad18125041ea76c7064", cons)

prop_rec = json.loads(raw_rows[3179].decode("utf-8"))
cons_rec = json.loads(raw_rows[3184].decode("utf-8"))
chk("row 3180 is codex proposal 19:50:13",
    prop_rec.get("from") == "codex" and prop_rec.get("time") == "2026-07-31 19:50:13",
    "%s %s" % (prop_rec.get("from"), prop_rec.get("time")))
chk("row 3185 is claude consent 20:43:47",
    cons_rec.get("from") == "claude" and cons_rec.get("time") == "2026-07-31T20:43:47+09:00",
    "%s %s" % (cons_rec.get("from"), cons_rec.get("time")))

# extract the quoted section from the proposal text and compare byte-for-byte
ptext = prop_rec["text"]
start = ptext.index("## North Star")
end = ptext.index("【明确不在范围】")
quoted = ptext[start:end].rstrip("\n")
inserted_norm = inserted_text.strip("\n")
chk("landed section == proposal quote (verbatim)", quoted == inserted_norm,
    "quoted %d chars / landed %d chars" % (len(quoted), len(inserted_norm)))
if quoted != inserted_norm:
    for a, b in zip(quoted.split("\n"), inserted_norm.split("\n")):
        if a != b:
            out.append({"check": "first differing line", "ok": False, "detail": repr(a)[:200] + " != " + repr(b)[:200]})
            break

# --- 5. disclosure table blobs ----------------------------------------------
charter_blob = git("rev-parse", COMMIT + ":CHARTER.md").decode().strip()
chk("CHARTER.md blob in commit bca561e1...",
    charter_blob == "bca561e1f3c97eaf6852f6754eacf2a539e7ed41", charter_blob)
charter_parent = git("rev-parse", PARENT + ":CHARTER.md").decode().strip()
chk("CHARTER.md unchanged by this commit", charter_blob == charter_parent, charter_parent)

# --- 6. no out-of-scope repo targets touched --------------------------------
paths = [l.split("\t", 1)[1] for l in name_status.split("\n") if l.strip()]
allowed = {"ROADMAP.md", "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"}
chk("changed path set == {ROADMAP.md, peer-chat.jsonl}", set(paths) == allowed, str(sorted(paths)))

# --- 7. rollback preimage is reachable --------------------------------------
chk("parent ROADMAP blob recoverable for rollback",
    sha256(git("cat-file", "blob", "c226ac8ab18803bcbe8f3d3f5ddf7113d6b56219"))
    == "bd32917c74701e672187d3270b57ee9124e09238949609536d69048623ba5031", "")

failed = [o for o in out if not o["ok"]]
print(json.dumps({"commit": COMMIT, "checks": out, "passed": len(out) - len(failed),
                  "total": len(out), "failed": failed,
                  "landed_section": inserted_text}, ensure_ascii=False, indent=2))
sys.exit(1 if failed else 0)
