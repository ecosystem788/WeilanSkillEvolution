"""Follow-up read-only probe: WHY does the compiled view mention "withdrawal-link"?

Probe 1 found L1_written_artifacts_mentioning_withdrawal_link["view.jsonl"] == True
while applied == 0. If the hit comes from chat prose rather than from an applied
correction, then a grep-based reader of the compiled view gets the right hit for
the wrong reason -- the same homomorphic-masking shape we have been tracking.
"""

from __future__ import annotations

import json
import importlib.util
import tempfile
from pathlib import Path

REPO = Path(r"D:\WeilanSkillEvolution")
CV_PATH = REPO / "proposals" / "lineage-log-append-only-correction-v0.1" / "compile_view.py"
RAW = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.jsonl"
CORR = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.corrections.jsonl"

spec = importlib.util.spec_from_file_location("compile_view_probe2", CV_PATH)
CV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CV)

tmp = Path(tempfile.mkdtemp(prefix="weilan_probe2_"))
view = tmp / "view.jsonl"
summary = CV.compile_view(RAW, CORR, view, tmp / "rej.jsonl")

needle = "withdrawal-link"
hits = []
for i, line in enumerate(view.read_text(encoding="utf-8", errors="replace").splitlines(),
                         start=1):
    if needle not in line:
        continue
    try:
        rec = json.loads(line)
    except Exception:
        rec = {}
    hits.append({
        "view_line": i,
        "from": rec.get("from"),
        "time": rec.get("time"),
        "has_corrected_from_marker": "_corrected_from" in rec,
        "needle_in_text_field": needle in str(rec.get("text", "")),
        "top_level_kind_field": rec.get("kind"),
    })

out = {
    "summary": summary,
    "view_hits_for_withdrawal_link": hits,
    "hits_that_are_applied_corrections": sum(
        1 for h in hits if h["has_corrected_from_marker"]),
    "hits_that_are_merely_chat_prose": sum(
        1 for h in hits if h["needle_in_text_field"] and not h["has_corrected_from_marker"]),
    # is the target line 3017 changed at all in the view?
    "line_3017_identical_in_view": (
        CV.line_without_lf(RAW.read_bytes().splitlines(keepends=True)[3016])
        == json.dumps(json.loads(view.read_text(encoding="utf-8").splitlines()[3016]),
                      ensure_ascii=False).encode("utf-8")
    ),
    "tmp_dir": str(tmp),
}
print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
