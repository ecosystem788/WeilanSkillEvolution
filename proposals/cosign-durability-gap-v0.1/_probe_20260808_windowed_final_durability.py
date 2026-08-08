"""Windowed durability probe (2026-07-29T00:00:00+09:00 .. now):
reapply the 07-28 census rule to execution receipts in the window and judge
each labelled final/post image for durability, so a reader can see whether
NEW signed finals appeared since the section 7.2 universe was fixed at 5.

Rule copied from _probe_20260728_signed_final_durability.py (visible, not
assumed): scan execution-receipt messages, collect 64-hex tokens whose
preceding context contains a FINAL key and no NOT_FINAL key, judge each
unique image: reachable-from-ref (durable) / object-present-unreachable
(orphaned) / no-object (stranded). Window filter is the only delta.

Zero authority. Read-only. Never writes git objects. Writes one .out.json.
Exits 0 always.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
CHAT = os.path.join(REPO, r"proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "_probe_20260808_windowed_final_durability.out.json")

RECEIPT_MARKERS = ("\u6267\u884c\u6536\u636e", "\u5df2\u843d\u5730",
                   "\u6267\u884c\u5b8c\u6bd5", "\u843d\u5730\u6536\u636e",
                   "\u843d\u5730\u56de\u6267", "PUSH_RECEIPT")
HEX = re.compile(r"(?<![0-9a-f])([0-9a-f]{64})(?![0-9a-f])")
FINAL_KEYS = ("final", "post", "\u843d\u76d8", "\u6267\u884c\u540e",
              "\u73b0\u6587", "\u6539\u540e")
NOT_FINAL_KEYS = ("base", "manifest_digest", "digest=", "before",
                  "\u6539\u524d", "\u539f\u6587", "raw_bytes",
                  "matched_hash", "witness")
WINDOW = "2026-07-29T00:00:00"


def git(*args, binary=False):
    r = subprocess.run(["git"] + list(args), cwd=REPO, capture_output=True)
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
        p = subprocess.run(["git", "cat-file", "--batch"], cwd=REPO,
                           input="\n".join(chunk).encode() + b"\n",
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        buf = p.stdout
        pos = 0
        for _ in chunk:
            nl = buf.index(b"\n", pos)
            header = buf[pos:nl].decode()
            parts = header.split()
            size = int(parts[2])
            body = buf[nl + 1:nl + 1 + size]
            out.setdefault(hashlib.sha256(body).hexdigest(), parts[0])
            pos = nl + 1 + size + 1
    return out


def all_disk_sha256():
    out = {}
    for root, dirs, files in os.walk(REPO):
        if ".git" in dirs:
            dirs.remove(".git")
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                with open(fp, "rb") as fh:
                    out.setdefault(hashlib.sha256(fh.read()).hexdigest(),
                                   os.path.relpath(fp, REPO))
            except OSError:
                continue
    return out


def main():
    blobs = all_git_blob_sha256()
    reach = reachable_oids()
    disk = all_disk_sha256()
    rows = []
    with io.open(CHAT, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except ValueError:
                continue
            t = (obj.get("time") or "").strip()[:19]
            if t < WINDOW:
                continue
            text = obj.get("text", "")
            if any(m in text for m in RECEIPT_MARKERS):
                rows.append((lineno, obj))
    judged = []
    labelled_lines = set()
    for lineno, obj in rows:
        text = obj.get("text", "")
        for m in HEX.finditer(text):
            h = m.group(1)
            ctx = text[max(0, m.start() - 70):m.start()].replace("\n", " ")
            low = ctx.lower()
            if any(k in low for k in NOT_FINAL_KEYS):
                continue
            if not any(k in low for k in FINAL_KEYS):
                continue
            labelled_lines.add(lineno)
            oid = blobs.get(h)
            judged.append({
                "line": lineno,
                "from": obj.get("from"),
                "time": obj.get("time"),
                "sha256": h,
                "context": ctx[-55:],
                "oid": oid,
                "object_present": oid is not None,
                "reachable": bool(oid) and oid in reach,
                "on_disk": h in disk,
                "disk_path": disk.get(h),
            })
    seen = set()
    uniq = []
    for j in judged:
        if j["sha256"] in seen:
            continue
        seen.add(j["sha256"])
        uniq.append(j)
    payload = {
        "probe": "_probe_20260808_windowed_final_durability.py",
        "window_start": WINDOW + "+09:00",
        "receipt_messages_in_window": len(rows),
        "messages_with_labelled_final": len(labelled_lines),
        "distinct_labelled_final_images": len(uniq),
        "durable": len([j for j in uniq if j["reachable"]]),
        "orphaned": len([j for j in uniq
                         if j["object_present"] and not j["reachable"]]),
        "stranded": len([j for j in uniq if not j["object_present"]]),
        "images": uniq,
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print("window >= %s+09:00" % WINDOW)
    print("receipt messages in window: %d" % len(rows))
    print("messages carrying a labelled final image: %d" % len(labelled_lines))
    print("distinct labelled final images: %d" % len(uniq))
    print("  durable   : %d" % payload["durable"])
    print("  orphaned  : %d" % payload["orphaned"])
    print("  stranded  : %d" % payload["stranded"])
    print()
    for j in uniq:
        if j["reachable"]:
            flag = "DURABLE  "
        elif j["object_present"]:
            flag = "ORPHANED "
        else:
            flag = "STRANDED "
        dk = "disk:%s" % j["disk_path"] if j["on_disk"] else "not-on-disk"
        print("%s L%-5d %s %s  %s" % (flag, j["line"], j["time"], j["from"],
                                       j["sha256"][:20]))
        print("          ctx ...%s" % j["context"])
        print("          %s  oid=%s" % (dk, j["oid"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
