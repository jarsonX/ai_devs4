# L7 Electricity README

## Table Of Contents

- [Purpose](#purpose)
- [Status](#status)
- [Workflow](#workflow)
- [Board Representation](#board-representation)
- [LLM And Vision Design](#llm-and-vision-design)
- [Deterministic Support Plan](#deterministic-support-plan)
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

`L7_electricity_gpt_5_mini` is a paused experimental documentation track for a cheaper version of the `electricity` solution around `gpt-5-mini`.

The task remains the same:

- read the current 3x3 cable board from the Hub image,
- compare it with the solved target board,
- calculate deterministic clockwise rotations,
- submit them until the board reaches the correct state.

The goal of this track is different from the working `gpt-5.5` snapshot:

- keep the deterministic solver,
- keep the stable preprocessing improvements,
- add extra deterministic support so that `gpt-5-mini` has a smaller and easier perception job.

This documentation is being kept so the experiment can be resumed later without rebuilding the design context from scratch.

## Status

Current status: this track is paused.

It should be read as a design snapshot for a possible future return, not as an active implementation plan.

What is already known:

- the `gpt-5.5` version solved the task end to end on real services,
- `gpt-5-mini` was promising enough to reach guarded diagnostic runs,
- `gpt-5-mini` was not yet stable enough to be trusted as the default parser model,
- the next technical direction would be to reduce the burden on the model with deterministic support layers.

Current decision:

- keep `gpt-5.5` as the active working version,
- stop active implementation work on the `gpt-5-mini` variant for now,
- preserve the design and notes in case the experiment becomes worth resuming later.

Reference working snapshot:

- `src/apps/L7_electricity/L7_electricity_gpt_5_5/`

## Workflow

Planned application flow for this track:

1. Reuse the stable deterministic board download flow.
2. Reuse deterministic board-rectangle isolation.
3. Reuse light inner tile crop before model calls.
4. Replace solved-board vision parsing with a deterministic solved reference map.
5. Parse only the current board with `gpt-5-mini`.
6. Validate the parsed current board with stronger deterministic checks.
7. Solve the board deterministically.
8. Execute a guarded or full rotation sequence.
9. Re-parse the refreshed current board and compare expected versus observed changes.
10. Stop on inconsistency instead of trusting unstable vision output.

Current workflow implementation state:

- download, preprocessing, solving, and rotation execution already exist in the main working version,
- the mini-specific deterministic supports were not implemented before this track was paused.

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

Allowed directions:

- `up`
- `right`
- `down`
- `left`

Allowed tile exit counts:

- `2` for straight or corner tiles,
- `3` for T-junction tiles.

## LLM And Vision Design

This track keeps the same high-level rule:

- the model is used for perception,
- deterministic code is used for rotation logic and safety checks.

Planned `gpt-5-mini` role:

- parse only the current board tile exits,
- return structured JSON only,
- stay inside a narrow tile-classification task.

Planned deterministic code role:

- provide the solved reference map without calling the model,
- validate tile shape type and orientation more strictly,
- compare expected post-rotation changes against observed post-rotation parses,
- reject suspicious board transitions before continuing.

## Deterministic Support Plan

The current plan is to add the following deterministic supports around `gpt-5-mini`:

1. Deterministic solved reference map:
   - remove solved-board vision parsing from the critical path,
   - reduce the number of model calls,
   - cut one major source of parse mismatch.

2. Regression harness on frozen tile crops:
   - compare `gpt-5-mini` and `gpt-5.5` on the same difficult tile images,
   - measure where `gpt-5-mini` fails most often,
   - use those cases to drive prompt or validation changes.

3. Two-stage tile classification:
   - stage 1: classify `straight`, `corner`, or `t-junction`,
   - stage 2: classify orientation only within that shape family,
   - keep both stages bounded and schema-validated.

4. Extra validation heuristics:
   - detect implausible changes on tiles that were not rotated,
   - compare expected and observed post-rotation local shape changes,
   - fail fast when a new parse contradicts deterministic expectations.

## Implementation Plan

Planned steps for this track if work resumes:

1. Create this design and notes workspace.
2. Define the deterministic solved reference map format.
3. Build a small benchmark set from saved tile crops.
4. Review whether the two-stage classifier changes the approved LLM design scope.
5. Add deterministic validation around current-board parsing.
6. Run guarded comparisons on `gpt-5-mini`.
7. Decide whether `gpt-5-mini` can become acceptable for this exercise.

Current completion state:

- step `1` is done,
- steps `2` to `7` are paused and remain TBU.

## Configuration

Expected configuration is likely to remain close to the working app:

| Name | Purpose |
|---|---|
| `AI_DEVS_API_KEY` | Hub authentication. |
| `OPENAI_API_KEY` | OpenAI API access for tile parsing. |
| `HUB_VERIFY_URL` | Rotation verification endpoint. |
| `L7_ELECTRICITY_VISION_MODEL` | Expected to be `gpt-5-mini` for this track. |

Configuration details that change runtime layout or cache strategy were not finalized before the experiment was paused.

## Data Paths

Likely data-path options still need a final decision if this track is resumed:

- reuse `data/L7_electricity/...` and isolate only cache keys,
- or create a dedicated experiment path such as `data/L7_electricity_gpt_5_mini/...`.

This decision is currently TBU because the experiment is paused.

## Main Modules

Expected module ownership for this track if implementation resumes:

| Module | Planned role |
|---|---|
| `config.py` | TBU |
| `image_parser.py` | Add mini-oriented deterministic support layers. |
| `solver.py` | Reuse deterministic solving logic. |
| `workflow.py` | Add comparison and validation checkpoints. |
| `benchmark / harness module` | Planned new support for frozen tile-crop evaluation. |

The exact code layout is still TBU because implementation never moved past the design workspace.

## Run

Probable command shape:

```powershell
.\venv\Scripts\python.exe -m src.apps.L7_electricity.L7_electricity_gpt_5_5.main
```

There is no active mini-track run command at the moment.
Mini-track specific run commands are still TBU if the experiment returns.

## Verification

Planned verification sequence if work resumes:

1. Confirm that the deterministic solved reference map matches the known target layout.
2. Run the regression harness on saved difficult tile crops.
3. Compare `gpt-5-mini` outputs against the stable `gpt-5.5` baseline on the same dataset.
4. Run guarded end-to-end attempts with explicit low rotation caps.
5. Check whether deterministic post-rotation validation catches unstable parses early.
6. Attempt a full run only after guarded runs become stable enough.

Current verification state:

- not started for this dedicated mini track,
- benchmark dataset and deterministic solved reference are still TBU.

## Assumptions And Risks

Assumptions:

- the solved target board can be represented safely without a model call,
- `gpt-5-mini` can become usable if the visual task is narrowed enough,
- the current preprocessing pipeline is already good enough to support the experiment.

Risks:

- even with deterministic supports, `gpt-5-mini` may still be too unstable on edge cases,
- two-stage parsing may add complexity without enough quality gain,
- diagnostic validation may catch errors but not eliminate them,
- the experiment may still conclude that the cheaper model is not worth the extra engineering.

## LLM Design Reviews

Current state:

- the original working `L7_electricity` app already passed its MVP1 LLM design review,
- this mini track has not yet recorded a separate review for any new LLM workflow change,
- the experiment was paused before a separate mini-specific implementation scope was approved,
- if the two-stage parser becomes more than a prompt tweak, a new scoped review should be added here.

## Reference Alignment

This experimental track follows the same reference family as the working solution:

- `_agent/references/exercises/L7_exercise.md`
- `_agent/references/L1_task_decomposition_and_pipeline_design.md`
- `_agent/references/L1_structured_outputs_and_validation.md`
- `_agent/references/L4_image_recognition_and_generation_agents.md`

The key difference is not the course goal, but the engineering trade-off preserved in these notes:

- accept more deterministic support work,
- in exchange for a chance to make `gpt-5-mini` good enough for the same task.
