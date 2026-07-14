"""Independent verification of receipt memory-export-20260714T0915JST.json.

Recomputes, from the candidate tree and the local private-strings file only:
  1. built tree hash (must equal receipt.built_tree_hash)
  2. private-string scan (must be zero hits)
  3. secret/photo scan (must be zero hits)
  4. scan_ruleset_hash (must equal receipt.scan_ruleset_hash)
  5. template_hash (must equal receipt.template_hash)
Run by Claude as the second signature's own evidence; writes nothing.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

BASE = Path(r"D:\WeilanSkillEvolution\proposals\memory-opensource-export-v0.1")
EXPORT = Path(r"D:\WeilanMemoryExport\snapshot-redacted-20260714T0915JST")
RECEIPT = BASE / "receipts" / "memory-export-20260714T0915JST.json"
PRIVATE = Path(r"D:\WeilanSkillEvolution\proposals\scaffold-opensource-export-v0.1"
               r"\redaction-private-strings.local.txt")

spec = importlib.util.spec_from_file_location("bs", BASE / "build_snapshot.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

receipt = json.loads(RECEIPT.read_text(encoding="utf-8-sig"))

built_manifest = bs.manifest(EXPORT)
built_hash = "sha256:" + bs.tree_hash(built_manifest)

private_raw, private_patterns = bs.load_private_strings(PRIVATE)
private_hits = bs.scan_private_strings(EXPORT, private_patterns)
secret_hits, photo_hits = bs.scan_tree(EXPORT)

scan_ruleset = {
    "secret_patterns": {k: v.decode("ascii") for k, v in bs.SECRET_PATTERNS.items()},
    "photo_suffixes": sorted(bs.PHOTO_SUFFIXES),
    "photo_magics": [kind for _, kind in bs.PHOTO_MAGICS] + ["webp", "heif"],
    "exporter_sha256": bs.sha256_file(BASE / "build_snapshot.py"),
    "private_strings_sha256": hashlib.sha256(private_raw).hexdigest(),
    "private_string_count": len(private_patterns),
    "private_replacement_policy": "first non-ascii->云; ascii->yun",
}
material = (json.dumps(scan_ruleset, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\0" + private_raw)
ruleset_hash = "sha256:" + hashlib.sha256(material).hexdigest()

template_hash = "sha256:" + bs.sha256_file(EXPORT / "EXPORT_POLICY.md")

receipt_files = {e["path"]: e["sha256"] for e in receipt["file_hashes"]}
local_files = {p: "sha256:" + h for p, h in built_manifest.items()}

checks = {
    "tree_hash_match": built_hash == receipt["built_tree_hash"],
    "scanned_tree_is_built_tree":
        receipt["scan_result"]["scanned_tree_hash"] == receipt["built_tree_hash"],
    "private_string_hits": len(private_hits),
    "secret_hits": len(secret_hits),
    "photo_hits": len(photo_hits),
    "ruleset_hash_match": ruleset_hash == receipt["scan_ruleset_hash"],
    "template_hash_match": template_hash == receipt["template_hash"],
    "file_manifest_match": receipt_files == local_files,
    "file_count": len(local_files),
    "computed_tree_hash": built_hash,
    "computed_ruleset_hash": ruleset_hash,
}
ok = (checks["tree_hash_match"] and checks["scanned_tree_is_built_tree"]
      and checks["private_string_hits"] == 0 and checks["secret_hits"] == 0
      and checks["photo_hits"] == 0 and checks["ruleset_hash_match"]
      and checks["template_hash_match"] and checks["file_manifest_match"])
checks["VERDICT"] = "PASS" if ok else "FAIL"
print(json.dumps(checks, ensure_ascii=False, indent=2))
sys.exit(0 if ok else 1)
