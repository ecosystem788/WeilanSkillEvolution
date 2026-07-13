# Issue — Frame Lineage Poisoning: repair route and prevention boundary

Status: `reshadow_failed_no_adoption`
Previous status: `shadow_failed_no_adoption` (superseded `shadow_plan_validated_awaiting_real_agent_execution`
2026-07-05: owner delegated fix-design authority to Claude, evidence-capture
`75a0c027-e2b2-4de3-9075-a8d989cdb4d3`; Codex review found the existing `frame-repair`
append-only overlay channel can cure the verified live malformed-event instance; route decision
split immediate authorized live repair from candidate work; owner then authorized the first five
candidate steps for write-path prevention only, and Codex froze candidate artifact
`203b8c1f37ad54abf9e3cdc011ea122a5f8961b26cfd1dea8138549bb997b32c`; owner then authorized live
frame-repair, which completed under repair id `be5f818c-9dc8-42d2-9873-c3b0f1a9604b`, and Codex
diff audit passed)
Date: 2026-07-05

Diagnostic scorer update, 2026-07-05: Claude authored a hidden-aware replacement scorer for
`fusion-dogfood-v0.1`; Codex adversarially reviewed it, added recomputable grader provenance,
froze hashes, and rescored the existing `mwp-shadow-20260705` run as a diagnostic-only record.
Receipt: `SCORER_FREEZE_RECEIPT.md`. Diagnostic mean delta is `0.096875`, but the original gate
outcome remains `shadow_failed_no_adoption`; no adoption, deployment, manifest edit, rubric edit,
or hidden-check mutation is authorized by this diagnostic record.

Fresh re-shadow update, 2026-07-05: after targeted UTF-8 console-output deployment
`cbfe4af9af792d7bcf719113aaf95d1f04a5b12cd946b0bfde3f9d4e5320215c`, Codex bound
`RESHADOW_PREREG.md` to that deployed baseline and ran 24 fresh real-agent executions under
`shadow/runs/mwp-reshadow-cbfe4af9-20260705/`. Frozen-scorer result hash:
`635f5c5958a8e54fa51de13995336908e62d4d7e4a6f06f2215d9d56599d5d96`; gate wrapper:
`RESHADOW_GATE_RESULT.json`. Result: `reshadow_failed_no_adoption`, mean delta `-0.110937`,
with fixed-case negative regressions on `fusion-p2-instrument-noise-recovery`,
`fusion-s0-env-probe-attribution`, and `fusion-scope-redirection-to-eval-proposal`.
No adoption, deployment, rollback, manifest edit, rubric edit, hidden-check edit, or candidate edit
is authorized.
Author: Claude (spec/review role). A live `frame-repair` overlay would touch
`D:\CodexData\home\method-state` and requires separate owner authorization. Any candidate Skill
behavior change touches `weilan_trace.py` and is therefore a **method-behavior change**: it must
go through the normal proposal → shadow → owner-adoption channel (SE-0.6 discipline), not the
targeted deployment channel. Filing this issue changes nothing outside `proposals/` and
`LOCAL_STATUS.md`.

## 1. Defect statement

Frame lineage validation requires a causal parent frame to be *fully* schema-valid. One malformed
event can therefore poison a branch head until a sanctioned append-only disposition is applied.
Initial filing missed that deployed `49e656d2…` already has a `frame-repair` overlay channel:
`read_events()` applies repair overlays before `assert_closed_parent()` validates a causal parent.

Revised defect boundary:

- The verified live malformed-event instance is repairable by existing `frame-repair`; it still
  requires separate owner authorization because it touches live method-state.
- Prevention remains incomplete unless every frame-event write path is proven to run full
  validation before appending.
- A new graft relation is only justified for poison shapes that `frame-repair` cannot cure, such
  as missing or unreadable frame files.

## 2. Mechanism (verified in deployed Skill code)

All references are to `scripts/weilan_trace.py` in the deployed Skill (inspected copy:
`C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py`; deployed artifact
`49e656d2…` at `D:\CodexData\skills\solve-with-weilan`):

- `REQUIRED_EVENT_FIELDS["trace_emitted"]` (lines 177–183) requires `once_reasonable`,
  `invalidating_evidence`, `reusable_results`, `forbidden_assumption`, `reentry_condition`.
- `assert_closed_parent` (lines 481–496) replays the parent frame's **entire** event stream
  through `validate_events(..., require_closed=True)`; any validation error anywhere in the
  stream rejects the parent ("causal parent frame is invalid").
- `command_open_lineaged_fenced`: `continue` requires the parent to equal the active branch head
  (lines 530–542); `fork` requires the parent to be an active branch head (lines 543–554);
  `root` requires an empty lineage (lines 527–529). So a poisoned branch head is unreachable by
  every relation, and no other frame can substitute.
- Frame event files are strictly append-only (project-wide discipline). There is no event-level
  retraction, supersession, or void marker, but deployed `49e656d2…` does have a separate
  append-only `frame-repair` overlay channel for parseable event-data malformations.

Secondary observation (prevention side, distinct from the repair side): the malformed event got
*written* despite the field requirements, i.e. required-field validation is enforced at
read/lineage time but may not be uniformly enforced before append on every frame-event write path.
Preventing new poison does not cure the already-written live poison; the existing `frame-repair`
channel is the current cure route for this parseable malformation.

