"""Read-only: hash the code a measurement actually reaches, not the file it lives in.

Why this exists.  measure_drift.py's comparison_key includes measurer.sha256, which
pins the whole file.  Editing a docstring therefore mints a new dimension even when
the code that produces the numbers is untouched -- and that has already happened
three times in this file's own history.  The alternative usually proposed is a
hand-declared method_id, but that is an author's claim ("the algorithm did not
change") which a reader cannot check.

This computes the claim instead.  Given a source file and one or more declared root
names, it walks module-level references from those roots, drops docstrings, and
hashes the normalised text of exactly the definitions reached.  What remains an
author's claim shrinks from "the method is unchanged" to "these are the roots" --
which a reader can check by reading the call site.  Nothing is written.

Honest limits, all of them load-bearing:
  * Sufficient only, and only on the source-text axis.  Equal closure hash means the
    reached definitions are textually identical after normalisation.  It says nothing
    about execution semantics (interpreter, filesystem) -- that is a separate axis
    and stays in measure_drift.py's runtime_semantics.
  * The hash is normalised by ast.unparse, whose output is not guaranteed stable
    across Python versions.  Two closure hashes are comparable only under the same
    unparser; the boundary is reported so a reader can refuse the comparison.
  * Three guards run, and only two of them are complete.

    1. The statement partition, complete.  Every statement in the module body is
       sorted into exactly one bucket: hashed as material, matched by a named inert
       shape, declared an import boundary, a script entry measured separately, or
       unaccounted -- and one unaccounted statement makes the result unknown.
       Completeness is structural: the last bucket is the default, so a shape nobody
       has ruled on lands there.  This matters because module-level statements run at
       import, before the measurement calls a root, and can rebind it.
    2. The bare-name channel, complete.  Every free name in a guarded statement must
       be module-bound, locally bound, or on an allow-list of names that return data
       and cannot hand back a callable from this module's namespace.  getattr,
       __import__, exec, and every builtin nobody has ruled on are absent on purpose;
       an unlisted name is not judged, it is refused, and it is named in the report.
    3. The attribute channel, NOT complete and not completable.  It is two partial
       detectors on different axes, and keeping them apart is what stops either from
       being read as the whole.

       By module: reflection through an imported module (sys.modules[...], importlib)
       is caught by a named partial list, matched against what a name was *imported
       from* as well as against how the file spells it, so `import sys as s` and
       `from sys import modules` are the listed shape and not an escape from it.
       Partial is the stated limit; evadable by rebinding was a false claim, and was
       live until this was written.
       Two things bound the resolution, in opposite directions, and both run rather
       than being described.  An alias made by assignment rather than import
       (`s = sys`) still evades: that is a miss, and a NOT_CLOSED case.  And the
       import map is read per module and per statement but not per scope, so a
       parameter or local reusing an imported name -- `def root(s)` after `import sys
       as s` -- resolves to the module and is refused although it is not one: that is
       a cost, not a miss, and an OVERCUT case with the kill that keeps it.  The two
       must not be filed together; the sections differ in what they assert.

       By attribute name: a name that is a *function/frame convention* -- `__globals__`,
       `f_globals` -- is refused wherever it is read, with no test on the base.  This
       axis exists because the module list structurally could not reach these: the
       base is a call (`inspect.currentframe().f_globals`), or the member is unlisted
       on a listed module (`sys._getframe`).  It is unqualified because the qualifier
       was measured: `X.__globals__` yields this module's namespace off a def, off an
       assignment alias, off a local lambda and off a parameter alike, so a rule
       keyed on the base's provenance catches one of four and looks principled doing
       it.  Convention is not exclusivity: an ordinary object may spell the same name,
       and then the refusal is wrong.  That is a cost, it is charged as one, and the
       claim it replaces -- "a name no ordinary object carries" -- read as a fact about
       Python when it was a bet about how people write.  What bounds this axis is the
       membership rule: `__dict__` is excluded because ordinary objects carry it
       routinely, and any name nobody has run a counterexample on is unlisted rather
       than cleared.

  * The import boundary, stated because it was previously silent.  An import runs
    the imported module's top level, which is outside this file and outside this
    hash -- equally so whether or not the import is reached.  Imports are therefore
    listed rather than hashed: hashing them would claim a coverage this tool does
    not have, and would also make an unrelated new import read as a changed method.
  * The script boundary, and there are two numbers because of it.  closure_sha256
    covers import-time execution plus what the declared roots reach -- all of it,
    when the file is imported as a library.  Running it as a script also runs the
    `__main__` guard, which is the caller: it can mutate what a root reads before
    calling it.  That is not exempted and not assumed harmless; it is measured as
    script_entry_sha256 over the guard and everything it reaches.  Comparing two
    script invocations needs both numbers.  Keeping them apart is deliberate in
    both directions -- editing main() must not mint a new measurement dimension,
    and mutating a root's state must not hide behind an equal measurement hash.
  * Consequently a hash never establishes that execution reaches *only* the hashed
    definitions.  It establishes that those definitions are textually identical.
    The gaps are real and were found by counterexample, not by reasoning:
      - a module whose root called getattr(sys.modules[__name__], name) returned 1
        in one revision and 2 in the next under an equal hash (attribute channel);
      - a module that wrote `for root in [lambda: 2]` after `def root` returned 2
        and 3 across revisions under an equal hash, with no reflection at all, and
        `CONFIG["k"] = 2` did the same by mutating instead of binding (partition);
      - a module whose `__main__` guard ran `CONFIG.append(2)` before `print(root())`
        printed 2 and 3 across revisions under an equal hash, while the guard was
        classified inert for binding no module-level name -- the test was measuring
        binding when what mattered was mutation, and it also refused guards that
        bind, which at import run no more than the mutating one does (script entry).
    The second and third families are closed by construction now.  The first is not,
    and saying so is the point: guards 1 and 2 are complete over what they cover,
    guard 3 is a detector, and no arrangement of the three proves execution is
    confined.
  * Whatever a root does not reach is out of scope by construction, and is listed in
    unreached_module_names so an over-narrow root list is visible, not hidden.  The
    escape from an unaccounted statement is to declare its name a root, which does
    not excuse the statement -- it hashes it.

Usage:
  python measurement_closure.py --source measure_drift.py --root collect --root sha256
  python measurement_closure.py --git-rev 8e93653 --git-path proposals/.../measure_drift.py \
      --root collect --root sha256
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Free names the walk is willing to see and keep going.  The selection rule is narrow:
# a listed name returns data, and cannot hand back a callable drawn from this module's
# own namespace.  getattr/setattr/globals/vars/locals/eval/exec/compile/__import__/dir/
# super/type are all absent on purpose -- each can.  Absence is not a verdict about a
# name, it is a refusal to guess: an unlisted name makes the result unknown and appears
# in the report, so the list grows by decision rather than by drift.
ALLOWED_FREE_NAMES = frozenset({
    # data and iteration
    "abs", "all", "any", "bool", "bytes", "dict", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "hash", "hasattr", "id", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next", "open", "ord",
    "chr", "print", "range", "repr", "reversed", "round", "set", "slice", "sorted",
    "str", "sum", "tuple", "zip",
    # exceptions, which are raised and caught, never called to reach code
    "AttributeError", "Exception", "FileNotFoundError", "IndexError", "KeyError",
    "NotImplementedError", "OSError", "RuntimeError", "StopIteration", "SystemExit",
    "TypeError", "ValueError",
    # strings, not references: __name__ for the universal `if __name__ == "__main__"`
    # guard, __file__ for the universal `Path(__file__)`.  Using either to index a
    # module registry is caught on the attribute channel below.  `object` is pointedly
    # absent despite being a data-ish builtin: object.__subclasses__() hands back every
    # class defined in this module, which is exactly what the rule excludes.
    "__name__", "__file__",
})

# The attribute channel.  Unlike the allow-list above this list is *not* complete and
# cannot be made complete -- an imported module can offer reflection under any name.
# It is here because the shapes that actually appear are worth catching, and because a
# named partial detector is honester than an unstated assumption.
#
# The entries name *modules and their members*, not identifiers appearing in the source.
# That distinction is load-bearing and was not always honoured: the matcher used to
# compare the written base against the string below, so `import sys as s` renamed the
# channel out of existence -- `s.modules[__name__]` reached a definition, both revisions
# hashed equal and known, and the tool went on claiming this shape was caught.  Being
# partial is a stated limit; being evadable by rebinding is a false claim, which is
# worse.  `_import_bindings` below resolves what a local name was imported from, so the
# list means the module regardless of what the file calls it.
#
# What it does not do is ask which binding is live where the name is used: the map is
# built per module and per statement, never per scope.  So `def root(s)` after `import
# sys as s` reads its own parameter as sys and the result is unknown.  That direction is
# refusal rather than escape, and it is not free -- dropping the resolution for a locally
# bound base loses `reflection_via_an_alias_imported_inside_the_function`, where the base
# is locally bound *by an import* and genuinely is sys.  Measured, both ways, and the
# price is charged in OVERCUT rather than carried as a claim.
REFLECTIVE_ATTRIBUTE_PATHS = (
    ("sys", "modules"),
    ("builtins", None),
    ("importlib", None),
    ("inspect", "getmembers"),
)

# A second channel on a different axis, and the membership rule is the whole of it: an
# attribute name that is a *function/frame convention*, so reading it is ordinarily
# evidence that a namespace is being fetched.  Matched regardless of what the base is.
#
# "Ordinarily", and the gap in that word is charged rather than talked away.  The rule
# first landed claiming these are names *no ordinary object carries*, which is a fact
# about Python and is false: `class Box: __globals__ = {...}` compiles, and the guard
# then refuses a pair whose two revisions are the same program.  Codex's probe on
# 39164b2 found it; it runs as an OVERCUT cost sample rather than as a sentence, because
# the version of it that was a sentence had already been wrong for a commit.
#
# Not a second spelling of the list above.  That one names modules and needs the base
# resolved; this one needs no base at all, which is why it reaches shapes the other
# cannot: `inspect.currentframe().f_globals` and `sys._getframe().f_globals` both hang
# the attribute off a *call*, and `sys._getframe` is an unlisted member of a listed
# module -- three escapes that lengthening the module list would have closed one at a
# time, badly.
#
# Qualifying these by the base's provenance was the obvious next move and it was
# measured and rejected, which is why the rule is unqualified.  `X.__globals__` hands
# back this module's namespace whatever X is: measured escaping off a module-level def
# (aa2c42aa), off a module-level assignment alias (8d7768d6), off a local lambda
# (e722a126), and off a parameter (434dd25c) -- all four equal-known while root()
# returned 2 then 3.  A rule keyed on "the base is bound at module level by a def"
# would have caught the first and let the other three through while looking principled.
#
# `__dict__` is pointedly absent, and its absence is the reason this list can exist at
# all: ordinary objects carry it, so reading it is not evidence of anything.  A local
# instance's `obj.__dict__["value"]` runs as a STABLE pair, and every `__dict__` escape
# that could be built -- injecting into a def's dict, reaching a subclass through a
# class dict -- was already refused by the statement partition, since the definition
# being reached that way is by construction unreached and therefore unaccounted.  That
# is where that shape currently falls; it is not a claim that it always will.
#
# Absence is a refusal to guess here exactly as it is in ALLOWED_FREE_NAMES: `f_locals`,
# `__closure__`, `__subclasses__` and the rest are unlisted because nobody has run a
# counterexample on them, not because they were judged safe.
#
# The list grows by measurement, and after the probe above that means measurement on
# both sides.  Admitting a name costs two runs, not one: the escape it closes, and the
# ordinary same-named attribute it will now refuse -- registered as a cost sample if one
# can be written, and if none can be, that is a finding worth stating rather than a step
# to skip.  One-sided admission is how a list gets washed by time into whatever its
# authors found plausible: every entry looks measured, because the half that would have
# argued was never run.
REFLECTIVE_ATTRIBUTE_NAMES = frozenset({"__globals__", "f_globals"})

_NESTED_SCOPES = (
    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
)


def _binding_targets(target: ast.AST, out: list[str]) -> None:
    """Names a store/delete target binds.  Attribute and Subscript targets bind none.

    `CONFIG["k"] = 2` binds nothing, which is exactly why it must not be mistaken for
    an inert statement: it mutates an object a reached definition reads.
    """
    if isinstance(target, ast.Name):
        out.append(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            _binding_targets(element, out)
    elif isinstance(target, ast.Starred):
        _binding_targets(target.value, out)


def _module_bindings(node: ast.stmt) -> list[str]:
    """Every module-level name this statement can bind, at any nesting of blocks.

    The old version of this only understood def/class/import/assign at the top of the
    statement, so `for root in [...]`, `with open(p) as root`, `if C: root = a`, and
    `root += 1` all bound a name it never saw -- and a statement it thinks binds
    nothing was neither hashed nor, until now, refused.  Block statements are walked;
    nested function, class, lambda and comprehension scopes are not, since a name
    bound there is not bound at module level (a `global` inside a function binds only
    when that function is called, which requires reaching it).
    """
    out: list[str] = []

    def walk(node: ast.AST) -> None:
        if isinstance(node, _NESTED_SCOPES):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.append(node.name)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            out.extend(alias.asname or alias.name.split(".")[0] for alias in node.names)
            return
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _binding_targets(target, out)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            _binding_targets(node.target, out)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            _binding_targets(node.target, out)
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                _binding_targets(node.optional_vars, out)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                out.append(node.name)
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                _binding_targets(target, out)
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(node)
    return sorted(set(out))


def _is_literal_only(node: ast.AST) -> bool:
    """True for an expression built from constants and constant containers alone.

    No Call, no Attribute, no Subscript, no Name, no BinOp: each of those can run code
    at import (`ROOT / "x"` calls __truediv__, `Path(...)` calls a constructor), and
    running code is the whole risk being guarded against here.
    """
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_literal_only(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(k is not None and _is_literal_only(k) for k in node.keys) and all(
            _is_literal_only(v) for v in node.values
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _is_literal_only(node.operand)
    return False


def _is_main_guard(node: ast.stmt) -> bool:
    """The canonical `if __name__ == "__main__":` test, and nothing else.

    Matching the shape says only *when* the body runs -- under script execution and
    not at import.  It says nothing about what the body does, which is why the body
    is measured as its own region rather than exempted; see `script_entry` below.
    """
    if not isinstance(node, ast.If) or node.orelse:
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _def_runs_code_at_import(node: ast.stmt, postponed_annotations: bool) -> str | None:
    """Why an unreached `def` is not inert, or None if it only binds a function object.

    Executing a `def` does not execute its body, which is why an unreached function is
    harmless.  Three things in the header do run at import: decorators, default
    argument expressions, and -- unless `from __future__ import annotations` made them
    strings -- annotations.  A `class` is absent from this exemption on purpose: a
    class body executes at import.
    """
    if node.decorator_list:
        return "decorator runs code at import"
    args = node.args
    defaults = list(args.defaults) + [d for d in args.kw_defaults if d is not None]
    if not all(_is_literal_only(d) for d in defaults):
        return "default argument runs code at import"
    if not postponed_annotations:
        annotations = [a.annotation for a in (
            args.args + args.posonlyargs + args.kwonlyargs
            + [a for a in (args.vararg, args.kwarg) if a is not None]
        ) if a.annotation is not None]
        if node.returns is not None:
            annotations.append(node.returns)
        if not all(_is_literal_only(a) for a in annotations):
            return "annotation is evaluated at import (no `from __future__ import annotations`)"
    return None


def _classify(node: ast.stmt, postponed_annotations: bool) -> tuple[str, str]:
    """Sort one non-material module statement into a named bucket.

    The bucket list is an allow-list of shapes, and `unaccounted` is the default, so
    a shape nobody has ruled on lands in the refusing bucket rather than sliding past.
    """
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        return "inert", "literal_expression_statement"
    if isinstance(node, ast.Pass):
        return "inert", "pass"
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return "import_boundary", "import"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        why = _def_runs_code_at_import(node, postponed_annotations)
        if why is None:
            return "inert", "unreached_def_binds_only_a_function_object"
        return "unaccounted", why
    if _is_main_guard(node):
        # Not inert, and the previous test for it ("binds nothing at module level")
        # was measuring the wrong thing in both directions.  It let through a guard
        # that binds nothing but mutates what a reached definition reads --
        # `CONFIG.append(2)` before `print(root())` -- and it refused a guard that
        # binds a name, which at import runs no more than the mutating one does.
        # What is actually true of this shape is only *when* it runs: not at import,
        # and as the caller under script execution.  So it gets its own region with
        # its own hash instead of an exemption; a caller whose effects are measured
        # separately is a different claim from a caller assumed to have none.
        return "script_entry", "runs under script execution only, measured separately"
    if _module_bindings(node):
        if (
            isinstance(node, ast.Assign)
            and all(isinstance(t, ast.Name) for t in node.targets)
            and _is_literal_only(node.value)
        ):
            return "inert", "literal_binder"
        return "unaccounted", "binds an unreached name by running code at import"
    return "unaccounted", "runs at import, binds nothing, and may mutate reached state"


def _strip_docstrings(node: ast.AST) -> ast.AST:
    """Remove docstrings everywhere, so prose edits do not move the hash.

    Comments are already absent -- ast.parse discards them -- which is the point:
    the hash tracks code, and this makes docstrings behave the same way.
    """
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = sub.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                sub.body = body[1:] or [ast.Pass()]
    return node


def _referenced_names(node: ast.AST) -> set[str]:
    """Every bare name read inside this statement, including attribute bases."""
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.add(sub.id)
    return out


def _locally_bound(node: ast.AST) -> set[str]:
    """Names bound anywhere inside this statement.

    Python's own scope rule is used deliberately: a name assigned anywhere in a
    function body is local to it, branch or no branch.  So this is not a loose
    over-approximation -- it is the same rule the interpreter applies.
    """
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
            out.add(sub.id)
        elif isinstance(sub, ast.arg):
            out.add(sub.arg)
        elif isinstance(sub, ast.alias):
            out.add(sub.asname or sub.name.split(".")[0])
        elif isinstance(sub, ast.ExceptHandler) and sub.name:
            out.add(sub.name)
        elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(sub.name)
    return out


def _import_bindings(nodes) -> dict[str, str]:
    """Bound name -> the dotted thing it was imported as, over the import statements
    among `nodes`.

    `import sys` and `import sys as s` both give "sys"; `import a.b` binds `a` to "a"
    (the attribute path continues from there); `import a.b as c` gives c -> "a.b";
    `from a import b [as c]` gives the bound name -> "a.b", so a member lifted out of a
    module is still known to be that member.  Relative imports are skipped: `from .
    import x` names a package this walk cannot resolve, and guessing would put a wrong
    module behind a right-looking name.

    The caller chooses the scope: `tree.body` for the module map, `ast.walk(stmt)` for
    the imports a single statement performs inside itself.  Both are needed, and it was
    measured which -- `def root(): import sys as s; ...` binds nothing at module level,
    so a module-only map leaves that spelling evading the very list it names.
    """
    out: dict[str, str] = {}
    for stmt in nodes:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.asname:
                    out[alias.asname] = alias.name
                else:
                    out[alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.level or not stmt.module:
                continue
            for alias in stmt.names:
                if alias.name == "*":
                    continue
                out[alias.asname or alias.name] = f"{stmt.module}.{alias.name}"
    return out


def _reflective_paths(node: ast.AST, imported: dict[str, str] | None = None) -> set[str]:
    """Uses of the partial reflection list, however the file spells them.

    Three matches, and the second and third are why this is not just a text compare:
    an attribute on a name the file imported the module under (`s.modules` after
    `import sys as s`), and a bare name the file imported the member under
    (`import_module` after `from importlib import import_module`) -- the latter has no
    attribute access at all, so a matcher that only walks `ast.Attribute` cannot see it.
    The plain written form is still matched too, so this only ever adds: a base that is
    not an import resolves to nothing and falls back to the spelling, and nothing that
    was refused before is now allowed.

    A finding is reported as written, with what it resolved to in parentheses when the
    two differ, so a reader can both find it in the source and see why it counted.

    Imports written *inside* this statement are folded in on top of the module map, so
    a function that imports its own alias is resolved the same way.  What is still not
    resolved is an alias made by assignment (`s = sys`): that is dataflow, not an
    import, and claiming it here would repeat the mistake this function just fixed.  It
    runs as a NOT_CLOSED case in the fixture rather than being described.

    A fourth match needs neither map: a function/frame-convention attribute name
    (`REFLECTIVE_ATTRIBUTE_NAMES`), matched with no test on the base at all.  Ordinary
    objects can define the same spelling, so this is a deliberate overcut paid by a
    running cost fixture.  The unqualified match is the only way to see
    `inspect.currentframe().f_globals`, where the base is a call rather than a name,
    and qualifying it by the base's provenance was measured leaking three ways.

    Neither map is scoped, and that is a deliberate over-approximation rather than an
    oversight: a name shadowed by a parameter or a local still resolves to the module it
    was imported as, and the region is refused.  The cheap repair -- skip a base that
    `_locally_bound` reports -- was run and rejected, because an alias imported inside
    the function is locally bound by that very import, so the repair reopens a case this
    file measured evading.  Both directions run as fixtures: the miss in NOT_CLOSED, the
    cost in OVERCUT.
    """
    scoped = dict(imported or {})
    scoped.update(_import_bindings(ast.walk(node)))
    out = set()

    def resolve(name: str) -> str | None:
        return scoped.get(name)

    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr in REFLECTIVE_ATTRIBUTE_NAMES:
            # No base test on purpose; see REFLECTIVE_ATTRIBUTE_NAMES.  Reported as
            # written so a reader can find it, base expression and all.
            out.add(ast.unparse(sub))
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            written = f"{sub.value.id}.{sub.attr}"
            target = resolve(sub.value.id)
            for base, attr in REFLECTIVE_ATTRIBUTE_PATHS:
                if attr not in (None, sub.attr):
                    continue
                if sub.value.id == base:
                    out.add(written)
                elif target == base:
                    out.add(f"{written} ({base}.{sub.attr})")
        elif isinstance(sub, ast.Name):
            target = resolve(sub.id)
            if not target or target == sub.id:
                continue
            for base, attr in REFLECTIVE_ATTRIBUTE_PATHS:
                if target == f"{base}.{attr}" or (attr is None
                                                  and target.startswith(f"{base}.")):
                    out.add(f"{sub.id} ({target})")
    return out


def _reach(binders: dict[str, list[ast.stmt]], seeds: list[str]) -> dict[str, list[ast.stmt]]:
    """Module-level names transitively referenced from `seeds`, with their binders.

    A name can be bound by several module statements (`def root` then a later
    `for root in ...`).  All of them run at import, so all of them are kept when the
    name is reached; keeping only the last would hide the shadowed one.
    """
    reached: dict[str, list[ast.stmt]] = {}
    frontier = [s for s in seeds if s in binders]
    while frontier:
        name = frontier.pop()
        if name in reached:
            continue
        reached[name] = binders[name]
        for stmt in binders[name]:
            for ref in sorted(_referenced_names(stmt)):
                if ref in binders and ref not in reached:
                    frontier.append(ref)
    return reached


def _units(stmts: list[ast.stmt], reached: dict[str, list[ast.stmt]],
           tree: ast.Module, order: dict[str, int]) -> list[dict]:
    """Normalised, docstring-free text for each statement, labelled by what it binds.

    One statement can bind several reached names (a shared import line); it is hashed
    once, labelled by every reached name it binds, so the label set is itself part of
    what is hashed.  A statement that binds no reached name (the `__main__` guard) is
    labelled by the position it occupies, which is enough to order it.

    That `at` key is present only on those units, and the condition is load-bearing
    rather than tidy.  Adding it unconditionally moved every closure_sha256 in this
    file's own history -- 30e835d 12a33037 -> 4bf92919 and the other four 500862dd ->
    00828193 -- for a change that touched only the script-entry region.  A
    representation edit must not mint a new measurement dimension; that is the rule
    this whole tool exists to enforce, and running it on itself is what caught it.
    """
    units = []
    for stmt in sorted(stmts, key=lambda s: tree.body.index(s)):
        labels = sorted(n for n, v in reached.items() if any(stmt is r for r in v))
        text = ast.unparse(_strip_docstrings(ast.parse(ast.unparse(stmt))))
        unit = {"binds": labels, "normalised": text}
        if not labels:
            unit["at"] = tree.body.index(stmt)
        units.append(unit)
    units.sort(key=lambda u: (order[u["binds"][0]] if u["binds"] else u["at"],
                              u["binds"]))
    return units


def _name_channel(stmts: list[ast.stmt], binders: dict[str, list[ast.stmt]],
                  imported: dict[str, str]) -> tuple[set[str], set[str]]:
    """Free names this region cannot resolve, and reflective paths found in it.

    `imported` is the module-level import map, so the attribute channel matches the
    module a name was imported from rather than the identifier the file happens to use.
    """
    unresolved: set[str] = set()
    reflective: set[str] = set()
    for stmt in stmts:
        free = _referenced_names(stmt) - _locally_bound(stmt)
        unresolved |= {n for n in free if n not in binders and n not in ALLOWED_FREE_NAMES}
        reflective |= _reflective_paths(stmt, imported)
    return unresolved, reflective


def closure(source: str, roots: list[str]) -> dict:
    tree = ast.parse(source)
    imported = _import_bindings(tree.body)

    binders: dict[str, list[ast.stmt]] = {}
    order: dict[str, int] = {}
    for index, stmt in enumerate(tree.body):
        for name in _module_bindings(stmt):
            binders.setdefault(name, []).append(stmt)
            order.setdefault(name, index)

    missing_roots = [r for r in roots if r not in binders]

    reached = _reach(binders, roots)
    material_stmts = [s for s in tree.body if any(s is r for v in reached.values() for r in v)]
    units = _units(material_stmts, reached, tree, order)

    # Every remaining statement in the module body is classified.  `unaccounted` is
    # the default bucket, so the partition is complete without enumerating shapes.
    postponed_annotations = any(
        isinstance(s, ast.ImportFrom) and s.module == "__future__"
        and any(a.name == "annotations" for a in s.names)
        for s in tree.body
    )
    inert, imports, unaccounted, entries = [], [], [], []
    for stmt in tree.body:
        if any(stmt is s for s in material_stmts):
            continue
        bucket, why = _classify(stmt, postponed_annotations)
        entry = {"line": stmt.lineno, "node": type(stmt).__name__, "shape": why}
        if bucket == "inert":
            inert.append(entry)
        elif bucket == "import_boundary":
            entry["modules"] = _module_bindings(stmt)
            imports.append(entry)
        elif bucket == "script_entry":
            entries.append(stmt)
        else:
            unaccounted.append(entry)

    # The free-name guard covers the reached definitions and nothing else.  It
    # deliberately does NOT cover an unreached `def`: its body never runs, so refusing
    # a name that appears only in an unreached function's annotation would report
    # unknown for code the measurement cannot reach.  Nor does it cover a `__main__`
    # guard any more -- that used to be folded in here while the guard was called
    # inert, which meant one region's verdict was answering for two regions' code.
    # The guard has its own name channel below, over its own material.
    unresolved, reflective = _name_channel(material_stmts, binders, imported)

    # The script-entry region.  A `__main__` guard does not run at import, so it is
    # outside the measurement closure; under `python file.py` it runs as the caller,
    # so it is not nothing either.  It is measured with the same walk and the same
    # guards, and reported as a second number.  Keeping the two apart is the point:
    # editing main() must not mint a new measurement dimension, and mutating what a
    # root reads must not hide behind an equal one.
    entry_reached = _reach(binders, sorted({n for s in entries
                                            for n in _referenced_names(s)} & set(binders)))
    entry_material = entries + [s for s in tree.body
                                if any(s is r for v in entry_reached.values() for r in v)
                                and not any(s is e for e in entries)]
    entry_unresolved, entry_reflective = _name_channel(entry_material, binders, imported)
    entry_outside = sorted(n for n in entry_reached if n not in reached)

    material = {
        "roots": sorted(roots),
        "units": units,
        "unparser": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    # Still "not reached by a declared root", not "not reached by anything": a name
    # the script entry reaches is still outside the measurement, and hiding it here
    # because the caller happens to touch it would mask an over-narrow root list.
    unreached = sorted(n for n in binders if n not in reached)

    result = {
        "roots_declared": sorted(roots),
        "roots_missing": sorted(missing_roots),
        "reached_names": sorted(reached, key=lambda n: (order[n], n)),
        "unreached_module_names": unreached,
        "unparser_boundary": material["unparser"],
        "reference_guard": {
            "statement_partition": {
                "policy": "every module statement is material, inert, an import "
                          "boundary, or unaccounted; unaccounted yields unknown",
                "complete": True,
                "material": len(material_stmts),
                "inert": inert,
                "unaccounted": unaccounted,
            },
            "name_channel": {
                "policy": "allow-list; an unlisted free name yields unknown",
                "complete": True,
                "scopes_checked": {"reached_definitions": len(material_stmts)},
                "unresolved_names": sorted(unresolved),
            },
            "attribute_channel": {
                "policy": "two partial detectors: a named list of reflective module "
                          "members, matched through import bindings rather than "
                          "spelling; and a named list of attribute names no ordinary "
                          "object carries, matched with no test on the base",
                "complete": False,
                "paths_found": sorted(reflective),
            },
            "import_boundary": {
                "policy": "listed, not hashed; the imported module's top level runs "
                          "outside this file and outside this hash",
                "complete": False,
                "imports": imports,
            },
            "script_entry": {
                "policy": "a __main__ guard does not run at import and is not part of "
                          "the measurement closure; under script execution it runs as "
                          "the caller, so it is measured as its own region instead of "
                          "being exempted, and reported as script_entry_sha256",
                # A guard that binds a name the roots reach is a binder like any
                # other, so it is already hashed inside closure_sha256 and has no
                # separate region.  Both counts are reported rather than one flag,
                # because "no separate region" and "no guard" are not the same fact.
                "guards_in_module": sum(1 for s in tree.body if _is_main_guard(s)),
                "measured_as_own_region": len(entries),
                "statements": [{"line": s.lineno, "node": type(s).__name__}
                               for s in entries],
                "material": len(entry_material),
                "reaches_outside_closure": entry_outside,
                "unresolved_names": sorted(entry_unresolved),
                "paths_found": sorted(entry_reflective),
            },
            "verdict": (
                "unbounded"
                if (unresolved or reflective or unaccounted)
                else "bounded_on_the_source_text_axis"
            ),
        },
    }
    if not entries:
        result["script_entry_sha256"] = None
    elif unaccounted:
        # Unaccounted statements run at import, and running the script imports it, so
        # they take this region down with the other one rather than only that one.
        result["script_entry_sha256"] = "unknown"
        result["script_entry_unknown_reason"] = (
            "import-time statements neither hashed nor inert also precede the caller: "
            + ", ".join(f"L{e['line']} {e['node']} ({e['shape']})" for e in unaccounted)
        )
    elif entry_unresolved or entry_reflective:
        result["script_entry_sha256"] = "unknown"
        result["script_entry_unknown_reason"] = (
            "the caller can construct a reference the walk cannot follow: "
            + ", ".join(sorted(entry_unresolved) + sorted(entry_reflective))
        )
    else:
        result["script_entry_sha256"] = hashlib.sha256(json.dumps({
            "units": _units(entry_material, entry_reached, tree, order),
            "unparser": material["unparser"],
        }, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if missing_roots:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = "declared root not found at module level"
    elif unaccounted:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = (
            "module statements run at import that are neither hashed nor inert: "
            + ", ".join(f"L{e['line']} {e['node']} ({e['shape']})" for e in unaccounted)
        )
    elif unresolved or reflective:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = (
            "a reference can be constructed here that the walk cannot follow: "
            + ", ".join(sorted(unresolved) + sorted(reflective))
        )
    else:
        result["closure_sha256"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    result["authority"] = (
        "sufficient only, source-text axis; equal closure_sha256 => the reached "
        "definitions are textually identical after normalisation; unequal => nothing "
        "established. It does NOT follow that execution reaches only those "
        "definitions: the statement partition and the name channel are complete over "
        "what they cover, but the attribute channel is a partial detector and imports "
        "are listed rather than hashed, so undetected reflection or an imported "
        "module's own top level can run code the hash never saw. Execution semantics "
        "(interpreter, filesystem) are a separate axis and are not covered here. "
        "closure_sha256 covers import-time execution plus what the declared roots "
        "reach, which is the whole of it when the file is imported as a library. "
        "Running the file as a script also runs the __main__ guard, which can mutate "
        "what a root reads before calling it -- that is measured, not assumed away, "
        "as script_entry_sha256; comparing two script invocations therefore needs "
        "both numbers, and a difference in the second one is a difference in the "
        "caller, not in the measurement."
    )
    return result


def _git_show(rev: str, path: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{rev}:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="path to a source file on disk")
    ap.add_argument("--git-rev", action="append", default=[],
                    help="read the source at this revision instead (repeatable)")
    ap.add_argument("--git-path", help="repo-relative path, required with --git-rev")
    ap.add_argument("--root", action="append", default=[], required=True,
                    help="module-level name the measurement enters through (repeatable)")
    args = ap.parse_args()

    reports = []
    if args.git_rev:
        if not args.git_path:
            print("--git-rev requires --git-path", file=sys.stderr)
            return 2
        for rev in args.git_rev:
            src = _git_show(rev, args.git_path)
            if src is None:
                reports.append({"rev": rev, "path": args.git_path,
                                "closure_sha256": "unknown",
                                "unknown_reason": "git show failed"})
                continue
            report = closure(src, args.root)
            report["rev"] = rev
            report["path"] = args.git_path
            report["file_sha256"] = hashlib.sha256(src.encode("utf-8")).hexdigest()
            reports.append(report)
    else:
        if not args.source:
            print("give --source or --git-rev/--git-path", file=sys.stderr)
            return 2
        raw = Path(args.source).read_bytes()
        report = closure(raw.decode("utf-8"), args.root)
        report["path"] = str(Path(args.source))
        report["file_sha256"] = hashlib.sha256(raw).hexdigest()
        reports.append(report)

    print(json.dumps(reports if len(reports) > 1 else reports[0],
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
