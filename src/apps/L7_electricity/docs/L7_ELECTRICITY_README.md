# L7 Electricity README

## Table Of Contents

- [Purpose](#purpose)
- [Status](#status)
- [Workflow](#workflow)
- [Board Representation](#board-representation)
- [LLM And Vision Design](#llm-and-vision-design)
- [Implementation Plan](#implementation-plan)
- [Configuration](#configuration)
- [Data Paths](#data-paths)
- [Main Modules](#main-modules)
- [Run](#run)
- [Verification](#verification)
- [Assumptions And Risks](#assumptions-and-risks)
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

Current status: design planned, implementation not started.

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

## Implementation Plan

Planned implementation steps:

1. Create the application skeleton and configuration loader.
2. Add data path helpers for `data/L7_electricity/input/`, `data/L7_electricity/references/`, `data/L7_electricity/output/`, and `data/L7_electricity/cache/`.
3. Implement core tile models and coordinate validation.
4. Implement deterministic rotation utilities.
5. Implement the solver that converts current and target board maps into a rotation sequence.
6. Add unit tests for tile rotation and board solving using hand-written board maps.
7. Implement a hub client for downloading board images and submitting one rotation per request.
8. Add masked request and response logging.
9. Define the image parsing design in this README with enough detail for the LLM design checklist.
10. Review the LLM and vision scope with `_agent/instructions/llm_design_checklist.md`.
11. After the design review passes, implement the image parser.
12. Add parser validation and failure handling.
13. Run the full workflow in a guarded mode with a small maximum number of rotation requests.
14. Verify the final board state and capture the hub flag when returned.

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
| `L7_ELECTRICITY_VISION_MODEL` | Vision model name used by the image parser after design approval. |

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
| `config.py` | Environment loading, configuration validation, and runtime guards. |
| `paths.py` | Repository-relative data path construction. |
| `models.py` | Typed board, tile, coordinate, and run result structures. |
| `rotation.py` | Direction rotation and tile normalization helpers. |
| `solver.py` | Deterministic board comparison and rotation sequence calculation. |
| `hub_client.py` | Board image download and rotation verification requests. |
| `image_parser.py` | Image-to-board-map parser, added only after LLM design approval. |
| `logging_utils.py` | Masked request, response, and run report persistence. |

Each class, function, and method should include a short `#` purpose comment, following the repository instructions.

## Run

Planned command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L7_electricity.main
```

The command is not available yet because the application has not been implemented.

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
.\venv\Scripts\python.exe -m pytest tests
```

The exact test path can be narrowed after the test layout is created.

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

## LLM Design Reviews

No LLM design review has passed yet.

Before implementing `image_parser.py` or any agent loop that uses a model to interpret board images, review the planned scope with:

```text
_agent/instructions/llm_design_checklist.md
```

The first recommended review scope is:

```text
MVP1: vision parser and deterministic rotation solver orchestration
```

Implementation boundary until that review passes:

- deterministic tile models, rotation utilities, solver, configuration, and masked logging may be implemented,
- model-based image parsing and agentic tool orchestration should wait for checklist approval.

## Reference Alignment

This design was shaped by:

- `_agent/references/exercises/L7_exercise.md`
- `_agent/references/L1_task_decomposition_and_pipeline_design.md`
- `_agent/references/L4_image_recognition_and_generation_agents.md`
- `_agent/references/L3_tool_family_and_response_contracts.md`

How they influenced the design:

- the workflow is decomposed into perception, validation, deterministic solving, execution, and verification,
- deterministic rotation logic stays outside the model,
- model output is validated before it can drive hub requests,
- the future agent should use compact tools with clear response contracts instead of raw free-form actions.
