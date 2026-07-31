"""Freeze the *payload* a T1 commit would durably store, not the worktree bytes.

Why this exists: on 2026-07-28T14:38:44+09:00 Codex co-signed T1_COMMIT_SCOPE.tsv
(sha256 0a63c2f5...), which binds `path/status/size/sha256` **as measured on disk**. At
staged-precommit Codex found 4 of the 45 blobs disagreed with that object: `* text=auto`
in .gitattributes plus core.autocrlf=true normalize CRLF->LF on the way into the index, so
the bytes Git would keep are not the bytes that were signed. Codex hit its death line and
aborted with no commit (peer-chat 2026-07-28T14:4x). Its instruction for the next case:
the signature object must be the staged/commit payload.

This script produces exactly that object. Path set is NOT re-litigated: it is imported from
t1_scope.build_rows(), the same source the 14:38:44 signature used, so the payload manifest
cannot silently cover a different set of files.

Signature object (same shape convention as t1_scope, one column swapped):
  rows sorted by path, each `path<TAB>blob_oid<TAB>payload_size<TAB>payload_sha256`,
  joined by LF, no trailing LF.
The frozen file T1_COMMIT_PAYLOAD.tsv *is* those bytes, so `sha256sum` on it checks the
digest without trusting this script.

How the payload is obtained: `git add` into a **temporary index** (GIT_INDEX_FILE), then
`git ls-files --stage` for the oids and `git cat-file --batch` for the stored bytes. This is
Git's own filter pipeline, not a re-implementation of it, so no normalization rule can be
missed. Two honest side effects, both disclosed rather than hidden:
  * it writes loose blob objects into .git/objects — the same blobs a commit would write,
    unreferenced until then, and gc-prunable;
  * it refuses to run unless the real index is empty, and never touches it.

  freeze:  python proposals/uncommitted-drift-inventory-v0.1/t1_payload.py --freeze
  verify:  python proposals/uncommitted-drift-inventory-v0.1/t1_payload.py --verify
Verify exits 0 only if the live tree still produces the frozen payload exactly.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t1_scope  # noqa: E402  (path set + worktree measurements come from the signed script)

ROOT = t1_scope.ROOT
PAYLOAD = os.path.join(t1_scope.OUT_DIR, "T1_COMMIT_PAYLOAD.tsv")


def git(args, **kw):
    return subprocess.run(["git"] + args, capture_output=True, cwd=ROOT, **kw)


def real_index_entries():
    """Staged paths in the *real* index. Must be empty: we refuse to work beside a
    half-staged tree, because then 'index was clean before/after' proves nothing."""
    out = git(["diff", "--cached", "--name-only", "-z"]).stdout
    return [p.decode("utf-8") for p in out.split(b"\x00") if p]


def stage_into_temp_index(paths):
    """Run the real filter pipeline for `paths` in a throwaway index -> {path: oid}."""
    fd, tmp_index = tempfile.mkstemp(prefix="t1_payload_index_")
    os.close(fd)
    os.unlink(tmp_index)  # git wants to create it itself; a 0-byte file is not a valid index
    env = dict(os.environ, GIT_INDEX_FILE=tmp_index)
    try:
        # --add --renormalize is deliberately NOT used: plain `git add` is what the real
        # commit would run, and the point is to reproduce that, not to improve on it.
        for i in range(0, len(paths), 100):  # chunked: Windows argv limit
            r = git(["add", "--"] + paths[i:i + 100], env=env)
            if r.returncode != 0:
                raise RuntimeError("git add failed: " + r.stderr.decode("utf-8", "replace"))
        out = git(["ls-files", "--stage", "-z"], env=env).stdout
        staged = {}
        for rec in out.split(b"\x00"):
            if not rec:
                continue
            meta, path = rec.split(b"\t", 1)
            _mode, oid, _stage = meta.split()
            staged[path.decode("utf-8")] = oid.decode()
        return staged
    finally:
        if os.path.isfile(tmp_index):
            os.unlink(tmp_index)


def payload_digests(oids):
    """oid -> (stored_size, sha256 of stored bytes), read back through git cat-file."""
    if not oids:
        return {}
    proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write(("\n".join(oids) + "\n").encode())
    proc.stdin.flush()
    proc.stdin.close()
    result = {}
    stream = proc.stdout
    for oid in oids:
        header = b""
        while not header.endswith(b"\n"):
            ch = stream.read(1)
            if not ch:
                raise RuntimeError("cat-file stream ended early at " + oid)
            header += ch
        got_oid, kind, size = header.decode().split()
        if kind != "blob":
            raise RuntimeError("%s is a %s, not a blob" % (got_oid, kind))
        size = int(size)
        body = b""
        while len(body) < size:
            chunk = stream.read(size - len(body))
            if not chunk:
                raise RuntimeError("truncated blob " + got_oid)
            body += chunk
        stream.read(1)  # trailing LF git appends after each record
        result[got_oid] = (size, hashlib.sha256(body).hexdigest())
    proc.stdout.close()
    proc.wait()
    return result


def build():
    """Returns (rows, canonical_bytes, digest, report_fragment)."""
    scope_rows, _canonical, scope_digest, notes = t1_scope.build_rows()
    paths = [r[0] for r in scope_rows]
    worktree = {r[0]: (r[2], r[3]) for r in scope_rows}

    staged = stage_into_temp_index(paths)
    missing = sorted(set(paths) - set(staged))
    extra = sorted(set(staged) - set(paths))
    if missing or extra:
        raise RuntimeError("temp index does not match the T1 path set: missing=%s extra=%s"
                           % (missing, extra))

    digests = payload_digests(sorted(set(staged.values())))
    rows, normalized = [], []
    for path in sorted(paths):
        oid = staged[path]
        size, sha = digests[oid]
        rows.append((path, oid, size, sha))
        if (size, sha) != worktree[path]:
            normalized.append({
                "path": path,
                "worktree_size": worktree[path][0], "worktree_sha256": worktree[path][1],
                "payload_size": size, "payload_sha256": sha,
                "delta_bytes": size - worktree[path][0],
            })
    canonical = "\n".join("%s\t%s\t%d\t%s" % r for r in rows).encode("utf-8")
    fragment = {
        "t1_scope_digest": scope_digest,
        "scope_notes": notes,
        "files": len(rows),
        "worktree_bytes": sum(worktree[p][0] for p in paths),
        "payload_bytes": sum(r[2] for r in rows),
        "normalized_by_git": normalized,
    }
    return rows, canonical, hashlib.sha256(canonical).hexdigest(), fragment


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--verify"
    dirty = real_index_entries()
    if dirty:
        print(json.dumps({"verdict": "REAL INDEX NOT EMPTY; refusing to measure",
                          "staged": dirty}, ensure_ascii=False, indent=2))
        return 2
    rows, canonical, digest, report = build()
    report["git_head"] = git(["rev-parse", "HEAD"]).stdout.decode().strip()
    report["t1_payload_digest"] = digest
    if mode == "--freeze":
        with open(PAYLOAD, "wb") as fh:
            fh.write(canonical)
        report["wrote"] = os.path.relpath(PAYLOAD, ROOT).replace("\\", "/")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not os.path.isfile(PAYLOAD):
        report["verdict"] = "no frozen payload on disk; run --freeze first"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    frozen = open(PAYLOAD, "rb").read()
    report["frozen_digest"] = hashlib.sha256(frozen).hexdigest()
    report["match"] = frozen == canonical
    if not report["match"]:
        live = {r[0]: r for r in rows}
        old = {}
        for line in frozen.decode("utf-8").split("\n"):
            if not line:
                continue
            p, o, z, h = line.split("\t")
            old[p] = (p, o, int(z), h)
        report["drift"] = {
            "added": sorted(set(live) - set(old)),
            "removed": sorted(set(old) - set(live)),
            "changed": sorted(p for p in set(live) & set(old) if live[p] != old[p]),
        }
    report["verdict"] = "payload unchanged; signature still binds" if report["match"] \
        else "PAYLOAD DRIFTED; any signature over the frozen digest is void"
    # The real index must still be untouched -- we promised not to write to it.
    report["real_index_after"] = real_index_entries()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["match"] and not report["real_index_after"] else 1


if __name__ == "__main__":
    sys.exit(main())
