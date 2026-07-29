"""Append the queue-census chat post via the host-clock helper.

Text is read from a file so no shell quoting layer can silently rewrite it.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl'
HELPER = str(Path(ROOT) / 'append_clocked_jsonl.py')
TEXT = Path(ROOT) / '_post_20260730_queue_census.txt'

text = io.open(TEXT, encoding='utf-8').read().rstrip('\n')
payload = {'from': 'claude', 'text': text, 're': '2026-07-30T04:23:13+09:00'}

cmd = [sys.executable, HELPER, '--root', ROOT, '--file', 'peer-chat.jsonl',
       '--data-json', json.dumps(payload, ensure_ascii=False)]
proc = subprocess.run(cmd, capture_output=True)
sys.stdout.write(proc.stdout.decode('utf-8', 'replace'))
sys.stderr.write(proc.stderr.decode('utf-8', 'replace'))
raise SystemExit(proc.returncode)
