"""Read-only probe: what does any REAL entrypoint expose about the withdrawal-link
correction record?

Codex (peer-chat 2026-07-30T03:58:39+09:00) narrowed his claim to:
  "record_kind will put explicit kind=withdrawal-link into meta_visible;
   but it only exposes the raw record, does not follow replacement_ref."

This probe tests that at three levels, without writing anything into the repo:
  L0  private  _load_corrections(...)      -> does the entry land in meta_visible?
  L1  public   compile_view(...)           -> what does the returned summary carry?
  L2  CLI      python compile_view.py ...  -> what does stdout carry?

view/rejections outputs are redirected to a temp dir so the ledger's siblings
are untouched.
"""

from __future__ import annotations

import io
import json
import contextlib
import importlib.util
import tempfile
from pathlib import Path

REPO = Path(r"D:\WeilanSkillEvolution")
CV_PATH = REPO / "proposals" / "lineage-log-append-only-correction-v0.1" / "compile_view.py"
RAW = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.jsonl"
CORR = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.corrections.jsonl"

spec = importlib.util.spec_from_file_location("compile_view_probe", CV_PATH)
CV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CV)

out: dict = {}
out["module_header_line"] = CV_PATH.read_text(encoding="utf-8").splitlines()[0]

raw_lines = RAW.read_bytes().splitlines(keepends=True)
corr_lines = CORR.read_bytes().splitlines(keepends=True)
out["raw_physical_lines"] = len(raw_lines)
out["corrections_physical_lines"] = len(corr_lines)

# --- which corrections rows carry an explicit kind, per record_kind ------------
kinds = []
for i, pl in enumerate(corr_lines, start=1):
    b = CV.line_without_lf(pl)
    try:
        rec = json.loads(b.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        kinds.append({"line": i, "parse_error": type(exc).__name__})
        continue
    if not isinstance(rec, dict):
        kinds.append({"line": i, "not_object": True})
        continue
    kind, basis = CV.record_kind(rec)
    kinds.append({"line": i, "kind": kind, "basis": basis,
                  "corrects": rec.get("corrects")})
out["corrections_kinds"] = kinds
out["kind_histogram"] = {}
for k in kinds:
    key = k.get("kind", "<unparsed>")
    out["kind_histogram"][key] = out["kind_histogram"].get(key, 0) + 1

# --- L0: private _load_corrections ------------------------------------------
index = CV.build_line_index(raw_lines)
accepted, rejected, meta_visible = CV._load_corrections(CORR, index)
out["L0_private"] = {
    "accepted": len(accepted),
    "rejected": len(rejected),
    "meta_visible": len(meta_visible),
    "meta_visible_kinds": sorted({m["kind"] for m in meta_visible}),
    "withdrawal_link_entries": [
        {"kind": m["kind"], "basis": m["basis"],
         "raw_prefix": m["correction_raw"][:120]}
        for m in meta_visible if m["kind"] == "withdrawal-link"
    ],
}
# does the exposed dict carry anything beyond basis/correction_raw/kind?
out["L0_private"]["meta_visible_item_keys"] = (
    sorted(meta_visible[0].keys()) if meta_visible else []
)

# --- L1: public compile_view() ----------------------------------------------
tmp = Path(tempfile.mkdtemp(prefix="weilan_probe_"))
summary = CV.compile_view(RAW, CORR, tmp / "view.jsonl", tmp / "rejections.jsonl")
out["L1_public_summary"] = summary
out["L1_summary_value_types"] = {k: type(v).__name__ for k, v in summary.items()}

# does any written artifact mention the withdrawal-link record?
needle = "withdrawal-link"
out["L1_written_artifacts_mentioning_withdrawal_link"] = {
    "view.jsonl": needle in (tmp / "view.jsonl").read_text(encoding="utf-8",
                                                           errors="replace"),
    "rejections.jsonl": needle in (tmp / "rejections.jsonl").read_text(
        encoding="utf-8", errors="replace"),
}

# --- L2: CLI main() ----------------------------------------------------------
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = CV.main([str(RAW), "--corrections", str(CORR),
                  "--view", str(tmp / "view2.jsonl"),
                  "--rejections", str(tmp / "rej2.jsonl")])
out["L2_cli"] = {"rc": rc, "stdout": buf.getvalue().strip()}
out["L2_stdout_mentions_withdrawal_link"] = needle in buf.getvalue()

out["tmp_dir"] = str(tmp)
print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
