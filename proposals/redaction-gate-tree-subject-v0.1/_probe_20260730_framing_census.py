"""How wide is the silent-skip class? Census the landed tree by framing.

The gate scans content in three regimes:
  utf-8        -> per-record identity, anchorable
  utf-16 only  -> line_framing="unsupported", never anchorable (fail-closed)
  neither      -> content never examined at all (silent), path still scanned

This counts each regime in the landed commit tree, and measures how often the
third regime is reachable at all: utf-16 accepts almost any even-length byte
string, so the silent class is roughly "odd-length or lone-surrogate binary".
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution")
GATE_PATH = ROOT / "proposals" / "scaffold-opensource-export-v0.1" / "scan_only_gate.py"
LANDED = "8ef57756a7c5a31e0c73385e4dca02e08a6bcbeb"

SPEC = importlib.util.spec_from_file_location("gate_census", GATE_PATH)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

os.chdir(ROOT)
entries = GATE.parse_ls_tree(GATE.resolve_commit(LANDED))
blobs = GATE.read_blobs(entries)

counts = {"utf8": 0, "utf16_only": 0, "silent": 0}
utf16_paths = []
odd_length_non_utf8 = 0
for entry in entries:
    if entry["type"] != "blob":
        continue
    raw = blobs[entry["oid"]]
    try:
        raw.decode("utf-8")
        counts["utf8"] += 1
        continue
    except UnicodeDecodeError:
        pass
    if len(raw) % 2:
        odd_length_non_utf8 += 1
    try:
        raw.decode("utf-16")
        counts["utf16_only"] += 1
        if len(utf16_paths) < 10:
            utf16_paths.append({"path": entry["path"], "bytes": len(raw)})
    except UnicodeDecodeError:
        counts["silent"] += 1

json.dump({
    "landed_commit": LANDED,
    "blob_count": sum(e["type"] == "blob" for e in entries),
    "framing_counts": counts,
    "non_utf8_blobs": counts["utf16_only"] + counts["silent"],
    "odd_length_non_utf8_blobs": odd_length_non_utf8,
    "utf16_only_sample": utf16_paths,
    "note": ("silent==0 today because the tree carries no blob that fails both "
             "decoders; utf-16 accepts nearly any even-length byte string, so "
             "the silent class is narrow but not closed"),
}, sys.stdout, ensure_ascii=False, indent=1)
print()
