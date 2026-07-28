"""Repro: a stale remote-tracking ref makes the closure UNDER-include, and the
scanner exits 0 on a push that publishes a synthetic secret.

Self-contained: builds a bare "remote" and a work repo in a temp dir, touches no
network and no repository state outside that temp dir.

Scenario (the shrink direction that `remote_ref_freshness` now names, and that
`closure_semantics` still calls a "conservative publication boundary"):

  1. work repo pushes C1(clean), C2(synthetic key), C3(clean) to the remote
  2. work repo fetches -> origin/main == C3
  3. remote history is rewritten back to C1 and pruned (objects for C2/C3 gone)
  4. work repo commits C4(clean) and does NOT re-fetch -> origin/main still C3
  5. scanner --remote-ref origin/main sees only C4 -> clean=true, exit 0
  6. the actual push is a fast-forward from C1 and republishes C2's secret blob

The assertion below is the WRONG answer on purpose: it asserts the exit code is
0 while the remote receives the secret. If freshness ever becomes enforced, this
script turns red -- delete it then, do not keep it as a regression test.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

SCANNER = pathlib.Path(__file__).with_name("scan_push_manifest.py")


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check,
                          capture_output=True)


def out(repo, *args):
    return git(repo, *args).stdout.decode().strip()


def synthetic_aws_key(fill):
    # runtime assembly: no literal key shape lives in this file
    return "AK" + "IA" + fill * 16


def write_commit(repo, name, text, message):
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return out(repo, "rev-parse", "HEAD")


def main():
    key = synthetic_aws_key("S")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        remote = root / "remote.git"
        work = root / "work"
        remote.mkdir()
        work.mkdir()
        git(remote, "init", "-q", "--bare", "-b", "main", ".")
        git(work, "init", "-q", "-b", "main", ".")
        git(work, "config", "user.email", "stale-test@local")
        git(work, "config", "user.name", "stale-test")
        git(work, "remote", "add", "origin", str(remote))

        c1 = write_commit(work, "a.txt", "clean\n", "c1 clean")
        git(work, "push", "-q", "origin", "main")

        write_commit(work, "leak.txt", key + "\n", "c2 secret")
        secret_blob = out(work, "rev-parse", "HEAD:leak.txt")
        c3 = write_commit(work, "a.txt", "clean again\n", "c3 clean")
        git(work, "push", "-q", "origin", "main")
        git(work, "fetch", "-q", "origin")
        tracked = out(work, "rev-parse", "origin/main")

        # remote history rewritten back to c1, unreferenced objects pruned
        git(remote, "update-ref", "refs/heads/main", c1)
        git(remote, "reflog", "expire", "--expire=now", "--all")
        git(remote, "gc", "-q", "--prune=now")
        remote_has_secret_before = git(
            remote, "cat-file", "-e", secret_blob, check=False).returncode == 0

        # work repo commits and does NOT re-fetch: origin/main is now stale
        write_commit(work, "b.txt", "clean\n", "c4 clean")
        stale = out(work, "rev-parse", "origin/main")

        proc = subprocess.run(
            [sys.executable, str(SCANNER), "--remote-ref", "origin/main"],
            cwd=work, capture_output=True)
        receipt = json.loads(proc.stdout.decode("utf-8"))

        push = git(work, "push", "origin", "main", check=False)
        remote_has_secret_after = git(
            remote, "cat-file", "-e", secret_blob, check=False).returncode == 0

        print(json.dumps({
            "remote_ref_after_rewrite": out(remote, "rev-parse", "refs/heads/main"),
            "stale_tracking_ref": stale,
            "tracking_ref_was": tracked,
            "closure_objects": receipt["closure_objects"],
            "commits_to_publish": len(receipt["commits_to_publish"]),
            "scanner_exit_code": proc.returncode,
            "scanner_clean": receipt["clean"],
            "closure_semantics": receipt["closure_semantics"],
            "remote_had_secret_before_push": remote_has_secret_before,
            "push_exit_code": push.returncode,
            "remote_has_secret_after_push": remote_has_secret_after,
        }, indent=2, ensure_ascii=False))

        assert proc.returncode == 0 and receipt["clean"] is True, \
            "scanner flagged it -- the false negative is gone, delete this repro"
        assert not remote_has_secret_before, "remote still held the pruned blob"
        assert push.returncode == 0, "push did not succeed"
        assert remote_has_secret_after, "push did not republish the secret blob"
        assert receipt["closure_objects"] == 3, \
            f"closure was {receipt['closure_objects']} objects, expected c4 only"
        print("\nWRONG ANSWER REPRODUCED: exit 0 / clean=true, "
              "while the push republished the synthetic secret blob "
              f"{secret_blob}")


if __name__ == "__main__":
    raise SystemExit(main())
