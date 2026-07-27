# The census counts only the LOUD half (lines that fail to parse). This samples
# the SILENT half: rows that parse fine but whose text is mojibake -- valid
# JSON, correct "type", garbage content, no error signal anywhere.
#
# Three buckets, because "not cleanly reversible" is NOT "not corrupted":
#   clean        : round-trips gbk->utf-8 back to itself; genuinely intact
#   reversible   : gbk->utf-8 recovers real text; corrupted but salvageable
#   irreversible : cannot round-trip at all (lost bytes / U+E000-range debris
#                  left by the lossy decode) -- corrupted AND unsalvageable
# A first cut of this probe called `irreversible` clean and halved the damage.
import json
from pathlib import Path

ROOT = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\wake-codex-runs")
runs = sorted(ROOT.glob("*.jsonl"))
sample = runs[:: max(1, len(runs) // 40)][:40]      # even stride across all history

def classify(s):
    try:
        rec = s.encode("gbk").decode("utf-8")
    except Exception:
        return "irreversible"
    return "clean" if rec == s else "reversible"

buckets = {"clean": 0, "reversible": 0, "irreversible": 0}
rows_total = rows_nonascii = 0
files_hit = 0
for p in sample:
    raw = p.read_bytes()
    text = raw.decode("utf-16") if raw.startswith(b"\xff\xfe") else raw.decode("utf-8", "replace")
    hit = False
    for line in text.splitlines():
        if not line.strip(): continue
        try: row = json.loads(line)
        except Exception: continue
        rows_total += 1
        blob = json.dumps(row, ensure_ascii=False)
        if blob.isascii(): continue
        rows_nonascii += 1
        verdict = classify(blob)
        buckets[verdict] += 1
        if verdict != "clean": hit = True
    files_hit += 1 if hit else 0

print("sampled runs                 :", len(sample), "of", len(runs))
print("parseable rows in sample     :", rows_total)
print("  of which carry non-ASCII   :", rows_nonascii)
for k in ("clean", "reversible", "irreversible"):
    print("    %-13s: %4d  (%.1f%% of non-ASCII rows)"
          % (k, buckets[k], 100 * buckets[k] / max(rows_nonascii, 1)))
print("sampled runs with >=1 silently corrupted row:", files_hit, "/", len(sample))
