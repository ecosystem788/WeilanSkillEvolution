"""Addendum probe: the 20 CRLF-bearing peer-chat lines exist only on disk.

peer-chat.corrections.jsonl anchors lines by a raw-byte sha256 whose convention
string reads "remove exactly one trailing LF byte; stored CR preserved". Every
committed blob of peer-chat.jsonl is LF-only, so a clone recomputes a different
hash for any anchored line that carries CR here. Question: do the anchored
lines overlap the CR-bearing lines?
"""
import hashlib, io, json, os, subprocess, sys

ROOT = r"D:\WeilanSkillEvolution"
IMPL = os.path.join(ROOT, "proposals", "bounded-scheduler-v0.1", "impl")
CHAT = os.path.join(IMPL, "peer-chat.jsonl")
CORR = os.path.join(IMPL, "peer-chat.corrections.jsonl")


def main():
    raw = io.open(CHAT, "rb").read()
    # keepends so we can see each line's actual terminator bytes
    lines = raw.splitlines(keepends=True)
    cr_lines = [i for i, b in enumerate(lines, 1) if b.endswith(b"\r\n")]

    head = subprocess.run(["git", "cat-file", "blob", "HEAD:proposals/"
                           "bounded-scheduler-v0.1/impl/peer-chat.jsonl"],
                          cwd=ROOT, capture_output=True).stdout
    head_lines = head.splitlines(keepends=True)

    anchored = []
    if os.path.exists(CORR):
        for n, ln in enumerate(io.open(CORR, encoding="utf-8"), 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            anchored.append({"corrections_line": n, "record": rec})

    # which line numbers do the corrections point at, by raw-byte hash match?
    def h(b):
        return hashlib.sha256(b).hexdigest()

    hits = []
    for a in anchored:
        # real field names, read off the ledger: before_hash pins current physical
        # bytes ("no trailing LF" -> a CR would be retained), sentinel_equiv_hash
        # is the re-pin variant.
        for key in ("before_hash", "sentinel_equiv_hash", "after_hash"):
            want = a["record"].get(key)
            if want:
                break
        if not want:
            continue
        found_disk = found_head = None
        for i, b in enumerate(lines, 1):
            if h(b.rstrip(b"\n")) == want or h(b) == want:
                found_disk = i
                break
        for i, b in enumerate(head_lines, 1):
            if h(b.rstrip(b"\n")) == want or h(b) == want:
                found_head = i
                break
        hits.append({
            "corrections_line": a["corrections_line"],
            "target_field": key,
            "target_hash": want[:16],
            "resolves_on_disk_at": found_disk,
            "resolves_in_HEAD_blob_at": found_head,
            "disk_line_is_crlf": found_disk in cr_lines if found_disk else None,
        })

    payload = json.dumps({
        "probe": "crlf_line_identity",
        "disk_total_lines": len(lines),
        "disk_crlf_line_numbers": cr_lines,
        "head_blob_crlf_count": head.count(b"\r\n"),
        "corrections_records": len(anchored),
        "anchor_resolution": hits,
        "anchors_unresolvable_in_HEAD": [x["corrections_line"] for x in hits
                                         if x["resolves_in_HEAD_blob_at"] is None],
    }, ensure_ascii=False, indent=2)
    if len(sys.argv) > 1:
        with io.open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
