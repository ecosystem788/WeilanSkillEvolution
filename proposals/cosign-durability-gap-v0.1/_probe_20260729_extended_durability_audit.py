"""Extended durability audit: same verdict logic as `_audit_cosign_durability.py`,
but the denominator comes from the governance ledger instead of a hand-written list.

`_audit_cosign_durability.py` walks 5 hard-coded execution dirs and prints
"0/5 STRANDED". Seven such dirs exist on disk; the ledger records 12 strong-binding
co-signs. Three of those executions have no distinct preflight-state.json anchor,
so any enumeration keyed on that artifact cannot reach them.

This probe re-derives (target, base, final) directly from each 【同意】 message --
the artifact that actually carries the signature -- so an execution that skipped
the archive step is still audited.

NOT in scope: wake_prompt_codex.md (2026-07-28). That co-sign explicitly declined
the five-binding rule and proceeded as an ordinary co-sign (see peer-chat line 2826),
so its absence here is correct by class, not a coverage hole. See
EVIDENCE_DENOMINATOR_CLASS_SPLIT.md §1.

Extraction is deliberately strict: a candidate is admitted ONLY if all three of
target / base sha256 / final sha256 can be parsed out of the co-sign text. Every
strong-binding co-sign that fails extraction is printed under UNEXTRACTED so the
reader sees the residue rather than a silently shrunken denominator.

Zero authority. Read-only. Never writes git objects. Exits 0 always.
"""
import hashlib
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

HEX64 = r"([0-9a-f]{64})"
STRONG = "强绑定"          # 强绑定
AGREE = "同意"                  # 同意
OPPOSE = "反对"                 # 反对

# target=<path> | target: <path> | target path `<path>` | target `<path>`
RE_TARGET = re.compile(
    r"target(?:\s*path)?\s*[=:：]?\s*[``]?([A-Za-z0-9_./\-]+\.[A-Za-z0-9]{1,5})")
RE_ANYPATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./\-]*\.[A-Za-z0-9]{1,5}")
RE_BASE = re.compile(r"base[^\n]{0,24}?" + HEX64)
RE_FINAL = re.compile(
    r"(?:proposed[-\s]?final|final)[^\n]{0,24}?" + HEX64)



def _basename_index():
    """basename -> [tracked repo-relative paths]. Built from git, not os.walk,
    so untracked scratch files cannot shadow a real target."""
    proc = subprocess.run(["git", "-C", REPO, "ls-files"], capture_output=True)
    idx = {}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if line:
            idx.setdefault(os.path.basename(line), []).append(line)
    return idx


BASENAME_INDEX = _basename_index()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def head_bytes(target):
    proc = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + target],
                          capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def header(text):
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
                pass
    return rows


def classify(final, base, wt, head):
    if head == final:
        return "DURABLE"
    if wt == final and head == base:
        return "STRANDED@base"
    if wt == final:
        return "STRANDED"
    if head == final or wt == final:
        return "MIXED"
    return "SUPERSEDED"


