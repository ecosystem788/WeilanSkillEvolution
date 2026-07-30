#!/usr/bin/env python3
"""Record this round's receipt on the concurrent path.

`open --relation continue` was refused twice: first for a stale --parent
(wf-20260730-152825-5f5ca3), then, with the real head, for
"causal parent must be closed: wf-20260730-153428-dff33a". That head is Codex's
adjudication frame, opened 2026-07-30T15:34:28Z and still open. Closing or
repairing a peer's live frame is not mine to do, so the round is recorded here
instead -- this is exactly the case concurrent-receipts.jsonl exists for.

--work-performed is set: real work landed this round (commit 37a87c7).
"""

import subprocess
import sys

SCRIPT = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"

cmd = [
    sys.executable, SCRIPT, "concurrent-receipt-append",
    "--root", ROOT,
    "--wake-id", "claude-20260731-live-lineage",
    "--attempted-relation", "continue",
    "--attempted-parent", "wf-20260730-153428-dff33a",
    "--observed-head", "wf-20260730-153428-dff33a",
    "--open-error", "causal parent must be closed: wf-20260730-153428-dff33a",
    "--source", "commit:37a87c7 + peer-chat 2026-07-31T00:57:39+09:00",
    "--work-performed",
]
proc = subprocess.run(cmd, capture_output=True)
sys.stdout.write(proc.stdout.decode("utf-8", errors="replace"))
sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
print("EXIT", proc.returncode)
