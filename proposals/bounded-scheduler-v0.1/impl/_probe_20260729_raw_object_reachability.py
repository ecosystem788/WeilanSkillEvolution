"""Probe an overlay-independent, three-valued reachability evaluator.

Question from peer-chat 2026-07-29T03:58:46+09:00:
must every definite reachability answer bind graph-rewrite mechanisms to the
same process/snapshot, or can the evaluator define canonical reachability over
raw content-addressed commit parent edges instead?

All repositories are temporary. The evaluator deliberately does not use a Git
revision walker. It reads each commit object with replacement disabled, verifies
the returned object bytes against the requested OID, and follows raw ``parent``
headers. Missing objects produce UNKNOWN rather than FALSE.
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
        [GIT] + args,
        cwd=cwd,
        env=effective_env,
        capture_output=True,
        text=False,
    )
    if check and process.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} -> rc={process.returncode}\n"
            f"{process.stderr.decode('utf-8', errors='replace')}"
        )
    return process


def text(process):
    return process.stdout.decode("utf-8", errors="replace").strip()


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


def hash_object(object_format, object_type, payload):
    framed = object_type.encode("ascii") + b" " + str(len(payload)).encode("ascii")
    framed += b"\0" + payload
    return hashlib.new(object_format, framed).hexdigest()


def raw_commit(root, oid):
    """Return verified raw commit bytes, or None when the object is unavailable."""
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


def raw_reachability(root, ancestor, descendant, after_first_read=None):
    """TRUE when connected, FALSE when the complete raw domain excludes ancestor,
    and UNKNOWN when any required raw commit object is unavailable."""
    pending = [descendant]
    seen = set()
    reads = 0
    missing = []
    while pending:
        oid = pending.pop()
        if oid in seen:
            continue
        seen.add(oid)
        if oid == ancestor:
            return {"answer": "TRUE", "reads": reads, "missing": missing}
        payload = raw_commit(root, oid)
        reads += 1
        if payload is None:
            missing.append(oid)
            continue
        if reads == 1 and after_first_read is not None:
            after_first_read()
        pending.extend(parents(payload))
    if missing:
        return {"answer": "UNKNOWN", "reads": reads, "missing": sorted(missing)}
    return {"answer": "FALSE", "reads": reads, "missing": []}


def walker_answer(root, ancestor, descendant):
    process = run(
        ["merge-base", "--is-ancestor", ancestor, descendant],
        root,
        check=False,
    )
    return "TRUE" if process.returncode == 0 else (
        "FALSE" if process.returncode == 1 else "UNKNOWN"
    )


def write_graft(root, oid):
    graft_path = text(run(["rev-parse", "--git-path", "info/grafts"], root))
    graft = pathlib.Path(graft_path)
    if not graft.is_absolute():
        graft = pathlib.Path(root, graft)
    graft.parent.mkdir(parents=True, exist_ok=True)
    graft.write_text(f"{oid}\n", encoding="ascii")
    return str(graft)


def file_url(path):
    return pathlib.Path(path).resolve().as_uri()


def main():
    output = {
        "git_version": text(run(["--version"], os.getcwd())),
        "legs": {},
    }
    temp_root = tempfile.mkdtemp(prefix="raw_reachability_")
    try:
        baseline = os.path.join(temp_root, "baseline")
        oids = make_repo(baseline)
        c1, c5, head = oids[0], oids[4], oids[-1]
        output["legs"]["A_baseline"] = {
            "walker": walker_answer(baseline, c1, head),
            "raw": raw_reachability(baseline, c1, head),
        }

        replace_repo = os.path.join(temp_root, "replace")
        shutil.copytree(baseline, replace_repo)
        run(["replace", "--graft", c5], replace_repo)
        output["legs"]["B_replace_overlay"] = {
            "walker": walker_answer(replace_repo, c1, head),
            "raw": raw_reachability(replace_repo, c1, head),
            "replace_count": len(text(run(["replace", "-l"], replace_repo)).splitlines()),
        }

        graft_repo = os.path.join(temp_root, "graft")
        shutil.copytree(baseline, graft_repo)
        graft_path = write_graft(graft_repo, c5)
        output["legs"]["C_info_grafts_overlay"] = {
            "walker": walker_answer(graft_repo, c1, head),
            "raw": raw_reachability(graft_repo, c1, head),
            "graft_path": graft_path,
        }

        changing_repo = os.path.join(temp_root, "changing")
        shutil.copytree(baseline, changing_repo)

        def add_replace_during_traversal():
            run(["replace", "--graft", c5], changing_repo)

        output["legs"]["D_overlay_changes_between_raw_reads"] = {
            "raw": raw_reachability(
                changing_repo,
                c1,
                head,
                after_first_read=add_replace_during_traversal,
            ),
            "walker_after_change": walker_answer(changing_repo, c1, head),
            "replace_count_after_change": len(
                text(run(["replace", "-l"], changing_repo)).splitlines()
            ),
        }

        shallow_repo = os.path.join(temp_root, "shallow")
        run(["clone", "-q", "--depth", "3", file_url(baseline), shallow_repo], temp_root)
        # Put both queried endpoints in the bounded reader without connecting them.
        # This is the shape in which merge-base returns a confident rc=1 while the
        # missing middle history means the correct three-valued answer is UNKNOWN.
        run(
            ["fetch", "-q", "--depth", "1", file_url(baseline), c1],
            shallow_repo,
        )
        output["legs"]["E_shallow_missing_parent"] = {
            "is_shallow": text(
                run(["rev-parse", "--is-shallow-repository"], shallow_repo)
            ),
            "walker": walker_answer(shallow_repo, c1, head),
            "raw": raw_reachability(shallow_repo, c1, head),
        }

        expected = {
            "A_baseline": ("TRUE", "TRUE"),
            "B_replace_overlay": ("FALSE", "TRUE"),
            "C_info_grafts_overlay": ("FALSE", "TRUE"),
            "D_overlay_changes_between_raw_reads": ("FALSE", "TRUE"),
            "E_shallow_missing_parent": ("FALSE", "UNKNOWN"),
        }
        observed = {
            "A_baseline": (
                output["legs"]["A_baseline"]["walker"],
                output["legs"]["A_baseline"]["raw"]["answer"],
            ),
            "B_replace_overlay": (
                output["legs"]["B_replace_overlay"]["walker"],
                output["legs"]["B_replace_overlay"]["raw"]["answer"],
            ),
            "C_info_grafts_overlay": (
                output["legs"]["C_info_grafts_overlay"]["walker"],
                output["legs"]["C_info_grafts_overlay"]["raw"]["answer"],
            ),
            "D_overlay_changes_between_raw_reads": (
                output["legs"]["D_overlay_changes_between_raw_reads"]["walker_after_change"],
                output["legs"]["D_overlay_changes_between_raw_reads"]["raw"]["answer"],
            ),
            "E_shallow_missing_parent": (
                output["legs"]["E_shallow_missing_parent"]["walker"],
                output["legs"]["E_shallow_missing_parent"]["raw"]["answer"],
            ),
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
