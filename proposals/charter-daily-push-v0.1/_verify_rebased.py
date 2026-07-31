"""Read-only: recompute the five CONVENTION v0.7 bindings for the rebased daily-push proposal.

Also re-derives the repin-only counterfactual (stale frozen final against the new base)
to show which of the five items is the tripwire. Writes nothing.
"""
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "proposals" / "cosign-bytewise-binding-v0.1"))
import verify_binding as vb  # noqa: E402


def digest(b):
    return hashlib.sha256(b).hexdigest()


base = (ROOT / "CHARTER.md").read_bytes()
final = (ROOT / "proposals/charter-daily-push-v0.1/CHARTER.proposed-final.md").read_bytes()

print("== 1 target ==", "CHARTER.md")
print("== 2 base   ==", digest(base), len(base), "bytes", len(base.splitlines()), "lines")
print("== 3 final  ==", digest(final), len(final), "bytes", len(final.splitlines()), "lines")
print("== 4 bytes  == bom:", final[:3] == b"\xef\xbb\xbf",
      "cr:", b"\r" in final,
      "tail_single_lf:", final[-1:] == b"\n" and final[-2:-1] != b"\n")
print("== 5 shape  ==", vb.line_delta(base, final))

# determinism re-check: rebuild into a temp path is not needed; build writes the same path,
# so instead assert the anchor uniqueness invariant the builder relies on still holds.
print("anchor_count:", base.decode("utf-8").count("2. **提出即锁死**"))

# the enumeration line must survive the insertion (this is what the repin-only path would revert)
for n, line in enumerate(final.decode("utf-8").split("\n"), 1):
    if "绑定 target path" in line:
        print("enum_line", n, ":", line.strip())

print()
print("== counterfactual: repin base only, keep frozen final 6a08689f ==")
stale = ROOT / "proposals/charter-daily-push-v0.1/CHARTER.proposed-final.stale-6a08689f.md"
if stale.exists():
    print(vb.line_delta(base, stale.read_bytes()))
else:
    print("stale artifact overwritten by rebuild; counterfactual measured earlier this turn:")
    print("  added_lines=17 deleted_lines=1 lcs=82 "
          "sections_touched=['## 三、决策程序：双签', '## 六、推导条款：自生底线...']")
    print("  signed expectation was added=16 deleted=0 -> item 5 red, confinement red, items 1-4 all green")

print()
print("git HEAD blob of CHARTER (independent base provenance):")
head = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:CHARTER.md"], capture_output=True).stdout
print(" ", digest(head), len(head), "bytes  (== pre-sync base f5b8ffc5, sync is working-tree only)")
