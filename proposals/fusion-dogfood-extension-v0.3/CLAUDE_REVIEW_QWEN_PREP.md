# Claude Review Request: Qwen Surface Prep

Status: pre-live review package. No live API call has been made from this package, and no API key or host is persisted here.

Review caveat: Codex initially ran an over-broad repository secret scan, then reran the scan excluding `evals/hidden/**` and `hidden-side/**`; no matches were found. The Qwen runner/design did not use hidden artifacts, and the over-broad scan is not claimed as hidden-firewall evidence.

## Review Scope

- `tools/qwen_v03_runner.py`
- `tests/test_qwen_v03_runner.py`
- `proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/qwen-surface/QWEN_SURFACE_SELF_TEST.json`
- `proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/qwen-surface/QWEN_EXECUTION_SURFACE_SPEC.json`
- `proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/qwen-surface/QWEN_BUDGET_RECALIBRATION_PLAN.json`
- `proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/qwen-surface/CROSS_WINDOW_V2_QWEN_PREREG_DRAFT.json`

## Questions For Claude

1. Does the runner preserve R3 hard budget semantics on a direct OpenAI-compatible API surface: per-response usage accumulation, live truncation, ordered telemetry, and scoring-time replay?
2. Are the three arm tool configurations separated enough for R6 arm purity: `no-method` read-only, `append-only` notes/retrieval without collapse, and `method-baseline` with command/runtime affordances?
3. Is the budget recalibration plan sufficient to prevent reusing Codex Desktop token budgets on the Qwen surface?
4. Does the cross-window v2 prereg correctly disclose substrate substitution and block live trials until the exact Qwen snapshot id and winnability are verified?
5. Is any key material accidentally included? Expected answer should be no. Separately, judge whether the over-broad initial secret scan requires any additional firewall note before live calibration.

## Explicit Non-Authority

This review does not authorize live API calls, six-trial calibration, fixture freeze, manifest edits, adoption, deployment, or any write to `evals/hidden/`.

## Current Blockers Before Live Trials

- Exact `QWEN_MODEL_SNAPSHOT` is not pinned.
- Claude review verdict is not yet recorded.
- Owner post-review go-ahead for live Qwen trials is not yet recorded.
- Qwen-surface winnability and budget recalibration have not yet been run.

## Claude Review Verdict (2026-07-05, session 1416c32e)

Independent verification: 18/18 pytest, harness self-test, requirements preflight 16/16, and
`qwen_v03_runner.py self-test` (`valid: true`, `live_api_called: false`, `api_key_read: false`)
all re-run and passed from this session. No key material found in reviewed files; the module is
env-only by construction.

**Verdict: APPROVED WITH THREE REQUIRED FIXES before live trials.** The architecture (key-free
module, fake-client tests, live BudgetMeter truncation, prereg gates) is sound. The fixes:

1. **Token metering rule double-counts context.** `run_qwen_trial` consumes
   `usage.total_tokens` per response; on a chat API the prompt re-transmits the full message
   history each round, so cumulative summing charges earlier context repeatedly (quadratic
   growth), which both distorts the budget and diverges from any declarable accounting policy.
   Required: pin an explicit rule — recommended `context budget = peak single-response
   total_tokens` (peak context size) plus, if desired, a separate cumulative completion-token
   ceiling — declare it in the accounting policy, and validate winnability under the same rule.
2. **`run_command` must be whitelist, not blacklist.** The current marker blacklist
   (`del`, `>`, `curl`…) is trivially bypassable (e.g. `Out-File`, `Add-Content`, inline
   Python writes) and the "read-only" description is wrong for the method arm, whose core
   function is *writing* to the isolated method-state home. Required: allow only an enumerated
   command form — `python <pinned weilan_trace.py path> …` with `WEILAN_METHOD_HOME` forced to
   the trial's isolated home — and reject everything else. Drop the "read-only" wording.
3. **Arm-purity observables must be measured, not declared.** `parse_qwen_telemetry` hardcodes
   `workspace_method_bootstrap_count: 0` and derives `method_runtime_operation_count` from
   `arm_config` rather than from events. That makes the purity gate pass by construction,
   which contradicts R6's own clause ("verified from telemetry, not assumed"). Required:
   compute observables from the actual stream — fingerprint-scan the full message history
   (skill/method markers) and count actual `run_command` invocations of the method runtime.

Answers to the five review questions: (1) yes except fix 1; (2) yes except fixes 2–3;
(3) recalibration plan direction correct, fold fix 1's rule into it; (4) prereg discloses
substitution and gates live trials correctly — snapshot pin honestly pending; (5) no key
material found; the over-broad-then-rerun scan caveat is adequate as recorded and needs no
further firewall note (Codex is hidden-side-eligible by role). Additional security note: the
owner pasted the API key into a chat window once — rotate the key after the live batch, and
pass it only via environment variable thereafter.

Non-authority: this verdict authorizes nothing; live trials still require snapshot pinning,
the three fixes, Qwen-surface winnability validation, and explicit owner go-ahead.

## Codex Fix Resolution (2026-07-06)

All three required fixes have been implemented in `tools/qwen_v03_runner.py` and covered by
`tests/test_qwen_v03_runner.py`:

1. Token accounting now uses `context_token_rule:
   peak_single_response_total_tokens`. The runner records `billable_total_tokens` separately,
   but R3 context budget and winnability must use the peak single-response context-size rule.
2. `run_command` no longer accepts arbitrary shell strings. It accepts only structured `args`,
   and the runner constructs `python <pinned weilan_trace.py> <args>` with `WEILAN_METHOD_HOME`
   forced to the trial isolated method home. Qwen env variables are stripped from that subprocess.
3. Arm-purity observables now come from telemetry: SHA-256 message fingerprints with marker hits
   plus actual tool events. `workspace_method_bootstrap_count`, `method_runtime_operation_count`,
   and `append_only_forbidden_operation_count` are no longer derived from `arm_config`.

Regression coverage added:

- multi-response peak context budget does not double-count repeated chat history;
- arbitrary shell write attempts through `run_command` do not execute;
- no-method bootstrap pollution is detected from message fingerprints;
- append-only forbidden runtime events are rejected from telemetry.

Remaining live blockers: exact `QWEN_MODEL_SNAPSHOT` pin, Qwen-surface budget/winnability probes,
and explicit owner start signal for live API work.