def main():
    admitted, residue = [], []
    for ln, r in load_rows():
        text = r.get("text", "") or ""
        head_seg = header(text)
        if AGREE not in head_seg or OPPOSE in head_seg:
            continue
        if STRONG not in text:
            continue
        t = RE_TARGET.search(text)
        b = RE_BASE.search(text)
        f = RE_FINAL.search(text)
        rec = {"line": ln, "from": r.get("from"), "time": r.get("time"),
               "header": head_seg,
               "target": t.group(1) if t else None,
               "base": b.group(1) if b else None,
               "final": f.group(1) if f else None}
        if rec["target"] and rec["base"] and rec["final"] and rec["base"] != rec["final"]:
            admitted.append(rec)
        else:
            residue.append(rec)

    proc = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                          capture_output=True)
    print("repo HEAD: %s" % proc.stdout.decode().strip())
    print("ledger: %s" % os.path.relpath(CHAT, REPO).replace("\\", "/"))

    print("\n== admitted: strong-binding co-signs with all three fields parsed : %d =="
          % len(admitted))
    rows = []
    for rec in admitted:
        target = rec["target"]
        wt_path = os.path.join(REPO, target)
        wt = sha(io.open(wt_path, "rb").read()) if os.path.exists(wt_path) else "ABSENT"
        hb = head_bytes(target)
        hd = sha(hb) if hb is not None else "ABSENT"
        verdict = classify(rec["final"], rec["base"], wt, hd)
        rows.append((verdict, rec, wt, hd))

    print("%-14s %-6s %-26s %-13s %-13s %s"
          % ("verdict", "chatL", "cosign time", "final[:12]", "HEAD[:12]", "target"))
    for verdict, rec, wt, hd in rows:
        print("%-14s L%-5d %-26s %-13s %-13s %s"
              % (verdict, rec["line"], rec["time"], rec["final"][:12],
                 hd[:12] if hd != "ABSENT" else hd, rec["target"]))

    stranded = [r for r in rows if r[0].startswith("STRANDED")]
    print("\n  %d/%d STRANDED under the ledger-derived denominator"
          % (len(stranded), len(rows)))
    for verdict, rec, wt, hd in stranded:
        print("    %s  %s  (co-signed at %s, chat line %d)"
              % (verdict, rec["target"], rec["time"], rec["line"]))

    print("\n== UNEXTRACTED residue: strong-binding co-signs this probe could NOT parse : %d =="
          % len(residue))
    print("   (printed in full -- these are NOT asserted clean, only unmeasured here)")
    for rec in residue:
        print("  L%-5d %-26s target=%s base=%s final=%s"
              % (rec["line"], rec["time"], rec["target"],
                 (rec["base"] or "-")[:12], (rec["final"] or "-")[:12]))
        print("         %s" % rec["header"])

    # ------------------------------------------------------------------
    # P2: ordinary co-signs -- single file named, base pinned, NO final.
    # CONVENTION's five-binding rule applies only when the WHOLE file is
    # locked byte-for-byte; a co-sign may lawfully decline it (and one did,
    # in as many words). Those executions leave no final digest anywhere,
    # so the audit's verdict function has no input: their durability is not
    # merely unmeasured, it is undecidable from the record they left.
    # The one probe we CAN run is HEAD == base, i.e. "the co-signed edit is
    # not in git history at all".
    # ------------------------------------------------------------------
    p2 = []
    for ln, r in load_rows():
        text = r.get("text", "") or ""
        head_seg = header(text)
        if AGREE not in head_seg or OPPOSE in head_seg:
            continue
        if STRONG in text:
            continue
        b = RE_BASE.search(text)
        f = RE_FINAL.search(text)
        if not b or f:
            continue
        # No `target=` label to lean on: an ordinary co-sign has no required
        # schema. Fall back to "names a path that exists in the repo today".
        # This is a weaker rule and it is stated as such -- it can miss a
        # co-sign whose target was later renamed or deleted.
        # An ordinary co-sign usually writes a bare basename, not a repo-relative
        # path, so resolve basenames against the tracked-file index and keep only
        # unambiguous hits.
        named = []
        for cand in RE_ANYPATH.findall(text):
            cand = cand.strip("`` ")
            hit = None
            if os.path.isfile(os.path.join(REPO, cand)):
                hit = cand
            else:
                owners = BASENAME_INDEX.get(os.path.basename(cand), [])
                if len(owners) == 1:
                    hit = owners[0]
            if hit and hit not in named:
                named.append(hit)
        if len(named) != 1:
            continue
        p2.append({"line": ln, "time": r.get("time"), "target": named[0],
                   "base": b.group(1), "header": head_seg})

    print("\n== P2: ordinary co-signs naming a target + base but NO final digest : %d =="
          % len(p2))
    print("   the audit's verdict function needs `final`; for these it has no input.")
    if not p2:
        print("   *** 0 here means THE RULE FOUND NOTHING, not that the population")
        print("   *** is empty. At least one such co-sign is known to exist")
        print("   *** (peer-chat 2826/2827, wake_prompt_codex.md, currently unlanded).")
        print("   *** It is unreachable because an ordinary co-sign has no required")
        print("   *** schema: that message names five different file paths and")
        print("   *** nothing marks which one is the target. Do not read this 0 as")
        print("   *** a clean bill. See EVIDENCE_DENOMINATOR_CLASS_SPLIT.md §4.")
    unlanded = 0
    for rec in p2:
        hb = head_bytes(rec["target"])
        hd = sha(hb) if hb is not None else "ABSENT"
        if hd == rec["base"]:
            verdict = "UNLANDED@base"
            unlanded += 1
        else:
            verdict = "MOVED-PAST-BASE"
        print("  %-16s L%-5d %-26s %s" % (verdict, rec["line"], rec["time"],
                                          rec["target"]))
        print("                   HEAD=%s base=%s" % (hd[:12], rec["base"][:12]))
    print("\n  %d/%d of P2 have HEAD still exactly at the co-signed base:" % (unlanded, len(p2)))
    print("  the signed edit is absent from git history, and because no final was")
    print("  ever recorded, no audit can decide whether the worktree holds it either.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
