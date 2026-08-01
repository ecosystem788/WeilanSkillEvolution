"""Roll a sandbox copy of method-state back to the state just before this round's open.

Read-only against production. Operates only inside the sandbox work tree so that a
`continue` open in the sandbox faces exactly the conditions the production open faced
(same lineage length, same closed parent).
"""

import io
import json
import os
import sys
from pathlib import Path

WORK = Path(sys.argv[1])
DROP_FRAME = sys.argv[2]          # the frame this round opened in production
EXPECT_PARENT = sys.argv[3]       # head that should be restored

report = {"work": str(WORK), "drop_frame": DROP_FRAME}

# 1) remove the frame event file
removed = []
for path in (WORK / "frames").glob(f"*/{DROP_FRAME}.jsonl"):
    path.unlink()
    removed.append(str(path))
report["removed_frame_files"] = removed

# 2) drop its lineage record
lin_dirs = [d for d in (WORK / "memory" / "lineage" / "workspaces").glob("*/*") if d.is_dir()]
dropped = []
for d in lin_dirs:
    for f in d.glob("*.jsonl"):
        raw = f.read_bytes()
        lines = raw.split(b"\n")
        keep = []
        for ln in lines:
            if not ln.strip():
                continue
            if DROP_FRAME.encode() in ln:
                dropped.append({"file": str(f), "bytes": len(ln)})
                continue
            keep.append(ln)
        new = b"\n".join(keep) + (b"\n" if keep else b"")
        if new != raw:
            f.write_bytes(new)
report["dropped_lineage_records"] = dropped

# 3) rewind any heads file that points at the dropped frame
rewound = []
for f in (WORK / "memory" / "lineage" / "heads").rglob("*.json"):
    doc = json.loads(io.open(f, encoding="utf-8-sig").read())
    changed = False
    branches = doc.get("branches", {})
    for bid, state in branches.items():
        if state.get("head_frame_id") == DROP_FRAME:
            state["head_frame_id"] = EXPECT_PARENT
            changed = True
    if changed:
        with io.open(f, "w", encoding="utf-8", newline="\n") as h:
            json.dump(doc, h, ensure_ascii=False, indent=2, sort_keys=True)
            h.write("\n")
        rewound.append(str(f))
report["rewound_heads"] = rewound

print(json.dumps(report, ensure_ascii=False, indent=2))
