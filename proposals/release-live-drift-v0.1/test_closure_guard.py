"""Read-only: the counterexample family the closure guard has to survive.

Each case is a *pair* of modules that differ only in a way the guard is supposed to
notice.  For every pair the tool must either report unknown, or report two different
hashes -- never an equal hash while `root()` actually returns different values.  That
is the whole invariant; the cases below are the shapes that have broken it, plus the
neighbours of those shapes.

The `not_closed` section is the attribute channel, which is a partial detector by
construction.  Its cases are here so the incompleteness is a running fact rather than
a sentence in a docstring: they print an equal hash beside two different return
values, every run.  One that starts being caught is good news; one that is silently
removed is not.

Run: python test_closure_guard.py       (exit 0 = every case as documented)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurement_closure import closure  # noqa: E402

BASE = 'def root():\n    return 1\n'

CASES = [
    # (name, source A, source B, must_be_caught)
    (
        "for_target_rebinds_root",
        BASE + 'for root in [lambda: 2]:\n    pass\n',
        BASE + 'for root in [lambda: 3]:\n    pass\n',
        True,
    ),
    (
        "with_target_rebinds_root",
        BASE + 'import contextlib\nwith contextlib.nullcontext(lambda: 2) as root:\n    pass\n',
        BASE + 'import contextlib\nwith contextlib.nullcontext(lambda: 3) as root:\n    pass\n',
        True,
    ),
    (
        "conditional_rebinds_root",
        BASE + 'if True:\n    root = lambda: 2\n',
        BASE + 'if True:\n    root = lambda: 3\n',
        True,
    ),
    (
        "augassign_mutates_reached_constant",
        'N = 1\ndef root():\n    return N\nN += 1\n',
        'N = 1\ndef root():\n    return N\nN += 2\n',
        True,
    ),
    (
        "subscript_store_mutates_container",
        'CONFIG = {"k": 1}\ndef root():\n    return CONFIG["k"]\nCONFIG["k"] = 2\n',
        'CONFIG = {"k": 1}\ndef root():\n    return CONFIG["k"]\nCONFIG["k"] = 3\n',
        True,
    ),
    (
        "bare_call_mutates_container",
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\nCONFIG.append(2)\n',
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\nCONFIG.append(3)\n',
        True,
    ),
    (
        "unreached_binder_runs_code_at_import",
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\nSIDE = CONFIG.append(2)\n',
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\nSIDE = CONFIG.append(3)\n',
        True,
    ),
    # Exercised as a script, not an import: under import the guard genuinely does not
    # run, so an import-mode fixture would show 1 vs 1 and prove nothing.  Script mode
    # is the case the exemption has to survive.
    (
        "main_guard_rebinding_a_root",
        BASE + 'if __name__ == "__main__":\n    root = lambda: 2\n    print(root())\n',
        BASE + 'if __name__ == "__main__":\n    root = lambda: 3\n    print(root())\n',
        True,
    ),
    # Codex's counterexample against the old exemption: the guard binds no module-level
    # name, so `main_guard_binding_nothing` called it inert and the hash was equal
    # (14839e4b) while the script printed 2 and 3.  It is caught on the script-mode
    # pair now, and specifically by the second number -- the first is still equal here,
    # correctly: the reached definitions really are textually identical.
    (
        "main_guard_mutates_what_a_root_reads",
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\n'
        'if __name__ == "__main__":\n    CONFIG.append(2)\n    print(root())\n',
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\n'
        'if __name__ == "__main__":\n    CONFIG.append(3)\n    print(root())\n',
        True,
    ),
    # The other direction of the same mistake: the guard reaches a helper it calls, and
    # the helper -- not the guard -- is what differs.  Nothing rebinds and nothing
    # mutates at the top level.
    (
        "main_guard_calls_a_helper_that_differs",
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\ndef prep():\n    CONFIG.append(2)\n'
        'if __name__ == "__main__":\n    prep()\n    print(root())\n',
        'CONFIG = [1]\ndef root():\n    return CONFIG[-1]\ndef prep():\n    CONFIG.append(3)\n'
        'if __name__ == "__main__":\n    prep()\n    print(root())\n',
        True,
    ),
    (
        "reflection_via_sys_modules",   # attribute channel: caught, but by a detector
        'import sys\ndef hidden():\n    return 2\ndef root():\n'
        '    return getattr(sys.modules[__name__], "hidden")()\n',
        'import sys\ndef hidden():\n    return 3\ndef root():\n'
        '    return getattr(sys.modules[__name__], "hidden")()\n',
        True,
    ),
]

# Pairs that must NOT be flagged: prose and unrelated edits must leave the hash alone,
# or the tool over-cuts and stops being usable.  Equal hash is the requirement here.
# The axis says which number is being held stable, and the distinction is the point of
# having two: `main_body_changes` asserts the *measurement* hash is unmoved by an edit
# to the caller -- its script_entry hash does move, which is correct, because the
# caller did change.  `prose_edit_under_a_guard` asserts the pair, so the second number
# is held to the same no-over-cutting standard as the first.
STABLE = [
    ("docstring_edit", BASE + 'X = 1\n',
     'def root():\n    "prose"\n    return 1\nX = 1\n', "closure"),
    ("unrelated_literal_constant_changes", BASE + 'UNUSED = [1, 2]\n',
     BASE + 'UNUSED = [1, 2, 3]\n', "closure"),
    ("unrelated_import_added", BASE, 'import json\n' + BASE, "closure"),
    ("main_body_changes_measurement_does_not",
     BASE + 'def main():\n    return 0\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
     BASE + 'def main():\n    return 1\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
     "closure"),
    ("prose_edit_under_a_guard",
     BASE + 'def main():\n    return 0\nif __name__ == "__main__":\n    raise SystemExit(main())\n',
     'def root():\n    "prose"\n    return 1\ndef main():\n    "more prose"\n    return 0\n'
     'if __name__ == "__main__":\n    raise SystemExit(main())\n',
     "pair"),
]

# Cases the guard is documented NOT to close, and must not be quietly deleted.
#
# The first draft of this section used `vars()["hidden"]()`, which the tool does catch
# -- `vars` is not on the free-name allow-list.  It proved nothing about the attribute
# channel and was replaced.  The case below reaches a definition through an imported
# module's attribute that is not on the partial reflection list, so every guard passes
# and the hash is equal while root() returns 2 in one revision and 3 in the other.
# This is the gap the docstring claims exists; here it is, running.
NOT_CLOSED = [
    (
        "reflection_via_an_unlisted_module_attribute",
        'import inspect\ndef hidden():\n    return 2\n'
        'def root():\n    return inspect.currentframe().f_globals["hidden"]()\n',
        'import inspect\ndef hidden():\n    return 3\n'
        'def root():\n    return inspect.currentframe().f_globals["hidden"]()\n',
    ),
]


def _run(source: str) -> object:
    """What root() actually returns: by import, or by script if there is a guard.

    A `__main__` guard is dead code under import, so a source containing one is run as
    a script and its own printed value is read back.  Returns None when the module
    will not run at all.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case_module.py"
        path.write_text(source, encoding="utf-8")
        if '__main__' in source:
            done = subprocess.run([sys.executable, str(path)],
                                  capture_output=True, text=True)
            return done.stdout.strip() or None
        spec = importlib.util.spec_from_file_location("case_module", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["case_module"] = module
        try:
            spec.loader.exec_module(module)
            return module.root()
        except Exception:
            return None
        finally:
            sys.modules.pop("case_module", None)


def _key(report: dict, axis: str = "auto") -> tuple:
    """The hashes a comparison actually rests on, on the axis the fixture runs.

    `_run` executes a source with a `__main__` guard as a script, so for those the
    honest comparison is the pair: the measurement hash plus the caller's.  Comparing
    only the first would let a caller that mutates a root's state pass, which is
    exactly the counterexample this file now carries.  Sources without a guard have no
    second number and compare on the first alone.
    """
    entry = report.get("script_entry_sha256")
    if axis == "closure" or entry is None:
        return (report["closure_sha256"],)
    return (report["closure_sha256"], entry)


def _show(key: tuple) -> str:
    return "+".join(k[:8] for k in key)


def main() -> int:
    failures = []

    for name, src_a, src_b, must_catch in CASES:
        ka = _key(closure(src_a, ["root"]))
        kb = _key(closure(src_b, ["root"]))
        va, vb = _run(src_a), _run(src_b)
        caught = "unknown" in ka or "unknown" in kb or ka != kb
        behaviour_differs = va != vb
        status = "caught" if caught else "MISSED"
        print(f"{status:8} {name:42} root(): {va} vs {vb}  hash: "
              f"{_show(ka)} vs {_show(kb)}")
        if must_catch and behaviour_differs and not caught:
            failures.append(f"{name}: equal hash while root() returned {va} then {vb}")
        if must_catch and not behaviour_differs:
            failures.append(f"{name}: fixture is broken, both revisions return {va}")

    for name, src_a, src_b, axis in STABLE:
        ka = _key(closure(src_a, ["root"]), axis)
        kb = _key(closure(src_b, ["root"]), axis)
        stable = ka == kb and "unknown" not in ka
        print(f"{'stable' if stable else 'OVERCUT':8} {name:42} [{axis}] hash: "
              f"{_show(ka)} vs {_show(kb)}")
        if not stable:
            failures.append(f"{name}: expected one equal, known hash, got {ka} / {kb}")

    for name, src_a, src_b in NOT_CLOSED:
        ka = _key(closure(src_a, ["root"]))
        kb = _key(closure(src_b, ["root"]))
        va, vb = _run(src_a), _run(src_b)
        caught = "unknown" in ka or ka != kb
        print(f"{'closed!' if caught else 'open':8} {name:42} root(): {va} vs {vb}  "
              f"hash: {_show(ka)} vs {_show(kb)}   (documented as not closed)")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  " + f)
        return 1
    print("\nall cases as documented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
