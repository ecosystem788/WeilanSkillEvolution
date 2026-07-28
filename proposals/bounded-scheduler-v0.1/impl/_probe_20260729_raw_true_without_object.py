"""Probe the TRUE side of the raw-object canonical reachability evaluator.

Question raised against peer-chat 2026-07-29T04:11:35+09:00 (probe
``_probe_20260729_raw_object_reachability.py``, commit ac4cc7b): that evaluator
is sound for canonical-graph semantics because every traversed edge is
content-bound. This probe does not dispute soundness. It asks what its TRUE
*means*, and tests two ways to make it wrong.

Leg 1 (the claim under test): ``raw_reachability`` checks ``oid == ancestor``
*before* reading the object, so it can answer TRUE about a commit that does not
exist in the repository at all. Constructed in a shallow clone, where the
boundary commit's raw ``parent`` header names an object the reader does not
have and cannot walk. Expected: raw=TRUE, object absent, walker refuses.
This is the exact inversion of that probe's leg E (raw fail-closed / walker
fail-open) and matters because the origin question of this line -- third-party
reachability -- asks whether a reader can obtain bytes, not whether an edge
exists in the abstract.

Leg 2 (control, an attack that should fail): a commit whose *message body*
contains a forged ``parent <oid>`` line. If the header/body boundary were not
respected this would fabricate an edge and produce a genuinely unsound TRUE.
Expected: not traversed.

Leg 3 (control): in the full repository the same query as leg 1 is TRUE *and*
the object is present -- showing the two TRUEs are indistinguishable in the
answer, and separable only by an availability check the evaluator does not make.

All repositories are temporary; the workspace is read-only to this probe.
"""

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


GIT = "git"


def run(args, cwd, env=None, check=True):
    effective_env = dict(os.environ)
    effective_env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    effective_env.setdefault("HOME", cwd)
    if env:
        effective_env.update(env)
    process = subprocess.run(
        [GIT] + args, cwd=cwd, env=effective_env, capture_output=True, text=False
    )
    if check and process.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} -> rc={process.returncode}\n"
            f"{process.stderr.decode('utf-8', errors='replace')}"
        )
    return process


def text(process):
    return process.stdout.decode("utf-8", errors="replace").strip()


def hash_object(object_format, object_type, payload):
    framed = object_type.encode("ascii") + b" " + str(len(payload)).encode("ascii")
    framed += b"\0" + payload
    return hashlib.new(object_format, framed).hexdigest()


# --- evaluator copied verbatim in behaviour from ac4cc7b -----------------------

def raw_commit(root, oid):
    env = {"GIT_NO_REPLACE_OBJECTS": "1"}
    process = run(["cat-file", "commit", oid], root, env=env, check=False)
    if process.returncode != 0:
        return None
    object_format = text(run(["rev-parse", "--show-object-format"], root))
    actual_oid = hash_object(object_format, "commit", process.stdout)
    if actual_oid != oid:
        raise RuntimeError(f"object identity mismatch: wanted {oid}, got {actual_oid}")
    return process.stdout


def parents(payload):
    result = []
    for line in payload.split(b"\n"):
        if not line:
            break
        if line.startswith(b"parent "):
            result.append(line[7:].decode("ascii"))
    return result


def raw_reachability(root, ancestor, descendant):
    pending = [descendant]
    seen = set()
    reads = 0
    missing = []
    answered_without_reading = None
    while pending:
        oid = pending.pop()
        if oid in seen:
            continue
        seen.add(oid)
        if oid == ancestor:
            # instrumentation only: did we ever read the object we are asserting about?
            answered_without_reading = oid not in READ_OIDS[root]
            return {
                "answer": "TRUE",
                "reads": reads,
                "missing": missing,
                "answered_about_unread_oid": answered_without_reading,
            }
        payload = raw_commit(root, oid)
        reads += 1
        if payload is None:
            missing.append(oid)
            continue
        READ_OIDS[root].add(oid)
        pending.extend(parents(payload))
    if missing:
        return {"answer": "UNKNOWN", "reads": reads, "missing": sorted(missing)}
    return {"answer": "FALSE", "reads": reads, "missing": []}


READ_OIDS = {}


def evaluate(root, ancestor, descendant):
    READ_OIDS[root] = set()
    return raw_reachability(root, ancestor, descendant)


# -----------------------------------------------------------------------------

def walker_answer(root, ancestor, descendant):
    process = run(["merge-base", "--is-ancestor", ancestor, descendant], root, check=False)
    rc = process.returncode
    label = "TRUE" if rc == 0 else ("FALSE" if rc == 1 else "UNKNOWN")
    return {
        "answer": label,
        "rc": rc,
        "stderr": process.stderr.decode("utf-8", errors="replace").strip()[:200],
    }


def object_present(root, oid):
    return run(["cat-file", "-e", f"{oid}^{{object}}"], root, check=False).returncode == 0


