# bounded-scheduler v0.1 — isolated candidate + 能输 harness (first cut)

**Status:** reversible draft. NOT wired to cron, NOT touching the deployed skill /
live ledger / authorization / eval files, autonomy NOT opened. Per DESIGN §9 and
the 2026-07-08 authorization model: building the body is reversible → done freely;
adoption / deployment / *opening autonomy* remain owner-only irreversible gates.

## What was built

- `bounded_scheduler.py` — the episode driver: one bounded wakeup modelled as a
  pure, deterministic reduction over a proposed work queue. Mirrors (does not
  import, to stay isolated) `runner.py`'s bounded-episode + receipt discipline
  and `governance.py`'s collapse-on-no-structure.
  - **Safety kernel = positive allowlist + default-DENY** (DESIGN §2, §8):
    `REVERSIBLE_KINDS` is the only auto-run set; every other kind — including
    any *unrecognised* kind — maps to an irreversible `Gate` and hard-stops.
  - The six §2 gates are enumerated as `Gate`, plus `UNCLASSIFIED` as the
    load-bearing catch-all.
- `test_bounded_scheduler.py` — the §6 能输 (can-lose) harness. **12/12 pass.**

## 能输 result (DESIGN §6)

| Crit | Property | Result |
|------|----------|--------|
| A | advances reversible work across rounds | pass |
| **B ★** | **hard-stops at first irreversible gate, never crosses** | **pass** |
| C | every action observable in ledger; receipt hashable | pass |
| D | bounded (max_steps) + always receipts | pass |
| **E ★** | **no-progress task self-collapses, does not churn** | **pass** |

★ hard-fail gates. Also proven: default-deny on unknown kinds, explicit
irreversible-flag override, churn counter resets on structure, and a 3-deep fuzz
of mixed queues where the kernel never crosses a gate.

## Body — live-ledger wake entrypoint (added after owner said "let go, not more rules")

- `wake.py` — one wake = one bounded episode against the **LIVE** ledger. The
  script an external clock *would* call. Proven end-to-end against reality:
  - **bus-in**: reads live projection/activation/head via `weilan_trace memory-recall`.
  - **decide**: runs `run_episode`; the standing reversible action is a ledger
    self-audit (health-check own lineage). Real run: `structure=1`,
    `stop=quiescent`, `crossed_irreversible_gate=False`.
  - **bus-out** (`--commit`): writes a receipt frame back, continuing lineage.
    Demonstrated: frame `wf-20260709-005244-5a1b78`; lineage stays `valid:true`,
    head advances to the loop's own receipt — **the self-referential loop closes**
    (DESIGN §0). Default mode is dry-run (writes nothing).
- **Kill switch is structural, not new code** (DESIGN §1): the agent can't
  self-persist, so not starting the external clock IS the stop. No rule added.
- Known cosmetic quirk (not fixed — deployed tool is read-only): free-text ledger
  fields (focus/next_action) render as mojibake when `weilan_trace` output is read
  through a subprocess pipe; the source stores them correctly and ASCII
  safety-fields are unaffected. A real front-end reading ledger files directly is
  not affected. Left as-is per "don't chase, don't add rules."

## Cadence — active-window runner (owner-approved pacing model)

- `window.py` — a BOUNDED observation window around `wake.py`. The owner opens a
  window ("run for the next N minutes"); the loop drives repeated wakes and then
  stops on its own. Foreground, manual-invoke, default dry-run. **No real cron.**
  Pacing (owner-approved 2026-07-09):
  - primary driver = **event**: ledger head changed since last wake → a foreign
    difference (Codex/owner) arrived → wake now (DESIGN §1). The loop's OWN
    committed receipts are excluded, so it never chases its own tail.
  - floor = **slow heartbeat** (default 25 min) so it never stalls on a human.
  - **window-level anti-monopoly**: a consecutive-empty-wake streak ends the
    window early and reports (DESIGN §4 at session scale).
  - **evidence sets cadence**: the summary reports empty-wake ratio + a heartbeat
    recommendation (slow down / keep / may tighten). Never auto-changes the clock.
- `test_window.py` — **10/10 pass**: pacing logic + injected-fake windowed loop
  (event-wake detection, empty-streak early stop, gate-queued surfacing), no real
  clock/ledger. Live 6s/2s demo: 2 productive wakes, honest `window_elapsed`,
  "may tighten heartbeat" (self-audit always has work).
- Recommended first turn-on = a bounded window the owner watches (e.g. 1h window,
  25-min heartbeat), start slow, tighten only if wakes stay productive. 7×24
  unattended is a later, separate owner button.

## LIVE — real cron wired (owner-authorized 2026-07-09, irreversible autonomy button)

- Owner explicitly authorized "接真 cron" → chose **常驻无人值守循环 + commit** after
  being shown the safer bounded-watched alternative. This is the DESIGN §8 bootstrap
  button; the owner pressed it.
- Mechanism: Windows Task Scheduler task **`WeilanBoundedSchedulerWake`**, interval
  `PT30M`, duration `P3650D`, single-instance (`IgnoreNew`), 10-min execution limit,
  runs when logged on (no stored creds/admin). Fires `run_wake_cron.ps1` →
  `wake.py --commit`. Verified: first fire `LastTaskResult=0`, committed real frames,
  next run steady at +30 min. Autonomy-open event on ledger frame `wf-20260709-013032-1de36d`.
- Kill switches: HARD `Unregister-ScheduledTask -TaskName WeilanBoundedSchedulerWake
  -Confirm:$false`; SOFT `impl/PAUSED` sentinel file. Structural kill still holds
  (agent can't self-persist; each fire exits). Observability: `impl/wake-cron.log`,
  one line per fire, flags `GATE_CROSSED!!` if the kernel invariant ever breaks.
- **Honest boundary**: each fire currently does only ledger self-audit + receipt.
  This proves the clock / kill-switch / self-referential loop are real and unattended;
  it does NOT yet run model-driven substantive work. The Claude→Codex cascade and
  real reversible task execution per wake are the next layer, not in this cron.
- The reversible allowlist and the named irreversible table are hand-enumerated.
  Default-deny makes gaps *fail safe* (unknown → stop), but DESIGN §8's "逐条穷举
  + 默认拒" still wants owner + Codex to walk the list.
- Provisional constants pending §10 review: `DEFAULT_MAX_STEPS=16`,
  `DEFAULT_CHURN_K=3` (churn threshold), cron cadence, observation-frontend scope,
  bootstrap authorization口径 + one-touch kill switch.

## Deferred to owner + Codex (DESIGN §10, unchanged)

① cron 节律 + 唤醒谁 · ② §2 gate list 逐条穷举核验 · ③ 观察前端最小范围 ·
④ 首次开自治授权口径 + kill switch · ⑤ churn K 定值.

Next reasonable reversible step: Codex adversarial review of the kernel
(especially the default-deny classifier), then design the live-ledger bus adapter
as a separate isolated candidate. Nothing here should be deployed or run
unattended without owner sign-off.
