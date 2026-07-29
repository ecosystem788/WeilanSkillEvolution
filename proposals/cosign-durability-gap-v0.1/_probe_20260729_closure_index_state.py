#!/usr/bin/env python3
"""Probe: does a plumbing-based durability closure leave the real index stale?

Context: PROPOSAL-POSTCHECK-DURABILITY-CLOSURE.md v0.1 leaves the implementation
free ("命令偏好不写进法") and its fixture 1 only pins "*other* index/worktree state
unchanged". This probe asks what happens to the *target's own* index entry when
closure is done with a temporary index + plumbing, which is one of the two
implementations the proposal explicitly permits.

Read-only w.r.t. this repository: everything happens in a throwaway temp repo.
Run: python _probe_20260729_closure_index_state.py
"""

import json
import os
import shutil
import subprocess
import tempfile

TARGET = "target.txt"
BASE = b"base bytes\n"
SIGNED = b"signed final bytes\n"


def git(repo, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, env=e, text=False
    )
    if p.returncode != 0:
        raise RuntimeError(f"git {args} -> {p.returncode}: {p.stderr.decode(errors='replace')}")
    return p.stdout.decode().strip()


def main():
    repo = tempfile.mkdtemp(prefix="wl-closure-probe-")
    try:
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "probe@local")
        git(repo, "config", "user.name", "probe")
        git(repo, "config", "core.autocrlf", "false")

        # baseline commit
        with open(os.path.join(repo, TARGET), "wb") as f:
            f.write(BASE)
        with open(os.path.join(repo, "unrelated.txt"), "wb") as f:
            f.write(b"unrelated base\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "base")
        base_head = git(repo, "rev-parse", "HEAD")

        # the co-signed transaction: signed final written to the worktree only
        with open(os.path.join(repo, TARGET), "wb") as f:
            f.write(SIGNED)
        # unrelated concurrent drift, as fixture 1 requires
        with open(os.path.join(repo, "unrelated.txt"), "ab") as f:
            f.write(b"drift\n")
        git(repo, "add", "unrelated.txt")  # staged drift
        with open(os.path.join(repo, "untracked.txt"), "wb") as f:
            f.write(b"untracked\n")

        # --- durability closure, temp-index/plumbing flavour (permitted by the proposal) ---
        tmp_index = os.path.join(repo, ".git", "closure-index")
        env = {"GIT_INDEX_FILE": tmp_index}
        git(repo, "read-tree", "HEAD", env=env)
        blob = git(repo, "hash-object", "-w", "--", TARGET)
        git(repo, "update-index", "--cacheinfo", f"100644,{blob},{TARGET}", env=env)
        tree = git(repo, "write-tree", env=env)
        commit = git(repo, "commit-tree", tree, "-p", base_head, "-m", "closure")
        git(repo, "update-ref", "--create-reflog", "refs/heads/main", commit, base_head)
        os.remove(tmp_index)

        # --- what the proposal's four states would report ---
        four_states = {
            "signed_raw_present": open(os.path.join(repo, TARGET), "rb").read() == SIGNED,
            "local_ref_reachable": git(repo, "rev-parse", "refs/heads/main") == commit,
            "git_blob_equals_signed_raw": git(repo, "cat-file", "blob", blob).encode()
            == SIGNED.replace(b"\n", b""),
            "remote_visibility": "not_in_scope",
        }
        delta = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit)

        # --- what the real index now says ---
        status = git(repo, "status", "--porcelain")
        staged = git(repo, "diff", "--cached", "--name-status")

        # --- the hazard: an ordinary later commit of the index ---
        git(repo, "commit", "-q", "-m", "some later ordinary commit")
        after = git(repo, "show", f"HEAD:{TARGET}").encode() + b"\n"

        print(json.dumps({
            "four_states_all_pass": four_states,
            "closure_commit_path_delta": delta.splitlines(),
            "real_index_after_closure": {
                "status_porcelain": status.splitlines(),
                "diff_cached_name_status": staged.splitlines(),
            },
            "hazard": {
                "next_plain_commit_target_bytes": after.decode(),
                "equals_signed_final": after == SIGNED,
                "equals_pre_signature_base": after == BASE,
            },
        }, ensure_ascii=False, indent=2))
    finally:
        shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    main()
