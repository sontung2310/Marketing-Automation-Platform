# Spec Delta

## Purpose
Routing of chat messages to the Strategy or Execution agent, or to a direct answer, as agents-spec §5.2 describes: classifier decisions, explicit hints, clarification, out-of-scope answers and session references.

## ADDED Requirements

### Requirement: Classifier routing

A chat message with no `agent_hint`, or with `AUTO`, SHALL be classified into a `RouteDecision` by the router model (`OPENAI_MODEL_ROUTER`, structured output). Questions about direction (*what, which, should, why, who*) SHALL route to Strategy. Requests to produce an artifact (*write, draft, create, rewrite, turn into*) SHALL route to Execution. The decision's method (`CLASSIFIER`), reason and confidence SHALL be stored on the run and returned in `route`.

#### Scenario: Strategy question
- **WHEN** the message is "What should we post about next week?"
- **THEN** the run routes to Strategy with intent `TOPIC_RECOMMENDATION` and method `CLASSIFIER`

#### Scenario: Execution request
- **WHEN** the message is "Write a LinkedIn post about AI search for B2B founders"
- **THEN** the run routes to Execution with intent `FREEFORM_DELIVERABLE` and deliverable type `LINKEDIN_POST`

### Requirement: Clarify and out of scope

A decision with confidence below 0.6, or intent `CLARIFY`, SHALL return `200 NEEDS_CLARIFICATION` with a short question and 2–3 quick-reply options, and SHALL start no run. Intent `OUT_OF_SCOPE` (non-marketing or disallowed) SHALL return `200 OUT_OF_SCOPE` with the fixed message "I can help with Marketing Eye's marketing: competitor moves, content ideas and drafts. That request is outside what I do." and SHALL start no run.

#### Scenario: Ambiguous one-word message (6-E)
- **WHEN** the message is "LinkedIn"
- **THEN** `200` returns `NEEDS_CLARIFICATION` with 2–3 options, and no run is created

#### Scenario: Off-topic message (6-E)
- **WHEN** the message is "What's the weather in Sydney?"
- **THEN** `200` returns `OUT_OF_SCOPE`, and no run is created

### Requirement: Explicit agent hint

With `agent_hint` `STRATEGY` or `EXECUTION`, the router SHALL keep that agent, classify only the intent and references within that agent, and use method `EXPLICIT`. A message the hinted agent cannot serve SHALL still route to that agent, and the agent responds within its own scope.

#### Scenario: Hint mismatch
- **WHEN** the hint is `STRATEGY` and the message is "Write a post about AI search"
- **THEN** the run routes to Strategy with method `EXPLICIT`

### Requirement: Session references

References SHALL resolve against the session: `recommendation:N` is the Nth recommendation of the latest Strategy run in the session, and `deliverable:last` is the session's latest deliverable. A resolved reference SHALL be passed to the agent as its trigger context, the same as the matching UI button. An unresolvable reference SHALL return `200 NEEDS_CLARIFICATION` with the message "No recommendation #N in this session" (or "No earlier deliverable in this session") and SHALL start no run.

#### Scenario: Recommendation by number (5-C, RT-REF)
- **GIVEN** a session whose latest Strategy run has 3 recommendations
- **WHEN** the message is "Write the LinkedIn post for recommendation #2"
- **THEN** the run routes to Execution with recommendation 2 as its trigger context

#### Scenario: Unresolvable number (5-C, RT-REF)
- **GIVEN** the same session
- **WHEN** the message is "#7"
- **THEN** `200 NEEDS_CLARIFICATION` returns "No recommendation #7 in this session", and no run is created

### Requirement: Router golden dataset

`evaluation/golden/router.jsonl` SHALL hold at least 36 cases covering every evaluation-spec §3.1 category at its minimum. The `router` suite SHALL check agent, intent, status, deliverable type and resolved references deterministically, with no judge. Its committed baseline SHALL meet the router thresholds in evaluation-spec §6 at one repeat.

#### Scenario: Router baseline (6-F)
- **WHEN** `python -m evals.cli run --suite router --repeats 1` runs
- **THEN** deterministic pass is at least 95% overall, `RT-OOS` passes 100%, every `demo-path` case passes, and p95 latency is at most 3 s
