"""Derive the expected line-level shape from the SIGNED proposal text alone.

Reads only the OLD/NEW constants of _derive_proposed_final.py (whose sha256 was
pinned as a preflight invariant). Does NOT read the landed target file, so the
number it produces cannot have been fitted to the observed postcheck output.
"""
import hashlib, importlib.util, pathlib, sys

SRC = pathlib.Path(r"D:\WeilanSkillEvolution\proposals\codex-cold-start-scope-ambiguity-v0.1\_derive_proposed_final.py")
PINNED = "eaf01ae9bad1f296fa77dd9c5af24ff88f116ea49565c065e9b4466877cc5644"

got = hashlib.sha256(SRC.read_bytes()).hexdigest()
if got != PINNED:
    raise SystemExit(f"derivation source drifted: {got} != {PINNED}")

spec = importlib.util.spec_from_file_location("_d", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

old = mod.OLD.splitlines(keepends=True)
new = mod.NEW.splitlines(keepends=True)

# OLD must be a subsequence of NEW for the whole base file to be a subsequence
# of the final file; verify rather than assume.
it = iter(new)
subseq = all(any(n == o for n in it) for o in old)
if not subseq:
    raise SystemExit("OLD is not a subsequence of NEW; shape not derivable this way")

print("old_block_lines", len(old))
print("new_block_lines", len(new))
print("expect_added", len(new) - len(old))
print("expect_deleted", 0)
print("basis", "base file is a subsequence of final file => LCS == len(base)")
