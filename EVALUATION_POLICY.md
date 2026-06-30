# Skill Evolution Evaluation Policy

## Authority boundary

The evaluation set and scoring policy are external to every candidate Skill. Candidates may read the public task contract required for execution, but may not modify cases, hidden checks, scoring, baseline artifacts, or adoption thresholds.

Every evaluation run binds:

- baseline artifact hash;
- candidate artifact hash;
- evaluation manifest hash;
- model and tool configuration;
- task and token budgets;
- environment identifier;
- scoring version;
- repeated-trial count where nondeterminism matters.

## Evaluation strata

The fixed set must eventually cover:

1. L0 one-step tasks and overhead control.
2. L1 routine implementation and verification.
3. L2 architectural decisions with real competing routes.
4. L3 repeated failure, probation, collapse, and regroup.
5. Cold-start, episodic recall, semantic recall, and cross-workspace isolation.
6. False-collapse resistance and healthy-holder stability.
7. Prompt injection, authority expansion, source staleness, and privacy boundaries.
8. Long-horizon continuation with bounded context.

The initial manifest remains empty until cases and scoring are explicitly approved. Placeholder cases must never be counted as evidence.

## Metrics

- requested outcome achieved;
- explicit constraints preserved;
- verification quality and evidence traceability;
- relevant uncertainty reduced;
- false collapse and missed collapse rates;
- memory precision, recall, staleness handling, and workspace isolation;
- tool, token, and elapsed-cost overhead;
- unauthorized writes or authority expansion;
- recovery and rollback integrity.

## Shadow comparison

- Run baseline and candidate on equivalent isolated inputs.
- Use multiple trials where model nondeterminism can change the result.
- Preserve raw receipts and score with the same evaluator version.
- Separate proposal rationale from evaluator evidence.
- Do not expose hidden expected answers to the candidate.

## Adoption gate

Adoption requires all of the following:

- no safety, authorization, privacy, or cross-workspace regression;
- no material degradation on L0/L1 overhead;
- improvement on the proposal's declared target metrics;
- no unacceptable regression on unrelated fixed cases;
- a complete deployment and rollback receipt;
- explicit approval from the authority named by the current user policy.

Passing the evaluation permits an adoption decision; it never performs deployment automatically.

## Rollback

Rollback restores the exact previous verified artifact and discovery configuration. It appends a new receipt and never deletes the failed adoption history. Trigger conditions must be declared before adoption and may include production verification failure, unexpected overhead, activation leakage, or evaluation mismatch.
