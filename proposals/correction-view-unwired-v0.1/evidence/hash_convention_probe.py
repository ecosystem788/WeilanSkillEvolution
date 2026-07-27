import json, io, hashlib, sys
from pathlib import Path

impl = Path("proposals/bounded-scheduler-v0.1/impl")
corr_path = impl / "peer-chat.corrections.jsonl"
raw_lines = (impl / "peer-chat.jsonl").read_bytes().splitlines()
raw_hashes = {hashlib.sha256(l).hexdigest() for l in raw_lines}


def canonical_delegation(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


variants = {
    "delegation(ensure_ascii=False,sort_keys,compact)": lambda x: canonical_delegation(x),
    "ensure_ascii=False,no_sort,compact": lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
    "ensure_ascii=True,sort_keys,compact": lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    "ensure_ascii=False,no_sort,default_sep": lambda x: json.dumps(x, ensure_ascii=False).encode("utf-8"),
    "ensure_ascii=False,no_sort,compact+LF": lambda x: (json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
}

rows = [json.loads(l) for l in io.open(corr_path, encoding="utf-8").read().splitlines() if l.strip()]
for n, c in enumerate(rows, 1):
    cj = c.get("corrected_json")
    bh = c.get("before_hash")
    ah = c.get("after_hash")
    print("--- correction", n, "from=", c.get("from"))
    print("    before_hash_convention:", c.get("before_hash_convention"))
    print("    after_hash_convention :", c.get("after_hash_convention"))
    print("    before_hash in raw lines?", (bh in raw_hashes) if isinstance(bh, str) else "n/a")
    if not isinstance(cj, dict):
        print("    corrected_json is", type(cj).__name__, "-> not an object")
        continue
    hit = [name for name, fn in variants.items() if hashlib.sha256(fn(cj)).hexdigest() == ah]
    print("    after_hash matches convention:", hit or "NONE OF THE 5 TESTED")
