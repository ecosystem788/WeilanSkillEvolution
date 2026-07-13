# WeiLan Skill Evolution Architecture

> 2026-07-11 起本文件为**工程指引**(非授权闸),依 CHARTER.md 治理;社区可双签修订,观察员可否决。


## Purpose

This project evolves the global WeiLan problem-solving Skill without allowing the candidate Skill to control its own roadmap, evaluation, adoption, or rollback.

The existing deployed system is frozen as **WeiLan Memory Runtime 0.7**. Its version number describes the supporting runtime only. It does not establish completion of **Skill Evolution SE-0.7**.

## Causal core and clock boundary

Frame continuity is causal, not wall-clock based:

```text
user / tool / file change / authorized clock trigger
                         -> event
                         -> causal Frame transition
```

No event means no new Frame is required. A clock may satisfy a prospective-memory condition and inject an event, but it does not create synthetic consciousness, empty Frames, or action authority.

## Four planes

### Memory Plane

Owns episodic events, conversation evidence, semantic memory, indexes, projections, source freshness, and archival. It provides evidence and recall, never action authority.

### Control Plane

Owns user authorization, active scope, goals, feedback pressure, holder eligibility, collapse, and re-entry conditions. It may govern action but may not rewrite evidence.

### Execution Plane

Owns bounded transactions, idempotency, receipts, recovery, and foreground execution. It may materialize an authorized decision but may not select or approve one.

### Evolution Plane

Owns Skill proposals, fixed evaluations, baseline/candidate shadow comparison, adoption, rejection, and rollback. A candidate cannot modify this plane's authority artifacts.

## Source and deployment topology

```text
D:\WeilanSkillEvolution
  canonical roadmap + evaluation authority + frozen baseline + candidates

D:\CodexData\skills\solve-with-weilan
  currently deployed runtime; read-only until explicit adoption

D:\CodexData\home\method-state
  operational evidence, control, projections, and receipts
```

The project repository becomes the source of truth for evolution work. Deployment remains a separate explicit operation. Copying, testing, or proposing a candidate does not change the installed Skill.

## Evolution transaction

```text
source evidence
-> bounded proposal
-> immutable candidate artifact
-> baseline/candidate shadow evaluation
-> evidence comparison
-> explicit adopt or reject
-> reversible deployment receipt
-> monitored result
-> keep or rollback
```

Every transition is bounded by scope, budget, accepted file paths, evaluation manifest hash, and stop conditions.

## Non-goals

- No autonomous modification of roadmap or evaluation authority.
- No direct self-edit of the deployed Skill.
- No wall-clock heartbeat pretending to be Frame continuity.
- No unbounded proposal or evaluation loop.
- No claim that the existing Memory Runtime already constitutes Skill self-evolution.
