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

The `overcut` section is the mirror of that, and exists for the same reason.  These
are pairs the guard refuses although nothing about them differs -- the cost of the
refusal, printed beside the cases that justify it, so a relaxation is argued against
running counterexamples rather than against a recollection of them.  Same reading
rule: one that starts being accepted is good news, one that is silently removed is
not.  It is held to one rule the not-closed section is not: a cost is only kept while
the relaxations that would remove it are still killed by cases still running here.
An incompleteness we cannot fix is a fact; a refusal we chose is a decision, and a
decision has to keep paying for itself.  That rule is enforced by the only check here
whose subject is this file rather than the tool, so it is itself checked, on invented
facts, every run -- see AUDIT_SELFTEST.

Run: python test_closure_guard.py       (exit 0 = every case as documented)
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurement_closure import REFLECTIVE_ATTRIBUTE_NAMES, closure  # noqa: E402

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
    # `from __future__ import annotations` turns an annotation into a string, which is
    # the reason it looks exempt-able: nothing evaluates it at def time.  But a string
    # in `__annotations__` is not dead -- typing.get_type_hints() evaluates it in this
    # module's globals on demand, and hands back whatever it names.  Here `hidden` is
    # named nowhere but in the annotation, and root() returns 2 then 3.  Caught by
    # reachability: the walk reads names inside annotations, so `hidden` is reached and
    # hashed.  A relaxation that stopped walking annotations would print an equal hash
    # on this pair.
    (
        "annotation_reaches_a_helper_under_postponed_annotations",
        'from __future__ import annotations\nimport typing\ndef hidden():\n    return 2\n'
        'def root(x: hidden = None) -> int:\n'
        '    return typing.get_type_hints(root)["x"]()\n',
        'from __future__ import annotations\nimport typing\ndef hidden():\n    return 3\n'
        'def root(x: hidden = None) -> int:\n'
        '    return typing.get_type_hints(root)["x"]()\n',
        True,
    ),
    # The narrower relaxation -- keep walking annotations, but stop *refusing* the free
    # names in them that resolve to nothing at module level -- fails too, and this is
    # the pair that decides it.  `getattr` is such a name: unbound here, and refused
    # today only because the name channel does not exempt annotations.  Evaluated back
    # out of the annotation string it is the builtin, and the builtin reaches `hidden`
    # through root.__globals__ without ever naming it.  Note `hidden` is absent from
    # reached_names on both revisions: only the refusal is holding this, so relaxing it
    # yields an equal, *known* hash while root() returns 2 then 3.  Measured rather than
    # argued: re-adding "getattr" to ALLOWED_FREE_NAMES -- which for this pair does
    # exactly what exempting annotation names would do, the name occurring nowhere else
    # -- gives both revisions fa72727f2d483787, known and equal.
    (
        "annotation_smuggles_a_builtin_under_postponed_annotations",
        'from __future__ import annotations\nimport typing\ndef hidden():\n    return 2\n'
        'def root(x: getattr = None) -> int:\n'
        '    g = typing.get_type_hints(root)["x"]\n'
        '    return g(root, "__globals__")["hidden"]()\n',
        'from __future__ import annotations\nimport typing\ndef hidden():\n    return 3\n'
        'def root(x: getattr = None) -> int:\n'
        '    g = typing.get_type_hints(root)["x"]\n'
        '    return g(root, "__globals__")["hidden"]()\n',
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
    # The three below are the same listed channel written under a different name.  Each
    # was measured evading it before the matcher resolved imports: equal and *known*
    # hash, root() returning 2 and 3.  The one above does not cover them -- it is also
    # caught by `getattr` on the bare-name channel, so it would keep passing with the
    # attribute channel switched off entirely.  These do not name getattr.
    (
        "reflection_via_sys_modules_under_an_import_alias",   # import X as y
        'import sys as s\ndef hidden():\n    return 2\ndef root():\n'
        '    return s.modules[__name__].hidden()\n',
        'import sys as s\ndef hidden():\n    return 3\ndef root():\n'
        '    return s.modules[__name__].hidden()\n',
        True,
    ),
    (
        "reflection_via_a_from_imported_module_member",   # from X import member
        'from sys import modules\ndef hidden():\n    return 2\ndef root():\n'
        '    return modules[__name__].hidden()\n',
        'from sys import modules\ndef hidden():\n    return 3\ndef root():\n'
        '    return modules[__name__].hidden()\n',
        True,
    ),
    (
        # No attribute access anywhere: the reflective thing is a bare call.  A matcher
        # that only walks ast.Attribute cannot see this shape at all.
        "reflection_via_a_from_imported_reflective_helper",
        'from importlib import import_module\ndef hidden():\n    return 2\ndef root():\n'
        '    return import_module(__name__).hidden()\n',
        'from importlib import import_module\ndef hidden():\n    return 3\ndef root():\n'
        '    return import_module(__name__).hidden()\n',
        True,
    ),
    (
        # Not a fourth spelling of the same fix: the alias is bound inside the function,
        # so a module-level-only import map does not have it.  Measured evading after
        # the first three were caught, which is why the map is also read per statement.
        "reflection_via_an_alias_imported_inside_the_function",
        'def hidden():\n    return 2\ndef root():\n'
        '    import sys as s\n    return s.modules[__name__].hidden()\n',
        'def hidden():\n    return 3\ndef root():\n'
        '    import sys as s\n    return s.modules[__name__].hidden()\n',
        True,
    ),
    # The four below are the other axis of the attribute channel: a function/frame-
    # convention attribute name matched with no test on the base.  Ordinary objects can
    # define the same spelling, so the unqualified match is a paid overcut rather than
    # a fact about Python.  All four ran as equal-known misses before it existed, and
    # the first two were NOT_CLOSED cases.
    (
        "reflection_via_function_globals",
        'def hidden():\n    return 2\ndef root():\n    return root.__globals__["hidden"]()\n',
        'def hidden():\n    return 3\ndef root():\n    return root.__globals__["hidden"]()\n',
        True,
    ),
    (
        # The base is a *call*, so no matcher keyed on the base name can see this --
        # `inspect` is not on the module list under `currentframe`, and it does not
        # need to be.
        "reflection_via_frame_globals",
        'import inspect\ndef hidden():\n    return 2\n'
        'def root():\n    return inspect.currentframe().f_globals["hidden"]()\n',
        'import inspect\ndef hidden():\n    return 3\n'
        'def root():\n    return inspect.currentframe().f_globals["hidden"]()\n',
        True,
    ),
    (
        # Not a second spelling of the one above: `sys` *is* on the module list, under
        # `modules` only.  This was measured escaping at 79d1825c and is the pair that
        # says a listed module does not make its other members listed.
        "reflection_via_an_unlisted_member_of_a_listed_module",
        'import sys\ndef hidden():\n    return 2\n'
        'def root():\n    return sys._getframe().f_globals["hidden"]()\n',
        'import sys\ndef hidden():\n    return 3\n'
        'def root():\n    return sys._getframe().f_globals["hidden"]()\n',
        True,
    ),
    (
        # The kill for qualifying the name match by the base's provenance -- the obvious
        # narrowing, since `root.__globals__` above has a base bound at module level by
        # a def.  Here the base is a local lambda bound nowhere at module level, and the
        # namespace comes back all the same.  Measured escaping at e722a126; a
        # module-level assignment alias (8d7768d6) and a parameter (434dd25c) do it too,
        # and are not carried as separate samples of the one relaxation.
        "function_globals_off_a_base_with_no_module_binding",
        'def hidden():\n    return 2\n'
        'def root():\n    f = lambda: 1\n    return f.__globals__["hidden"]()\n',
        'def hidden():\n    return 3\n'
        'def root():\n    f = lambda: 1\n    return f.__globals__["hidden"]()\n',
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
    # The kill for putting `__dict__` on REFLECTIVE_ATTRIBUTE_NAMES beside `__globals__`
    # and `f_globals`.  Same attribute-read-then-subscript shape as those, and the same
    # absence of any static handle on what the base is -- but ordinary objects carry
    # `__dict__`, so the name is not evidence and refusing it costs this known, stable
    # pair.
    #
    # The asymmetry that keeps one name off the list and the other two on it is not
    # shared-versus-unshared: the OVERCUT sample below is an ordinary object carrying
    # `__globals__`, so both spellings are shareable and the earlier wording here was the
    # same refuted claim.  What separates them is the shape of the cost each one charges,
    # and both shapes are running a few lines apart: the source below carries `__dict__`
    # without ever naming it, because every object has one, while the cost sample for
    # `__globals__` has to write `__globals__ = {...}` into a class body to carry it at
    # all.  A name is admissible when an ordinary object must *declare* it; `__dict__`
    # comes free with the object and so can never be that.  Note what is still only
    # judged: that the declared shape is the rarer one in code people write.  Nothing
    # here measures that, and it is the third time a sentence has stood in for a cost on
    # this axis, so it is written as an admission rather than as a rule.
    ("ordinary_object_dunder_dict_is_not_module_reflection",
     'def root():\n    class Box:\n        pass\n    obj = Box()\n'
     '    obj.__dict__["value"] = 1\n    return obj.__dict__["value"]\nUNUSED = [1]\n',
     'def root():\n    class Box:\n        pass\n    obj = Box()\n'
     '    obj.__dict__["value"] = 1\n    return obj.__dict__["value"]\nUNUSED = [1, 2]\n',
     "closure"),
]

# Cases the guard is documented NOT to close, and must not be quietly deleted.
#
# The four-cell discriminator that used to be described here has been run and spent, so
# it is recorded rather than restated: `root.__globals__` and `frame.f_globals` moved
# into CASES, the ordinary-object `obj.__dict__` cell stayed STABLE, and the import
# shadowing cell stayed OVERCUT.  What the grid was expected to show -- that the
# reflected object's identity was the discriminating axis -- is not what it showed.
# Provenance turned out to be the leaky half: the module namespace comes back off a def,
# an assignment alias, a local lambda and a parameter alike.  The half that held is the
# attribute name, and only for names ordinary objects do not carry, which is why
# `__dict__` is on the other side of the line and staying there.
#
# What remains open here is one gap, and it is narrower and less comfortable than the
# ones that closed.  It reaches a *listed* module under a name assigned rather than
# imported.  Closing it means following assignments, which is dataflow and a different
# tool; it stays running so nobody can mistake import alias resolution for
# spelling-proof resolution.
NOT_CLOSED = [
    (
        "reflection_via_a_listed_module_aliased_by_assignment",
        'import sys\ns = sys\ndef hidden():\n    return 2\n'
        'def root():\n    return s.modules[__name__].hidden()\n',
        'import sys\ns = sys\ndef hidden():\n    return 3\n'
        'def root():\n    return s.modules[__name__].hidden()\n',
    ),
]


# What the guard costs: pairs it refuses although the two revisions are the same
# program.  These are not failures and not aspirations -- they are the price of the
# `annotation_*` cases above, kept running so the trade is re-read rather than
# remembered.
#
# The shape below is ordinary modern typed code: a forward reference, or a name
# imported only under `if TYPE_CHECKING`, in the annotation of a reached definition.
# Under `from __future__ import annotations` it is never evaluated at def time and the
# module runs; the walk still sees the bare name, cannot resolve it, and refuses -- so
# an unrelated literal edit that should have compared as equal compares as unknown.
#
# It was tempting to exempt annotations for exactly this case, and the two
# `annotation_*` counterexamples are why the exemption is not taken: the first kills
# "stop walking annotations", the second kills "walk them but stop refusing their
# unresolved names".  Both were run before the decision, not after.  The escape stays
# on the reader's side -- an unknown names the refused word, so a reader who knows the
# annotation is inert can say so -- because that is a claim a reader can check, and an
# exemption is one nobody could.
#
# The second shape is the other half of the import-resolution fix, found by Codex's
# probe on the commit that landed it.  The import map is read per module and per
# statement, never per scope, so a parameter or local reusing an imported name resolves
# to the module: `def root(s)` after `import sys as s` is reported `s.modules
# (sys.modules)` and the region is refused although no reflection is there.  It is filed
# here and not in NOT_CLOSED on purpose, and the difference is not a label -- NOT_CLOSED
# prints and asserts nothing, so a cost parked there would be a cost nobody is charged
# for, which is exactly how a debt gets read as a limit later.  Here it is charged, and
# the policy below has to keep proving the refusal is still load-bearing.
#
# The third shape was found the same way one commit later, and the pattern in that is
# worth more than either sample: both times a rule was landed with a sentence standing in
# for the cost, and both times the sentence was the part that was wrong.  A refusal
# justified in prose reads as free until someone writes the program it refuses.
OVERCUT = [
    (
        "forward_reference_under_postponed_annotations",
        'from __future__ import annotations\n'
        'def root(x: Widget = None) -> Widget:\n    return 1\nUNUSED = [1]\n',
        'from __future__ import annotations\n'
        'def root(x: Widget = None) -> Widget:\n    return 1\nUNUSED = [1, 2]\n',
        "annotation_names_are_refused_like_any_other",
    ),
    (
        "imported_name_shadowed_by_a_local",
        'import sys as s\nclass Box:\n    modules = 1\n'
        'def root():\n    s = Box()\n    return s.modules\nUNUSED = [1]\n',
        'import sys as s\nclass Box:\n    modules = 1\n'
        'def root():\n    s = Box()\n    return s.modules\nUNUSED = [1, 2]\n',
        "import_resolution_is_not_scoped",
    ),
    (
        # The third shape, and the one that says the second attribute axis is a bet
        # rather than a fact.  `REFLECTIVE_ATTRIBUTE_NAMES` landed at 39164b2 calling
        # its members names *no ordinary object carries*; Codex's probe wrote an
        # ordinary object that carries one.  Both revisions are the same program and
        # root() returns 1 either way, and both are refused.  The `__dict__` STABLE
        # cell above does not cover this: it only kills adding a name that comes free
        # with every object, and prices nothing about refusing a declared one
        # unconditionally.
        "ordinary_object_declaring_a_convention_reflective_name",
        'def root():\n    class Box:\n        __globals__ = {"value": 1}\n'
        '    return Box().__globals__["value"]\nUNUSED = [1]\n',
        'def root():\n    class Box:\n        __globals__ = {"value": 1}\n'
        '    return Box().__globals__["value"]\nUNUSED = [1, 2]\n',
        "convention_reflective_names_are_refused_unqualified",
    ),
    (
        # The same cost for the other spelling, and it is a separate sample because the
        # match is per spelling.  `REFLECTIVE_ATTRIBUTE_NAMES` is tested with `sub.attr
        # in ...`, so admitting `f_globals` refuses every read of that word on its own
        # account; the sample above prices `__globals__` and pays nothing toward this.
        # Codex's per-name probe on a346769 found the gap -- the membership rule said
        # every admitted name owes a cost run, and one of the two names had never had
        # one.  A rule owed per name and paid per policy is a rule that stops being
        # checked the moment a second name joins the first.
        "ordinary_object_declaring_the_frame_convention_name",
        'def root():\n    class Box:\n        f_globals = {"value": 1}\n'
        '    return Box().f_globals["value"]\nUNUSED = [1]\n',
        'def root():\n    class Box:\n        f_globals = {"value": 1}\n'
        '    return Box().f_globals["value"]\nUNUSED = [1, 2]\n',
        "convention_reflective_names_are_refused_unqualified",
    ),
]

# The rule the section above is held to: a retained cost is a *policy*, and a policy
# stays only while every relaxation that would drop it is still killed by a case still
# running in CASES.  Per category, not per sample -- a policy may cost several shapes
# and does not owe each of them its own kill; what it owes is that the refusal is still
# load-bearing.  Without this, "printed, not judged" lets the cost set grow forever on
# counterexamples nobody re-runs.
#
# The check is mechanical and deliberately shallow: the named kill must be present in
# CASES, must still return different values across its two revisions, and must still be
# caught.  It does not read the sources and does not try to decide whether a
# counterexample "really" kills the relaxation named beside it -- that judgement is the
# reviewer's, recorded here as a name they can check.  A script guessing it would be
# wrong quietly, which is worse than a mapping that is wrong out loud.
OVERCUT_POLICIES = {
    # policy -> {relaxation it refuses: the case in CASES that kills that relaxation}
    "annotation_names_are_refused_like_any_other": {
        "stop walking annotations":
            "annotation_reaches_a_helper_under_postponed_annotations",
        "walk annotations but stop refusing their unresolved names":
            "annotation_smuggles_a_builtin_under_postponed_annotations",
    },
    # One relaxation, and it is the obvious one: a reader meeting the cost above will
    # reach for `_locally_bound` immediately.  The kill is that an alias imported inside
    # the function is locally bound *by that import*, so the repair that clears the
    # shadowed parameter also clears the case where the base really is sys.  Run before
    # the entry was written: under the relaxation that case returns a known, equal hash
    # while root() returns 2 then 3.
    "import_resolution_is_not_scoped": {
        "skip the import resolution when the base name is locally bound":
            "reflection_via_an_alias_imported_inside_the_function",
    },
    # Two relaxations, because a reader meeting this cost has two exits and they are not
    # the same repair.  The first narrows the rule; the second deletes it.  Both would
    # drop the cost, so the policy owes a kill to each.
    "convention_reflective_names_are_refused_unqualified": {
        # The narrowing: clear the match when the base is not function- or frame-shaped
        # -- here a call to a class defined two lines up.  Whatever static test stands in
        # for "function-shaped", a local lambda bound to a local name is on the same side
        # of it as `Box()` is, and the namespace comes back regardless.  This is the same
        # kill that already refutes provenance-keyed narrowing, cited twice because the
        # relaxations differ even though the counterexample does not.
        "qualify the name match by what the base looks like":
            "function_globals_off_a_base_with_no_module_binding",
        # The deletion: drop the name axis and let the module list carry the attribute
        # channel alone, which is what the file did before 39164b2.  The base here is a
        # *call*, so no base-resolving matcher can see it however long the list gets.
        "drop the name axis and leave the module list to cover it":
            "reflection_via_frame_globals",
    },
}


def _audit_overcut_policies(case_results, charged, policies) -> list:
    """The audit as a function of the facts alone, so it can be run on made-up facts.

    `case_results` maps a case name to (caught, behaviour_differs); `charged` is the
    (cost sample, policy) pairs OVERCUT declares; `policies` is the mapping above.
    Returns one finding per thing checked, as
    (verdict, policy, relaxation, kill, failure), where `failure` is None exactly when
    the verdict is "kills".  Nothing here reads a source or runs a module: the caller
    collects the facts, this decides what they mean.
    """
    findings = []
    charged_policies = {policy for _, policy in charged}

    for sample, policy in charged:
        if policy not in policies:
            findings.append(("STRAY", policy, None, None,
                             f"{sample}: cost charged to {policy!r}, which is not a "
                             f"policy in OVERCUT_POLICIES"))

    for policy, relaxations in policies.items():
        if policy not in charged_policies:
            findings.append(("UNPAID", policy, None, None,
                             f"{policy}: retained with no cost sample in OVERCUT -- "
                             f"either the cost is no longer paid, or a sample was dropped"))
        if not relaxations:
            findings.append(("VACUOUS", policy, None, None,
                             f"{policy}: retained without naming a single relaxation it "
                             f"refuses, so nothing can be checked against it"))
        for relaxation, kill in sorted(relaxations.items()):
            result = case_results.get(kill)
            if result is None:
                findings.append(("MISSING", policy, relaxation, kill,
                                 f"{policy}: kill case {kill!r} for {relaxation!r} is not "
                                 f"in the running fixture"))
            elif not result[1]:
                findings.append(("SAME", policy, relaxation, kill,
                                 f"{policy}: kill case {kill!r} for {relaxation!r} no "
                                 f"longer behaves differently, so it kills nothing"))
            elif not result[0]:
                findings.append(("UNCAUGHT", policy, relaxation, kill,
                                 f"{policy}: kill case {kill!r} for {relaxation!r} is no "
                                 f"longer caught, so the relaxation is no longer refuted"))
            else:
                findings.append(("kills", policy, relaxation, kill, None))

    return findings


# The audit is the only check in this file whose subject is the file itself, and it fails
# open: a bug in it keeps printing `kills` beside a policy nothing kills any more, and
# nothing else in the run would object.  So it is checked on facts that are made up
# rather than measured -- the one place here where a fixture is allowed to be fiction,
# because the thing under test consumes facts and does not produce them.
#
# The expected column is written out by hand, not derived: a table that computed what to
# expect would be the audit again, and would agree with any bug that was in both.  This
# replaces a throwaway driver that produced six mutant *copies of the file* by string
# substitution -- it proved the same six branches once and then stopped existing, and it
# would have gone stale silently the first time a line it patched was reworded.
_HOLDS = {"kill_one": (True, True), "kill_two": (True, True)}   # (caught, differs)
_TWO_RELAXATIONS = {"a_policy": {"r1_relaxation": "kill_one",
                                 "r2_relaxation": "kill_two"}}
_ONE_COST = [("a_cost_sample", "a_policy")]

AUDIT_SELFTEST = [
    # (name, case_results, charged, policies, expected verdicts in order)
    ("baseline_every_kill_still_kills",
     _HOLDS, _ONE_COST, _TWO_RELAXATIONS, ("kills", "kills")),
    ("kill_renamed_out_of_the_fixture",
     {"kill_two": (True, True)}, _ONE_COST, _TWO_RELAXATIONS, ("MISSING", "kills")),
    ("kill_no_longer_behaves_differently",
     {"kill_one": (True, False), "kill_two": (True, True)},
     _ONE_COST, _TWO_RELAXATIONS, ("SAME", "kills")),
    # The branch that earns the section: a kill that stops being caught while sitting in
    # CASES with must_catch=False is invisible to the CASES loop, and this is the only
    # thing that objects.
    ("kill_still_present_but_no_longer_caught",
     {"kill_one": (False, True), "kill_two": (True, True)},
     _ONE_COST, _TWO_RELAXATIONS, ("UNCAUGHT", "kills")),
    ("policy_with_no_cost_sample_left",
     _HOLDS, [], _TWO_RELAXATIONS, ("UNPAID", "kills", "kills")),
    ("cost_charged_to_an_undeclared_policy",
     _HOLDS, [("a_cost_sample", "a_policy_nobody_declared")], _TWO_RELAXATIONS,
     ("STRAY", "UNPAID", "kills", "kills")),
    ("policy_that_refuses_nothing",
     _HOLDS, _ONE_COST, {"a_policy": {}}, ("VACUOUS",)),
]


def _declared_attribute_names(source: str) -> set[str]:
    """Attribute names an ordinary object in this source is made to *carry*.

    Bindings only, never reads, and that distinction is the whole load: the cost sample
    for `__globals__` also contains `Box().__globals__["value"]`, so a check that
    accepted a mention would pass on a sample that prices nothing -- the exact failure
    the per-name audit exists to catch.  What counts is a name bound in a class body
    (assignment, annotated assignment with a value, or a def), an assignment to
    `something.name`, and `setattr(x, "name", ...)` spelled with a literal.  A module- or
    function-level variable that happens to be called `f_globals` is not an attribute of
    anything and does not count.

    Undercounts deliberately: a name reached through a computed string is invisible here,
    and should be.  The audit's demand is that a sample *show* the declaration, and a
    sample that hides the spelling in a variable shows a reader nothing either.  Purely
    syntactic -- it does not run the source and cannot tell whether the class is ever
    instantiated; the OVERCUT loop's own `root()` comparison is what checks that.
    """
    declared: set[str] = set()

    def bound_targets(stmt) -> list:
        if isinstance(stmt, ast.Assign):
            return list(stmt.targets)
        if isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            return [stmt.target] if stmt.value is not None else []
        return []

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                declared |= {t.id for t in bound_targets(stmt) if isinstance(t, ast.Name)}
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    declared.add(stmt.name)
        declared |= {t.attr for t in bound_targets(node) if isinstance(t, ast.Attribute)}
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "setattr" and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)):
            declared.add(node.args[1].value)

    return declared


