"""Read-only private-string gate over one explicitly named subject.

``--tree`` preserves the export-oriented filesystem scan and receipt byte for
byte; its result must not be cited as a judgment about a Git push.

``--commit`` scans the resolved commit tree.  Its governing invariant is:
every current occurrence that lacks an anchor with an exactly matching
six-field identity *and* the current ``ruleset_digest`` is ``NEW_MATCHES``.
Reason codes are diagnostic only.  Registry-wide stale anchors never produce a
state.

The tool never modifies its subject or registry and never prints a pattern.

The ``--commit`` receipt contract is named by ``GATE_VERSION``.  The name
covers its top-level keys, occurrence keys, identity projection,
``registry_anchor_set_sha256`` algorithm, and state/exit-code mapping.
"""

# Read-only pre-push gate (push 前脱敏门 v4).
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

DEFAULT_PRIVATE = os.path.join(
    r"D:\WeilanSkillEvolution", "proposals", "scaffold-opensource-export-v0.1",
    "redaction-private-strings.local.txt")
DEFAULT_REGISTRY = os.path.join(
    r"D:\WeilanSkillEvolution", "proposals", "redaction-gate-tree-subject-v0.1",
    "occurrence-registry.jsonl")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
IDENTITY_FIELDS = (
    "path", "ruleset_digest", "pattern_index", "where", "line_hash",
    "occurrence_ordinal",
)
REGISTRY_REQUIRED_FIELDS = set(IDENTITY_FIELDS) | {
    "peer_attestation",
    "live_remote_oid",
    "proposal_line_sha256",
    "consent_line_sha256",
}
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
GATE_VERSION = "scan-only-gate/4.1"


def longpath(path):
    return path if path.startswith("\\\\?\\") else "\\\\?\\" + os.path.abspath(path)


