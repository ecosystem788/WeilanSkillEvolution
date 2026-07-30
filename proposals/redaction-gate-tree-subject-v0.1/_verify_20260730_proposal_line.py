# Read-only: locate the 【提案】 line inside the committed blob and report its
# current-record-minus-LF-v1 hash, so the later execution commit can cite it
# without trusting my transcription.
import hashlib
import json
import subprocess
import sys

COMMIT = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"

blob_oid = subprocess.run(
    ["git", "rev-parse", "%s:%s" % (COMMIT, LEDGER)],
    stdout=subprocess.PIPE, check=True).stdout.decode().strip()
raw = subprocess.run(
    ["git", "cat-file", "blob", blob_oid],
    stdout=subprocess.PIPE, check=True).stdout

records = raw.split(b"\n")
if records and records[-1] == b"":
    records.pop()

out = {"commit": COMMIT, "ledger": LEDGER, "blob_oid": blob_oid,
       "record_count": len(records), "found": []}
for number, record in enumerate(records, start=1):
    try:
        row = json.loads(record.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        continue
    text = row.get("text", "")
    if row.get("from") == "claude" and text.startswith("【提案｜按 3 换主体"):
        # current-record-minus-LF-v1: splitting on 0x0A already removed exactly
        # the one trailing LF; any stored CR before it stays in the payload.
        payload = record
        out["found"].append({
            "line_number": number,
            "time": row.get("time"),
            "time_authority": row.get("time_authority"),
            "trailing_cr": record.endswith(b"\r"),
            "line_hash_sha256": hashlib.sha256(payload).hexdigest(),
        })

json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
print()