def _audit_reflective_name_costs(names, charged) -> list:
    """The membership rule for REFLECTIVE_ATTRIBUTE_NAMES, run instead of read.

    That rule says a name is admitted on two runs, not one: the escape it closes and the
    ordinary same-named attribute it will now refuse.  The second half was prose until
    here, and prose is what it had already been wrong as, twice on this axis.

    Per name, because the match is per spelling.  `names` is the set as the tool holds
    it; `charged` is (sample name, the attribute names that sample's source declares)
    for every OVERCUT entry.  Returns one finding per name as
    (verdict, name, samples, failure), `failure` None exactly on "priced".  Reads no
    sources and runs nothing: the caller supplies the facts, this decides what they mean.
    """
    findings = []
    for name in sorted(names):
        samples = sorted(sample for sample, declared in charged if name in declared)
        if samples:
            findings.append(("priced", name, samples, None))
        else:
            findings.append(("UNPRICED", name, [],
                             f"{name}: admitted to REFLECTIVE_ATTRIBUTE_NAMES with no "
                             f"OVERCUT sample declaring it -- this spelling is refused "
                             f"on its own account and has never been paid for"))
    return findings


# Both halves above fail open the same way the policy audit does -- a scanner that
# quietly stopped seeing class bodies would print `priced` beside a name nothing prices
# -- so both are checked on facts nobody measured, every run.  Expected columns written
# by hand: a table that derived them would be the same code agreeing with its own bug.
_DECLARATION_SELFTEST = [
    # (name, source, every attribute name the scanner should report)
    ("class_body_assignment", 'class Box:\n    f_globals = {}\n', {"f_globals"}),
    ("class_body_annotated_assignment",
     'class Box:\n    f_globals: dict = {}\n', {"f_globals"}),
    ("class_body_annotation_with_no_value", 'class Box:\n    f_globals: dict\n', set()),
    ("class_body_def",
     'class Box:\n    def f_globals(self):\n        return {}\n', {"f_globals"}),
    ("instance_attribute_assignment", 'def f(obj):\n    obj.f_globals = {}\n', {"f_globals"}),
    ("setattr_with_a_literal_name",
     'def f(obj):\n    setattr(obj, "f_globals", {})\n', {"f_globals"}),
    ("setattr_with_a_computed_name", 'def f(obj, k):\n    setattr(obj, k, {})\n', set()),
    # The three that earn the scanner.  Each is a way a sample could look like it prices
    # a spelling while declaring nothing an object carries.
    ("only_a_read_of_the_name", 'def f(x):\n    return x.f_globals["v"]\n', set()),
    ("module_level_variable_of_that_name", 'f_globals = {}\n', set()),
    ("local_variable_of_that_name",
     'def f():\n    f_globals = {}\n    return f_globals\n', set()),
]

