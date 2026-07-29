"""Who authored the two private-string hits that scan_only_gate v3 reports on
the exact HEAD tree, and are they already published at base?

Deliberately never prints a pattern, a matched substring, or the surrounding
text — only pattern_index, line number, and the ledger row's own `from`/`time`
metadata. Same output discipline as scan_only_gate.py, so this output is safe to
commit and to quote in the tea room.

Read-only: reads the gitignored private-strings file and two ledger blobs out of
git (never the working copy), writes nothing.
"""
import json
import subprocess

REPO = "D:/WeilanSkillEvolution"
PRIVATE = ("D:/WeilanSkillEvolution/proposals/scaffold-opensource-export-v0.1/"
           "redaction-private-strings.local.txt")
BASE = "0c3d9b25ddb86010837a0930c40accad3c78189a"
HEAD = "310e57546dd51742fc8f38c403c3df3fcdeb375f"
PATHS = [
    "proposals/bounded-scheduler-v0.1/impl/codex-inbox.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl",
]


def show(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"],
                          capture_output=True).stdout.decode("utf-8", "replace")


def main():
    with open(PRIVATE, encoding="utf-8") as fh:
        patterns = [ln.strip() for ln in fh if ln.strip()]

    report = []
    for path in PATHS:
        for rev, label in ((HEAD, "head"), (BASE, "base")):
            text = show(rev, path)
            for lineno, line in enumerate(text.splitlines(), 1):
                for index, pattern in enumerate(patterns):
                    if pattern in line:
                        row = {"rev": label, "path": path,
                               "pattern_index": index, "line": lineno}
                        try:
                            obj = json.loads(line)
                            row["row_from"] = obj.get("from")
                            row["row_time"] = obj.get("time")
                            row["row_id"] = obj.get("id")
                            row["authored_by_observer"] = (
                                obj.get("from") == "owner")
                        except Exception:
                            row["row_parse"] = "unparseable"
                        report.append(row)
    print(json.dumps({
        "pattern_count": len(patterns),
        "note": "no pattern text is emitted by design",
        "hits": report,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
