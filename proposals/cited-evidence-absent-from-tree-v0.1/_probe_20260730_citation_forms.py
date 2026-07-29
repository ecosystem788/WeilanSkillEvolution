"""Read-only: show the exact citation context for the absent paths, so the census's
8 absences can be triaged by cause rather than lumped together."""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHAT = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.jsonl"

TARGETS = [
    (2772, "scan_push_manifest.py"),
    (2777, "cosign-durability-gap-v0.1/FINDING.md"),
    (2778, "postcheck-receipt.json"),
    (2862, "postcheck-receipt.json"),
    (2862, "TARGETED_SHADOW_RESULT.json"),
    (2862, "T1_COMMIT_PAYLOAD.tsv"),
    (2982, "preflight-state.json"),
    (3009, "FINDING"),
    (3009, "CENSUS"),
    (3010, "FINDING"),
    (3010, "CENSUS"),
]

lines = CHAT.read_bytes().split(b"\n")

for n, needle in TARGETS:
    rec = json.loads(lines[n - 1].decode("utf-8"))
    text = rec.get("text") or ""
    print("=" * 72)
    print("[line %d] %s %s   needle=%r" % (n, rec.get("time"), rec.get("from"), needle))
    hits = [m.start() for m in re.finditer(re.escape(needle), text)]
    if not hits:
        print("   (needle not present)")
        continue
    for h in hits[:3]:
        print("   ...%s..." % text[max(0, h - 90): h + len(needle) + 40].replace("\n", " / "))
