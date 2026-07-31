"""Independent recomputation of Codex's CHARTER five-item enumeration sync proposal.

Read-only. Writes nothing. Prints measured values next to the signed expectations.
"""
import difflib
import hashlib

CHARTER = "CHARTER.md"
CONVENTION = "proposals/cosign-bytewise-binding-v0.1/CONVENTION.md"

EXPECT_BASE = "f5b8ffc510f04365954da43e69c3a840f7fe6b49c08c4335e30e5b5be9b38a4a"
EXPECT_FINAL = "d11739550eb7deb7cd7d7ac2bac8c8fef5cc7947c7cb5ec31a20f2d75e488e6d"
EXPECT_CONVENTION = "413d2ab27709b354e5babb8c3ed2456710317607ab4d4abbf970336809c7c63c"

ANCHOR = (
    "  绑定 target path + base SHA-256 + proposed-final SHA-256 + "
    "字节口径：执行前 base 不符则签名失效，"
)
REPLACEMENT = (
    "  绑定 target path + base SHA-256 + proposed-final SHA-256 + "
    "字节口径 + 行级形状（增行数与删行数）"
    "：执行前 base 不符则签名失效，"
)

SECTION = "## 三、决策程序：双签"


def sha(b):
    return hashlib.sha256(b).hexdigest()


base = open(CHARTER, "rb").read()
conv = open(CONVENTION, "rb").read()

print("== CONVENTION v0.7 landed? ==")
print("  measured", sha(conv))
print("  expected", EXPECT_CONVENTION)
print("  match   ", sha(conv) == EXPECT_CONVENTION)

print("\n== base preimage ==")
print("  sha256  ", sha(base), sha(base) == EXPECT_BASE)
print("  bytes   ", len(base), "expected 6247")
print("  crlf    ", base.count(b"\r\n"), " bare CR", base.count(b"\r"))
print("  bom     ", base[:3] == b"\xef\xbb\xbf")
print("  trailing single LF", base.endswith(b"\n") and not base.endswith(b"\n\n"))

text = base.decode("utf-8")
print("  lines   ", len(text.splitlines()), "expected 83")

print("\n== anchor ==")
n = text.count(ANCHOR)
print("  occurrences of anchor:", n, "(must be exactly 1)")
print("  occurrences of replacement already present:", text.count(REPLACEMENT))

if n == 1:
    after = text.replace(ANCHOR, REPLACEMENT)
    ab = after.encode("utf-8")
    print("\n== independently generated post-image ==")
    print("  sha256  ", sha(ab), sha(ab) == EXPECT_FINAL)
    print("  bytes   ", len(ab), "expected 6289")
    print("  lines   ", len(after.splitlines()), "expected 83")
    print("  crlf    ", ab.count(b"\r\n"), " bom", ab[:3] == b"\xef\xbb\xbf")

    bl = text.splitlines()
    al = after.splitlines()
    sm = difflib.SequenceMatcher(a=bl, b=al, autojunk=False)
    ins = dele = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            dele += i2 - i1
        if tag in ("replace", "insert"):
            ins += j2 - j1
    lcs = sum(bk.size for bk in sm.get_matching_blocks())
    print("\n== line shape ==")
    print("  added", ins, "deleted", dele, "expected 1/1")
    print("  canonical LCS length", lcs, "expected 82")

    print("\n== section confinement ==")
    # every changed line must live under the claimed section prefix
    idx_sec = [i for i, ln in enumerate(bl) if ln.startswith(SECTION)]
    print("  section header line(s) (0-indexed):", idx_sec)
    nxt = [i for i in range(idx_sec[0] + 1, len(bl)) if bl[i].startswith("## ")]
    end = nxt[0] if nxt else len(bl)
    print("  section spans lines", idx_sec[0] + 1, "..", end, "(1-indexed inclusive-ish)")
    changed = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed.extend(range(i1, i2))
    print("  changed base line numbers (1-indexed):", [i + 1 for i in changed])
    print("  all inside section:", all(idx_sec[0] < i < end for i in changed))
else:
    print("  ABORT: anchor not unique, cannot generate post-image")
