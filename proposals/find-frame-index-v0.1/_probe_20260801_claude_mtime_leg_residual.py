"""Read-only: measure the guard's mtime leg in isolation, at its natural rate.

Why this probe exists. My re-run of the load-bearing equivalence probe found the
foreign-second-file scenario now agreeing with the baseline 25/25, with no sleep
anywhere. That number is true and it is misleading, and the difference matters
more than the number does.

The guard has two legs: it compares the SET of date-directory names and it
compares each directory's mtime. Equivalence scenario 9 writes its first file to
2026-07-20 and its second to 2026-07-21, and the temp ledger starts empty -- so
the second write CREATES a directory. A new key in the map is a mismatch no
matter what the mtime grain is. Scenario 9 therefore exercises the name-set leg
and never reaches the mtime leg. Reading its 25/25 as "the residual is rarer than
measured" would be reading a zero-hit count as a zero-input count.

This probe removes that shortcut. An anchor frame pre-creates the second date
directory, so the foreign write lands in a directory that already exists and the
name set never changes. Only the mtime leg can catch it. No sleep: the two
operations are back-to-back, which is the worst case for a roughly 1 ms grain.

Codex's T2 regression test uses this same shape but sleeps 5 ms on either side of
the foreign write, which is correct for a regression test -- it pins the
guarantee, not the race. This probe is the complement: it drops the sleeps to
find out how often the guarantee's premise actually holds unaided.

Not a defect hunt. The proposal discloses this hole and explicitly does not make
it a rollback trigger. This measures its size.

Writes only inside its own temp directory. Emits JSON to stdout.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

CAND = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
HERE = os.path.dirname(os.path.abspath(__file__))
REPEATS = int(os.environ.get("WEILAN_PROBE_REPEATS", "60"))

EVENT = (
    '{"schema_version": "x", "event_id": "e0", "frame_id": "%s", '
    '"timestamp_utc": "2026-08-01T00:00:00+00:00", "event_type": "frame_opened", '
    '"level": "L2", "workspace": "W", "data": {}}\n'
)


def write_frame(frames_root, date_dir, frame_id):
    directory = os.path.join(frames_root, date_dir)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, frame_id + ".jsonl")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(EVENT % frame_id)
    return path


def child(method_home, repeats):
    sys.path.insert(0, os.environ["WEILAN_PROBE_SCRIPTS"])
    os.environ["WEILAN_METHOD_HOME"] = method_home
    import weilan_trace  # noqa: E402 -- must follow the sys.path/env setup

    frames_root = os.path.join(method_home, "frames")
    os.makedirs(os.path.join(frames_root, "2026-07-20"), exist_ok=True)
    os.makedirs(os.path.join(frames_root, "2026-07-21"), exist_ok=True)
    write_frame(frames_root, "2026-07-21", "wf-anchor")

    outcomes = []
    for index in range(repeats):
        frame_id = "wf-race-%03d" % index
        write_frame(frames_root, "2026-07-20", frame_id)
        weilan_trace.invalidate_frame_index()
        try:
            first = weilan_trace.find_frame(frame_id)
        except Exception as exc:  # noqa: BLE001
            outcomes.append({"stage": "first_lookup", "outcome": type(exc).__name__})
            continue
        # Foreign write into a directory that already exists: the name set is
        # unchanged, so only the mtime comparison can notice this.
        write_frame(frames_root, "2026-07-21", frame_id)
        try:
            weilan_trace.find_frame(frame_id)
            outcomes.append({"stage": "second_lookup", "outcome": "path",
                             "guard_fired": False})
        except RuntimeError:
            outcomes.append({"stage": "second_lookup", "outcome": "RuntimeError",
                             "guard_fired": True})
        except Exception as exc:  # noqa: BLE001
            outcomes.append({"stage": "second_lookup", "outcome": type(exc).__name__,
                             "guard_fired": None})
        assert first  # the first lookup's path is not the observation here
    json.dump(outcomes, sys.stdout, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child")
    args = parser.parse_args()
    if args.child:
        child(args.child, REPEATS)
        return

    scripts = os.path.join(HERE, "artifacts", CAND, "solve-with-weilan", "scripts")
    with tempfile.TemporaryDirectory(prefix="ffi-mtime-leg-") as tmp:
        method_home = os.path.join(tmp, "method-state")
        os.makedirs(method_home, exist_ok=True)
        environment = os.environ.copy()
        environment["WEILAN_PROBE_SCRIPTS"] = scripts
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", os.path.abspath(__file__),
             "--child", method_home],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=environment,
        )
    if proc.returncode != 0:
        json.dump({"child_returncode": proc.returncode,
                   "stderr_tail": proc.stderr.strip()[-800:]},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    outcomes = json.loads(proc.stdout)
    fired = sum(1 for row in outcomes if row.get("guard_fired") is True)
    missed = sum(1 for row in outcomes if row.get("guard_fired") is False)
    result = {
        "probe": "claude_mtime_leg_residual",
        "measured_by": "claude (reviewer, not implementer)",
        "candidate_artifact_hash": CAND,
        "shape": ("anchor frame pre-creates the second date directory, so the "
                  "date-directory name set never changes and only the mtime "
                  "comparison can catch the foreign write; no sleep anywhere"),
        "repeats": len(outcomes),
        "guard_fired_runtime_error": fired,
        "guard_missed_returned_single_path": missed,
        "other": [row for row in outcomes if row.get("guard_fired") is None],
        "miss_fraction": round(missed / len(outcomes), 4) if outcomes else None,
        "reading": ("A nonzero miss count is the disclosed residual at its "
                    "natural rate, not a defect. A zero FIRED count would be the "
                    "defect. Do not generalise this rate: it is one filesystem, "
                    "one machine, one write pattern."),
        "outcomes": outcomes,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
