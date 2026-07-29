"""Read-only probe: independently re-verify the withdrawal-link sidecar entry
appended by Codex at peer-chat.corrections.jsonl line 16 (2026-07-30T03:40:04+09:00).

Checks, all from raw bytes / git objects, never from the receipt's own restatement:
  1. before_hash  -> which physical line(s) of peer-chat.jsonl it hits (working tree).
  2. replacement_hash -> same.
  3. whether the pointed lines carry a trailing CR (line-hash-eol-convention axis).
  4. whether the same hashes resolve against the HEAD blob of peer-chat.jsonl
     (i.e. whether a third party cloning the repo can resolve the linkage at all).
  5. whether the three implicated lines have ever entered any commit.
No writes. No mutation of any ledger.
"""
import hashlib
import json
import subprocess
import sys

ROOT = r"D:\WeilanSkillEvolution"
CHAT = r"proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
CORR = r"proposals/bounded-scheduler-v0.1/impl/peer-chat.corrections.jsonl"


def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args),
                       capture_output=True)
    return p.returncode, p.stdout, p.stderr


def split_lines(blob: bytes):
    """Physical lines, each without its terminating LF; stored CR preserved."""
    parts = blob.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    return parts


def digest(line: bytes) -> str:
    return hashlib.sha256(line).hexdigest()


def hits(lines, want):
    return [i + 1 for i, ln in enumerate(lines) if digest(ln) == want]


def main():
    with open(rf"{ROOT}\{CHAT}".replace("/", "\\"), "rb") as f:
        wt = f.read()
    wt_lines = split_lines(wt)

    with open(rf"{ROOT}\{CORR}".replace("/", "\\"), "rb") as f:
        corr_lines = split_lines(f.read())
    entry = json.loads(corr_lines[15])

    out = {"corrections_line_16": entry}

    # 1/2 working-tree resolution
    bh, rh = entry["before_hash"], entry["replacement_hash"]
    out["wt_total_lines"] = len(wt_lines)
    out["wt_before_hash_hits"] = hits(wt_lines, bh)
    out["wt_replacement_hash_hits"] = hits(wt_lines, rh)

    # independent recompute of the two named lines
    out["wt_recomputed"] = {
        "line_3017": digest(wt_lines[3016]),
        "line_3019": digest(wt_lines[3018]),
    }
    out["wt_line_time_fields"] = {}
    for n in (3017, 3019):
        try:
            o = json.loads(wt_lines[n - 1].decode("utf-8"))
            out["wt_line_time_fields"][str(n)] = {"from": o.get("from"),
                                                  "time": o.get("time")}
        except Exception as exc:  # noqa: BLE001
            out["wt_line_time_fields"][str(n)] = f"parse_error: {exc}"

    # 3 CR presence
    out["cr_on_pointed_lines"] = {
        "line_3017": wt_lines[3016].endswith(b"\r"),
        "line_3019": wt_lines[3018].endswith(b"\r"),
    }

    # 4 HEAD blob resolution
    rc, head_blob, err = git("show", f"HEAD:{CHAT}")
    if rc != 0:
        out["head_blob"] = f"error: {err.decode('utf-8', 'replace')}"
    else:
        head_lines = split_lines(head_blob)
        out["head_blob"] = {
            "lines": len(head_lines),
            "before_hash_hits": hits(head_lines, bh),
            "replacement_hash_hits": hits(head_lines, rh),
        }
    rc, head_oid, _ = git("rev-parse", "HEAD")
    out["head"] = head_oid.decode().strip() if rc == 0 else None

    # 5 have the three implicated records ever entered any commit?
    out["ever_committed"] = {}
    for label, needle in (
        ("chat_3017_stamp", "2026-07-30T02:58:26+09:00"),
        ("chat_3019_stamp", "2026-07-30T03:17:03+09:00"),
        ("corrections_16_stamp", "2026-07-30T03:40:04+09:00"),
    ):
        rc, sout, _ = git("log", "--all", "--oneline", "-S", needle)
        out["ever_committed"][label] = sout.decode("utf-8", "replace").strip() or "none"

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
