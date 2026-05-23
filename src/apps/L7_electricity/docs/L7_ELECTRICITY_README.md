# L7 Electricity README

## Table Of Contents

- [Purpose](#purpose)
- [Status](#status)
- [Workflow](#workflow)
- [Board Representation](#board-representation)
- [LLM And Vision Design](#llm-and-vision-design)
- [Image Parsing Design](#image-parsing-design)
- [Implementation Plan](#implementation-plan)
- [Configuration](#configuration)
- [Data Paths](#data-paths)
- [Main Modules](#main-modules)
- [Run](#run)
- [Verification](#verification)
- [Assumptions And Risks](#assumptions-and-risks)
- [LLM Checklist Review](#llm-checklist-review)
- [LLM Design Reviews](#llm-design-reviews)
- [Reference Alignment](#reference-alignment)

## Purpose

`L7_electricity` is a learning application for the AI_devs `electricity` exercise.

The task is to solve a 3x3 electrical cable puzzle by rotating board tiles until three power plants are connected to the emergency power source. The hub stores the current board as a PNG image, accepts one clockwise 90-degree tile rotation per verification request, and returns the final flag when the board reaches the correct configuration.

The main learning goal is to separate visual perception from deterministic puzzle solving:

- a vision or image parsing step should convert board images into structured tile descriptions,
- ordinary code should calculate tile rotations from those descriptions,
- an agent can orchestrate the workflow and call tools, but stable rotation logic should not live inside prompt reasoning.

## Status

Current status: deterministic foundation implemented, vision parser not started.

Implemented so far:

- configuration loading and runtime path helpers,
- core board, coordinate, direction, and tile models,
- deterministic rotation utilities,
- deterministic board solver,
- unit tests for rotation and solving,
- Hub client for image download and one-tile rotation requests,
- masked request and response logging helpers.

No hub requests should be sent by this app until configuration, logging, and request masking are implemented.

No LLM-powered or vision-powered implementation is approved yet. The LLM and vision workflow must pass `_agent/instructions/llm_design_checklist.md` before implementation starts.

## Workflow

Planned application flow:

1. Load configuration from environment variables.
2. Download the current board PNG from the hub data endpoint.
3. Save the current board image to `data/L7_electricity/input/current_board.png`.
4. Download or load the target solved board image.
5. Save the target board image to `data/L7_electricity/references/solved_board.png`.
6. Parse each board image into a structured 3x3 tile map.
7. Validate that both parsed boards contain exactly nine known tile descriptors.
8. Compare each current tile with the target tile at the same coordinate.
9. Calculate the number of clockwise rotations needed for each tile.
10. Send one verification request per planned rotation.
11. Save masked request and response records under `data/L7_electricity/output/`.
12. After a rotation batch, download the current board again and verify it against the target board.
13. Stop when the hub returns the final flag or when validation detects that the parsed board state is inconsistent.

The first implementation should prefer a small fixed workflow. A broader agent loop can be added later if it improves learning value, but it should call the same deterministic tools instead of replacing them with free-form model reasoning.

## Board Representation

Board positions use the hub coordinate format:

| Position | Meaning |
|---|---|
| `1x1` | Row 1, column 1 |
| `1x2` | Row 1, column 2 |
| `1x3` | Row 1, column 3 |
| `2x1` | Row 2, column 1 |
| `2x2` | Row 2, column 2 |
| `2x3` | Row 2, column 3 |
| `3x1` | Row 3, column 1 |
| `3x2` | Row 3, column 2 |
| `3x3` | Row 3, column 3 |

Each tile should be represented as a set of cable exits.
The set size is part of the tile shape: a tile may have two exits, such as a bend or straight connector, or three exits, such as a T-junction.

```json
{
  "1x1": ["right", "down"],
  "1x2": ["left", "right"],
  "1x3": ["left", "down"],
  "2x2": ["up", "right", "down"]
}
```

Allowed directions:

- `up`
- `right`
- `down`
- `left`

Allowed exit counts:

- `2` for straight or bend connectors,
- `3` for T-junction connectors.

Clockwise rotation transforms directions as follows:

| Before | After one clockwise rotation |
|---|---|
| `up` | `right` |
| `right` | `down` |
| `down` | `left` |
| `left` | `up` |

The solver should find the smallest number of clockwise rotations from `0` to `3` that makes a current tile match the target tile. A tile with two exits must only match a target tile with the same two-exit shape after rotation, and a tile with three exits must only match a target tile with the same three-exit shape after rotation.

## LLM And Vision Design

The planned design uses the model for perception, not for deterministic rotation logic.

Planned model responsibility:

- inspect a prepared board image or prepared tile image,
- describe each tile as a structured set of exits,
- return only the agreed schema,
- include an uncertainty marker when a tile is ambiguous.

Planned deterministic code responsibility:

- split or normalize images before model analysis,
- validate model output shape and allowed values,
- rotate tile descriptors,
- compare current and target descriptors,
- build the rotation sequence,
- submit rotation requests,
- persist masked logs and run reports.

This interpretation remains compatible with the exercise guidance that an agent can calculate rotations. In this design, the agent calculates rotations by invoking a deterministic solver tool rather than by improvising the calculation in natural language.

Vision model output must be treated as untrusted until validation passes. If the parser returns an invalid coordinate, an unknown direction, a missing tile, an extra tile, or low confidence, the workflow should stop before sending rotation requests.

## Image Parsing Design

This section defines the planned `image_parser.py` scope for the future LLM design review.

Review mode target:

- `non-production`

Expected final parser output:

- one validated `Board` object for the current board image,
- one validated `Board` object for the solved reference image,
- optional parser metadata for debugging, such as the model name, crop count, and uncertain tiles.

The parser should be a fixed workflow, not a free-form agent loop.

### Parsing Workflow

Planned parsing steps:

1. Load one local PNG file from `data/L7_electricity/input/current_board.png` or `data/L7_electricity/references/solved_board.png`.
2. Deterministically crop the full 3x3 board into 9 tile images and save temporary crops under `data/L7_electricity/cache/tiles/`.
3. Send either:
   - one tile crop at a time to the vision model, or
   - one prepared 3x3 board image only if tile-by-tile parsing proves worse in practice.
4. Ask the model to return only the exits visible on that tile.
5. Validate the model output against the agreed schema and allowed values.
6. Assemble the 9 validated tile outputs into one board map.
7. Convert the board map into a `Board` domain object.
8. Stop with a hard failure if validation fails and no bounded retry remains.

Default design choice:

- prefer tile-by-tile parsing over whole-board parsing, because each model call then sees one small local classification task instead of 9 coupled decisions.

### Model Steps

Planned model usage is intentionally narrow.

Step A:

- Input: one tile crop image.
- Goal: identify which edges contain cable exits.
- Why model is needed: image understanding is the uncertain part that is hard to replace with plain code at this stage.
- Output: one tiny structured record describing only that tile.
- Planned primary model: `gpt-5-mini`.
- Planned fallback model: `gpt-4.1` if the primary model proves unreliable on small tile-edge details.

Step B:

- No second reasoning model step is planned by default.
- Assembly, validation, solving, and request sequencing should stay deterministic in Python code.

If later testing shows that one tile crop is insufficient, the first fallback should still be a narrow model step, such as sending one tile crop plus a simple textual coordinate label. The design should avoid a large prompt that asks the model to parse the whole board and also plan the rotations.

### Structured Output Contract

Planned per-tile schema:

```json
{
  "coordinate": "2x3",
  "exits": ["up", "left"],
  "confidence": "high"
}
```

Field rules:

| Field | Type | Allowed values | Notes |
|---|---|---|---|
| `coordinate` | string | `1x1` to `3x3` | Passed in by code and echoed back for validation. |
| `exits` | array of strings | `up`, `right`, `down`, `left` | Must contain exactly `2` or `3` unique values. |
| `confidence` | string | `high`, `medium`, `low` | Used only for validation and retry decisions. |

Planned full-board assembled shape before domain conversion:

```json
{
  "1x1": ["right", "down"],
  "1x2": ["left", "right"],
  "1x3": ["left", "down"],
  "2x1": ["up", "down"],
  "2x2": ["up", "right", "down"],
  "2x3": ["up", "left"],
  "3x1": ["up", "right"],
  "3x2": ["left", "right", "down"],
  "3x3": ["up", "left"]
}
```

The model should not return explanations, chain-of-thought, long descriptions, rotation advice, or any fields not required by downstream code.

### Prompt Plan

Illustrative prompt example for one tile crop:

```text
You are reading one tile from a 3x3 cable puzzle.
Return JSON only.
Coordinate: 2x3
List only the cable exits visible on the tile edges.
Allowed exits: up, right, down, left.
Return exactly 2 or 3 unique exits.
Also return confidence as high, medium, or low.
Do not explain.
```

This block is a design example, not a locked final template.

Implementation rule:

- keep the real parser prompt semantically equivalent to this example,
- allow small wording changes if testing improves reliability,
- do not expand the prompt into a multi-purpose instruction that mixes tile parsing with solving or tool decisions.

Prompt constraints:

- keep the instruction short and stable across calls,
- include only the current tile image and its coordinate,
- do not include full conversation history,
- do not include solved examples unless validation data later proves they are necessary.

Model selection rule:

- default `L7_ELECTRICITY_VISION_MODEL` to `gpt-5-mini`,
- switch to `gpt-4.1` if evaluation on real tile crops shows that `gpt-5-mini` misses edge exits too often,
- do not introduce a larger agent-style reasoning model unless a later review changes the approved boundary.

### Context And Tool Exposure

The planned parser step should receive only:

- one tile crop image,
- one coordinate label,
- the short parser prompt,
- the selected vision model name.

The planned parser step should not receive:

- the full run history,
- previous failed parser outputs unless a bounded retry explicitly uses them,
- the Hub verification tool,
- the solver,
- any write-capable tool beyond saving local cache artifacts already controlled by code.

This means the future agent or workflow should keep tool exposure narrow:

- image parsing step: vision model only,
- downstream board solving step: deterministic Python only,
- downstream rotation execution step: Hub client only.

### Token, Retry, And Caching Plan

Token control rules:

- use one small prompt per tile,
- keep output to the tiny schema only,
- avoid sending the full board unless tile crops fail,
- avoid sending both current and solved boards in one model call by default.

Retry rules:

- allow at most one bounded retry per tile when schema validation fails or confidence is `low`,
- the retry may tighten the prompt but must not broaden tool access,
- if the retry still fails, stop the workflow and report the exact tile coordinate.

Caching rules:

- save prepared tile crops under `data/L7_electricity/cache/tiles/`,
- persist the raw per-tile parsed JSON under `data/L7_electricity/cache/` when helpful for debugging,
- reuse the solved board parse if the solved image is unchanged across runs,
- do not reuse the current board parse after any rotation request.

### Validation Rules

Validation must happen before any parsed output reaches the solver.

Per-tile validation:

- `coordinate` must equal the requested tile coordinate,
- `exits` must contain only allowed direction values,
- `exits` must contain exactly `2` or `3` unique values,
- `confidence` must be one of `high`, `medium`, `low`.

Full-board validation:

- assembled output must contain exactly 9 coordinates,
- there must be no duplicates and no missing tiles,
- every tile must convert successfully into the `Tile` domain model,
- the final map must convert successfully into the `Board` domain model.

Failure handling:

- if any tile is invalid after the bounded retry, fail explicitly,
- do not guess missing exits,
- do not continue with partial board data,
- do not send any Hub rotation request until the whole board is valid.

### Approved Boundary For The Next Review

The intended checklist scope for step 10 is:

```text
MVP1: tile-by-tile vision parsing of current and solved board images, deterministic board assembly, deterministic solver orchestration
```

Out of scope for that review:

- autonomous multi-agent exploration,
- open-ended reflection loops,
- model-written rotation plans,
- unbounded retries,
- production-style resumable jobs.

## Implementation Plan

Planned implementation steps:

1. Completed: create the application skeleton and configuration loader.
2. Completed: add data path helpers for `data/L7_electricity/input/`, `data/L7_electricity/references/`, `data/L7_electricity/output/`, and `data/L7_electricity/cache/`.
3. Completed: implement core tile models and coordinate validation.
4. Completed: implement deterministic rotation utilities.
5. Completed: implement the solver that converts current and target board maps into a rotation sequence.
6. Completed: add unit tests for tile rotation and board solving using hand-written board maps.
7. Completed: implement a hub client for downloading board images and submitting one rotation per request.
8. Completed: add masked request and response logging.
9. Completed: define the image parsing design in this README with enough detail for the LLM design checklist.
10. Completed: review the LLM and vision scope with `_agent/instructions/llm_design_checklist.md`.
11. Pending: after the design review passes, implement the image parser.
12. Pending: add parser validation and failure handling.
13. Pending: run the full workflow in a guarded mode with a small maximum number of rotation requests.
14. Pending: verify the final board state and capture the hub flag when returned.

The recommended first milestone is the deterministic solver plus tests. This gives a stable foundation before any uncertain vision step is introduced.

## Configuration

Required environment variables:

| Name | Purpose |
|---|---|
| `AI_DEVS_API_KEY` | API key used to authenticate hub requests. |
| `HUB_DATA_BASE_URL` | Base hub data location used to build the board image request. |
| `HUB_VERIFY_URL` | Hub verification endpoint used for rotation requests. |
| `HUB_SOLVED_IMAGE_URL` | Location of the solved reference image. |

Optional environment variables:

| Name | Purpose |
|---|---|
| `L7_ELECTRICITY_RESET_ON_START` | When enabled, download the board with the hub reset option before solving. |
| `L7_ELECTRICITY_MAX_ROTATIONS` | Hard guard for the maximum number of rotation requests in one run. |
| `L7_ELECTRICITY_VISION_MODEL` | Vision model name used by the image parser after design approval. Recommended default: `gpt-5-mini`. Planned fallback: `gpt-4.1`. |

Secrets must stay in `.env` or another approved secret store. Source code, Markdown files, reports, logs, and commit messages must not contain real API keys, private URLs, tokens, or unmasked request payloads.

## Data Paths

Runtime files should live outside the application source directory:

| Path | Purpose |
|---|---|
| `data/L7_electricity/input/current_board.png` | Latest downloaded current board image. |
| `data/L7_electricity/references/solved_board.png` | Target solved board image. |
| `data/L7_electricity/cache/tiles/` | Optional prepared tile crops or normalized images. |
| `data/L7_electricity/output/run_report.json` | Chronological run report with masked requests and responses. |
| `data/L7_electricity/output/rotation_plan.json` | Calculated rotation plan for review and debugging. |

The run report should never store the raw API key. Request payloads should either omit `apikey` or store it as `***REDACTED***`.

## Main Modules

Planned source files:

| Module | Responsibility |
|---|---|
| `main.py` | CLI entrypoint and top-level workflow orchestration. |
| `config.py` | Environment loading, configuration validation, runtime guards, and repository-relative path construction. |
| `models.py` | Typed board, tile, coordinate, and run result structures. |
| `rotation.py` | Direction rotation and tile normalization helpers. |
| `solver.py` | Deterministic board comparison and rotation sequence calculation. |
| `hub_client.py` | Board image download and rotation verification requests. |
| `image_parser.py` | Image-to-board-map parser, added only after LLM design approval. |
| `logging_utils.py` | Masked request, response, and artifact persistence. |

Each class, function, and method should include a short `#` purpose comment, following the repository instructions.

## Run

Planned command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L7_electricity.main
```

The command is available now and currently loads configuration, ensures runtime directories, and prints a readiness summary.

## Verification

Verification should be added incrementally:

1. Run unit tests for clockwise direction rotation.
2. Run unit tests for tile matching after `0`, `1`, `2`, and `3` rotations.
3. Run unit tests for board solving from hand-written current and target maps.
4. Validate that malformed board maps fail before any hub request is sent.
5. Validate that masked logging never persists raw secrets.
6. After image parsing is implemented, compare parser output against a manually reviewed board map.
7. Run a guarded end-to-end attempt with `L7_ELECTRICITY_MAX_ROTATIONS` set to a small explicit value.
8. Confirm that the final run stops with either a hub flag or a clear validation error.

The simplest practical first check after implementing the solver should be:

```powershell
.\venv\Scripts\python.exe -m unittest tests.L7_electricity.test_rotation_and_solver
```

This focused suite currently verifies deterministic tile rotation and board solving from hand-written maps.

## Assumptions And Risks

Assumptions:

- The target solved board image is stable for the exercise.
- Each board tile can be represented by two or three cable exits on the four cardinal edges.
- Rotation is always clockwise and always changes exactly one tile by 90 degrees.
- The hub returns the flag only after the correct final board configuration is reached.

Risks:

- Vision models may misread small cable shapes, especially on a full 3x3 image.
- A wrong parsed tile can cause unnecessary rotations and may require a reset.
- The board state changes after each successful rotation request, so stale image data must not be reused for final verification.
- The hub may rate-limit or return transient errors during multi-request rotation batches.
- If model output is used without validation, it can drive incorrect external API calls.

Mitigations:

- Parse and validate structured tile maps before solving.
- Prefer cropped or normalized tile images if full-board parsing is unreliable.
- Keep a hard maximum number of rotation requests per run.
- Verify the refreshed board after each planned batch.
- Save masked run artifacts for debugging and learning.

## LLM Checklist Review

Review date:

- `2026-05-23`

Review mode:

- `non-production`

Review scope:

- `MVP1: tile-by-tile vision parsing of current and solved board images, deterministic board assembly, deterministic solver orchestration`

Checklist:

| Section | Checklist item | Result | Design note |
|---|---|---|---|
| Scope And Workflow | The application has a clearly defined goal and expected output. | YES | Goal: parse two board PNG files into validated `Board` objects, solve deterministic rotations, and prepare one-turn Hub requests. |
| Scope And Workflow | The workflow is split into small steps when one model call would mix multiple responsibilities. | YES | The design splits cropping, tile parsing, schema validation, board assembly, solving, and Hub execution into separate steps. |
| Scope And Workflow | Deterministic code is planned for stable logic, and LLM calls are reserved for language or reasoning tasks. | YES | Only tile-image interpretation uses a vision model; rotation math, validation, solving, and request sequencing stay in Python. |
| Scope And Workflow | Each planned workflow step has a clear purpose. | YES | README now defines one purpose per step from local PNG load through bounded parser retry and deterministic solving. |
| Model And Prompt Plan | Each LLM step has a reason for using a model instead of ordinary code. | YES | The tile parser uses a model only for visual exit recognition, which is the one uncertain perception task. |
| Model And Prompt Plan | The selected model for each step matches the expected difficulty of that step. | YES | `L7_ELECTRICITY_VISION_MODEL` is scoped to `gpt-5-mini` as the primary model for narrow tile-by-tile image classification, with `gpt-4.1` as the fallback if small edge details need a stronger vision pass. |
| Model And Prompt Plan | Prompts are planned to be short, focused, and limited to the current step. | YES | The planned prompt covers only one tile crop, one coordinate, one exit schema, and one confidence field. |
| Model And Prompt Plan | Token usage is intentionally limited for both model input and model output. | YES | The design prefers tile-by-tile parsing, tiny JSON output, no full history, and no full-board prompt by default. |
| Model And Prompt Plan | Structured outputs are planned wherever code will consume the result. | YES | The parser schema explicitly defines `coordinate`, `exits`, and `confidence`, and the assembled board map is defined before implementation. |
| Context And Tools | The design limits context to only what the current step needs. | YES | The parser step receives one tile crop, one coordinate label, one short prompt, and the selected model name. |
| Context And Tools | The design limits tool exposure to only the tools needed for the current step. | YES | Vision parsing is isolated from the solver and Hub tools; downstream execution uses deterministic code plus the Hub client only. |
| Context And Tools | The design avoids passing full history, full datasets, or irrelevant examples by default. | YES | The parser design explicitly excludes full run history, solved examples by default, and unrelated tool outputs. |
| Context And Tools | The workflow includes batching, caching, or persisted intermediate results where repeated or long-running calls are likely. | YES | Tile crops live under `data/L7_electricity/cache/tiles/`, solved-board parses may be reused, and per-tile JSON may be cached for debugging. |
| Runtime Performance And Task Lifecycle | Production-only: Long-running LLM, tool, media generation, or agent tasks have a planned progress or heartbeat mechanism. | N/A | Non-production local exercise; no deployed long-running job system is planned. |
| Runtime Performance And Task Lifecycle | Production-only: The user can understand what is happening while waiting for slow model, tool, media generation, or agent work. | N/A | Non-production CLI workflow; production-style waiting UX is out of scope. |
| Runtime Performance And Task Lifecycle | Production-only: Long-running work can continue safely if the user closes the browser, loses connection, or leaves the application. | N/A | Non-production local run; no browser-coupled runtime exists in this app. |
| Runtime Performance And Task Lifecycle | Production-only: The workflow defines how task state, intermediate outputs, and final results are persisted. | N/A | Production-grade resumable task persistence is out of scope for this local exercise. |
| Runtime Performance And Task Lifecycle | Production-only: The design supports pausing and resuming tasks when waiting for user approval, tool results, retries, or agent completion. | N/A | Non-production local CLI run; pause/resume orchestration is not planned. |
| Runtime Performance And Task Lifecycle | Production-only: User interaction during long-running work is planned, such as message queueing, cancellation, or opening a separate thread. | N/A | Non-production local exercise; no interactive multi-session runtime is planned. |
| Runtime Performance And Task Lifecycle | Production-only: UI state is not tightly coupled to backend execution state for long-running tasks. | N/A | Non-production local CLI workflow; no UI/backend split applies here. |
| Runtime Performance And Task Lifecycle | Production-only: Event-driven or job-based orchestration is considered where a synchronous request/response flow would be fragile. | N/A | The current scope is a short local workflow rather than a production job system. |
| Validation And Safety | The design includes validation before model output is used downstream. | YES | The parser design defines per-tile schema checks and full-board domain validation before the solver runs. |
| Validation And Safety | The design treats model output as untrusted until validation passes. | YES | The README explicitly states that invalid coordinates, exits, confidence values, or incomplete boards must stop the workflow. |
| Validation And Safety | The design keeps authorization, permissions, and risky actions outside the model. | YES | The model never receives the Hub verification tool or secret-bearing request authority; Hub calls stay in deterministic client code. |
| Validation And Safety | The workflow handles missing required inputs without guessing important values. | YES | Missing or invalid tiles fail explicitly after one bounded retry; the workflow does not guess exits or continue with partial board data. |

Checklist result:

- PASS

Approved implementation boundary from this review:

- implement `image_parser.py` for tile-by-tile parsing of current and solved board images,
- implement parser-side schema validation, bounded retry, cache usage, and conversion into `Board`,
- keep solving and Hub request sequencing deterministic,
- do not add model-written rotation plans, open-ended agent loops, or unbounded retries without a separate review.

## LLM Design Reviews

| Date | Scope | Checklist | Result | Approved Implementation Boundary |
|---|---|---|---|---|
| 2026-05-23 | MVP1: tile-by-tile vision parsing of current and solved board images, deterministic board assembly, deterministic solver orchestration | `_agent/instructions/llm_design_checklist.md` | PASS | Implement `image_parser.py`, parser validation, bounded retry, cache usage, and deterministic solver orchestration only. Model-written rotation plans, open-ended agent loops, and unbounded retries require separate review. |

## Reference Alignment

This design was shaped by:

- `_agent/references/exercises/L7_exercise.md`
- `_agent/references/L1_task_decomposition_and_pipeline_design.md`
- `_agent/references/L1_structured_outputs_and_validation.md`
- `_agent/references/L4_image_recognition_and_generation_agents.md`
- `_agent/references/L3_tool_family_and_response_contracts.md`

How they influenced the design:

- the workflow is decomposed into perception, validation, deterministic solving, execution, and verification,
- model output is constrained to a tiny schema before Python code consumes it,
- deterministic rotation logic stays outside the model,
- model output is validated before it can drive hub requests,
- the future agent should use compact tools with clear response contracts instead of raw free-form actions.
