"""Probe: does CONVENTION 3.1 wording admit multiple honest values?

Read-only. Recomputes the pre/post aggregate fingerprint of c2ad677 under
several readings of "多文件时按路径字典序串联 sha256 后的总指纹",
and reports which (if any) reproduces the value recorded in the commit message.
"""
import hashlib
import json
import subprocess

COMMIT = "c2ad677"
PARENT = "6337964"
RECORDED_PRE = "a2faf20ad8330c79d053cad8b951ff1e381650191536ff2d22a06e0462dece97"
RECORDED_POST = "ef405e0917233056a4d3fe5517af35a089eeae14a2ea6d67b558b844e49c65e9"


def run(args):
    return subprocess.run(args, capture_output=True)


def changed_paths():
    out = run(["git", "diff", "--name-only", PARENT, COMMIT]).stdout
    return sorted(p for p in out.decode("utf-8").split("\n") if p.strip())


def blob(rev, path):
    """Raw bytes of path at rev; b'' if absent."""
    r = run(["git", "show", "%s:%s" % (rev, path)])
    return r.stdout if r.returncode == 0 else None


def sha(b):
    return hashlib.sha256(b).hexdigest()


def readings(paths, rev):
    """Each reading returns a hex digest. All are honest readings of 3.1."""
    present = []
    for p in paths:
        b = blob(rev, p)
        present.append((p, b))

    # A: concatenate raw bytes, absent = empty bytes
    a = hashlib.sha256()
    for p, b in present:
        a.update(b if b is not None else b"")

    # B: concatenate per-file sha256 hex digests (ascii), absent = empty bytes hashed
    bb = hashlib.sha256()
    for p, b in present:
        bb.update(sha(b if b is not None else b"").encode("ascii"))

    # C: concatenate per-file raw 32-byte digests
    c = hashlib.sha256()
    for p, b in present:
        c.update(hashlib.sha256(b if b is not None else b"").digest())

    # D: concatenate "path\0sha256hex\n" lines (path-bound manifest)
    d = hashlib.sha256()
    for p, b in present:
        d.update(("%s\0%s\n" % (p, sha(b if b is not None else b""))).encode("utf-8"))

    # E: like B but absent files skipped entirely (not counted as empty)
    e = hashlib.sha256()
    for p, b in present:
        if b is not None:
            e.update(sha(b).encode("ascii"))

    # F: like A but absent files skipped entirely
    f = hashlib.sha256()
    for p, b in present:
        if b is not None:
            f.update(b)

    return {
        "A_concat_raw_bytes_absent_empty": a.hexdigest(),
        "B_concat_hexdigests_absent_empty": bb.hexdigest(),
        "C_concat_rawdigests_absent_empty": c.hexdigest(),
        "D_path_bound_manifest": d.hexdigest(),
        "E_concat_hexdigests_absent_skipped": e.hexdigest(),
        "F_concat_raw_bytes_absent_skipped": f.hexdigest(),
    }


def main():
    paths = changed_paths()
    pre = readings(paths, PARENT)
    post = readings(paths, COMMIT)
    result = {
        "commit": COMMIT,
        "parent": PARENT,
        "n_paths": len(paths),
        "paths": paths,
        "recorded_pre": RECORDED_PRE,
        "recorded_post": RECORDED_POST,
        "pre_readings": pre,
        "post_readings": post,
        "pre_matches": [k for k, v in pre.items() if v == RECORDED_PRE],
        "post_matches": [k for k, v in post.items() if v == RECORDED_POST],
        "distinct_pre_values": len(set(pre.values())),
        "distinct_post_values": len(set(post.values())),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