Correction after Codex review: a metabolism channel already exists for parseable frame-event data
malformations. `frame-repair` appends `weilan_frame_repair_v0.1` overlays under
`memory/frame-repairs/<frame_id>.jsonl`; `read_events()` applies those overlays; and
`assert_closed_parent()` consumes `read_events()`. In an isolated dry-run, adding the five missing
`trace_emitted` fields through `frame-repair` made `wf-20260704-145514-4ac09e` validate with
`--require-closed`.

## 3. Verified live instance

- File: `D:\CodexData\home\method-state\frames\2026-07-04\wf-20260704-145514-4ac09e.jsonl`,
  line 5: a `trace_emitted` event whose `data` contains a single stray key
  (`"EXP-9 frozen at spec sha256"`) and **none** of the five required fields.
- The frame is `relation: continue`, `branch_id: main`, scope `fusion-program`, workspace
  `D:\weilan-llm-fusion` — i.e. it is the recorded head of that scope's main branch.
- Consequence already materialized: subsequent frames
  `wf-20260705-003116-946812` and `wf-20260705-032827-46ec05` (2026-07-05) were opened with
  `causal: null` (standalone, no lineage) and their `problem` text explicitly records that
  `continue`/`fork`/`root` were rejected because the branch head's `trace_emitted` is missing
  required fields. The fusion-program lineage is severed as of those frames.

## 4. Candidate / repair directions

All directions obey the core principle: **never rewrite history; dispose by appending**, the same
idea as ledger metabolism.

- (0) **Existing frame-repair overlay**: repair the current malformed `trace_emitted` by appending
  five missing fields through `frame-repair`. This is not a Skill candidate; it is live
  method-state repair and requires separate owner authorization.
- (1) **Write-path prevention**: verify and harden every frame-event append path so malformed
  lifecycle events fail before anything is written. This is a candidate Skill behavior change if a
  bypass is found.

- (2) **Append-only isolation event**: a new event/record type marks a specific malformed event
  as `void` (with authority, reason, and evidence). Validators skip voided events when computing
  the containing frame's legality; the poison stays in history, visibly quarantined.
- (3) **Lineage graft**: a new frame explicitly declares a logical parent that bypasses a poisoned
  frame that cannot be repaired by `frame-repair` (for example, a missing or unreadable head),
  recording an auditable graft event that names the bypassed frame and the reason. The poisoned
  frame remains in history as a dead limb.

Open design questions after revision: whether the immediate live repair should be executed through
existing `frame-repair`; whether write-path prevention alone deserves a candidate; and whether a
future graft relation should be scoped only to missing/unreadable frame poison that `frame-repair`
cannot address.

## 5. Theme note

This remains part of the recurring theme "append-only state requires explicit metabolism"; the
revision narrows this case from "no channel exists" to "the existing repair channel must be
recognized, authorized, and complemented by prevention where needed":

1. semantic ledger grow-only accumulation (37 active all-append frames observed in
   fusion-program, disposition/lifecycle all zero — recorded in `wf-20260705-003116-946812`);
2. EXP-8 state-level rigidity (sibling P3 line, `D:\weilan-llm-fusion`);
3. this defect (frame-event level: one bad append blocks lineage until an authorized repair
   overlay is applied).

The pattern suggests the fix should be designed as an instance of a general disposition
principle, not a one-off patch to `assert_closed_parent`.

## 6. Non-goals / boundaries

- No implementation in this issue; no change to the deployed Skill, `evals/manifest.json`,
  frozen suites, or authorization documents.
- The live instance's method-state under `D:\CodexData\home\method-state` is evidence — do not
  hand-edit it, including as a "quick fix" (that would be exactly the history rewrite this issue
  exists to avoid).
- Scheduling: independent of the fusion-dogfood-v0.2 / successor-v0.2 critical path; can wait,
  but note the fusion-program scope accrues lineage-less frames until repaired.

## 7. Shadow gate update

2026-07-05: owner authorized continuation to the next planned non-regression shadow gate. Codex
created and validated proposal-local plan
`shadow/method-state-write-path-prevention-v0.1-plan.json` against frozen `fusion-dogfood-v0.1`.
Validation returned `valid:true`, `issues:[]`, `expected_receipt_count:24`.

This is not a shadow result. Completing the gate still requires 24 fresh real baseline/candidate
agent execution receipts plus `shadow-compare`. Existing receipts from other artifact hashes must
not be rebound or reused.

## 8. Shadow result update

2026-07-05: owner authorized real shadow execution. Codex ran 24 fresh real agent executions under
`shadow/runs/mwp-shadow-20260705/`, generated 24 trial receipts, and ran `shadow-compare`.

Result: `adoption_eligible:false`, `mean_delta:-0.01875000000000001`,
`result_hash:efc9b4ac57cf1c9e91f9023e8be591c823e7c00c3a3cdb1f45a6ac379cee70d1`.

Gate failures:

- `mean delta below external gate`
- `unacceptable fixed-case regression: fusion-memory-scope-recovery`
- `unacceptable fixed-case regression: fusion-scope-redirection-to-eval-proposal`

This is negative shadow evidence. It does not authorize adoption, deployment, rollback, deployed
Skill edits, or eval manifest edits.
