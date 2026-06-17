# L14 Negotiations Development Notes

## Table Of Contents

- [Useful References](#useful-references)
- [Data Findings](#data-findings)
- [Open Questions](#open-questions)
- [LLM Design Review](#llm-design-review)
- [LLM Optimization Review](#llm-optimization-review)
- [Debugging Notes](#debugging-notes)
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

- the task example uses free-form Polish text instead of a catalog-style lookup phrase;
- Polish inflection changes important product words, for example `kabel` to `kabla`;
- parameters may appear as descriptions, for example `dlugosci 10 metrow` instead of `10m`;
- synonymy matters, for example `kabel` and `przewod` may point to the same catalog family;
- a token matcher can produce a confident-looking but wrong match when only numbers or generic words overlap.

## Open Questions

These questions remain implementation-tuning items, not design blockers:

- How strict should the deterministic confidence threshold be before we refuse a match?
- Should the parser support both comma-separated lists and free-form conjunctions such as `and`, `oraz`, `plus`?
- Should availability lookup precompute `itemCode -> set(cityCode)` at startup for simpler request handling?
- Should the matcher expose more structured debug reasons for strong-but-underspecified wins so future tuning does not rely on ad hoc log reading?

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

## LLM Optimization Review

Review date: 2026-06-16.
Mode: non-production.
Scope: full local tool workflow through Batch 5 local validation.
Result: PASS.

README keeps the formal review record.
This section keeps the working checklist evidence.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Clearly defined task and output | YES | The app exposes one HTTP tool that returns compact Polish `output` with common city names or a safe failure message. |
| Split into smaller steps | YES | `query_interpreter.py`, `matcher.py`, `availability.py`, and `server.py` keep interpretation, validation, availability, and HTTP concerns separate. |
| Deterministic stable logic | YES | Catalog loading, match acceptance, city intersection, response size validation, and Hub payload construction are deterministic. |
| Model avoids unrelated jobs | YES | The interpreter is forbidden from choosing item codes, city codes, availability, or final answer text. |
| Workflow explainability | YES | README workflow and Mermaid flow match the implemented module boundaries. |
| Explicit model reason | YES | The model is used only for Polish product-intent extraction from free-form phrases such as `potrzebuje kabla dlugosci 10 metrow`. |
| Stronger models only when needed | YES | `gpt-5.4-mini` remains the cost-conscious default; `gpt-5.5` is only a documented fallback after failed evals. |
| No model where code is enough | YES | Deterministic code handles matching, availability, request validation, byte limits, and Hub helper behavior. |
| Avoidable retries | YES | The interpreter has one schema retry only and exact normalized-input cache. |
| Prompt clarity | YES | `SYSTEM_PROMPT` defines task, constraints, forbidden responsibilities, and schema-bound behavior. |
| Prompt context minimization | YES | The model receives only the current `params` string and no CSV catalog data. |
| No irrelevant history | YES | Endpoint is stateless; no conversation history is passed to the model. |
| Ambiguity handling | YES | `needs_clarification`, `missing_details`, and deterministic ambiguity rejection prevent silent guessing. |
| Current-step context only | YES | The interpreter has no access to availability, city names, Hub config, or prior requests. |
| Old history control | N/A | No persistent conversation history exists in this tool endpoint. |
| Tool result filtering | N/A | The model receives no tools and no tool results. |
| Context treated as limited | YES | Input is capped at 1,000 chars and output at 600 tokens. |
| Limited model tool list | YES | The LLM step exposes no tools. |
| Fewer high-value tool calls | YES | The external agent gets one combined tool endpoint instead of separate search and availability tools. |
| Batching | YES | One request may contain one to three product needs, which fits the course step budget. |
| Repeated external call caching | YES | Exact normalized params are cached in process memory. |
| No removable workflow step | YES | Each step owns a distinct boundary: interpret, normalize, match, intersect, format. |
| Structured model output | YES | The interpreter uses a strict JSON schema parsed into Pydantic models. |
| Output schema before execution | YES | Schema is defined in `query_interpreter.py` and documented in README. |
| Model output validation | YES | Pydantic validation runs before matcher use. |
| Treat model output as untrusted | YES | Deterministic matcher can reject low confidence, missing details, low score, or ambiguity. |
| Minimized LLM calls | YES | One interpreter call per uncached request, with one retry only on invalid output. |
| Minimized tool calls | YES | The public interface is one endpoint; Hub helper uses one registration call and one async check call. |
| Large prompts avoided | YES | The prompt contains only role boundary and extraction constraints, not catalog rows. |
| Output length controlled | YES | Interpreter output is token-capped and public response is byte-capped by `schemas.py`. |
| Cost and latency observability | YES | Model name, token cap, retry limit, cache, and response byte lengths are explicit and testable. |
| Expensive steps identifiable | YES | The only expensive step is `QueryInterpreter.call_model`. |
| Production progress heartbeat | N/A | Non-production synchronous course tool; requests are expected to be short. |
| Production waiting visibility | N/A | No user-facing long-running UI exists. |
| Production artifact inspection | N/A | No long-running artifact workflow exists. |
| Production disconnect survival | N/A | No resumable production job lifecycle is planned. |
| Production state persistence | N/A | Endpoint is stateless except in-memory interpreter cache. |
| Production pause and resume | N/A | No approval-waiting runtime workflow exists inside the app. |
| Production user interaction | N/A | Caller is the course agent, not a human UI. |
| Production UI separation | N/A | No UI exists. |
| Production event orchestration | N/A | Synchronous request-response is justified for this bounded tool. |
| Model not final authority | YES | The model interprets product needs only; code owns matching, availability, Hub helper, and final output. |
| Risky actions backend-protected | YES | Secrets come from `.env`, Hub calls require explicit helper commands, and request guards limit submissions. |
| Unsafe context mixing avoided | YES | User-provided `params` is sent as user input and cannot override system prompt or backend validation. |
| Missing inputs not guessed | YES | Missing details and clarification states are explicit and can stop matching. |
| No obvious replaceable LLM call | YES | The LLM call covers Polish paraphrase and inflection handling that deterministic-only design already failed as a safe default. |
| No removable workflow step | YES | Removing deterministic validation, availability intersection, or byte-limit formatting would reduce reliability. |
| No removable context block | YES | The current prompt is already minimal; removing constraints would weaken boundary enforcement. |
| Maintainability at larger size | YES | Module boundaries and tests make future product aliases, scoring changes, and response rules localized. |
| Production multi-task debuggability | N/A | Not a production multi-task app. |

Follow-up classification:

- The initial local optimization review was enough to continue implementation.
- Real OpenAI smoke validation and public Hub verification later exposed runtime-only issues that local fake-client tests could not catch.

## Debugging Notes

### 2026-06-17 Final Public Run

The final successful run required several runtime fixes that were invisible during local fake-client testing.

Observed failure sequence:

1. The local server was healthy, but early public requests were obscured by `pinggy` transport and warning-page behavior.
2. After the public `POST` reached the app, the real OpenAI call failed with `invalid_json_schema` because the generated strict schema did not list every object field in `required`.
3. After the schema fix, the public tool still failed the Hub task because `akumulator pod 48V` was treated as underspecified even though the catalog had one clear practical winner.

Root causes and fixes:

- `server.py` originally swallowed unexpected exceptions and returned only a generic fallback text. Runtime traceback logging was added under `data/L14_negotiations/logs/server_runtime_errors.log`.
- `query_interpreter.py` used raw Pydantic JSON schema output, which was not strict enough for the Responses API structured-output validator. The schema is now normalized before sending it to OpenAI.
- `matcher.py` rejected every request with `missing_details`, even when deterministic evidence was strong and conflict-free. A narrow override now accepts such cases only when the winner is strong, numeric evidence is present, and the margin over the runner-up is large.
- `availability.py` previously let `needs_clarification` override an already safe deterministic match. Final output assembly now prefers accepted matches.

This debugging cycle depended much more than usual on public-run observation rather than only local code inspection.
Manual server runs, `pinggy` checks, Hub submissions, and captured logs such as `run_20260617_1.log` and `run_20260617_2.log` were what separated tunnel behavior, `pinggy` warning-page behavior, OpenAI schema rejection, and matcher-policy mistakes into distinct failures instead of one blurry mess.

The same was true for the final matcher decision around `akumulator pod 48V`.
Static code review alone suggested caution, but direct inspection of `items.csv` together with the observed Hub behavior showed that the real catalog had one practical target, `Akumulator AGM 48V 150Ah`.
That is why the final relaxation for strong deterministic winners was introduced as an evidence-driven fix for this task's real runtime behavior, not as a generic "be less strict" tweak.

## Implementation Notes

Working notes that do not belong in README:

- Start with the root endpoint `/` for the tool URL unless local/public tests prove the Hub reliably accepts nested paths.
- Keep the `L3_proxy` server style as an implementation template, but do not copy its session handling because L14 should stay stateless.
- A smaller request body limit than `L3_proxy` should be enough because L14 receives only `{"params": "..."}`.
- The registration helper should probably be named `register_tools.py` to avoid implying that it submits the final answer; the Hub agent does that asynchronously.
- During implementation, keep scoring weights easy to inspect in tests. Magic numbers hidden inside a long function will make matcher failures miserable to debug.
- Free `pinggy` manual checks are not neutral transport. They can inject a warning page unless the request looks like an API call or explicitly sends `X-Pinggy-No-Screen`.
- Fake OpenAI clients are useful for local contract tests, but they are not enough to validate strict structured-output schema compatibility. One real smoke call is worth pages of confidence theater.

## Implementation Plan

This plan is grouped into implementation batches so an AI coding agent can make larger coherent changes without losing architectural discipline.
Each batch should end with a small local verification step before moving on.

### Batch 0: Matching Design Gate

Status: Completed.

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

Status: Completed.

Goal:
Create the app skeleton and make sure local catalog data can be loaded safely.

Steps:

5. Create the app skeleton under `src/apps/L14_negotiations/` with `docs/`, module stubs, and a small server entrypoint.
6. Implement catalog loading for `data/L14_negotiations/input/cities.csv`, `items.csv`, and `connections.csv`, including startup validation for missing columns and broken codes.

Checkpoint:

- the app starts locally;
- the loader reads all three CSV files;
- startup fails clearly when required data is broken or missing.
- verification passed with `.\venv\Scripts\python.exe -m src.apps.L14_negotiations.main --check-data`;
- compile check passed with `.\venv\Scripts\python.exe -m compileall -q src\apps\L14_negotiations`.

### Batch 2: Polish Interpretation And Matching Core

Status: Completed.

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
- normalization check maps `potrzebuje kabla dlugosci 10 metrow` to `kabel` and `10m`;
- local matcher checks accept `Inwerter DC/AC 48V 3000W`, `Akumulator AGM 48V 150Ah`, and `Turbina wiatrowa 400W 48V`;
- fake-client interpreter check confirms exact-input cache and `gpt-5.4-mini` request settings without calling OpenAI.

### Batch 3: Availability And Response Assembly

Status: Completed.

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
- compile check passed with `.\venv\Scripts\python.exe -m compileall -q src\apps\L14_negotiations`;
- data check still passes with 51 cities, 2137 items, and 5349 item-city relations;
- fake-interpreter request checks covered success, no match, unavailable item, clarification, and no-common-city response formatting without calling OpenAI.

### Batch 4: Tests And Verification Helper

Status: Completed.

Goal:
Harden the app before any public exposure.

Steps:

14. Add local tests for Polish interpretation, normalization, candidate ranking, Polish response text, no-match handling, unavailable-item handling, no-common-city handling, and success cases.
15. Add a small registration helper for `/verify` plus an async `check` mode, following the `L3_proxy` submit-helper style but using the `negotiations` tools payload.

Checkpoint:

- local tests cover the main matching and contract risks;
- the helper can prepare registration payloads, print masked payloads, and poll async verification status;
- no raw course responses leak into app docs or source files.
- test suite passed with `.\venv\Scripts\python.exe -m unittest discover -s tests\L14_negotiations -v`;
- 14 tests cover normalization, interpreter cache, candidate ranking, request schema, Polish response text, unavailable-item handling, no-common-city formatting, and guarded Hub helper behavior;
- `register.py` builds the `answer.tools` payload, builds the async `action: check` payload, masks API keys for display, uses a request guard, and applies the repository TLS/CA bundle when available before real Hub calls.

### Batch 5: Final Local Validation Before Public Run

Status: Completed.

Goal:
Prove the app is compact and predictable before exposing it publicly.

Steps:

16. Run local verification, measure response byte length on representative Polish cases, and only then expose the endpoint publicly for the final course run.

Checkpoint:

- representative Polish responses stay within 4-500 bytes;
- endpoint behavior is stable across the main success and failure paths;
- the app is ready for short-lived `pinggy` exposure and final course verification.
- compile check passed with `.\venv\Scripts\python.exe -m compileall -q src\apps\L14_negotiations tests\L14_negotiations`;
- test suite passed with `.\venv\Scripts\python.exe -m unittest discover -s tests\L14_negotiations -v`;
- data check still passes with 51 cities, 2137 items, and 5349 item-city relations;
- representative output byte lengths were: success 116, no match 83, unavailable item 91, clarification 42, no common city 129, broad city list 94;
- local HTTP handler tests cover valid POST `/` and invalid payload rejection without real OpenAI calls.

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