_AUDIT_NAME_SELFTEST = [
    # (name, names on the list, (sample, names it declares), expected verdicts in order)
    ("every_name_has_a_sample_declaring_it",
     {"a_name", "b_name"}, [("s_a", {"a_name"}), ("s_b", {"b_name"})],
     ("priced", "priced")),
    # The branch this check was written for: one spelling paying for two.
    ("one_name_riding_on_its_neighbours_sample",
     {"a_name", "b_name"}, [("s_a", {"a_name"})], ("priced", "UNPRICED")),
    ("a_sample_that_declares_nothing",
     {"a_name"}, [("s_a", set())], ("UNPRICED",)),
    ("no_samples_at_all", {"a_name"}, [], ("UNPRICED",)),
    ("nothing_on_the_list_to_check", set(), [("s_a", {"a_name"})], ()),
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
    case_results = {}

    for name, src_a, src_b, must_catch in CASES:
        ka = _key(closure(src_a, ["root"]))
        kb = _key(closure(src_b, ["root"]))
        va, vb = _run(src_a), _run(src_b)
        caught = "unknown" in ka or "unknown" in kb or ka != kb
        behaviour_differs = va != vb
        status = "caught" if caught else "MISSED"
        # Recorded, not re-derived: a case cited as a kill below is audited on the same
        # run that printed it, so the two cannot drift apart.
        case_results[name] = (caught, behaviour_differs)
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

    for name, src_a, src_b, policy in OVERCUT:
        ka = _key(closure(src_a, ["root"]))
        kb = _key(closure(src_b, ["root"]))
        va, vb = _run(src_a), _run(src_b)
        accepted = "unknown" not in ka and "unknown" not in kb and ka == kb
        print(f"{'accepted!' if accepted else 'refused':8} {name:42} root(): {va} vs {vb}  "
              f"hash: {_show(ka)} vs {_show(kb)}   (cost of policy: {policy})")
        # A pair whose revisions do not behave the same is not an overcut case at all,
        # so a broken fixture fails here rather than quietly widening what "cost" means.
        if va != vb:
            failures.append(f"{name}: fixture is broken, revisions return {va} then {vb}")

    # The audit checked before it is believed, on made-up facts.
    for name, results, charged, policies, expect in AUDIT_SELFTEST:
        findings = _audit_overcut_policies(results, charged, policies)
        got = tuple(verdict for verdict, _, _, _, _ in findings)
        print(f"{'audit' if got == expect else 'SELFTEST':8} {name:42} "
              f"{' '.join(got) or '(nothing)'}")
        if got != expect:
            failures.append(f"audit self-test {name}: expected {expect}, got {got}")
        # A verdict that carries no failure is a verdict nothing acts on, and a `kills`
        # that carries one would fail a fixture that is fine.  Checked here rather than
        # spelled out per row: it is a property of every finding, not a fact about one.
        #
        # The failure text has to be non-empty, not merely present: STRAY / UNPAID /
        # VACUOUS print no adjudication line, so the FAILURES section is the only place
        # a reader ever meets them.  Codex's probe blanked every non-`kills` failure and
        # the run still exited 0 saying every case was as documented -- the verdicts
        # survived while the only thing anyone reads vanished.
        for verdict, _, _, _, failure in findings:
            if verdict == "kills":
                well_formed = failure is None
            else:
                well_formed = isinstance(failure, str) and bool(failure.strip())
            if not well_formed:
                failures.append(f"audit self-test {name}: verdict {verdict} with "
                                f"failure={failure!r}")

    # The name audit checked before it is believed, likewise on made-up facts: first the
    # scanner that turns a source into declared names, then the rule that reads them.
    for name, source, expect in _DECLARATION_SELFTEST:
        got = _declared_attribute_names(source)
        print(f"{'declare' if got == expect else 'SELFTEST':8} {name:42} "
              f"{' '.join(sorted(got)) or '(nothing)'}")
        if got != expect:
            failures.append(f"declaration scanner {name}: expected {sorted(expect)}, "
                            f"got {sorted(got)}")

    for name, names, charged, expect in _AUDIT_NAME_SELFTEST:
        findings = _audit_reflective_name_costs(names, charged)
        got = tuple(verdict for verdict, _, _, _ in findings)
        print(f"{'names' if got == expect else 'SELFTEST':8} {name:42} "
              f"{' '.join(got) or '(nothing)'}")
        if got != expect:
            failures.append(f"name audit self-test {name}: expected {expect}, got {got}")
        for verdict, _, _, failure in findings:
            well_formed = (failure is None if verdict == "priced"
                           else isinstance(failure, str) and bool(failure.strip()))
            if not well_formed:
                failures.append(f"name audit self-test {name}: verdict {verdict} with "
                                f"failure={failure!r}")

    # The membership rule of REFLECTIVE_ATTRIBUTE_NAMES, held against the set the tool is
    # actually running: every spelling on it owes a sample that declares it.  Read off
    # the same OVERCUT sources printed above, so a sample cannot be edited into paying
    # for a name it no longer declares without this saying so.
    declaring = [(sample, _declared_attribute_names(src_a) | _declared_attribute_names(src_b))
                 for sample, src_a, src_b, _ in OVERCUT]
    for verdict, name, samples, failure in _audit_reflective_name_costs(
            REFLECTIVE_ATTRIBUTE_NAMES, declaring):
        print(f"{verdict:8} {name:42} priced by: {', '.join(samples) or '(nothing)'}")
        if failure is not None:
            failures.append(failure)

    # The policy audit: every cost still has a policy paying for it, and every policy is
    # still held up by kills that are still running and still killing.
    charged = [(name, policy) for name, _, _, policy in OVERCUT]
    for verdict, policy, relaxation, kill, failure in _audit_overcut_policies(
            case_results, charged, OVERCUT_POLICIES):
        if relaxation is not None:
            print(f"{verdict:8} {policy:42} refuses: {relaxation}\n"
                  f"{'':8} {'':42} killed by: {kill}")
        if failure is not None:
            failures.append(failure)

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
