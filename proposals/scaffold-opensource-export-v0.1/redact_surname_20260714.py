# Owner-directed redaction tool (owner 2026-07-14 08:59:17, peer-chat):
# remove observer's surname from all public materials. Sensitive patterns are NOT
# hardcoded here — they are read from the gitignored local private-strings file,
# so this script itself is safe to publish. First pattern line maps to 云 (Chinese),
# ASCII pattern lines map to yun. Handles utf-8 and utf-16 files, preserves encoding.
# Reports per-file before/after sha256 + replacement counts as JSON on stdout.
import hashlib
import json
import os
import sys

ROOT = r"D:\WeilanSkillEvolution"
PRIVATE = os.path.join(ROOT, "proposals", "scaffold-opensource-export-v0.1",
                       "redaction-private-strings.local.txt")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
SKIP_FILES = {"redaction-private-strings.local.txt"}

with open(PRIVATE, encoding="utf-8") as fh:
    patterns = [ln.strip() for ln in fh if ln.strip()]
REPL = [(p, "yun" if p.isascii() else "云") for p in patterns]

def longpath(path):
    return path if path.startswith("\\\\?\\") else "\\\\?\\" + os.path.abspath(path)

def load(path):
    with open(longpath(path), "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8", "utf-16"):
        try:
            return raw, raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw, None, None

report = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if fn in SKIP_FILES:
            continue
        path = os.path.join(dirpath, fn)
        raw, text, enc = load(path)
        if text is None:
            continue
        counts = {pat: text.count(pat) for pat, _ in REPL if text.count(pat)}
        if not counts:
            continue
        new = text
        for pat, sub in REPL:
            new = new.replace(pat, sub)
        with open(longpath(path), "wb") as fh:
            fh.write(new.encode(enc))
        report.append({
            "file": os.path.relpath(path, ROOT).replace("\\", "/"),
            "encoding": enc,
            "counts": counts,
            "before_sha256": hashlib.sha256(raw).hexdigest(),
            "after_sha256": hashlib.sha256(new.encode(enc)).hexdigest(),
        })

json.dump({"files": report, "total_files": len(report)}, sys.stdout, ensure_ascii=False, indent=1)
