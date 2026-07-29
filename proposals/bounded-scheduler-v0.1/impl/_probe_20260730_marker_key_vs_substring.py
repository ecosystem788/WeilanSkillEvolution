"""Does `_corrected_from` appear as a JSON KEY, or only inside our prose?

My 2026-07-30T04:11:35+09:00 chat post reported "_corrected_from marker hits 0".
A byte-substring scan of the freshly compiled view now returns 2 rows. This
separates the two readings. Read-only.
"""
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r'D:\WeilanSkillEvolution\proposals\lineage-log-append-only-correction-v0.1')
import compile_view  # noqa: E402

LEDGER = Path(r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl')
CORR = Path(r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.corrections.jsonl')

outdir = Path(tempfile.mkdtemp(prefix='markerchk_'))
view_out, rej_out = outdir / 'view.jsonl', outdir / 'rejections.jsonl'
print('compile_view():', json.dumps(compile_view.compile_view(LEDGER, CORR, view_out, rej_out)))

rows = [x for x in view_out.read_bytes().split(b'\n') if x.strip()]
print('view rows:', len(rows))

as_key, as_text = [], []
for i, raw in enumerate(rows, 1):
    if b'_corrected_from' not in raw:
        continue
    obj = json.loads(raw)
    (as_key if '_corrected_from' in obj else as_text).append((i, obj))

print()
print('ROWS WHERE _corrected_from IS A REAL TOP-LEVEL KEY: %d' % len(as_key))
for i, obj in as_key:
    print('   view line %d  from=%s time=%s  _corrected_from=%r' % (
        i, obj.get('from'), obj.get('time'), obj.get('_corrected_from')))

print()
print('ROWS WHERE IT ONLY OCCURS INSIDE FIELD VALUES (decoys): %d' % len(as_text))
for i, obj in as_text:
    where = [k for k, v in obj.items() if isinstance(v, str) and '_corrected_from' in v]
    print('   view line %d  from=%s time=%s  occurs in fields=%s' % (
        i, obj.get('from'), obj.get('time'), where))

# Same split for the raw ledger, so the decoy count is attributable.
raw_rows = [x for x in LEDGER.read_bytes().split(b'\n') if x.strip()]
raw_hits = [i for i, x in enumerate(raw_rows, 1) if b'_corrected_from' in x]
print()
print('raw ledger substring hits:', raw_hits)
print('=> substring scan and key scan disagree by %d row(s)' % len(as_text))
