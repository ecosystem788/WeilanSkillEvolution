"""Second half of the queue census: HOW do adjudication goals leave the queue?

A queue that drains by decision and a queue that drains by rot look identical
in a state histogram. This separates them by reading each terminal goal's own
transition_reason. Read-only.
"""
import io
import json
import sys

d = json.load(io.open(sys.argv[1], encoding='utf-8-sig'))
goals = []
for ref, g in d['goals'].items():
    g = dict(g)
    g.setdefault('goal_ref', ref)
    goals.append(g)

ADJ = [g for g in goals if g.get('goal_ref', '').endswith('-adjudication')]

print('=== TERMINAL ADJUDICATION GOALS: why did each leave the queue? ===')
for g in sorted(ADJ, key=lambda x: x.get('registered_sequence', 0)):
    if g.get('state') == 'ACTIVE':
        continue
    print('--- %s  [%s]  seq=%s' % (g['goal_ref'], g['state'], g.get('registered_sequence')))
    print('    replacement_goal_ref:', g.get('replacement_goal_ref'))
    print('    causal_event_id:', g.get('causal_event_id'))
    print('    transition_reason:', (g.get('transition_reason') or '(none)'))
    print()

print('=== ACTIVE ADJUDICATION GOALS: when does each become eligible? ===')
buckets = {}
for g in ADJ:
    if g.get('state') != 'ACTIVE':
        continue
    nb = (g.get('condition') or {}).get('not_before_utc')
    buckets.setdefault(nb, []).append(g['goal_ref'])
for nb in sorted(buckets):
    print('  %s  ->  %d goal(s)' % (nb, len(buckets[nb])))
    for ref in buckets[nb]:
        print('        ', ref)

print()
print('=== SAME QUESTION FOR NON-ADJUDICATION TERMINAL GOALS (control group) ===')
for g in sorted(goals, key=lambda x: x.get('registered_sequence', 0)):
    if g.get('goal_ref', '').endswith('-adjudication') or g.get('state') == 'ACTIVE':
        continue
    reason = (g.get('transition_reason') or '(none)').replace('\n', ' ')
    print('  %-52s %-10s %s' % (g['goal_ref'], g['state'], reason[:150]))
