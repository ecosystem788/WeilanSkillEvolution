"""Read-only mutation probe: does test_scan_only_gate.py pin all six canonical steps?

Criterion 8 of the double-signed v2 delegation demanded that changing any of
dedup / sort / separators / bool-normalisation turn a test red.  This probe
copies gate + test into a temp tree (the test derives GATE_PATH from
parents[2], so the copy self-binds), applies one mutation at a time, and runs
the suite.  A surviving mutant is an unpinned step.  Nothing in the workspace
is modified.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = r"D:\WeilanSkillEvolution"
GATE_REL = os.path.join("proposals", "scaffold-opensource-export-v0.1",
                        "scan_only_gate.py")
TEST_REL = os.path.join("proposals", "redaction-gate-tree-subject-v0.1",
                        "test_scan_only_gate.py")

MUTANTS = [
    ("drop_sort", '"\\n".join(sorted(rows))', '"\\n".join(list(rows))'),
    ("widen_separators", 'separators=(",", ":")', 'separators=(", ", ": ")'),
    ("flip_ensure_ascii", "ensure_ascii=False, separators=",
     "ensure_ascii=True, separators="),
    ("drop_dedup", "rows = set()", "rows = []"),
    ("drop_bool_normalisation", "if isinstance(value, bool):",
     "if False and isinstance(value, bool):"),
]


def build(tmp, name, old, new):
    root = os.path.join(tmp, name)
    for rel in (GATE_REL, TEST_REL):
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(REPO, rel), dst)
    gate = os.path.join(root, GATE_REL)
    with open(gate, encoding="utf-8") as fh:
        src = fh.read()
    count = src.count(old)
    if name == "drop_dedup":
        src = src.replace("rows.add(json.dumps(", "rows.append(json.dumps(")
    src = src.replace(old, new)
    with open(gate, "w", encoding="utf-8") as fh:
        fh.write(src)
    return root, count


def main():
    tmp = tempfile.mkdtemp(prefix="gate_mutation_")
    results = []
    # control: unmutated copy must be green
    for name, old, new in [("control", "rows = set()", "rows = set()")] + MUTANTS:
        root, count = build(tmp, name, old, new)
        proc = subprocess.run([sys.executable, os.path.join(root, TEST_REL)],
                              cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        err = proc.stderr.decode("utf-8", "replace")
        tail = [ln for ln in err.strip().splitlines() if ln.strip()][-1:]
        failed = [ln for ln in err.splitlines()
                  if ln.startswith("FAIL:") or ln.startswith("ERROR:")]
        results.append({
            "mutant": name,
            "target_occurrences_in_source": count,
            "rc": proc.returncode,
            "verdict": "GREEN(survived)" if proc.returncode == 0 else "RED(killed)",
            "summary": tail[0] if tail else "",
            "failing_tests": failed,
        })
    out = __file__.replace(".py", ".out.json")
    payload = {
        "meaning": ("control must be RED=false; a mutant with "
                    "verdict=GREEN(survived) is a canonical step the suite "
                    "does not pin"),
        "results": results,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(json.dumps(results, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
