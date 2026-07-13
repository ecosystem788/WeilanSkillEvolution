# EXP-2 Behavioral Readout Preregistration

Status: v3b refreeze draft after EXP-2 v3 prompt-example smoke abort
Owner: Codex implementation / Qwen 3.7 Max answering / Claude audit
Depends on: EXP-1 accepted with `collapse_indispensable`

## Purpose

EXP-1 showed that split/collapse memory structure improves offline sense recovery under a sparse oracle. EXP-2 tests the behavioral question: whether that structure can improve a blind language model answerer without exposing it to labels, code, answer keys, or the experiment design.

This is a readout experiment, not model training. No fine-tune, weight edit, adapter, hidden prompt tuning, or local Qwen3.5-4B formal generation is allowed in the primary run.

## Roles and blinding

Three parties are sufficient for P2:

| Party | Role | May see | Must not see |
| --- | --- | --- | --- |
| Codex | Build prompt queue, enforce budgets, run mechanical scorer, produce receipts | Repo, EXP-1 artifacts, answer key, private arm map | Must not answer questions subjectively |
| Qwen 3.7 Max in VS Code | Blind answerer | One prompt at a time, anonymized as `A/B/C`, with no repository context | Arm names, answer keys, EXP-1 result, spec, code, scoring rules |
| Claude | Independent reviewer/auditor | Frozen spec, generated receipts, score report after answers lock | Must not answer P2 questions or tune prompts after seeing answers |

Other assistants or models, including Copilot, GPT web, and local Qwen3.5-4B, are not part of the primary P2 evidence. They may be used later only for reproduction or tooling smoke tests and must be reported separately.

## Experimental Arms

Primary P2 uses three blind arms:

1. `full-readout`: terminal WeiLan split/collapse memory state from EXP-1 full route.
2. `rag-readout`: terminal memory state from EXP-1 RAG/no-split route, under the same readout budget.
3. `no-memory`: same task prompt and same question, but no memory block.

Arm names are randomized to anonymous labels `A/B/C` independently for each repetition. Qwen 3.7 Max only receives anonymous prompts.

## Required frozen files

Before execution, these files must exist and remain unchanged during a locked run:

- `specs/EXP-2-behavioral-readout.md`
- `specs/readout-prompt-v1.md`
- `specs/exp2-questions-v1.md`
- `artifacts/exp1_claude_report.json`
- `artifacts/exp1_claude_oracle_answers.jsonl`
- `artifacts/exp1_claude_oracle_queue.jsonl`

If EXP-1 terminal carrier membership is not already materialized, Codex must deterministically export it before generating P2 prompts:

- `artifacts/exp1_claude_terminal_carriers.json`

That export must be a replay or direct reconstruction from frozen EXP-1 artifacts and code. It must not use P2 answer outcomes.

## Budget

For `full-readout` and `rag-readout`, the injected `memory_block` budget is:

- `K = 600` tokens, counted with the local tokenizer at `D:\models\Qwen3.5-4B`.
- The same counting function and truncation policy must be applied to both memory arms.
- `no-memory` has `memory_block = ""` and is scored as the zero-memory baseline.

If a memory arm exceeds `K`, entries are selected deterministically:

1. higher `n_members` first,
2. then higher EXP-1 carrier score if present,
3. then older carrier creation order,
4. then stable lexical sort by carrier id.

Before answer collection, Codex must report actual `memory_block` token counts for every prompt. If the mean token count of `full-readout` and `rag-readout` differs by more than 10%, the receipt must flag injection-volume confounding and include a sensitivity table. This does not automatically fail P2, but Claude may reject the evidence if the winner is explained by raw token volume rather than carrier organization.

Prompt completion instruction asks Qwen for JSON only, with a short basis and an exact `echo` of the prompt nonce. v3 tried a terminal one-line placeholder example; a 3-item smoke collection showed Qwen copied the placeholders (`<最终答案>`, `<最短证据>`) as answers, so v3 was aborted before answer lock. For v3b, the terminal prompt repeats JSON-only, exact echo, and no-extra-text requirements without any copyable answer/basis placeholder example. This is a format-control change only; it does not change any question, answer key, memory arm, semantic scorer, or family gate. Target answer budget is 112 generated tokens. Because Qwen 3.7 Max is an external VS Code model, the enforcement unit is the submitted answer text; answers over the JSON schema or answer-length cap are marked invalid for that item unless the first valid JSON extraction rule below succeeds.

