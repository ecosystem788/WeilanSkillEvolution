"""Pre-flight: does the drafted proposal text contain any private pattern?

Prints per-pattern counts by index only. It never prints a pattern and never
prints the drafted text.
"""
import importlib.util
import json
import sys

GATE = r"D:\WeilanSkillEvolution\proposals\scaffold-opensource-export-v0.1\scan_only_gate.py"
DRAFT = r"D:\WeilanSkillEvolution\proposals\redaction-gate-tree-subject-v0.1\_append_20260730_anchor_registration_proposal.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = load(GATE, "scan_only_gate_preflight")
patterns, ruleset_digest = gate.load_patterns(gate.DEFAULT_PRIVATE)

with open(DRAFT, encoding="utf-8") as handle:
    source = handle.read()

# The draft module runs an append on import, so read its TEXT literally instead.
start = source.index('TEXT = """') + len('TEXT = """')
end = source.index('"""', start)
text = source[start:end]

counts = {index: text.count(pattern) for index, pattern in enumerate(patterns)}
report = {
    "ruleset_digest": ruleset_digest,
    "pattern_count": len(patterns),
    "draft_chars": len(text),
    "per_pattern_count": counts,
    "total_hits": sum(counts.values()),
    "clean": sum(counts.values()) == 0,
}
json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
print()