def decode_text(raw):
    for enc in ("utf-8", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def load_patterns(private_abs):
    with open(private_abs, encoding="utf-8") as fh:
        patterns = [ln.strip() for ln in fh if ln.strip()]
    if not patterns:
        raise ValueError("private_strings_file_empty")
    joined = "\n".join(patterns).encode("utf-8")
    return patterns, hashlib.sha256(joined).hexdigest()


def file_bytes_sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scan_tree(tree, private_abs, patterns):
    """Legacy --tree scan. Keep its traversal and receipt shape unchanged."""
    hits = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(tree):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if os.path.abspath(path) == private_abs:
                continue
            relative = os.path.relpath(path, tree).replace("\\", "/")
            scanned += 1
            for index, pattern in enumerate(patterns):
                count = relative.count(pattern)
                if count:
                    hits.append({"path": relative, "pattern_index": index,
                                 "count": count, "where": "path"})
            with open(longpath(path), "rb") as fh:
                raw = fh.read()
            text = decode_text(raw)
            if text is None:
                continue
            for index, pattern in enumerate(patterns):
                count = text.count(pattern)
                if count:
                    hits.append({"path": relative, "pattern_index": index,
                                 "count": count, "where": "content"})
    verdict = "PASS" if not hits else "FAIL"
    return {"tree": tree, "files_scanned": scanned,
            "pattern_count": len(patterns), "hit_count": len(hits),
            "hits": hits, "verdict": verdict}


def git_bytes(*args, input_bytes=None):
    proc = subprocess.run(
        ["git", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError("git_command_failed")
    return proc.stdout


def resolve_commit(commit_arg):
    try:
        resolved = git_bytes(
            "rev-parse", "--verify", f"{commit_arg}^{{commit}}"
        ).strip().decode("ascii").lower()
        object_type = git_bytes("cat-file", "-t", resolved).strip()
    except (RuntimeError, UnicodeDecodeError):
        raise ValueError("not_a_commit") from None
    if not HEX_40.fullmatch(resolved) or object_type != b"commit":
        raise ValueError("not_a_commit")
    return resolved


def parse_ls_tree(resolved):
    raw = git_bytes("ls-tree", "-r", "-z", resolved)
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path_raw = record.split(b"\t", 1)
            mode, object_type, oid = metadata.split(b" ", 2)
            path = path_raw.decode("utf-8")
            oid_text = oid.decode("ascii").lower()
        except (ValueError, UnicodeDecodeError):
            raise ValueError("invalid_ls_tree_record") from None
        entries.append({
            "mode": mode.decode("ascii"),
            "type": object_type.decode("ascii"),
            "oid": oid_text,
            "path": path,
        })
    return entries


def read_blobs(entries):
    blob_entries = [entry for entry in entries if entry["type"] == "blob"]
    if not blob_entries:
        return {}
    request = b"".join(
        entry["oid"].encode("ascii") + b"\n" for entry in blob_entries
    )
    output = git_bytes("cat-file", "--batch", input_bytes=request)
    result = {}
    offset = 0
    for entry in blob_entries:
        header_end = output.find(b"\n", offset)
        if header_end < 0:
            raise ValueError("invalid_cat_file_batch")
        header = output[offset:header_end].split(b" ")
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError("invalid_cat_file_batch")
        try:
            size = int(header[2])
        except ValueError:
            raise ValueError("invalid_cat_file_batch") from None
        start = header_end + 1
        end = start + size
        if end >= len(output) or output[end:end + 1] != b"\n":
            raise ValueError("invalid_cat_file_batch")
        result[entry["oid"]] = output[start:end]
        offset = end + 1
    if offset != len(output):
        raise ValueError("invalid_cat_file_batch")
    return result


def private_path_in_repository(private_abs):
    try:
        root = git_bytes("rev-parse", "--show-toplevel").strip().decode(
            sys.getfilesystemencoding()
        )
        root_abs = os.path.abspath(root)
        if os.path.commonpath([root_abs, private_abs]) != root_abs:
            return None
        return os.path.relpath(private_abs, root_abs).replace("\\", "/")
    except (RuntimeError, UnicodeDecodeError, ValueError):
        return None


def validate_registry_entry(entry):
    if not isinstance(entry, dict):
        return False
    if not REGISTRY_REQUIRED_FIELDS.issubset(entry):
        return False
    if not isinstance(entry["path"], str) or not entry["path"]:
        return False
    if not HEX_64.fullmatch(entry["ruleset_digest"]):
        return False
    if not isinstance(entry["pattern_index"], int) or entry["pattern_index"] < 0:
        return False
    if entry["where"] not in {"path", "content"}:
        return False
    if not HEX_64.fullmatch(entry["line_hash"]):
        return False
    if (not isinstance(entry["occurrence_ordinal"], int)
            or entry["occurrence_ordinal"] < 0):
        return False
    if (not isinstance(entry["peer_attestation"], str)
            or not entry["peer_attestation"].strip()):
        return False
    if not HEX_40.fullmatch(entry["live_remote_oid"]):
        return False
    if not HEX_64.fullmatch(entry["proposal_line_sha256"]):
        return False
    if not HEX_64.fullmatch(entry["consent_line_sha256"]):
        return False
    return True


def load_registry(registry_path):
    entries = []
    with open(registry_path, "rb") as fh:
        for line_number, raw in enumerate(fh.read().split(b"\n"), 1):
            if not raw:
                continue
            try:
                entry = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError(
                    f"invalid_registry_record:{line_number}"
                ) from None
            if not validate_registry_entry(entry):
                raise ValueError(
                    f"incomplete_registry_record:{line_number}"
                )
            entries.append(entry)
    return entries


def non_overlapping_positions(text, pattern):
    positions = []
    start = 0
    while True:
        position = text.find(pattern, start)
        if position < 0:
            return positions
        positions.append(position)
        start = position + len(pattern)


def make_occurrences(path, raw, patterns):
    occurrences = []
    path_bytes = path.encode("utf-8")
    for pattern_index, pattern in enumerate(patterns):
        positions = non_overlapping_positions(path, pattern)
        for ordinal, _position in enumerate(positions):
            occurrences.append({
                "path": path,
                "pattern_index": pattern_index,
                "where": "path",
                "line_hash": hashlib.sha256(path_bytes).hexdigest(),
                "occurrence_ordinal": ordinal,
                "line_framing": "path",
                "line_number": None,
                "count": len(positions),
            })

    try:
        raw.decode("utf-8")
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False

    if utf8:
        for line_number, record in enumerate(raw.split(b"\n"), 1):
            text = record.decode("utf-8")
            record_hash = hashlib.sha256(record).hexdigest()
            for pattern_index, pattern in enumerate(patterns):
                positions = non_overlapping_positions(text, pattern)
                for ordinal, _position in enumerate(positions):
                    occurrences.append({
                        "path": path,
                        "pattern_index": pattern_index,
                        "where": "content",
                        "line_hash": record_hash,
                        "occurrence_ordinal": ordinal,
                        "line_framing": "utf-8",
                        "line_number": line_number,
                        "count": len(positions),
                    })
        return occurrences

    try:
        text = raw.decode("utf-16")
    except UnicodeDecodeError:
        return occurrences
    blob_hash = hashlib.sha256(raw).hexdigest()
    for pattern_index, pattern in enumerate(patterns):
        positions = non_overlapping_positions(text, pattern)
        for ordinal, _position in enumerate(positions):
            occurrences.append({
                "path": path,
                "pattern_index": pattern_index,
                "where": "content",
                "line_hash": blob_hash,
                "occurrence_ordinal": ordinal,
                "line_framing": "unsupported",
                "line_number": None,
                "count": len(positions),
            })
    return occurrences


def identity(entry, include_digest=True):
    fields = IDENTITY_FIELDS if include_digest else tuple(
        field for field in IDENTITY_FIELDS if field != "ruleset_digest"
    )
    return tuple(entry[field] for field in fields)


def canonical_registry_anchor_set_sha256(registry):
    """Hash the set consumed by the gate using its exact identity semantics."""
    rows = set()
    for entry in registry:
        projected = []
        for field in IDENTITY_FIELDS:
            value = entry[field]
            if isinstance(value, bool):
                value = int(value)
            projected.append(value)
        rows.add(json.dumps(
            projected, ensure_ascii=False, separators=(",", ":")
        ))
    body = "\n".join(sorted(rows)).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def classify_occurrences(occurrences, registry, ruleset_digest):
    current_anchors = {
        identity(entry)
        for entry in registry
        if entry["ruleset_digest"] == ruleset_digest
    }
    old_anchors = {
        identity(entry, include_digest=False)
        for entry in registry
        if entry["ruleset_digest"] != ruleset_digest
    }
    reason_codes = []
    classified = []
    for occurrence in occurrences:
        occurrence["ruleset_digest"] = ruleset_digest
        if (occurrence["line_framing"] != "unsupported"
                and identity(occurrence) in current_anchors):
            occurrence["anchored"] = True
            occurrence["reason_code"] = None
        else:
            occurrence["anchored"] = False
            if (occurrence["line_framing"] != "unsupported"
                    and identity(occurrence, include_digest=False)
                    in old_anchors):
                reason = "anchor_ruleset_stale"
            else:
                reason = "unanchored_occurrence"
            occurrence["reason_code"] = reason
            if reason not in reason_codes:
                reason_codes.append(reason)
        classified.append(occurrence)
    return classified, reason_codes


def scan_commit(commit_arg, private_abs, private_bytes_sha256, registry_path,
                patterns, ruleset_digest):
    resolved = resolve_commit(commit_arg)
    entries = parse_ls_tree(resolved)
    private_relative = private_path_in_repository(private_abs)
    if (private_relative is not None
            and any(entry["path"] == private_relative for entry in entries)):
        raise ValueError("private_strings_in_commit_tree")
    registry = load_registry(registry_path)
    blobs = read_blobs(entries)
    occurrences = []
    non_blob_entries = 0
    for entry in entries:
        raw = b""
        if entry["type"] == "blob":
            raw = blobs[entry["oid"]]
        else:
            non_blob_entries += 1
        occurrences.extend(make_occurrences(entry["path"], raw, patterns))
    classified, reason_codes = classify_occurrences(
        occurrences, registry, ruleset_digest
    )
    stale_anchor_count = sum(
        entry["ruleset_digest"] != ruleset_digest for entry in registry
    )
    unanchored_count = sum(not item["anchored"] for item in classified)
    if not classified:
        state, exit_code = "CLEAN", 0
    elif not unanchored_count:
        state, exit_code = "KNOWN_PUBLIC_ONLY", 3
    else:
        state, exit_code = "NEW_MATCHES", 2
    receipt = {
        "commit": commit_arg,
        "resolved_oid": resolved,
        "entries_scanned": len(entries),
        "files_scanned": len(entries) - non_blob_entries,
        "non_blob_entries": non_blob_entries,
        "pattern_count": len(patterns),
        "ruleset_digest": ruleset_digest,
        "stale_anchor_count": stale_anchor_count,
        "occurrence_count": len(classified),
        "unanchored_occurrence_count": unanchored_count,
        "reason_codes": reason_codes,
        "occurrences": classified,
        "state": state,
        "private_strings_path": private_abs,
        "private_strings_bytes_sha256": private_bytes_sha256,
        "registry_path": registry_path,
        "registry_bytes_sha256": file_bytes_sha256(registry_path),
        "registry_entry_count": len(registry),
        "registry_anchor_set_sha256": canonical_registry_anchor_set_sha256(
            registry
        ),
        "gate_version": GATE_VERSION,
    }
    return receipt, exit_code


def usage_error(reason, **fields):
    payload = {"error": reason}
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="read-only private-string scan of an exact tree")
    subject = parser.add_mutually_exclusive_group(required=True)
    subject.add_argument("--tree", help="root of the exact export tree")
    subject.add_argument("--commit", help="commit-ish whose resolved commit tree is scanned")
    parser.add_argument("--private-strings", default=DEFAULT_PRIVATE)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)

    private_abs = os.path.abspath(args.private_strings)
    try:
        patterns, ruleset_digest = load_patterns(private_abs)
        private_bytes_sha256 = file_bytes_sha256(private_abs)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "private_strings_unreadable"
        return usage_error(reason)

    if args.tree is not None:
        tree = os.path.abspath(args.tree)
        if not os.path.isdir(tree):
            print(json.dumps({"error": "tree is not a directory", "tree": tree}), file=sys.stderr)
            return 1
        receipt = scan_tree(tree, private_abs, patterns)
        json.dump(receipt, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0 if not receipt["hits"] else 2

    try:
        registry_abs = os.path.abspath(args.registry)
        receipt, exit_code = scan_commit(
            args.commit, private_abs, private_bytes_sha256, registry_abs,
            patterns, ruleset_digest,
        )
    except FileNotFoundError:
        return usage_error("registry_unreadable")
    except ValueError as exc:
        return usage_error(str(exc), commit=args.commit)
    except RuntimeError:
        return usage_error("git_command_failed", commit=args.commit)
    except OSError:
        return usage_error("commit_scan_io_error", commit=args.commit)
    json.dump(receipt, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
