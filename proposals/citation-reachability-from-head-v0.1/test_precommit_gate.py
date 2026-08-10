# -*- coding: utf-8 -*-
"""Regression tests for the citation-reachability pre-commit gate.

Covers (proposal peer-chat:3733, agree peer-chat:3734):
  a) no peer-chat:N in the message -> PASS
  b) refs all <= ledger height -> PASS
  c) max ref > ledger height -> FAIL, stderr carries max_ref and head_height
  d) stash path documented: the hook/README state that stash-created commits
     bypass the gate by design (the hook never touches git stash)
  e) --no-verify bypass documented, NOT executed here -- testing the escape
     hatch would pin it

Hermetic: each gate case runs in a fresh temp git repo with a seeded ledger
of known height, so the tests do not depend on the live ledger size.

Ledger refs follow the P1 family: peer-chat:N with 3-5 digit N (two-digit
tokens are not citations, see peer_chat_locator docstring).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "pre_commit_gate.py")
REPO_ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))

LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
HEIGHT = 2000


def _git(repo, *args):
    p = subprocess.run(
        ["git", "-C", repo] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (
        p.returncode,
        p.stdout.decode("utf-8", errors="replace"),
        p.stderr.decode("utf-8", errors="replace"),
    )


def _make_repo_with_ledger(height=HEIGHT):
    tmp = tempfile.mkdtemp(prefix="wl-gate-test-")
    _git(tmp, "init", "-q")
    _git(tmp, "config", "user.email", "gate-test@example.invalid")
    _git(tmp, "config", "user.name", "gate test")
    os.makedirs(os.path.join(tmp, os.path.dirname(LEDGER)), exist_ok=True)
    path = os.path.join(tmp, LEDGER)
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(1, height + 1):
            fh.write('{"from": "seed", "text": "line %d"}\n' % i)
    _git(tmp, "add", LEDGER)
    _git(tmp, "commit", "-q", "-m", "seed ledger")
    return tmp


def _run_gate(repo, msg):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as fh:
        fh.write(msg)
        msg_path = fh.name
    p = subprocess.run(
        [sys.executable, GATE, msg_path],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    os.unlink(msg_path)
    return (
        p.returncode,
        p.stdout.decode("utf-8", errors="replace"),
        p.stderr.decode("utf-8", errors="replace"),
    )


def test_a_no_citation_passes():
    repo = _make_repo_with_ledger()
    rc, _, _ = _run_gate(repo, "plain commit message")
    assert rc == 0


def test_b_all_refs_within_height_pass():
    repo = _make_repo_with_ledger()
    rc, _, _ = _run_gate(repo, "decision: something (peer-chat:1003+1007)")
    assert rc == 0


def test_c_max_ref_beyond_height_fails_with_metrics():
    repo = _make_repo_with_ledger()
    rc, _, err = _run_gate(repo, "decision: something (peer-chat:2042)")
    assert rc == 1
    assert "max_ref=2042" in err
    assert "head_height=2000" in err


def test_d_stash_boundary_documented():
    hook = os.path.join(REPO_ROOT, ".githooks", "commit-msg")
    assert os.path.isfile(hook), "missing .githooks/commit-msg"
    text = open(hook, encoding="utf-8").read()
    assert "stash" in text.lower()
    readme = os.path.join(REPO_ROOT, "README.md")
    assert os.path.isfile(readme)
    assert "stash" in open(readme, encoding="utf-8").read().lower()


def test_e_no_verify_documented_not_pinned():
    hook = os.path.join(REPO_ROOT, ".githooks", "commit-msg")
    text = open(hook, encoding="utf-8").read()
    assert "--no-verify" in text
    readme = os.path.join(REPO_ROOT, "README.md")
    assert "--no-verify" in open(readme, encoding="utf-8").read()


def test_staged_copy_semantics_index_first():
    # Agreed correction (peer-chat:3734): the height is the staged copy
    # (index), falling back to HEAD. An unstaged ledger line must NOT
    # satisfy a citation; once staged, it must.
    repo = _make_repo_with_ledger()
    with open(os.path.join(repo, LEDGER), "a", encoding="utf-8") as fh:
        fh.write('{"from": "seed", "text": "line 2001"}\n')
    rc, _, err = _run_gate(repo, "cite peer-chat:2001")
    assert rc == 1, "unstaged new line must not satisfy the citation"
    assert "max_ref=2001" in err
    _git(repo, "add", LEDGER)
    rc, _, _ = _run_gate(repo, "cite peer-chat:2001")
    assert rc == 0, "staged new line must satisfy the citation"
