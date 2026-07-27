"""Derive the proposed final bytes of wake_codex.ps1 without writing it.

Deterministic: replaces exactly the $kick assignment block with the proposed
one, leaves every other byte untouched, and prints base/final sha256 so the
proposal can be byte-bound before execution.

--write applies it (only after co-sign).
"""

import argparse
import hashlib
from pathlib import Path

TARGET = Path(
    r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\wake_codex.ps1"
)

OLD = (
    '$kick = "Wake up for ONE bounded autonomous episode. First read the file " +\n'
    '        "\'proposals/bounded-scheduler-v0.1/impl/wake_prompt_codex.md\' " +\n'
    '        "(UTF-8, Chinese) and follow it EXACTLY as this episode\'s discipline. " +\n'
    '        "Operational note: the skill-evolution ledger is large; every " +\n'
)

NEW = (
    '$kick = "Wake up for ONE bounded autonomous episode. First read the file " +\n'
    '        "\'proposals/bounded-scheduler-v0.1/impl/wake_prompt_codex.md\' " +\n'
    '        "(UTF-8, Chinese) and follow it EXACTLY as this episode\'s discipline. " +\n'
    '        "Scope, stated here so you have it BEFORE any recall: this " +\n'
    '        "workspace has several ACTIVE scopes, and this episode\'s scope is " +\n'
    '        "skill-evolution. Every memory-recall you run MUST pass " +\n'
    '        "--scope skill-evolution. If an UNSCOPED recall returns " +\n'
    '        "CONFIRM_REQUIRED with reason multiple_or_ambiguous_scopes, that " +\n'
    '        "is an under-specified query, not an authority stop: re-run it " +\n'
    '        "scoped and obey THAT result. A non-ACTIVE or no-continuation " +\n'
    '        "result from the SCOPED recall still stops the episode -- write " +\n'
    '        "the blocked-by-activation receipt and exit, exactly as the " +\n'
    '        "prompt says. " +\n'
    '        "Operational note: the skill-evolution ledger is large; every " +\n'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    base = TARGET.read_bytes()
    text = base.decode("utf-8")
    if text.count(OLD) != 1:
        raise SystemExit(
            "base does not contain the expected kick block exactly once; "
            "signature is void"
        )
    final = text.replace(OLD, NEW).encode("utf-8")

    print("base_bytes ", len(base), hashlib.sha256(base).hexdigest())
    print("final_bytes", len(final), hashlib.sha256(final).hexdigest())
    non_ascii = [c for c in final.decode("utf-8") if ord(c) > 127]
    print("non_ascii_chars_in_final", len(non_ascii))
    print("crlf_in_final", final.count(b"\r\n"))

    if args.write:
        TARGET.write_bytes(final)
        print("WROTE", TARGET)


if __name__ == "__main__":
    raise SystemExit(main())
