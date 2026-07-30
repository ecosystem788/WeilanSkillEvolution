"""Execute ANCHOR-PROPOSAL-20260730-A1 exactly as cosigned.

Zero on-site freedom: every byte of the two registry records is determined by
the proposal (six identity fields + serialization convention) plus four fields
taken verbatim from the consent record, plus two hashes computed here from the
staged index blob.

Dry run by default; pass --apply to stage, append, and commit.
"""

import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
REGISTRY = "proposals/redaction-gate-tree-subject-v0.1/occurrence-registry.jsonl"
BASE_REGISTRY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
PROPOSAL_NONCE = "ANCHOR-PROPOSAL-20260730-A1"
CONSENT_NONCE = "ANCHOR-CONSENT-20260730-A1"
RULESET_DIGEST = (
    "51047b475e9e250bb8ddd3ff3bfe4a839da9015a5343442e7000987733f4eceb"
)

ANCHORS = [
    {
        "path": "proposals/bounded-scheduler-v0.1/impl/codex-inbox.jsonl",
        "ruleset_digest": RULESET_DIGEST,
        "pattern_index": 0,
        "where": "content",
        "line_hash": (
            "dd9b46ea61e330369440c1f49b2d1bf6874ed2182dbccf405e6c2748dd6d1f45"
        ),
        "occurrence_ordinal": 0,
        "_suffix": "A",
    },
    {
        "path": "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl",
        "ruleset_digest": RULESET_DIGEST,
        "pattern_index": 0,
        "where": "content",
        "line_hash": (
            "d07af3bfea217f3ebaaa2226dc85937517d951a0d0467becf695c3caa951bd1b"
        ),
        "occurrence_ordinal": 0,
        "_suffix": "B",
    },
]


def git(*args, **kwargs):
    out = subprocess.run(
        ["git"] + list(args), cwd=REPO, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, **kwargs
    )
    if out.returncode != 0:
        raise SystemExit(
            "git %s failed rc=%d: %s"
            % (" ".join(args), out.returncode, out.stderr.decode("utf-8", "replace"))
        )
    return out.stdout


def stop(msg):
    raise SystemExit("STOP: " + msg)


def locate(blob, sender, nonce):
    """current-record-minus-LF-v1 over the unique matching physical record."""
    hits = []
    for raw in blob.split(b"\n"):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        if obj.get("from") == sender and nonce in (obj.get("text") or ""):
            hits.append(raw)
    if len(hits) != 1:
        stop("nonce %s located %d records for from=%s (must be exactly 1)"
             % (nonce, len(hits), sender))
    return hits[0], hashlib.sha256(hits[0]).hexdigest()


def take_markers(record_bytes):
    text = json.loads(record_bytes.decode("utf-8"))["text"]
    wanted = [
        "live_remote_oid_A", "peer_attestation_A",
        "live_remote_oid_B", "peer_attestation_B",
    ]
    got = {}
    for name in wanted:
        marks = [ln for ln in text.split("\n") if ln.startswith(name + "=")]
        if len(marks) != 1:
            stop("marker %s appears %d times in the consent record (must be 1)"
                 % (name, len(marks)))
        got[name] = marks[0].split("=", 1)[1].strip()
    for suffix in ("A", "B"):
        oid = got["live_remote_oid_" + suffix]
        if len(oid) != 40 or any(c not in "0123456789abcdef" for c in oid):
            stop("live_remote_oid_%s is not 40 lowercase hex: %r" % (suffix, oid))
        if not got["peer_attestation_" + suffix]:
            stop("peer_attestation_%s is empty after strip" % suffix)
    return got


def serialize(obj):
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\x0a"


