"""Independent re-run of compile_view against the current 3025-line ledger.

Does not trust Codex's 2026-07-30T04:23:13+09:00 receipt (measured at 3024
lines). Recomputes: public return shape, whether the two thread-relevant rows
(the withdrawn one and its prose correction) are still uniquely hash-matched,
and whether either carries a correction marker in the compiled view.
Writes nothing outside a temp dir it owns.
"""
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r'D:\WeilanSkillEvolution\proposals\lineage-log-append-only-correction-v0.1')
import compile_view  # noqa: E402

LEDGER = Path(r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl')
CORR = Path(r'D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.corrections.jsonl')

BEFORE = '78db0a52'   # prefix of the withdrawn row's no-LF sha256 (from 03:52 probe)
AFTER = '7840543f'    # prefix of the replacement row's no-LF sha256

raw_bytes = LEDGER.read_bytes()
print('ledger bytes=%d  lf=%d  cr=%d' % (
    len(raw_bytes), raw_bytes.count(b'\n'), raw_bytes.count(b'\r')))

# Per-physical-line no-LF sha256, the convention the sidecar binds with.
hits_before, hits_after = [], []
with io.open(LEDGER, 'rb') as fh:
    for i, line in enumerate(fh, 1):
        h = hashlib.sha256(line[:-1] if line.endswith(b'\n') else line).hexdigest()
        if h.startswith(BEFORE):
            hits_before.append((i, h))
        if h.startswith(AFTER):
            hits_after.append((i, h))
print('before_hash hits:', hits_before)
print('after_hash  hits:', hits_after)

outdir = Path(tempfile.mkdtemp(prefix='cvrerun_'))
view_out = outdir / 'view.jsonl'
rej_out = outdir / 'rejections.jsonl'
result = compile_view.compile_view(LEDGER, CORR, view_out, rej_out)
print('compile_view() returned:', json.dumps(result, ensure_ascii=False))
print('return value types:', {k: type(v).__name__ for k, v in result.items()})

view_path = outdir / 'view.jsonl'
rej_path = outdir / 'rejections.jsonl'
view_lines = view_path.read_bytes().split(b'\n')
view_lines = [x for x in view_lines if x.strip()]
print('view.jsonl lines=%d' % len(view_lines))

marker_rows = [i for i, x in enumerate(view_lines, 1) if b'_corrected_from' in x]
print('rows carrying _corrected_from marker:', marker_rows)

wl_rows = [i for i, x in enumerate(view_lines, 1) if b'withdrawal-link' in x]
print('rows containing the string "withdrawal-link":', wl_rows)
for i in wl_rows:
    obj = json.loads(view_lines[i - 1])
    print('   view line %d  from=%s time=%s  (is it a correction record? %s)' % (
        i, obj.get('from'), obj.get('time'), '_corrected_from' in obj))

rej_txt = rej_path.read_bytes() if rej_path.exists() else b''
print('rejections.jsonl mentions withdrawal-link:', b'withdrawal-link' in rej_txt)

# The two rows of interest, as the compiled view renders them.
for label, hits in (('withdrawn(3017)', hits_before), ('replacement(3019)', hits_after)):
    if len(hits) != 1:
        print('%s: NOT uniquely matched (n=%d) -- binding would be void' % (label, len(hits)))
        continue
    n = hits[0][0]
    obj = json.loads(view_lines[n - 1])
    print('%s -> view line %d: _corrected_from=%s  _correction_reason=%s' % (
        label, n, '_corrected_from' in obj, '_correction_reason' in obj))
print('temp outdir:', outdir)
