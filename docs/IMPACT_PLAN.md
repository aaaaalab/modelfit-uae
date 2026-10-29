# Impact measurement and judging alignment

## Targets versus evidence

The challenge's 80% evaluation-time reduction and 100% compliance ambitions are targets to validate, not achieved outcomes. Mandatory coverage is the proportion of this service's configured mandatory requirements with a valid passing finding; it is not legal compliance. No savings estimate is presented in the app.

The prototype shows actual workflow counts: completed checks, mandatory evidence gaps, human-justified reuse decisions, assessment timestamps, decision records and reassessment tasks. Fixed model outputs and performance fixtures are simulated and labelled.

## Proposed measurement protocol

- Baseline: a human team performs the same defined assessment using its existing process. Capture active person-minutes, elapsed time, source retrieval, repeated tests, review rounds and errors.
- Pilot: comparable team and task with ModelFit; keep requirements and quality criteria equivalent. Record experience, case order and assistance differences.
- Savings calculation: `(baseline active minutes − pilot active minutes) / baseline active minutes × 100`, only for paired observed cases. State sample size, median/range, exclusions and uncertainty. Avoid causal claims from a small unrandomized pilot.
- Evidence quality: independent human review of source correctness, applicability, unsupported passes, missed mandatory failures and reuse rationales.
- Change-engine quality: known-change test corpus; report dependent checks correctly reopened, missed dependencies, unnecessary reopenings and time to resolution.
- Human accountability: proportion of decisions with verified reviewer authority, explicit scope, evidence snapshot, rationale, owners and review dates.
- Accessibility: keyboard/assistive-technology task completion, critical barriers and user feedback. No certification claim without assessment.

A first pilot could target 5–10 paired assessments if authorized. That is a planning hypothesis, not an achieved sample. Stop or revise if speed gains accompany lower evidence quality.

## Supplied judging weights

| Criterion | Weight | Implemented support | Remaining validation |
| --- | --- | --- | --- |
| Challenge alignment and impact | 25% | All five connected areas; contextual suitability; mandatory gates; accountable human decision; change impact. | User discovery, baseline/pilot outcomes and rule applicability. |
| Effective government open data | 20% | Official TDRA workbook preserved; source-grounded bilingual examples; provenance and use restrictions visible. | Source refresh process, broader corpus and domain review. |
| Innovative use of AI | 20% | Bounded source-linked assistant adapter; uncertainty and human confirmation; deterministic What Changed? dependencies. | Live AI is not connected. Real extraction/summary quality and adversarial safety remain to be evaluated. |
| Feasibility and planning | 15% | Single FastAPI/React deployment, persistent MySQL, tested rules, 90-day staged plan and explicit limitations. | Identity/security validation, costs, operational ownership and controlled pilot. |
| Presentation and communication | 20% | Distinctive workspace, three-minute journey, evidence traceability and honest simulated/live labels. | Rehearsal with presenters and accessibility review. |

These features support the criteria; no judging score or competition outcome is guaranteed.
