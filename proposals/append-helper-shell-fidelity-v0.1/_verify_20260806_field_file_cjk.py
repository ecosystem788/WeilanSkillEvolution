import hashlib
import json
from pathlib import Path

root = Path(r"D:\WeilanSkillEvolution\proposals\append-helper-shell-fidelity-v0.1")
ledger = root / "_scratch_20260806_cjk_field_file.jsonl"

# Intent: CJK + backtick + dollar + double-quote, encoded as UTF-8 hex so the
# script itself stays ASCII-clean (no shell/pipe boundary contact).
hexs = (
    "e4b8ade69687e6b58be8af95e58f8de5bc95e58fb7"
    "607469636b60"
    "e7be8ee58583"
    "24646f6c6c6172"
    "e58f8ce5bc95e58fb7"
    "2271756f746522"
    "e7bb93e69d9f"
)
intent = bytes.fromhex(hexs).decode("utf-8")

lines = ledger.read_text(encoding="utf-8").splitlines()
row = json.loads(lines[-1])
stored = row["note"]

result = {
    "intent_sha256": hashlib.sha256(intent.encode("utf-8")).hexdigest(),
    "stored_sha256": hashlib.sha256(stored.encode("utf-8")).hexdigest(),
    "exact_equal": intent == stored,
    "has_cjk": any("\u4e00" <= c <= "\u9fff" for c in stored),
    "has_backtick": chr(96) in stored,
    "has_dollar": "$" in stored,
    "has_dquote": chr(34) in stored,
    "row_keys": sorted(row.keys()),
    "time_authority": row["time_authority"],
    "ledger": str(ledger),
}
out = root / "_verify_20260806_field_file_cjk.out.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
