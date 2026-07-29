"""Correction to probe 2's last measurement.

probe2 compared view line 3017 against my own json.dumps re-serialization, not
against compile_view's canonical() form -- so its `line_3017_identical_in_view`
result measured my serializer, not the tool. Redone semantically here.
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

spec = importlib.util.spec_from_file_location("compile_view_probe3", CV_PATH)
CV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CV)

tmp = Path(tempfile.mkdtemp(prefix="weilan_probe3_"))
view = tmp / "view.jsonl"
CV.compile_view(RAW, CORR, view, tmp / "rej.jsonl")

raw_lines = RAW.read_bytes().splitlines(keepends=True)
view_lines = view.read_bytes().splitlines(keepends=True)

out = {}
for label, n in (("3017_retracted_line", 3017), ("3019_correction_line", 3019)):
    raw_b = CV.line_without_lf(raw_lines[n - 1])
    view_b = CV.line_without_lf(view_lines[n - 1])
    raw_obj = json.loads(raw_b.decode("utf-8"))
    view_obj = json.loads(view_b.decode("utf-8"))
    out[label] = {
        "bytes_equal": raw_b == view_b,
        "objects_equal": raw_obj == view_obj,
        "view_is_canonical_of_raw": view_b == CV.canonical(raw_obj),
        "view_has_corrected_from": "_corrected_from" in view_obj,
        "view_has_correction_reason": "_correction_reason" in view_obj,
        "from": view_obj.get("from"),
        "time": view_obj.get("time"),
    }

# how many view lines carry any applied-correction marker at all?
applied_markers = sum(
    1 for line in view_lines
    if b'"_corrected_from"' in CV.line_without_lf(line)
)
out["view_lines_with_corrected_from_marker"] = applied_markers
out["tmp_dir"] = str(tmp)
print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
