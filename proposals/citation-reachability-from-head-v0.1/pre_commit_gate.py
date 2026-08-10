# -*- coding: utf-8 -*-
"""pre-commit gate: keep peer-chat:N citations reachable from the new commit.

Dual-sign landing: proposal peer-chat:3733, agree peer-chat:3734.

Rule (proposal background, agreed wording): if the commit message cites
peer-chat:N, require the peer-chat ledger height IN THIS COMMIT -- the staged
copy, falling back to HEAD's copy -- to be >= max(N). Reject otherwise.

Only the git commit path is covered. Stash-created commits and --no-verify
bypass this hook by design: documented boundaries, not bugs to "fix".

Exit 0 = allow; exit 1 = reject.
"""
from __future__ import annotations

import os
import subprocess
import sys

LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"

HERE = os.path.dirname(os.path.abspath(__file__))
LOCATOR_DIR = os.path.normpath(
    os.path.join(HERE, os.pardir, "peer-chat-citation-integrity-v0.1")
)
if LOCATOR_DIR not in sys.path:
    sys.path.insert(0, LOCATOR_DIR)

from peer_chat_locator import extract_any  # noqa: E402


def _git(*args):
    """Run git, return (returncode, stdout_bytes, stderr_bytes).

    Never text=True -- GBK decode hazard on this box (same lesson as the
    census probe).
    """
    p = subprocess.run(
        ["git"] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return p.returncode, p.stdout, p.stderr


def ledger_height(rev_prefix):
    """Line count of LEDGER at ``rev_prefix + LEDGER`` (":0:" or "HEAD:")."""
    rc, oid_raw, _ = _git("rev-parse", rev_prefix + LEDGER)
    if rc != 0:
        return None
    oid = oid_raw.decode("ascii").strip()
    rc, blob, _ = _git("cat-file", "blob", oid)
    if rc != 0:
        return None
    return len(blob.decode("utf-8", errors="replace").splitlines())


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(argv) < 2:
        return 0
    try:
        with open(argv[1], "r", encoding="utf-8") as fh:
            msg = fh.read()
    except OSError:
        return 0
    refs = extract_any(msg)
    if not refs:
        return 0
    max_ref = max(refs)
    # "本次提交后的账本高度": the staged copy if present, else HEAD's copy.
    height = ledger_height(":0:")
    if height is None:
        height = ledger_height("HEAD:")
    if height is None:
        # Ledger absent from both index and HEAD -- nothing to verify against.
        return 0
    if max_ref > height:
        print(
            "peer-chat citation beyond ledger height: "
            "max_ref=%d head_height=%d" % (max_ref, height),
            file=sys.stderr,
        )
        print(
            "Stage the ledger first (ledger-only commit), or --no-verify "
            "once (documented boundary).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
