"""Enumerate + secret-scan the new reachable-object closure for a push.

Closure = objects reachable from HEAD that are not reachable from
`<remote-ref>`.  This is a conservative publication boundary relative to that
ref, not an exact network-transfer set.  A stale remote-tracking ref can make
the closure larger, so callers must fetch before treating it as a push review.

Prints a deterministic JSON receipt so the co-signer can re-run this
independently (CHARTER 六.1 requires the signer to rescan, not reuse output).

Usage:
  python scan_push_manifest.py --remote-ref origin/<branch>
"""

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys

# Secret shapes. Deliberately noisy: a false positive costs one human read,
# a false negative is an irreversible publication.
PATTERNS = [
    ("private_key_block", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("openssh_key_body", re.compile(rb"\bssh-(rsa|ed25519|dss)\s+AAAA[0-9A-Za-z+/]{40,}")),
    ("aws_access_key_id", re.compile(rb"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(rb"\bgh[pousr]_[0-9A-Za-z]{30,}")),
    ("anthropic_key", re.compile(rb"\bsk-ant-[0-9A-Za-z_-]{20,}")),
    ("generic_sk_key", re.compile(rb"\bsk-[0-9A-Za-z]{32,}")),
    ("slack_token", re.compile(rb"\bxox[abprs]-[0-9A-Za-z-]{10,}")),
    ("google_api_key", re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("bearer_literal", re.compile(rb"(?i)\bauthorization\s*[:=]\s*['\"]?bearer\s+[0-9A-Za-z._-]{20,}")),
    # assignment-shaped: catches `password = "..."` but not prose about passwords
    ("assigned_credential", re.compile(
        rb"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret)"
        rb"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
]


def git(*args, input=None):
    out = subprocess.run(
        ["git", *args], input=input, capture_output=True, check=True)
    return out.stdout


def reachable_objects(remote_ref):
    """Return stable object ids and non-authoritative path hints."""
    raw = git("rev-list", "--objects", "HEAD", "--not", remote_ref)
    hints = {}
    for line in raw.splitlines():
        object_id_bytes, separator, hint_bytes = line.partition(b" ")
        object_id = object_id_bytes.decode("ascii")
        hints.setdefault(object_id, set())
        if separator:
            hints[object_id].add(hint_bytes.decode("utf-8", "replace"))
    return [(object_id, sorted(hints[object_id]))
            for object_id in sorted(hints)]


def cat_file_batch(object_ids):
    """Read Git objects in one plumbing call, preserving requested order."""
    if not object_ids:
        return []
    request = b"".join(
        object_id.encode("ascii") + b"\n" for object_id in object_ids)
    raw = git("cat-file", "--batch", input=request)
    stream = io.BytesIO(raw)
    objects = []
    for expected_id in object_ids:
        header = stream.readline().rstrip(b"\n")
        parts = header.split()
        if len(parts) != 3 or parts[1] == b"missing":
            raise RuntimeError(
                f"cannot read closure object {expected_id}: "
                f"{header.decode('utf-8', 'replace')}")
        object_id = parts[0].decode("ascii")
        object_type = parts[1].decode("ascii")
        size = int(parts[2])
        if object_id != expected_id:
            raise RuntimeError(
                f"cat-file order mismatch: expected {expected_id}, "
                f"received {object_id}")
        payload = stream.read(size)
        if len(payload) != size or stream.read(1) != b"\n":
            raise RuntimeError(f"truncated cat-file payload for {object_id}")
        objects.append((object_id, object_type, payload))
    if stream.read():
        raise RuntimeError("unexpected trailing data from git cat-file --batch")
    return objects


def scan_object(object_id, object_type, payload, path_hints):
    findings = []
    for name, rx in PATTERNS:
        for match in rx.finditer(payload):
            finding = {
                "object_id": object_id,
                "object_type": object_type,
                "byte_offset": match.start(),
                "pattern": name,
                "excerpt": match.group(0)[:60].decode("utf-8", "replace"),
            }
            if path_hints:
                finding["path_hints"] = path_hints
            if object_type in {"blob", "commit"}:
                finding["line"] = payload.count(b"\n", 0, match.start()) + 1
            findings.append(finding)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote-ref", required=True)
    args = ap.parse_args(argv)

    base = git("rev-parse", args.remote_ref).decode().strip()
    head = git("rev-parse", "HEAD").decode().strip()

    commits = git("rev-list", "--reverse", f"{base}..{head}").decode().split()
    object_hints = reachable_objects(args.remote_ref)
    hints_by_id = dict(object_hints)
    entries, findings = [], []
    for object_id, object_type, payload in cat_file_batch(
            [object_id for object_id, _ in object_hints]):
        entry = {
            "object_id": object_id,
            "object_type": object_type,
            "bytes": len(payload),
        }
        path_hints = hints_by_id[object_id]
        if path_hints:
            entry["path_hints"] = path_hints
        entries.append(entry)
        findings.extend(
            scan_object(object_id, object_type, payload, path_hints))

    receipt = {
        "closure_semantics": (
            "objects reachable from HEAD and not remote_ref; conservative "
            "publication boundary relative to remote_ref, not an exact "
            "network-transfer set"
        ),
        "remote_ref_freshness": (
            "caller must fetch before review; a stale remote-tracking ref "
            "is not directionally safe: it may enlarge this closure during "
            "append-only remote advancement or shrink it after remote "
            "history is rewritten"
        ),
        "scan_semantics": (
            "clean means configured secret shapes did not match object "
            "payloads in this new reachable-object closure; it is not proof "
            "that the repository or published history contains no secret"
        ),
        "remote_ref": args.remote_ref,
        "base_commit": base,
        "head_commit": head,
        "commits_to_publish": commits,
        "closure_objects": len(entries),
        "manifest": entries,
        "manifest_digest": hashlib.sha256(
            json.dumps(
                entries,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "secret_findings": findings,
        "clean": not findings,
    }
    sys.stdout.write(json.dumps(receipt, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
