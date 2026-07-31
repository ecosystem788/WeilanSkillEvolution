"""Independent review probe for the 2026-07-28T07:55:01+09:00 execution receipt.

Cosigned scope: wake_prompt_codex.md line 3 only, base sha256=71f8fe43...(7739 bytes)
-> claimed post sha256=ce419759...(7761 bytes).

This probe does NOT trust the receipt's numbers. It recomputes them, and — the load-bearing
part — reconstructs the base by inverting exactly the three claimed insertions on line 3.
If the reconstructed bytes hash to the signed base, then no other byte in the file moved.
Read-only; writes nothing.
"""

import hashlib
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
TARGET = HERE / "wake_prompt_codex.md"

SIGNED_BASE_SHA = "71f8fe4316036cde01e226fe2f0d4d07a298f8d51282f52d959a5ca556af6a49"
SIGNED_BASE_BYTES = 7739
CLAIMED_POST_SHA = "ce41975991c77c930cbf85fef7953b31860c7b7f297346e3613f9ef88613daec"
CLAIMED_POST_BYTES = 7761

# The three insertions the proposal locked, as literal string pairs (new -> old).
INVERSIONS = [
    ("元寂计划.md", "元寂计划"),
    (
        "元寂的进一步讨论.txt(不是 .md)",
        "元寂的进一步讨论",
    ),
    ("无我.md", "无我"),
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    raw = TARGET.read_bytes()
    post_sha = sha256(raw)
    print("target            :", TARGET)
    print("bytes on disk     :", len(raw), "(claimed", CLAIMED_POST_BYTES, ")")
    print("sha256 on disk    :", post_sha)
    print("post sha matches  :", post_sha == CLAIMED_POST_SHA)
    print("post size matches :", len(raw) == CLAIMED_POST_BYTES)
    print("CRLF count        :", raw.count(b"\r\n"))

    lines = raw.split(b"\n")
    line3 = lines[2]
    print("line 3            :", line3.decode("utf-8"))

    # Invert exactly the three signed insertions on line 3, leave every other byte alone.
    text3 = line3.decode("utf-8")
    for new, old in INVERSIONS:
        if text3.count(new) != 1:
            print("!! inversion token not uniquely present:", new, "count=", text3.count(new))
            return 1
        text3 = text3.replace(new, old)
    print("line 3 inverted   :", text3)

    rebuilt_lines = list(lines)
    rebuilt_lines[2] = text3.encode("utf-8")
    rebuilt = b"\n".join(rebuilt_lines)
    base_sha = sha256(rebuilt)
    print("rebuilt bytes     :", len(rebuilt), "(signed base", SIGNED_BASE_BYTES, ")")
    print("rebuilt sha256    :", base_sha)
    print("BASE MATCHES      :", base_sha == SIGNED_BASE_SHA)
    print("byte delta        :", len(raw) - len(rebuilt))

    ok = (
        post_sha == CLAIMED_POST_SHA
        and len(raw) == CLAIMED_POST_BYTES
        and base_sha == SIGNED_BASE_SHA
        and len(rebuilt) == SIGNED_BASE_BYTES
    )
    print("VERDICT           :", "all green" if ok else "RED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
