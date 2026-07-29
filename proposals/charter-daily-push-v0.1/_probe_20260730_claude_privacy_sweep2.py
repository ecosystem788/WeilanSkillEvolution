"""Second pass of the publication-closure privacy sweep: dedupe and characterise.

Pass 1 (_probe_20260730_claude_privacy_sweep.py) reported raw hit counts, which
are dominated by repeats and by my own regex false positives. This pass reports
distinct matched strings per pattern with one example location each, so the
judgement is made on the set of *distinct* strings rather than on a count.
Read-only.
"""
import json
import io
import re
import subprocess
import sys
from collections import defaultdict

REPO = "D:/WeilanSkillEvolution"
MANIFEST = sys.argv[1] if len(sys.argv) > 1 else (
    "D:/WeilanSkillEvolution/proposals/charter-daily-push-v0.1/"
    "_scan_claude_20260730.json")

PATTERNS = {
    "any_email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "image_ext": re.compile(r"[\w./\\-]*\.(?:png|jpg|jpeg|gif|webp|bmp|heic)\b", re.I),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "win_userpath": re.compile(r"[Cc]:\\\\?Users\\\\?[A-Za-z0-9_.-]+"),
}


def cat(oid):
    return subprocess.run(["git", "-C", REPO, "cat-file", "blob", oid], capture_output=True).stdout


def main():
    d = json.load(io.open(MANIFEST, encoding="utf-8"))
    blobs = [m for m in d["manifest"] if m["object_type"] == "blob"]
    distinct = {k: defaultdict(lambda: {"count": 0, "example": None, "paths": set()}) for k in PATTERNS}
    for m in blobs:
        path = (m.get("path_hints") or ["<no-hint>"])[0]
        text = cat(m["object_id"]).decode("utf-8", "replace")
        for name, pat in PATTERNS.items():
            for mo in pat.finditer(text):
                key = mo.group(0)
                rec = distinct[name][key]
                rec["count"] += 1
                rec["paths"].add(path)
                if rec["example"] is None:
                    line = text.count("\n", 0, mo.start()) + 1
                    rec["example"] = f"{path}:{line}"
    out = {}
    for name, table in distinct.items():
        out[name] = {
            "distinct_strings": len(table),
            "items": sorted(
                (
                    {
                        "value": k,
                        "count": v["count"],
                        "distinct_paths": len(v["paths"]),
                        "example": v["example"],
                    }
                    for k, v in table.items()
                ),
                key=lambda r: -r["count"],
            )[:40],
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
