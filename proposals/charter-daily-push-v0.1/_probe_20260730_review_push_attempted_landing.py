#!/usr/bin/env python3
"""Read-only review probe for ab8aca0 (push_attempted layering).

Two independent questions, no remote contact, no writes:

1. Do the receipt's CHARTER-3 locatability claims hold?  Recompute the
   in-tree blob oids and the current-record-minus-LF-v1 line hashes for the
   cosigning peer-chat rows from ab8aca0's tree, not from the worktree.

2. Is the new ``push_attempted`` field guarded in the same direction on both
   of its producers?  Compare the signatures of ``fail`` and
   ``live_remote_oid`` and emit the receipt a *new* post-push exit would get
   if its author forgot the keyword.
"""

import hashlib
import inspect
import io
import json
import pathlib
import re
import subprocess
import sys
import contextlib

COMMIT = "ab8aca02c3120bca5ee271a1395e43c662fa92bf"
REPO = pathlib.Path(__file__).resolve().parents[2]
CHAT = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
TOOL = "proposals/charter-daily-push-v0.1/push_authorized_oid.py"
TEST = "proposals/charter-daily-push-v0.1/test_push_authorized_oid.py"

CLAIMED = {
    "peer_chat_blob": "2fc4e2f8d1dccabd1c7e974412bbc004cfb146bf",
    "tool_blob": "b88600395cfff771ef7cc6874ff3d4a84cfd8412",
    "test_blob": "ae017a87c7cead320695f98d990886e64a49846c",
    "line_3046": "51c135955b1f3b4cee4c0b4afe5026a8debb0f9a9608a4ce1832791454a3ace2",
    "line_3047": "8949e3da8a6e092d5d38dd18bc8d70f6dc87f799f9ed40e2e020a218412b45ae",
}


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        check=True,
    )


def blob_oid(path):
    out = git("rev-parse", f"{COMMIT}:{path}").stdout
    return out.decode("ascii").strip()


def line_hashes():
    """current-record-minus-LF-v1 over the blob as it sits in ab8aca0."""
    raw = git("cat-file", "blob", f"{COMMIT}:{CHAT}").stdout
    rows = raw.split(b"\n")
    result = {}
    for number in (3046, 3047):
        record = rows[number - 1]
        result[number] = {
            "sha256": hashlib.sha256(record).hexdigest(),
            "trailing_cr": record.endswith(b"\r"),
            "from": json.loads(record.decode("utf-8"))["from"],
            "time": json.loads(record.decode("utf-8"))["time"],
        }
    return result


def load_tool():
    source = git("cat-file", "blob", f"{COMMIT}:{TOOL}").stdout.decode("utf-8")
    namespace = {"__name__": "_probe_tool_ab8aca0"}
    exec(compile(source, TOOL, "exec"), namespace)
    return namespace


def signature_guard(namespace):
    report = {}
    for name in ("fail", "live_remote_oid"):
        parameter = inspect.signature(namespace[name]).parameters[
            "push_attempted"
        ]
        report[name] = {
            "kind": parameter.kind.name,
            "required": parameter.default is inspect.Parameter.empty,
            "default": (
                None
                if parameter.default is inspect.Parameter.empty
                else parameter.default
            ),
        }
    return report


def forgotten_keyword_receipt(namespace):
    """What a future post-push exit emits when its author omits the keyword."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        namespace["fail"](
            "hypothetical_new_post_push_exit",
            stage="post_verification",
            ref="refs/heads/main",
        )
    return json.loads(buffer.getvalue())


def stage_coupled_assertions():
    """Does any test tie 'stage is post-push' to push_attempted generically?"""
    text = (REPO / TEST).read_text(encoding="utf-8")
    return {
        "push_attempted_assertions": len(
            re.findall(r'receipt\["push_attempted"\]', text)
        ),
        "asserts_true": len(
            re.findall(r'receipt\["push_attempted"\] is True', text)
        ),
        "asserts_false": len(
            re.findall(r'receipt\["push_attempted"\] is False', text)
        ),
        "any_loop_over_all_exits": bool(
            re.search(r"for .*(exit|receipt)s? in", text)
        ),
    }


def main():
    observed_blobs = {
        "peer_chat_blob": blob_oid(CHAT),
        "tool_blob": blob_oid(TOOL),
        "test_blob": blob_oid(TEST),
    }
    hashes = line_hashes()
    observed = dict(observed_blobs)
    observed["line_3046"] = hashes[3046]["sha256"]
    observed["line_3047"] = hashes[3047]["sha256"]
    namespace = load_tool()
    json.dump(
        {
            "commit": COMMIT,
            "locatability": {
                "claimed": CLAIMED,
                "observed": observed,
                "all_match": observed == CLAIMED,
                "mismatched_keys": sorted(
                    key for key in CLAIMED if CLAIMED[key] != observed[key]
                ),
                "row_detail": hashes,
            },
            "push_attempted_guard": signature_guard(namespace),
            "forgotten_keyword_receipt": forgotten_keyword_receipt(namespace),
            "test_coverage_shape": stage_coupled_assertions(),
            "authority": "recomputed_from_git_objects_and_committed_source",
            "boundary": (
                "no remote contact; the hypothetical exit is emitted by "
                "calling fail() directly, it is not a live code path"
            ),
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