def make_repo(root, count=10):
    os.makedirs(root, exist_ok=True)
    run(["init", "-q", "-b", "main", "."], root)
    run(["config", "user.email", "probe@example.invalid"], root)
    run(["config", "user.name", "probe"], root)
    oids = []
    for number in range(1, count + 1):
        pathlib.Path(root, "f.txt").write_text(f"c{number}\n", encoding="utf-8")
        run(["add", "f.txt"], root)
        run(["commit", "-q", "-m", f"c{number}"], root)
        oids.append(text(run(["rev-parse", "HEAD"], root)))
    return oids


def file_url(path):
    return pathlib.Path(path).resolve().as_uri()


def main():
    output = {"git_version": text(run(["--version"], os.getcwd())), "legs": {}}
    temp_root = tempfile.mkdtemp(prefix="raw_true_")
    try:
        baseline = os.path.join(temp_root, "baseline")
        oids = make_repo(baseline)
        head = oids[-1]

        # --- leg 1: TRUE about an object the reader does not have ---------------
        shallow = os.path.join(temp_root, "shallow")
        run(["clone", "-q", "--depth", "3", file_url(baseline), shallow], temp_root)
        boundary = text(run(["rev-list", "--max-parents=0", "HEAD"], shallow))
        boundary_payload = raw_commit(shallow, boundary)
        boundary_parents = parents(boundary_payload)
        shallow_head = text(run(["rev-parse", "HEAD"], shallow))
        absent = boundary_parents[0] if boundary_parents else None

        leg1 = {
            "note": "shallow boundary commit still carries its raw parent header",
            "boundary_oid": boundary,
            "boundary_declares_parent": boundary_parents,
            "queried_ancestor": absent,
            "ancestor_object_present_in_reader": object_present(shallow, absent),
            "ancestor_is_real_ancestor_upstream": walker_answer(baseline, absent, head)["answer"],
            "raw": evaluate(shallow, absent, shallow_head),
            "walker": walker_answer(shallow, absent, shallow_head),
        }
        output["legs"]["L1_true_about_absent_object"] = leg1

        # --- leg 2: forged parent line in the commit message body ---------------
        forged_repo = os.path.join(temp_root, "forged")
        os.makedirs(forged_repo, exist_ok=True)
        run(["init", "-q", "-b", "main", "."], forged_repo)
        run(["config", "user.email", "probe@example.invalid"], forged_repo)
        run(["config", "user.name", "probe"], forged_repo)
        pathlib.Path(forged_repo, "a.txt").write_text("a\n", encoding="utf-8")
        run(["add", "a.txt"], forged_repo)
        run(["commit", "-q", "-m", "island"], forged_repo)
        island = text(run(["rev-parse", "HEAD"], forged_repo))
        run(["checkout", "-q", "--orphan", "other"], forged_repo)
        run(["rm", "-q", "-rf", "."], forged_repo)
        pathlib.Path(forged_repo, "b.txt").write_text("b\n", encoding="utf-8")
        run(["add", "b.txt"], forged_repo)
        run(["commit", "-q", "-m", f"unrelated\n\nparent {island}\n"], forged_repo)
        forged_head = text(run(["rev-parse", "HEAD"], forged_repo))
        forged_payload = raw_commit(forged_repo, forged_head)
        output["legs"]["L2_forged_parent_in_message"] = {
            "note": "message body contains a syntactically valid parent line",
            "body_contains_parent_line": b"\nparent " in forged_payload.split(b"\n\n", 1)[1],
            "island_oid": island,
            "raw": evaluate(forged_repo, island, forged_head),
            "walker": walker_answer(forged_repo, island, forged_head),
        }

        # --- leg 3: control, same shape but object present -----------------------
        c1 = oids[0]
        output["legs"]["L3_control_object_present"] = {
            "queried_ancestor": c1,
            "ancestor_object_present_in_reader": object_present(baseline, c1),
            "raw": evaluate(baseline, c1, head),
            "walker": walker_answer(baseline, c1, head),
        }

        expected = {
            "L1_raw": "TRUE",
            "L1_ancestor_present": False,
            "L1_answered_about_unread_oid": True,
            "L1_walker": "UNKNOWN",
            "L2_raw": "FALSE",
            "L3_raw": "TRUE",
            "L3_ancestor_present": True,
        }
        observed = {
            "L1_raw": leg1["raw"]["answer"],
            "L1_ancestor_present": leg1["ancestor_object_present_in_reader"],
            "L1_answered_about_unread_oid": leg1["raw"].get("answered_about_unread_oid"),
            "L1_walker": leg1["walker"]["answer"],
            "L2_raw": output["legs"]["L2_forged_parent_in_message"]["raw"]["answer"],
            "L3_raw": output["legs"]["L3_control_object_present"]["raw"]["answer"],
            "L3_ancestor_present": output["legs"]["L3_control_object_present"][
                "ancestor_object_present_in_reader"
            ],
        }
        output["expected"] = expected
        output["observed"] = observed
        output["all_expected"] = observed == expected
        print(json.dumps(output, ensure_ascii=False, indent=1))
        return 0 if output["all_expected"] else 1
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