def main():
    apply = "--apply" in sys.argv
    report = {"mode": "apply" if apply else "dry-run"}

    # Step 0 -- preimage of the target file.
    porcelain = git("status", "--porcelain", "--", REGISTRY).decode("utf-8")
    if porcelain.strip():
        stop("registry porcelain not empty: %r" % porcelain)
    abs_registry = os.path.join(REPO, REGISTRY)
    with open(abs_registry, "rb") as fh:
        pre = fh.read()
    pre_sha = hashlib.sha256(pre).hexdigest()
    if len(pre) != 0 or pre_sha != BASE_REGISTRY_SHA256:
        stop("registry preimage drifted: %d bytes sha256=%s" % (len(pre), pre_sha))
    report["preimage"] = {"bytes": 0, "sha256": pre_sha, "porcelain_empty": True}

    # Step 2 -- stage the source ledger so authorization ships in this commit.
    # Dry run must not touch the index, so it reads working-tree bytes instead;
    # those can differ from the index blob under text=auto (proposal section 9),
    # which is why the signature hashes are only authoritative under --apply.
    if apply:
        git("add", "--", LEDGER)
        index_blob = git("cat-file", "blob", ":" + LEDGER)
        report["hash_source"] = "index blob after staging"
    else:
        with open(os.path.join(REPO, LEDGER), "rb") as fh:
            index_blob = fh.read()
        report["hash_source"] = "working tree (provisional, dry run only)"

    # Step 3 -- independently compute the two signature hashes from the index blob.
    prop_bytes, prop_sha = locate(index_blob, "claude", PROPOSAL_NONCE)
    cons_bytes, cons_sha = locate(index_blob, "codex", CONSENT_NONCE)
    report["proposal_line_sha256"] = prop_sha
    report["consent_line_sha256"] = cons_sha
    report["proposal_record_bytes"] = len(prop_bytes)
    report["consent_record_bytes"] = len(cons_bytes)

    # Step 1 -- take the four consent-supplied fields verbatim.
    markers = take_markers(cons_bytes)
    report["markers"] = {k: (v[:60] + "...") if len(v) > 60 else v
                         for k, v in markers.items()}

    # Step 4 -- build exactly two records.
    payload = b""
    for anchor in ANCHORS:
        suffix = anchor["_suffix"]
        rec = {k: v for k, v in anchor.items() if not k.startswith("_")}
        rec["peer_attestation"] = markers["peer_attestation_" + suffix]
        rec["live_remote_oid"] = markers["live_remote_oid_" + suffix]
        rec["proposal_line_sha256"] = prop_sha
        rec["consent_line_sha256"] = cons_sha
        payload += serialize(rec)
    report["appended_bytes"] = len(payload)
    report["appended_sha256"] = hashlib.sha256(payload).hexdigest()
    report["record_count"] = payload.count(b"\x0a")

    if not apply:
        report["preview"] = payload.decode("utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    with open(abs_registry, "ab") as fh:
        fh.write(payload)
    git("add", "--", REGISTRY)

    staged = git("diff", "--cached", "--name-only").decode("utf-8").split()
    if sorted(staged) != sorted([LEDGER, REGISTRY]):
        stop("staged set is not exactly the two authorized paths: %r" % staged)
    report["staged"] = staged

    msg_path = os.path.join(os.path.dirname(__file__), "_msg_20260730_anchor_A1.txt")
    git("commit", "-F", msg_path)
    landed = git("rev-parse", "HEAD").decode("ascii").strip()
    report["landing_commit"] = landed

    # Step 6 -- postcheck against the landing commit's blob.
    post_blob = git("cat-file", "blob", landed + ":" + LEDGER)
    _, post_prop = locate(post_blob, "claude", PROPOSAL_NONCE)
    _, post_cons = locate(post_blob, "codex", CONSENT_NONCE)
    report["postcheck"] = {
        "proposal_line_sha256": post_prop,
        "consent_line_sha256": post_cons,
        "equal": post_prop == prop_sha and post_cons == cons_sha,
    }
    if not report["postcheck"]["equal"]:
        report["landed_claim"] = "REFUSED: postcheck mismatch"
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
