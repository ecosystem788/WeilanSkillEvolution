"""Read-only differential sweep over the 38-commit publication closure.

Purpose: scan_push_manifest.py reports `clean` only for its *configured secret
shapes*. This probe asks a different question on the same object set: does any
blob about to become public carry privacy-sensitive content that is not
secret-shaped (owner email, photo path/filename, credential-looking headers),
and are there any non-text blobs?

Input: the manifest JSON written by an independent run of scan_push_manifest.py.
No writes to the repository; reads blobs via `git cat-file`.
"""
import json
import io
import re
import subprocess
import sys
from collections import Counter

REPO = "D:/WeilanSkillEvolution"
MANIFEST = sys.argv[1] if len(sys.argv) > 1 else (
    "D:/WeilanSkillEvolution/proposals/charter-daily-push-v0.1/"
    "_scan_claude_20260730.json")

PATTERNS = {
    "owner_email": re.compile(r"kevinkubuso@onet\.pl", re.I),
    "any_email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "photo_filename": re.compile(r"\.(png|jpg|jpeg|gif|webp|bmp|heic)\b", re.I),
    "private_key_header": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "gh_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "bearer": re.compile(r"(?i)(authorization:\s*bearer|api[_-]?key\s*[=:]\s*['\"][A-Za-z0-9]{16,})"),
    "sk_openai": re.compile(r"sk-[A-Za-z0-9]{20,}"),
}


def cat(oid):
    return subprocess.run(
        ["git", "-C", REPO, "cat-file", "blob", oid],
        capture_output=True,
    ).stdout


def main():
    d = json.load(io.open(MANIFEST, encoding="utf-8"))
    blobs = [m for m in d["manifest"] if m["object_type"] == "blob"]
    ext = Counter()
    binary = []
    hits = {k: [] for k in PATTERNS}
    for m in blobs:
        path = (m.get("path_hints") or ["<no-hint>"])[0]
        ext[path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else "<noext>"] += 1
        raw = cat(m["object_id"])
        if b"\x00" in raw:
            binary.append((m["object_id"], path, len(raw)))
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", "replace")
        for name, pat in PATTERNS.items():
            for mo in pat.finditer(text):
                line = text.count("\n", 0, mo.start()) + 1
                hits[name].append({"path": path, "line": line, "match": mo.group(0)[:120]})

    out = {
        "manifest_digest": d["manifest_digest"],
        "base_commit": d["base_commit"],
        "head_commit": d["head_commit"],
        "blob_count": len(blobs),
        "extension_histogram": dict(sorted(ext.items(), key=lambda kv: -kv[1])),
        "binary_blobs": binary,
        "pattern_hit_counts": {k: len(v) for k, v in hits.items()},
        "pattern_hits": {k: v[:25] for k, v in hits.items() if v},
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
