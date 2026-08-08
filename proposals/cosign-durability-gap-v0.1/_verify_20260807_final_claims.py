"""Read-only byte-level verification of windowed signed-final claims.
ASCII-only source. Zero authority. Exits 0 always.
"""
import hashlib, subprocess, sys

REPO = r"D:\WeilanSkillEvolution"

def git(*args, binary=False):
    r = subprocess.run(["git"] + list(args), cwd=REPO, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(args) + " -> " + r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")

def blob_sha256(commit, path):
    """Return (oid, sha256hex) of the blob at commit:path, or (None, None)."""
    try:
        listing = git("ls-tree", "-r", commit, "--", path)
    except RuntimeError:
        return None, None
    for ln in listing.splitlines():
        parts = ln.split()
        if len(parts) == 4 and parts[1] == "blob":
            oid = parts[2]
            data = git("cat-file", "blob", oid, binary=True)
            return oid, hashlib.sha256(data).hexdigest()
    return None, None

def is_ancestor(commit):
    r = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                       cwd=REPO, capture_output=True)
    return r.returncode == 0

TARGETS = [
    # final_sha256, landing commit, path, also_check_head
    ("9fdab08587d37db33906a4b4dcdfe47c5891dd4dbca1aae07153a8aa8c10dc35", "b7f3f7d", "CHARTER.md", False),
    ("6b1432fbc5333f7c1802f5fc4f2285be7bae6ade42a7c0e95a52ddffb42938a8", "bf4329e", "CHARTER.md", False),
    ("bd32917c74701e672187d3270b57ee9124e09238949609536d69048623ba5031", "5d2aea08", "ROADMAP.md", False),
    ("2b97b0ff09700be1da8c1515ecb850572c281022728d59adb0b300e9511e7eae", "85c87ea2", "proposals/cosign-bytewise-binding-v0.1/verify_binding.py", True),
    ("5437f97ffcc39123efe5145615e3e714abb17549285f130d841a4701c849e9b2", "1b89d44f", "proposals/cosign-bytewise-binding-v0.1/test_verify_binding.py", True),
    ("ed16290d5c16d3864afe8c84c6c9426abe83d1e36c176a30d29b33ab061b32fc", "e8ba2d71", "proposals/cosign-bytewise-binding-v0.1/CONVENTION.md", True),
    ("7ac491da805a940bd61030e9952e873e85683e20398f0f3e2fb21fc8aec8d274", "18a16d0", "ROADMAP.md", True),
    ("b3b1fb0f9049ff042f75c37f223baa403596480c67f29d549619cd54bd58f450", "38fbd03", "proposals/canonical-workspace-cache-v0.1/.gitattributes", False),
    ("1775da2bf33c356d759cfa9e50cda74e9d8cb829b80a626fefa1344bfe09de10", "bd51f00", "proposals/canonical-workspace-cache-v0.1/.gitattributes", True),
    ("3d72884cd6af5a7f75b97d8cfe3a2897195cd634917144608b82378d73beca98", "eb4cdcc", "proposals/bounded-scheduler-v0.1/impl/append_clocked_jsonl.py", False),
    # 11th: build_proposed_final.py of witness-post-archival-asymmetry (L3170)
    ("ea126d8c04f85e9f91c76976f448a36dd4c64bac1d45d2ef546b36b34fe03f1a", "HEAD", "proposals/witness-post-archival-asymmetry-v0.1/build_proposed_final.py", False),
]

ok = True
for final, commit, path, head_also in TARGETS:
    subj = git("log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M", commit).strip() if commit != "HEAD" else "HEAD"
    anc = is_ancestor(commit) if commit != "HEAD" else True
    oid, sha = blob_sha256(commit, path)
    match = (sha == final)
    line = "PASS" if (match and anc) else "FAIL"
    if not match or not anc:
        ok = False
    print("%s  %s" % (line, subj))
    print("    path  : %s" % path)
    print("    final : %s" % final[:20])
    print("    at %s : oid=%s sha256=%s" % (commit, oid or "-", (sha or "-")[:20]))
    print("    ancestor-of-HEAD: %s   bytes-match: %s" % (anc, match))
    if head_also:
        ho, hs = blob_sha256("HEAD", path)
        hm = (hs == final)
        if not hm:
            ok = False
        print("    HEAD  : oid=%s sha256=%s  head==final: %s" % (ho or "-", (hs or "-")[:20], hm))
print("ALL_OK" if ok else "SOME_FAIL")
sys.exit(0)
