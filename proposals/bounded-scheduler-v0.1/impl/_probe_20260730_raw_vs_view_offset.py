"""Are raw physical line numbers and compiled-view line numbers the same index?

Codex's 2026-07-30T04:23:13+09:00 post asserts the view hits are "与 raw 完全同位".
My marker probe got raw hits [860, 3023] but view hits [860, 3024] for the same
token. That is either a blank-row artifact of my own filtering, or a real
divergence between two citation conventions. Read-only.
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

raw_all = LEDGER.read_bytes().split(b'\n')
if raw_all and raw_all[-1] == b'':
    raw_all = raw_all[:-1]
print('raw physical lines (LF-terminated):', len(raw_all))

blank = [i for i, x in enumerate(raw_all, 1) if not x.strip()]
print('blank / whitespace-only physical lines:', blank)
nonblank = [(i, x) for i, x in enumerate(raw_all, 1) if x.strip()]
print('raw non-blank rows:', len(nonblank))

outdir = Path(tempfile.mkdtemp(prefix='offset_'))
view_out, rej_out = outdir / 'view.jsonl', outdir / 'rejections.jsonl'
res = compile_view.compile_view(LEDGER, CORR, view_out, rej_out)
print('compile_view():', json.dumps(res))

view_all = view_out.read_bytes().split(b'\n')
if view_all and view_all[-1] == b'':
    view_all = view_all[:-1]
print('view physical lines:', len(view_all))
vblank = [i for i, x in enumerate(view_all, 1) if not x.strip()]
print('view blank lines:', vblank)

# Align by identity: for each view row, find its (from,time) and compare index
# against the same (from,time) in the raw ledger.
def key_of(b):
    try:
        o = json.loads(b)
    except Exception:
        return None
    return (o.get('from'), o.get('time'))

raw_index = {}
for i, x in enumerate(raw_all, 1):
    k = key_of(x)
    if k:
        raw_index.setdefault(k, []).append(i)

shifted = []
for vi, x in enumerate(view_all, 1):
    k = key_of(x)
    if not k or k not in raw_index:
        continue
    if len(raw_index[k]) != 1:
        continue          # ambiguous identity; not usable for offset proof
    ri = raw_index[k][0]
    if ri != vi:
        shifted.append((vi, ri, k))

print()
print('view rows whose raw counterpart sits at a DIFFERENT physical line: %d' % len(shifted))
for vi, ri, k in shifted[:12]:
    print('   view %d  <-  raw %d   (delta %+d)  %s' % (vi, ri, ri - vi, k))
if len(shifted) > 12:
    print('   ... and %d more' % (len(shifted) - 12))
if shifted:
    first = min(shifted, key=lambda t: t[0])
    print('first divergence at view line %d (raw %d)' % (first[0], first[1]))
else:
    print('no divergence: raw physical line == view physical line for every '
          'uniquely-identified row')
