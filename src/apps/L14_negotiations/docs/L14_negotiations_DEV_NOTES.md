# L14 Negotiations Development Notes

## Table Of Contents

- [Useful References](#useful-references)
- [Data Findings](#data-findings)
- [Open Questions](#open-questions)
- [LLM Design Review](#llm-design-review)
- [Implementation Notes](#implementation-notes)
- [Implementation Plan](#implementation-plan)

## Useful References

Selected from `_agent/references/INDEX.md`:

| Reference | Use |
| --- | --- |
| `L14_AI_Assisted_Tool_Interface_Design.md` | Keep the external tool contract narrow, explicit, and driven by real task constraints. |
| `L14_Tool_Contract_Evaluation_and_Stateful_Scenarios.md` | Design verification around tool behavior and failure cases, not only happy-path answers. |
| `L7_hybrid_retrieval_and_rag_effectiveness.md` | Sanity-check whether retrieval complexity is justified; for this task direct local search is enough. |
| `_agent/instructions/llm_design_gate.md` | Required before implementing an LLM-based Polish query interpreter or any model-call schema. |

## Data Findings

Observed facts from `data/L14_negotiations/input/`:

- `cities.csv`: 51 cities.
- `items.csv`: 2137 catalog items.
- `connections.csv`: 5349 item-to-city relations.
- Every city code in `cities.csv` appears in `connections.csv`.
- One catalog item currently has no city availability in `connections.csv`.
- Product names are structured and token-rich, which makes deterministic matching realistic.
- Natural-language ambiguity is a core requirement, not an edge case, because the task explicitly says the external agent may send requests such as `potrzebuje kabla dlugosci 10 metrow`.
- Catalog variants may differ only by units, tolerance, package, or descriptive suffixes, so semantic interpretation still needs deterministic validation.

Important interpretation:

- `connections.csv` is not a city graph.
- It is a direct availability mapping from `itemCode` to `cityCode`.
- Because of that, common-city calculation is cheap.
- Polish product interpretation and product resolution are the parts most likely to fail.

Why deterministic-only matching is no longer enough as the default:

- the task-provided example uses natural Polish phrasing instead of a catalog-like product name;
- Polish inflection changes important product words, for example `kabel` to `kabla`;
- parameters may appear as descriptions, for example `dlugosci 10 metrow` instead of `10m`;
- synonymy matters, for example `kabel` and `przewod` may point to the same catalog family;
- a token matcher can produce a confident-looking but wrong match when only numbers or generic words overlap.

## Open Questions

These questions remain implementation-tuning items, not design blockers:

- How strict should the deterministic confidence threshold be before we refuse a match?
- Should the parser support both comma-separated lists and free-form conjunctions such as `and`, `oraz`, `plus`?
- Should availability lookup precompute `itemCode -> set(cityCode)` at startup for simpler request handling?
- Should the public tool path be `/` for maximum tunnel simplicity or `/tools/find_common_cities` for clearer routing?

## LLM Design Review

Review date: 2026-06-16.
Mode: non-production.
Scope: Batch 0 LLM-based Polish query interpreter plus deterministic catalog validation.
Result: PASS.

README is the source of truth for the accepted interpreter settings, output schema, prompt boundary, and `LLM Usage And Reviews` record.
This section keeps the checklist evidence and review reasoning only.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Clear goal and output | YES | Goal is to expose one tool that returns Polish compact city availability answers for one to three product needs. |
| Small workflow steps | YES | Planned workflow separates interpretation, normalization, catalog matching, validation, availability, and formatting. |
| Deterministic stable logic | YES | Catalog loading, candidate validation, set intersection, and byte-limited Polish output are planned as deterministic code. |
| Clear step purpose | YES | The LLM step interprets Polish product intent; later deterministic steps validate and answer. |
| LLM use justified | YES | The task explicitly allows free-form Polish such as `potrzebuje kabla dlugosci 10 metrow`, which is brittle for deterministic-only matching. |
| Model matches difficulty | YES | `gpt-5.4-mini` is selected as the cost-conscious starting model for narrow Polish intent extraction; deterministic code handles catalog matching and validation, and `gpt-5.5` is reserved as an eval-driven fallback. |
| Focused prompts | YES | The prompt boundary limits the model to product intent extraction and forbids item codes, city decisions, availability, and final answers. |
| Input and output tokens limited | YES | Interpreter input is capped at 1,000 characters, output at 600 tokens, with one retry only for invalid structured output. |
| Structured consumed output | YES | The approved schema returns 1-3 structured product needs, attributes, confidence, missing details, and clarification state. |
| Current-step context only | YES | The planned interpreter needs only the incoming `params` string and a compact schema description, not full CSV data. |
| Limited tool exposure | YES | The interpreter should have no tools; deterministic code will read local CSV data. |
| No irrelevant history | YES | The endpoint is stateless, so prior requests and full conversation history are not needed. |
| Batching, caching, or persistence | YES | Exact normalized `params` strings will be cached in memory for one process lifetime; no durable interpreter cache is needed. |
| Production progress mechanism | N/A | Non-production course exercise; the endpoint should complete synchronously. |
| Production waiting visibility | N/A | Non-production course exercise with one short request-response tool call. |
| Production disconnect survival | N/A | No long-running task lifecycle is planned. |
| Production state persistence | N/A | The endpoint is intended to be stateless; runtime course responses belong only in ignored verification data. |
| Production pause and resume | N/A | No approval-waiting or resumable workflow is planned. |
| Production user interaction | N/A | The caller is the course agent, not a user-facing UI. |
| Production UI separation | N/A | No UI is planned. |
| Production event orchestration | N/A | A synchronous endpoint is appropriate for this bounded exercise. |
| Validate model output | YES | Design requires deterministic validation before any interpreted need can affect final catalog matching. |
| Treat output as untrusted | YES | The LLM may propose structured needs, but code must validate them against `items.csv` and critical parameters. |
| Permissions outside model | YES | The model will not authorize external calls, choose final item codes, or submit verification. |
| Missing inputs handled | YES | Missing or underspecified details are represented through `needs_clarification`, `clarification_reason`, and `missing_details`; the model must not guess. |

## Implementation Notes

Working notes that do not belong in README:

- Start with the root endpoint `/` for the tool URL unless local/public tests prove the Hub reliably accepts nested paths.
- Keep the `L3_proxy` server style as an implementation template, but do not copy its session handling because L14 should stay stateless.
- A smaller request body limit than `L3_proxy` should be enough because L14 receives only `{"params": "..."}`.
- The registration helper should probably be named `register_tools.py` to avoid implying that it submits the final answer; the Hub agent does that asynchronously.
- During implementation, keep scoring weights easy to inspect in tests. Magic numbers hidden inside a long function will make matcher failures miserable to debug.

## Implementation Plan

This plan is grouped into implementation batches so an AI coding agent can make larger coherent changes without losing architectural discipline.
Each batch should end with a small local verification step before moving on.

### Batch 0: Matching Design Gate

Goal:
Choose and approve the matching architecture before creating application source modules.

Steps:

1. Use the approved LLM-based Polish query interpreter design.
2. Keep the interpreter no-tool and schema-bound.
3. Keep final catalog selection, city availability, and response formatting deterministic.
4. Record any future expansion as a new review requirement before implementation.

Checkpoint:

- README states the approved matching architecture;
- the design review result is recorded as PASS;
- the interpreter output contract is explicit enough to test.

### Batch 1: App Skeleton And Data Access

Goal:
Create the app skeleton and make sure local catalog data can be loaded safely.

Steps:

5. Create the app skeleton under `src/apps/L14_negotiations/` with `docs/`, module stubs, and a small server entrypoint.
6. Implement catalog loading for `data/L14_negotiations/input/cities.csv`, `items.csv`, and `connections.csv`, including startup validation for missing columns and broken codes.

Checkpoint:

- the app starts locally;
- the loader reads all three CSV files;
- startup fails clearly when required data is broken or missing.

### Batch 2: Polish Interpretation And Matching Core

Goal:
Implement the core logic that turns one Polish natural-language request into one to three validated catalog matches.

Steps:

7. Implement the approved query interpreter boundary.
8. Build text normalization helpers for case folding, punctuation cleanup, morphology hints, unit normalization, and approved synonym replacement.
9. Implement request parsing that extracts one to three product needs from a single natural-language `params` string.
10. Implement deterministic candidate scoring with explicit weights, critical-token penalties, and a confidence threshold.

Checkpoint:

- task-style Polish phrases map to the expected structured product needs;
- representative product phrases map to the expected catalog entries;
- ambiguous phrases either choose a clearly better winner or fail safely;
- critical mismatches such as `24V` vs `48V` are penalized correctly.

### Batch 3: Availability And Response Assembly

Goal:
Turn matched item codes into final agent-usable answers.

Steps:

11. Build availability lookup and common-city intersection logic using precomputed in-memory maps.
12. Define strict request and response schemas for the public HTTP endpoint and validate all incoming payloads.
13. Implement compact response formatting for the four main status families: no match, unavailable item, no common city, and success.

Checkpoint:

- the endpoint accepts only the required `params` shape;
- successful requests return city names, not codes;
- success and failure cases are written in Polish;
- failure cases remain short, explicit, and within the byte budget.

### Batch 4: Tests And Verification Helper

Goal:
Harden the app before any public exposure.

Steps:

14. Add local tests for Polish interpretation, normalization, candidate ranking, Polish response text, no-match handling, unavailable-item handling, no-common-city handling, and success cases.
15. Add a small registration helper for `/verify` plus an async `check` mode, following the `L3_proxy` submit-helper style but using the `negotiations` tools payload.

Checkpoint:

- local tests cover the main matching and contract risks;
- the helper can prepare registration payloads, print masked payloads, and poll async verification status;
- no raw course responses leak into app docs or source files.

### Batch 5: Final Local Validation Before Public Run

Goal:
Prove the app is compact and predictable before exposing it publicly.

Steps:

16. Run local verification, measure response byte length on representative Polish cases, and only then expose the endpoint publicly for the final course run.

Checkpoint:

- representative Polish responses stay within 4-500 bytes;
- endpoint behavior is stable across the main success and failure paths;
- the app is ready for short-lived `pinggy` exposure and final course verification.

### Agent Execution Guidance

For an AI coding agent, the intended working mode is:

1. Complete one batch at a time.
2. Read the existing code and tests before editing the next batch.
3. Verify the batch locally before moving forward.
4. Stop and ask for approval if a batch requires:
   - an architecture change;
   - LLM usage;
   - dependency installation;
   - external API calls;
   - public exposure or deployment.
5. Prefer finishing a whole batch over partially touching several batches at once.
