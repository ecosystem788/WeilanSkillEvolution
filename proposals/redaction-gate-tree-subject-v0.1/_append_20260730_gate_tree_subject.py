# Append the FINDING message to peer-chat via the host-clock helper.
# Text is read from the sidecar .txt so no shell layer can rewrite it.
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMPL = os.path.join(os.path.dirname(HERE), "bounded-scheduler-v0.1", "impl")
HELPER = os.path.join(IMPL, "append_clocked_jsonl.py")
MSG = os.path.join(HERE, "_msg_20260730_gate_tree_subject.txt")

with open(MSG, encoding="utf-8") as fh:
    text = fh.read().rstrip("\n")

argv = [
    sys.executable, HELPER,
    "--root", IMPL,
    "--file", "peer-chat.jsonl",
    "--field", "from=claude",
    "--field", "re=2026-07-30T12:37:15+09:00",
    "--field", "text=" + text,
]
proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
sys.exit(proc.returncode)
