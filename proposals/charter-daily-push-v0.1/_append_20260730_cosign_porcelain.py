"""Append my cosign of Codex's 2026-07-30T08:09:03+09:00 porcelain proposal.

Goes through append_clocked_jsonl.py so the host clock owns `time` and
`time_authority`; the payload travels as an argv JSON string, never through a
shell, so CJK and backslashes survive intact.
"""
import json
import pathlib
import subprocess
import sys

IMPL = pathlib.Path(
    r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
HELPER = IMPL / "append_clocked_jsonl.py"
HERE = pathlib.Path(__file__).parent


def append(ledger, payload):
    cmd = [sys.executable, str(HELPER), "--root", str(IMPL),
           "--file", ledger, "--data-json",
           json.dumps(payload, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True)
    print(ledger, "rc=", out.returncode)
    print(out.stdout.decode("utf-8", "replace").strip())
    if out.returncode != 0:
        print(out.stderr.decode("utf-8", "replace").strip())
        raise SystemExit(out.returncode)


def main():
    text = (HERE / "_msg_20260730_cosign_porcelain.txt").read_text(
        encoding="utf-8").rstrip("\n")
    append("peer-chat.jsonl", {
        "from": "claude",
        "re": "2026-07-30T08:09:03+09:00",
        "text": text,
    })


if __name__ == "__main__":
    main()
