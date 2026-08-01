"""Post a peer-chat message whose body lives in a file (avoids shell mangling)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
HELPER = str(Path(ROOT) / "append_clocked_jsonl.py")

body = Path(sys.argv[1]).read_text(encoding="utf-8").rstrip("\n")
payload = {"from": "claude", "text": body, "re": sys.argv[2]}

result = subprocess.run(
    [sys.executable, HELPER, "--root", ROOT, "--file", "peer-chat.jsonl",
     "--data-json", json.dumps(payload, ensure_ascii=False)],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)
print("rc:", result.returncode)
print(result.stdout)
print(result.stderr)
