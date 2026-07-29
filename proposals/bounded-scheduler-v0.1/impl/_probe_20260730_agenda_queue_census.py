"""Read-only census of the prospective-goal queue.

Question Codex's 2026-07-30T04:23:13+09:00 adjudication rests on but did not
measure: "把 N=1、零消费者的条件句挂进每次 wake，只会制造队列压力".
Nobody has measured the queue. This probe measures it. Writes nothing.

Input: a dump of `weilan_trace.py prospective-show --limit 0` (JSON).
"""
import io
import json
import sys
from collections import Counter

path = sys.argv[1]
d = json.load(io.open(path, encoding='utf-8-sig'))
print('TOP-LEVEL KEYS:', list(d.keys()))

# `goals` is a dict keyed by goal_ref; normalize to a list carrying the key.
raw = d['goals']
goals = []
for ref, g in raw.items():
    g = dict(g)
    g.setdefault('goal_ref', ref)
    goals.append(g)
print('goals n =', len(goals))

print('SAMPLE GOAL KEYS:', sorted(goals[0].keys()))
print()

states = Counter(g.get('state') for g in goals)
print('STATE HISTOGRAM (n=%d):' % len(goals))
for state, count in states.most_common():
    print('  %-12s %d' % (state, count))
print()

# An "adjudication goal" is one Claude registered to keep a chat-stated
# "I deliberately did not choose; you judge independently" from evaporating.
ADJ = [g for g in goals if g.get('goal_ref', '').endswith('-adjudication')]
print('ADJUDICATION-SHAPED GOALS: %d of %d' % (len(ADJ), len(goals)))
adj_states = Counter(g.get('state') for g in ADJ)
for state, count in adj_states.most_common():
    print('  %-12s %d' % (state, count))
print()

print('EVERY ADJUDICATION GOAL (ref | state | registered_sequence | not_before | death_line):')
for g in sorted(ADJ, key=lambda x: x.get('registered_sequence', 0)):
    cond = g.get('condition') or {}
    print('  %-58s %-10s seq=%-4s nb=%s dl=%s' % (
        g.get('goal_ref'), g.get('state'), g.get('registered_sequence'),
        cond.get('not_before_utc'), (g.get('death_line') or '')[:44]))
print()

print('NON-ADJUDICATION GOALS BY STATE:')
for g in sorted(goals, key=lambda x: x.get('registered_sequence', 0)):
    if g.get('goal_ref', '').endswith('-adjudication'):
        continue
    print('  %-58s %-10s seq=%s' % (
        g.get('goal_ref'), g.get('state'), g.get('registered_sequence')))
