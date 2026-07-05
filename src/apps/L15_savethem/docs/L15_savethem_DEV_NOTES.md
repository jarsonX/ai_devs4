# L15 Savethem Development Notes

## Table Of Contents

- [Useful References](#useful-references)
- [API Exploration Scope](#api-exploration-scope)
- [API Findings](#api-findings)
- [Derived Mission Facts](#derived-mission-facts)
- [Design Decisions](#design-decisions)
- [Open Questions](#open-questions)
- [LLM Design Review](#llm-design-review)
- [LLM Optimization Review](#llm-optimization-review)
- [Live Run And Debugging Notes](#live-run-and-debugging-notes)
- [Implementation Plan](#implementation-plan)

## Useful References

Selected from `_agent/references/INDEX.md`:

| Reference | Use |
| --- | --- |
| `L2_workflow_orchestration_and_reflection.md` | Keep the workflow dynamic only where exploration truly depends on intermediate results. |
| `L3_tool_family_and_response_contracts.md` | Turn loose HTTP discovery into a small internal tool contract with explicit success and failure handling. |
| `L5_model_failure_modes_and_validation.md` | Separate value validation from shape validation and avoid inventing missing movement rules. |
| `L10_multi_agent_tool_assignment_and_sandboxing.md` | Use progressive discovery instead of injecting imaginary tools into the design. |
| `L11_observability_trace_and_prompt_versioning.md` | Preserve exploration traces and raw responses so later failures can be debugged from evidence. |
| `_agent/instructions/external_api_safety.md` | Keep exploratory API usage bounded and store raw course responses only under ignored runtime data. |

## API Exploration Scope

Exploration date: 2026-06-18.

Goal:
Confirm the real API contract for `toolsearch` and the discovered tools before any implementation decisions.

Boundaries used during exploration:

- small, manual, bounded set of requests;
- no source implementation yet;
- raw responses stored only under `data/L15_savethem/cache/`;
- no secrets written to docs or source files.

Saved runtime artifacts:

- `data/L15_savethem/cache/toolsearch_*.json`
- `data/L15_savethem/cache/tool_*.json`
- `data/L15_savethem/cache/tool_round2_*.json`
- `data/L15_savethem/cache/tool_round3_*.json`

## API Findings

### Tool Discovery Contract

Observed facts about the configured `HUB_TOOLSEARCH_URL` endpoint:

| Topic | Finding |
| --- | --- |
| Request shape | JSON with `apikey` and `query`. |
| Query language | English worked; task warning about English-only tools appears accurate. |
| Response shape | JSON with `code`, `message`, original `query`, and `tools`. |
| Result count | In practice it returned 1-2 tools for our queries, not always 3 despite the task text. |
| Matching behavior | It is relevance-based, not exhaustive. Query wording matters. |

Discovered tools:

| Tool | URL | Observed role |
| --- | --- | --- |
| `maps` | `/api/maps` | Returns the terrain map for a city. |
| `wehicles` | `/api/wehicles` | Returns one vehicle definition for an exact vehicle name. |
| `books` | `/api/books` | Full-text note search with top-3 matching notes. |

Important detail:

- the endpoint is spelled `wehicles`, not `vehicles`;
- any implementation must use the typo exactly as returned by the API.

### `maps` Contract

Observed facts:

| Topic | Finding |
| --- | --- |
| Request shape | Same `apikey` + `query` JSON contract as `toolsearch`. |
| Query expectation | The query must be the city name alone. |
| Verbose query behavior | Natural-language queries like `map of the route to Skolwin` failed with `code: -716` and `I don't have maps for such a city.` |
| Success response | `code: 241`, `message: "Map found."`, `cityName`, `map`, and `text`. |
| Useful representation | `text` is a newline-joined 10x10 map and is easier to log than the nested array. |

Successful map query:

- `query: "Skolwin"`

Returned map:

```text
........WW
.......WW.
.T....WW..
......W...
..T...W.G.
....R.W...
...RR.WW..
SR.....W..
......WW..
.....WW...
```

### `wehicles` Contract

Observed facts:

| Topic | Finding |
| --- | --- |
| Request shape | Same `apikey` + `query` JSON contract. |
| Query expectation | The query must be one exact vehicle name. |
| Invalid query behavior | Descriptive queries failed with `code: -616` and `Unknown vehicle. Allowed values: rocket, horse, walk, car.` |
| Success response | `code: 230`, `message`, `name`, `note`, and `consumption.fuel` plus `consumption.food`. |

Supported exact queries:

- `walk`
- `horse`
- `car`
- `rocket`

Per-move consumption from the API:

| Mode | Fuel | Food |
| --- | --- | --- |
| `walk` | `0.0` | `2.5` |
| `horse` | `0.0` | `1.6` |
| `car` | `0.7` | `1.0` |
| `rocket` | `1.0` | `0.1` |

### `books` Contract

Observed facts:

| Topic | Finding |
| --- | --- |
| Request shape | Same `apikey` + `query` JSON contract. |
| Query behavior | Full-text search over notes. |
| Success response | `code: 220`, `message`, `query`, `search_mode`, `returned`, and `notes`. |
| Result limit | Always top 3 matches at most. |
| Zero-result behavior | Valid success payload with `returned: 0` and empty `notes`, for example for query `Skolwin`. |

Most useful notes discovered:

| Note id | What it teaches |
| --- | --- |
| `maps-endpoint` | `maps` is the standard source of terrain data; send only the destination city name. |
| `legend-markers` | `T` tree, `W` water, `R` rocks, `S` start, `G` goal. |
| `travel-methods` | Valid travel modes are `walk`, `horse`, `car`, `rocket`; special transition command is `dismount`. |
| `orientation-and-api` | The map uses north-at-top orientation; valid answer keywords are `up`, `down`, `left`, `right`, `dismount`, `walk`, `rocket`, `car`, `horse`. |
| `resource-consumption` | Fuel and food are consumed when an actual move happens, not when selecting the initial vehicle. Running out of either fails the mission immediately. |
| `no-gas-stations` | No refueling exists; late `dismount` is a valid fallback strategy. |
| `water-travel` | Water can be crossed by `walk` and `horse`; `car` cannot; `rocket` should not be used there. |
| `trees-and-burn` | Entering `T` adds `0.2` fuel cost for powered travel. |
| `vehicle-selection` | Vehicle is chosen only at departure; later the only allowed mode change is `dismount` to walking. |
| `beavers-north` | Low-confidence route hint: northern wet terrain may matter because of beaver activity. |

## Derived Mission Facts

These are the most important planning facts we can already treat as source-grounded.

### Terrain And Coordinates

- The map is `10x10`.
- Standard orientation applies: north is at the top.
- `S` is the starting tile and `G` is the goal tile.
- On the returned Skolwin map:
  - start is at row `8`, column `1` in 1-based coordinates;
  - goal is at row `5`, column `9` in 1-based coordinates.
- `R` blocks movement completely.
- `W` can be crossed on foot and by horse, but not safely by car or rocket.
- `T` is traversable by every mode, but adds `0.2` fuel cost to powered travel.

### Commands And Mode Changes

- Final verification payload still uses `answer` as an array.
- Valid command vocabulary is:
  - `up`
  - `down`
  - `left`
  - `right`
  - `dismount`
  - `walk`
  - `horse`
  - `car`
  - `rocket`
- Vehicle selection happens at the start of the route.
- You cannot switch from one vehicle to another mid-route.
- The only legal transition after departure is `dismount`, which switches to `walk`.

### Resource Rules

- Starting resources from the exercise are still `10` food and `10` fuel.
- Resource consumption happens on each move, not on initial mode selection.
- Running out of food fails immediately.
- Running out of fuel fails immediately.
- There is no refueling on the map.

### Immediate Implementation Consequences

- A route solver should model state as at least `(row, col, mode, fuel_left, food_left)`.
- `dismount` must be modeled as a state transition, not as a terrain effect.
- `maps` and `wehicles` should be wrapped with narrow deterministic adapters because their real query contracts are much stricter than the task description suggests.
- `books` is useful as a supporting evidence source, not as the primary map or vehicle data source.

## Design Decisions

### 1. Exploration Should Happen Before Agent Logic

This is now evidence-backed, not theoretical.

- `maps` looked like a search endpoint from the task description, but in reality it expects one exact city name.
- `wehicles` also looked broad, but in reality it expects one exact enum value.
- `books` is the only genuinely fuzzy search tool among the discovered endpoints.

If we had implemented the agent first and explored later, we would have baked the wrong contracts into the design.

### 2. The Internal App Contract Should Be Stricter Than The External API

The external API is discoverable but inconsistent in ergonomics:

- one endpoint name is misspelled;
- one endpoint is exact-match;
- one endpoint is full-text;
- error semantics are useful but not uniform in shape.

So the app should normalize all of this into internal adapters with explicit return models and explicit failure types.

### 3. LLM Usage Is Now Fixed To Bounded Discovery Only

The implementation now follows the selected architecture:

- one bounded OpenAI-driven explorer loop discovers tools and endpoint contracts,
- deterministic code validates the resulting facts,
- deterministic code computes the final route,
- optional Hub verification stays outside the model.

This keeps the exercise aligned with the learning goal without handing route
optimization or submission policy over to the model.

## Open Questions

These are the remaining unknowns or accepted edges after implementation:

- Should the final app deliberately preserve a dynamic discovery phase even though the useful endpoints are now known?
- Do we treat the `beavers-north` note as a meaningful heuristic hint, or ignore it entirely in the deterministic solver?
- Should the solver optimize for the smallest total resource burn, the safest feasible route, or the shortest instruction list once feasibility is satisfied?
- Is there any hidden terrain type outside the current Skolwin map, or can the implementation safely scope itself to `.`, `S`, `G`, `R`, `T`, and `W` for this task?
- The current keyword extraction from one note still yields `and horse` instead of `horse`; this does not affect solving, but the parser should be tightened if the note wording changes again.

## LLM Design Review

Review date: 2026-06-18.
Mode: non-production.
Scope: one bounded API discovery agent plus deterministic validation and route solving.
Result: PASS.

README is the source of truth for the accepted app contract and implementation
boundary.
This section keeps the checklist evidence and review reasoning.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Clear goal and output | YES | The app should discover the mission API, normalize route facts, compute a valid answer array, and optionally submit it. |
| Small workflow steps | YES | Planned workflow separates tool discovery, endpoint querying, exploration finish validation, deterministic knowledge normalization, route solving, and guarded submission. |
| Deterministic stable logic | YES | Terrain validation, vehicle consumption parsing, route legality, resource accounting, and final payload construction stay deterministic. |
| Clear step purpose | YES | The model chooses discovery actions only; code validates facts and computes the route. |
| LLM use justified | YES | The learning goal explicitly asks for an agent that discovers its environment instead of receiving a fixed known tool surface up front. |
| Model matches difficulty | YES | `gpt-5-mini` is enough for short English discovery prompts, narrow tool selection, and structured stop decisions. |
| Focused prompts | YES | The planned system prompt is limited to discovery policy, tool policy, missing-information behavior, and finish criteria. |
| Input and output tokens limited | YES | The design uses bounded tool-result snippets, compact state summaries, and a strict structured finish payload instead of long free-form narration. |
| Structured consumed output | YES | The exploration loop should stop through a strict structured `finish_exploration` payload that deterministic code validates against observed traces. |
| Current-step context only | YES | The model receives only current mission state, discovered tool metadata, compact trace summaries, and selected tool outputs. |
| Limited tool exposure | YES | The model should see only `search_tools`, `query_tool`, and `finish_exploration`. |
| No irrelevant history | YES | The app should not pass full raw archives or old responses by default when compact summaries are enough. |
| Batching, caching, or persistence | YES | Raw tool responses will be cached in runtime data and repeated exact requests can be reused locally. |
| Production progress mechanism | N/A | This is a local non-production exercise. |
| Production waiting visibility | N/A | No user-facing production UI exists. |
| Production disconnect survival | N/A | No long-running deployed job system is planned. |
| Production state persistence | N/A | Runtime state is persisted only for local debugging and replay. |
| Production pause and resume | N/A | The current workbench flow is synchronous and bounded. |
| Production user interaction | N/A | No interactive production session is planned. |
| Production UI separation | N/A | No UI exists. |
| Production event orchestration | N/A | A local bounded CLI run is sufficient for this exercise. |
| Validate model output | YES | The finish payload will be checked against discovered tool names, observed endpoint responses, and required route facts before solver use. |
| Treat output as untrusted | YES | The model can summarize facts, but code must reject unsupported or contradicted values. |
| Permissions outside model | YES | The model will not own direct raw network access, authorization, or final submission policy. |
| Missing inputs handled | YES | The explorer should continue discovering or stop as blocked instead of inventing missing rules or fake tools. |

## LLM Optimization Review

Review date: 2026-06-18.
Mode: non-production.
Scope: completed `L15_savethem` workbench workflow after real OpenAI and Hub verification.
Result: PASS.

The optimization review was recorded in README after the live run.
No blocking redesign was needed.
One accepted workbench limitation remains in non-critical command keyword parsing.

| Checklist area | Result | Evidence |
| --- | --- | --- |
| Task design | YES | The app solves one concrete task: discover the task API, normalize the route facts, compute a valid `answer` array, and optionally submit it. |
| Model usage | YES | The model is used only for bounded discovery decisions inside `agent.py`; route solving, validation, and submission stay deterministic in `knowledge.py`, `solver.py`, and `workflow.py`. |
| Prompt quality | YES | The exploration prompt keeps a narrow job: discover tools, query them carefully, stop only when grounded evidence is sufficient, and avoid inventing facts. |
| Context control | YES | Tool responses are reduced to compact summaries and observation ids before reuse; the model does not receive the whole raw archive every turn. |
| Tool and workflow efficiency | YES | The model sees only `search_tools`, `query_tool`, and `finish_exploration`; repeated observations are cached under `data/L15_savethem/cache/`; deterministic recovery avoids pointless re-prompting once enough evidence already exists. |
| Output stability | YES | `finish_exploration` requires structured output that is validated against observed tool names and observation ids before downstream use. |
| Cost and latency | YES | The live solved run used 17 model calls and 17 tool calls, and the trace log makes expensive steps obvious during review. |
| Production runtime lifecycle | N/A | This is a local learning CLI, not a deployed persistent system. |
| Safety and control | YES | Authorization and submission stay in backend code; missing facts block solving instead of being guessed; raw course feedback is kept only in ignored runtime data. |
| Review validation | YES | There is no obvious remaining LLM step that should be replaced by ordinary code without breaking the exercise goal of runtime environment discovery. |

## Live Run And Debugging Notes

Live verification date: 2026-06-18.
Outcome: solved; Hub accepted; raw response kept only under ignored runtime data.

### What Failed First

- The first live agent runs wasted turns on descriptive queries such as `map of Skolwin` and vehicle-intent prompts, while the real `maps` and `wehicles` endpoints expect exact values.
- The first parser pass was too literal about rock-note phrasing and looked for narrow wording instead of accepting the observed sentence structure.
- The model could collect enough observations to solve the task but still fail to call `finish_exploration` before hitting the iteration guard.

### What We Changed

- Added tool-level recovery hints in `tools.py` so exact-match endpoints push the model toward `Skolwin`, `walk`, `horse`, `car`, and `rocket` instead of vague prose.
- Raised the default discovery budget from `12` to `20` turns in `config.py` and added stronger exploration hints in `agent.py`.
- Added deterministic `attempt_ready_recovery` logic so `workflow.py` can continue when the observed evidence is already sufficient even if the model stops one step too late.
- Relaxed rule parsing in `knowledge.py` so grounded note text like `R marks rocks that block movement completely` is accepted reliably.

### Successful Run Evidence

- `data/L15_savethem/output/run_report.json` recorded `status: solved`, `exploration_status: ready`, `stop_reason: finish`, `model_calls_used: 17`, and `tool_calls_used: 17`.
- `data/L15_savethem/output/route.json` recorded the accepted command sequence and resource usage summary.
- `data/L15_savethem/logs/trace.jsonl` preserved the full exploration trace, including tool queries, summarized responses, and the final structured finish payload.
- The accepted route starts with `rocket`, uses `dismount` near the water barrier, and reaches the goal with positive fuel and food reserves.

## Implementation Plan

This plan is intentionally implementation-oriented but stops before source code changes that would require final design lock-in.

### Batch 0: Exploration Summary And Contract Freeze

Status: Completed.

Goal:
Turn exploratory API results into a stable local understanding of the tool contract.

Steps:

1. Query `toolsearch` with several English prompts.
2. Query each discovered tool with bounded examples.
3. Capture success and failure cases.
4. Record the real contract and design implications in DEV NOTES.

Checkpoint:

- raw exploration artifacts exist under `data/L15_savethem/cache/`;
- DEV NOTES describe real request and response behavior;
- no secret values are written to docs.

### Batch 1: Design Lock-In Before Source Work

Status: Completed.

Goal:
Choose whether this app will stay deterministic after exploration or will include an LLM-guided discovery stage.

Steps:

1. Decide between deterministic discovery and LLM-guided discovery.
2. If LLM remains in scope, create the app README first and run the required LLM design review before any source implementation.
3. Freeze the internal adapter contracts for `toolsearch`, `maps`, `wehicles`, and `books`.

Checkpoint:

- README exists if LLM usage is `Yes` or `Undecided`;
- chosen architecture is explicit;
- internal data model boundaries are clear enough to implement without more API guessing.

### Batch 2: Deterministic Data Adapters And Validation

Status: Completed.

Goal:
Build deterministic wrappers that convert raw API responses into validated internal models.

Steps:

1. Implement a guarded HTTP client for the Hub APIs used by this task.
2. Add typed parsers for tool discovery, map data, vehicle data, and note search.
3. Validate map size, legal terrain markers, and vehicle consumption values.
4. Preserve raw responses in runtime logs while exposing normalized data to the solver.

Checkpoint:

- the app can retrieve and validate the Skolwin map and all four vehicles;
- malformed or unexpected responses fail clearly;
- runtime artifacts land only under `data/L15_savethem/`.

### Batch 3: Route State Model And Solver

Status: Completed.

Goal:
Compute a feasible and then optimal route under fuel, food, terrain, and `dismount` constraints.

Steps:

1. Define the route state model.
2. Implement legal move generation with terrain and mode restrictions.
3. Add resource accounting including tree penalties.
4. Search for a feasible path and rank competing feasible paths deterministically.

Checkpoint:

- local solver output is explainable step by step;
- route legality is checked independently from optimization;
- at least one candidate route can be reconstructed from state transitions.

### Batch 4: Verification Flow And Safe Final Run

Status: Completed.

Goal:
Submit the chosen route to `/verify` and preserve a useful audit trail.

Steps:

1. Build the final answer payload.
2. Add guarded verification submission with masked request logging.
3. Preserve raw verification responses only under ignored runtime data.
4. Update README after the design is finalized and implementation is complete.

Checkpoint:

- verification payload is reproducible from normalized runtime artifacts;
- no raw flag or secret leaks into source docs;
- final run can be explained from logs instead of memory theater;
- local mocked end-to-end verification passed on 2026-06-18;
- guarded live OpenAI plus Hub verification also passed on 2026-06-18.
