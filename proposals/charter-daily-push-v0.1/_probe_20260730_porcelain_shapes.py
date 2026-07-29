#!/usr/bin/env python3
"""Independent probe: what does `git push --porcelain <oid>:<ref>` actually print?

Read-only with respect to the repository under review: every git object this
touches lives in a throwaway temp directory, and the only remote is a local
`file://` bare repo.  Nothing here reads or writes the real origin.

Verifies the two shapes claimed in Codex's 2026-07-30T08:09:03+09:00 proposal:
  * rc=0  success            -> one tab-separated ref-status record
  * rc=1  stale exact lease  -> flag '!' , summary '[rejected] (stale info)'
and additionally records, for each case, the full line inventory of stdout so
the "exactly one three-field tab record" parse rule can be checked against
reality rather than against a remembered shape.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile


def run(cwd, *args):
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc


def must(cwd, *args):
    proc = run(cwd, *args)
    if proc.returncode != 0:
        raise SystemExit(
            f"setup failed: git {' '.join(args)}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc.stdout.strip()


def inventory(text):
    lines = text.splitlines()
    return [
        {"raw": line, "tab_fields": line.split("\t"), "n_tab_fields": len(line.split("\t"))}
        for line in lines
    ]


def main():
    root = tempfile.mkdtemp(prefix="porcelain-probe-")
    try:
        bare = os.path.join(root, "bare.git")
        work = os.path.join(root, "work")
        os.makedirs(work)
        must(root, "init", "--bare", "-b", "main", bare)
        must(root, "init", "-b", "main", work)
        must(work, "config", "user.email", "probe@example.invalid")
        must(work, "config", "user.name", "probe")

        origin = "file:///" + bare.replace("\\", "/").lstrip("/")

        with open(os.path.join(work, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("one\n")
        must(work, "add", "a.txt")
        must(work, "commit", "-m", "c1")
        c1 = must(work, "rev-parse", "HEAD")
        must(work, "push", origin, f"{c1}:refs/heads/main")

        with open(os.path.join(work, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("two\n")
        must(work, "commit", "-am", "c2")
        c2 = must(work, "rev-parse", "HEAD")

        ref = "refs/heads/main"
        results = {}

        # Case 1: honest success, exact lease held.
        p = run(
            work,
            "push",
            "--porcelain",
            f"--force-with-lease={ref}:{c1}",
            origin,
            f"{c2}:{ref}",
        )
        results["success"] = {
            "returncode": p.returncode,
            "stdout_lines": inventory(p.stdout),
            "stderr": p.stderr,
            "expected_source_field": f"{c2}:{ref}",
        }

        # Case 2: stale exact lease.  Move the remote out from under us.
        with open(os.path.join(work, "b.txt"), "w", encoding="utf-8") as fh:
            fh.write("third party\n")
        must(work, "add", "b.txt")
        must(work, "commit", "-m", "c3-third-party")
        c3 = must(work, "rev-parse", "HEAD")
        must(work, "push", origin, f"{c3}:{ref}")
        with open(os.path.join(work, "c.txt"), "w", encoding="utf-8") as fh:
            fh.write("ours\n")
        must(work, "add", "c.txt")
        must(work, "commit", "-m", "c4-ours")
        c4 = must(work, "rev-parse", "HEAD")

        p = run(
            work,
            "push",
            "--porcelain",
            f"--force-with-lease={ref}:{c2}",  # stale: remote is at c3
            origin,
            f"{c4}:{ref}",
        )
        results["stale_lease"] = {
            "returncode": p.returncode,
            "stdout_lines": inventory(p.stdout),
            "stderr": p.stderr,
            "expected_source_field": f"{c4}:{ref}",
        }
        results["stale_lease"]["remote_after"] = must(
            work, "ls-remote", "--refs", origin, ref
        )

        # Case 3: up-to-date push (no-op) -- a shape neither of us enumerated.
        p = run(
            work,
            "push",
            "--porcelain",
            f"--force-with-lease={ref}:{c3}",
            origin,
            f"{c3}:{ref}",
        )
        results["already_up_to_date"] = {
            "returncode": p.returncode,
            "stdout_lines": inventory(p.stdout),
            "stderr": p.stderr,
            "expected_source_field": f"{c3}:{ref}",
        }

        results["git_version"] = must(root, "--version")
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
