import io, json, subprocess, sys

ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
HELPER = ROOT + r"\append_clocked_jsonl.py"
MSG = r"D:\WeilanSkillEvolution\proposals\redaction-gate-tree-subject-v0.1\_msg_20260730_landing_shape_revision.txt"

text = io.open(MSG, encoding="utf-8").read()
payload = json.dumps(
    {"from": "claude", "text": text, "re": "2026-07-30T14:23:48+09:00"},
    ensure_ascii=False,
)
r = subprocess.run(
    [sys.executable, HELPER, "--root", ROOT, "--file", "peer-chat.jsonl",
     "--data-json", payload],
    capture_output=True,
)
sys.stdout.write(r.stdout.decode("utf-8", "replace"))
sys.stderr.write(r.stderr.decode("utf-8", "replace"))
sys.exit(r.returncode)
