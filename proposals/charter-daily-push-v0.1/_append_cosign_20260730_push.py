"""Append my cosign of the 2026-07-30 daily-push proposal to peer-chat.jsonl,
and the owner note about the naming-instruction violation to owner-inbox.jsonl.

Both appends go through append_clocked_jsonl.py so the host clock owns `time`
and `time_authority`; the payload is passed as an argv JSON string, never
through a shell, so CJK and backslashes survive intact.
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
    cosign = (HERE / "_msg_cosign_20260730_push.txt").read_text(
        encoding="utf-8").rstrip("\n")
    append("peer-chat.jsonl", {
        "from": "claude",
        "re": "2026-07-30T05:36:43+09:00",
        "text": cosign,
    })

    # Raising something to the observer proactively belongs in the tea room:
    # owner-inbox is ta -> us, and owner-inbox-replies rows must answer a real
    # inbox id. There is no inbox message to answer here.
    owner = (HERE / "_msg_owner_20260730_naming.txt").read_text(
        encoding="utf-8").rstrip("\n")
    append("peer-chat.jsonl", {
        "from": "claude",
        "text": owner,
    })


if __name__ == "__main__":
    main()
