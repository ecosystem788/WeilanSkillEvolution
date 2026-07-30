"""Are the 544 non-utf-8 blobs genuinely UTF-16, or reinterpreted garbage?

The gate falls back to raw.decode("utf-16"), which succeeds for nearly any
even-length byte string. When it succeeds on a blob that is NOT actually
UTF-16, the text scanned is mojibake, so a UTF-8 private string inside those
bytes cannot be found. Critically, line_framing="unsupported" is attached to
*occurrences* only -- with zero hits the receipt carries no trace that a
fallback decoder was used at all.

This decides which claim is honest:
  - if the 544 all carry a UTF-16 BOM -> today they decode correctly; the
    defect is an observability gap, not an active miss;
  - if some lack a BOM -> those were reinterpreted and are actively unscanned.

Plus a synthetic carrier: even-length, invalid utf-8, no BOM, token in utf-8.
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution")
GATE_PATH = ROOT / "proposals" / "scaffold-opensource-export-v0.1" / "scan_only_gate.py"
LANDED = "8ef57756a7c5a31e0c73385e4dca02e08a6bcbeb"

SPEC = importlib.util.spec_from_file_location("gate_utf16", GATE_PATH)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

os.chdir(ROOT)
entries = GATE.parse_ls_tree(GATE.resolve_commit(LANDED))
blobs = GATE.read_blobs(entries)

bom_le = bom_be = no_bom = 0
no_bom_sample = []
for entry in entries:
    if entry["type"] != "blob":
        continue
    raw = blobs[entry["oid"]]
    try:
        raw.decode("utf-8")
        continue
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("utf-16")
    except UnicodeDecodeError:
        continue
    if raw[:2] == b"\xff\xfe":
        bom_le += 1
    elif raw[:2] == b"\xfe\xff":
        bom_be += 1
    else:
        no_bom += 1
        if len(no_bom_sample) < 10:
            no_bom_sample.append({"path": entry["path"], "bytes": len(raw),
                                  "head_hex": raw[:8].hex()})

# synthetic carrier: even length, invalid utf-8, no BOM, token in utf-8 bytes
token = "fixture-private-token"
with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    repo = base / "repo"
    repo.mkdir()
    patterns = base / "patterns.txt"
    registry = base / "registry.jsonl"
    patterns.write_text(token + "\n", encoding="utf-8")
    registry.write_bytes(b"")
    run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    run("init", "-q")
    run("config", "user.email", "probe@example.invalid")
    run("config", "user.name", "Probe")
    payload_bytes = b"\x80\x80" + token.encode("utf-8")
    if len(payload_bytes) % 2:
        payload_bytes += b"\x00"
    (repo / "carrier.bin").write_bytes(payload_bytes)
    run("add", "-A")
    run("commit", "-q", "-m", "even-length non-utf8 carrier, no BOM")
    previous_cwd, previous_registry = os.getcwd(), GATE.DEFAULT_REGISTRY
    os.chdir(repo)
    GATE.DEFAULT_REGISTRY = str(registry)
    try:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = GATE.main(["--commit", "HEAD", "--private-strings", str(patterns)])
        receipt = json.loads(out.getvalue()) if out.getvalue() else None
    finally:
        GATE.DEFAULT_REGISTRY = previous_registry
        os.chdir(previous_cwd)

json.dump({
    "landed_commit": LANDED,
    "non_utf8_utf16_decodable": bom_le + bom_be + no_bom,
    "with_utf16_le_bom": bom_le,
    "with_utf16_be_bom": bom_be,
    "without_bom": no_bom,
    "without_bom_sample": no_bom_sample,
    "synthetic_carrier": {
        "carrier_bytes_len": len(payload_bytes),
        "token_present_as_utf8_bytes": token.encode("utf-8") in payload_bytes,
        "rc": rc,
        "state": receipt["state"] if receipt else None,
        "files_scanned": receipt["files_scanned"] if receipt else None,
        "occurrence_count": receipt["occurrence_count"] if receipt else None,
        "reason_codes": receipt["reason_codes"] if receipt else None,
        "receipt_mentions_fallback_decoder": (
            "unsupported" in json.dumps(receipt) if receipt else None
        ),
    },
}, sys.stdout, ensure_ascii=False, indent=1)
print()
