#!/usr/bin/env python3
"""Read-only: isolate the '...' path component failure in cited_artifact_receipt_check.

Claim under test: a cited path containing a dot-run component (e.g. "a/.../b.py") makes
_classify raise CheckError('invalid_path', 'path escapes root'), which in main() aborts
the WHOLE bucket check with rc=2 -- not merely skipping that one citation. The diagnosis
text is also wrong: nothing escapes root; Windows strips trailing dots from a path
component, so Path.resolve() returns an extended-length ('\\\\?\\') form that
relative_to() then rejects.
"""
from __future__ import annotations

import io
import json
from pathlib import Path, PurePosixPath
import sys

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
REPO = Path(r"D:\WeilanSkillEvolution")
sys.path.insert(0, str(IMPL))

import cited_artifact_receipt_check as gate  # noqa: E402


def main() -> int:
    sample = "proposals/fusion-dogfood-extension-v0.3/.../wf-20260705-085147-66482d.jsonl"
    out: dict[str, object] = {
        "probe": "ellipsis_component",
        "authority": "read_only_report",
        "sample": sample,
    }

    # 1. the regex + guard let it through
    out["extracted_by_cited_paths"] = gate.cited_paths(f"see {sample} for detail")
    parts = PurePosixPath(sample).parts
    out["parts"] = list(parts)
    out["guard_rejects_dot_and_dotdot_only"] = [p for p in parts if p in ("", ".", "..")]

    # 2. what Windows actually does to the component
    joined = REPO / Path(*parts)
    out["joined"] = str(joined)
    out["resolved"] = str(joined.resolve())
    out["resolved_is_extended_length"] = str(joined.resolve()).startswith("\\\\?\\")
    out["path_length"] = len(str(joined))

    # 3. _classify's actual behaviour
    tracked: set[str] = set()
    historical: set[str] = set()
    try:
        out["classify"] = gate._classify(
            root=REPO.resolve(), path=sample, tracked=tracked, historical=historical
        )
    except gate.CheckError as exc:
        out["classify_raised"] = {"reason": exc.reason, "detail": exc.detail}

    # 4. does a plain long path (no dot-run) also trip it? -- separates the two causes
    deep = "proposals/" + "/".join(["averylongdirectorysegmentname"] * 9) + "/x.py"
    deep_joined = REPO / Path(*PurePosixPath(deep).parts)
    out["control_long_path_length"] = len(str(deep_joined))
    out["control_long_path_resolved_extended"] = str(deep_joined.resolve()).startswith("\\\\?\\")
    try:
        out["control_long_path_classify"] = gate._classify(
            root=REPO.resolve(), path=deep, tracked=tracked, historical=historical
        )
    except gate.CheckError as exc:
        out["control_long_path_raised"] = {"reason": exc.reason, "detail": exc.detail}

    # 5. whole-bucket blast radius: does one bad citation kill the other citations?
    #    simulate check_bucket's loop contract without touching the ledger.
    good = "proposals/bounded-scheduler-v0.1/impl/append_clocked_jsonl.py"
    text = f"good {good} and elided {sample}"
    out["citations_in_mixed_text"] = gate.cited_paths(text)
    aborted = False
    classified: list[tuple[str, str]] = []
    try:
        for path in gate.cited_paths(text):
            classified.append(
                (path, gate._classify(root=REPO.resolve(), path=path,
                                      tracked=gate._git_lines(REPO, "ls-files"),
                                      historical=set()))
            )
    except gate.CheckError as exc:
        aborted = True
        out["mixed_text_abort"] = {"reason": exc.reason, "after_n_ok": len(classified)}
    out["mixed_text_aborted_whole_bucket"] = aborted

    # 6. is such a citation actually present in the live ledger?
    rows, _errors = gate._ledger_rows(IMPL / "peer-chat.jsonl")
    hits = []
    for line_number, _raw, record in rows:
        for path in gate.cited_paths(record.get("text")):
            if any(set(part) == {"."} and len(part) > 2 for part in PurePosixPath(path).parts):
                hits.append(
                    {
                        "physical_line": line_number,
                        "from": record.get("from"),
                        "time": record.get("time"),
                        "path": path,
                    }
                )
    out["live_ledger_dot_run_citations"] = hits
    out["live_ledger_dot_run_count"] = len(hits)

    io.open(
        r"D:\WeilanSkillEvolution\proposals\cited-artifact-clone-reachability-v0.1\_probe_20260801_ellipsis_component.out.json",
        "w",
        encoding="utf-8",
    ).write(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