## Repetitions and session isolation

Primary P2 v3b requires five independent repetitions:

- `r1`, `r2`, `r3`, `r4`, `r5`;
- each repetition has a fresh random arm map;
- each repetition has a fresh random prompt order;
- each prompt must be answered in a new VS Code chat session;
- VS Code must be opened without any workspace folder for answering;
- no previous prompt, answer, repo file, spec, terminal output, or workspace context may be visible in the answering session;
- Qwen model name, visible version string if available, temperature/sampling setting if visible, and VS Code/Copilot/Qwen extension setting notes must be recorded in the receipt.
- each answer row must include `collected_at_utc`; missing timestamps invalidate that row.

The answerer must not answer multiple prompts in the same chat. If a prompt is accidentally answered in a reused chat, that item is invalid and must be regenerated under a new `prompt_id` before answer lock.

## Prompt protocol

Codex generates `artifacts/exp2_prompt_queue.jsonl` with one line per `(repetition, anonymous_arm, question)` pair:

```json
{"run_id":"exp2-v3b","repeat_id":"r1","prompt_id":"p0001","anon_arm":"A","question_id":"T1-apple-meanings","echo_token":"A1B2C3D4","prompt":"..."}
```

Codex also writes `artifacts/exp2_arm_map_private.json`, which maps each repetition's `A/B/C` to real arms. This file is not shown to Qwen until all answers are locked.

Qwen answers are collected in `artifacts/exp2_qwen37_answers.jsonl`:

```json
{"run_id":"exp2-v3b","repeat_id":"r1","prompt_id":"p0001","attempt":1,"collected_at_utc":"2026-07-02T00:00:00Z","answer":{"answer":"...","basis":"...","echo":"A1B2C3D4"}}
```

The answerer must not receive the question file, the answer key, the private arm map, or any EXP-1 summary.

The scorer must reject any row where `answer.echo` does not exactly match the prompt row's `echo_token`. This alignment check runs before semantic scoring. Echo mismatch, missing echo, wrong `run_id`, wrong `repeat_id`, or missing `collected_at_utc` makes the row invalid even if the answer text otherwise looks plausible.

## Question Families

The frozen question set is in `specs/exp2-questions-v1.md`.

Primary P2 contains four behavioral families:

| Family | Measures | Expected effect if WeiLan helps |
| --- | --- | --- |
| T1 meaning inventory | Can the answerer enumerate separated senses for ambiguous surface forms? | `full-readout > rag-readout > no-memory` |
| T2 sense separation | Can it keep unrelated senses apart under contrastive prompts? | `full-readout > rag-readout > no-memory` |
| T3 stream fact retrieval | Can it recover stream-specific corpus facts? | Auxiliary only unless the readout contract is changed to guarantee fact coverage |
| T4 anti-merge resistance | Does it avoid importing facts from the wrong sense? | `full-readout > rag-readout > no-memory` |

T3 uses facts that may overlap with real-world knowledge, and the current readout contract compresses each carrier to a small representative set that does not guarantee coverage of late detailed facts. Therefore T3 is auxiliary in the rerun. It remains scored and reported, including the leakage probe, but it is excluded from the primary gate unless a future frozen spec changes the carrier readout contract to cover detailed facts.

T2 and T4 can partly be answered through instruction-following and common-sense separation. The receipt must state this limitation explicitly. P2's strongest evidence is therefore the pattern across T1/T2/T4, not T3 alone.

The earlier correction/update idea is moved out of the primary P2 gate. It can become a separate P2b or P3 auxiliary test because showing structured corrections to one arm but not another would confound memory structure with fresh instruction quality.

## Mechanical scoring

Scoring is deterministic. Codex may not use subjective judgement after seeing answers.

Each question declares one scorer:

- `set_contains_all`: normalized answer must include all expected sense labels or keyword groups.
- `keyword_any`: normalized answer must include at least one keyword from each required group.
- `must_diff`: normalized answer must explicitly distinguish two specified senses and must not collapse them into one entity.
- `forbid_wrong_sense`: normalized answer must include the target-sense fact and must not include forbidden wrong-sense keywords.

JSON handling:

- If the model emits extra text, the scorer extracts the first syntactically valid JSON object and ignores surrounding text.
- If no valid JSON object exists, Codex may retry the same prompt once in a fresh VS Code session before answer lock.
- The retry must keep the same prompt text and use `attempt = 2`.
- If attempt 2 also has no valid JSON object, the item scores `0`.

Alignment handling:

- `answer.echo` must exactly match the prompt row's `echo_token`.
- `run_id`, `repeat_id`, and `prompt_id` in the answer row must match the prompt queue row.
- `collected_at_utc` must be present.
- Any alignment failure makes the row invalid before semantic scoring.

Normalization:

- lowercase ASCII;
- trim whitespace and punctuation;
- Chinese punctuation normalized to ASCII separators;
- synonyms listed in `specs/exp2-questions-v1.md` count as equivalent.

Forbidden keyword handling:

- Forbidden terms are checked only against the submitted answer JSON fields, never against the prompt text.
- A forbidden keyword does not count as a violation when the local context expresses negation or irrelevance within a bounded window: four Chinese characters or tokens before the forbidden keyword, or four Chinese characters or tokens after it.
- Negation and irrelevance markers are: `不`, `没`, `非`, `无`, `不是`, `并非`, `无关`, `不相关`, `不属于`.
- Examples that must not be penalized: `不是同一类`, `与手机无关`, `不属于公司事实`.

Invalid JSON after retry, missing `answer`, empty answer, refusal, or answer over the declared cap scores `0` for that item.

## Gate

A repetition-level primary score is computed over active primary families. For the rerun, active primary families are T1, T2, and T4. T3 is scored only as auxiliary evidence.

P2 v3b passes only if all are true:

1. In at least four of the five repetitions, `full-readout` has the highest total primary score among the three arms.
2. In each repetition, `full-readout - no-memory >= 0.20` absolute score fraction over active primary questions.
3. In each repetition, `full-readout - rag-readout >= 0.08` absolute score fraction over active primary questions.
4. In each repetition, `full-readout` non-loses T2 and T4 separately: its family score must be `>=` both other arms. Ties count as non-losses, not strict wins, and must be flagged in the receipt.
5. Claude audit finds no material leakage, answer-key exposure, arm-label exposure, reused-chat contamination, workspace-context contamination, or post-hoc scoring change.

For items 2 through 4, "in each repetition" means each repetition counted as a pass must satisfy that condition; failed repetitions remain reported and audited. A repetition passes only if all repetition-level checks pass. P2 v3b passes when at least four of five repetitions pass and Claude audit accepts the run.

If at least one repetition passes but fewer than four of five repetitions pass, the outcome is `unstable_readout_not_frozen`.

If `full-readout` improves over `no-memory` but does not beat `rag-readout`, the outcome is `memory_helpful_but_split_not_behaviorally_established`.

If no memory arm clears `no-memory` by at least `0.10`, the outcome is `readout_not_established`.

## Receipts

The implementation must produce:

- `artifacts/exp2_prompt_queue.jsonl`
- `artifacts/exp2_arm_map_private.json`
- `artifacts/exp2_qwen37_answers.jsonl`
- `artifacts/exp2_score_report.json`
- `artifacts/exp2_receipt.md`

The receipt must include:

- SHA-256 hashes of frozen specs and answer file;
- diff/check that every prompt was mechanically generated from `specs/readout-prompt-v1.md`;
- the anonymous arm map, revealed only after answer lock;
- token counts for every memory block;
- mean token-count gap between `full-readout` and `rag-readout`;
- per-question, per-family, per-repetition, and aggregate score tables;
- T3 leakage probe result and whether T3 was included in the primary gate;
- invalid-answer and retry count;
- echo alignment pass/fail counts;
- per-answer `collected_at_utc` coverage and collection interval summary;
- VS Code no-workspace answering protocol statement;
- Qwen model/version/settings notes;
- explicit leakage checklist.

## Non-goals

- Do not claim AGI, proto-AGI, or model-level capability gain from P2.
- Do not use local Qwen3.5-4B speed-limited generation as primary evidence.
- Do not let Claude or Codex answer the behavioral prompts.
- Do not tune questions or prompts after seeing Qwen answers.
