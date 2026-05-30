<!-- This file gives a quick overview of what the FindHim app does and which modules are responsible for each part. -->

## L2 FindHim

This app solves the AI_devs `findhim` task using an agent with OpenAI Function Calling.

## Table Of Contents

- [L2 FindHim](#l2-findhim)
  - [What it does](#what-it-does)
  - [Main modules](#main-modules)
  - [Notes](#notes)
- [What This Task Should Teach](#what-this-task-should-teach)

### What it does

1. Loads suspects from the result of task `L1_people`.
2. Fetches power plant records from the course API.
3. Resolves approximate coordinates for power plant cities with OpenAI.
4. Combines plant codes with city coordinates.
5. Computes the shortest distance between each suspect's observed locations and the power plant cities.
6. Selects the best candidate by the smallest distance.
7. Fetches the candidate's `accessLevel`.
8. Builds the final answer and sends it to `/verify`.

### Main modules

- `agent.py`: agent loop using OpenAI Responses API and Function Calling
- `tools.py`: tool definitions and deterministic tool execution
- `api_client.py`: course API integration
- `city_resolver.py`: OpenAI-based city coordinate resolution
- `distance.py`: Haversine distance calculation
- `validator.py`: local validation before verification
- `pipeline.py`: end-to-end app execution

### Notes

- Secrets and private endpoints are loaded from `.env`.
- The agent orchestrates the workflow in stages (`setup`, `ranking`, `finalize`) and only sees the tools needed in the current stage.
- Calculations and API handling stay deterministic in Python.
- `workbench/` contains exploration scripts used during development.

## What This Task Should Teach

This task is mainly about using an agent as an orchestrator without letting it own the whole solution.
The important lesson is that Function Calling works best when tools are small, stage-specific, and backed by deterministic code that can validate the result.

Key learning points:

| Lesson | What it means in this app |
|---|---|
| Stage the agent workflow. | The app separates setup, candidate ranking, and finalization so each stage has a clear job. |
| Expose only useful tools. | The agent sees tools needed for the current stage instead of a large all-purpose toolbox. |
| Keep math out of model reasoning. | Haversine distance calculations are done in Python, not improvised by the model. |
| Use the model where ambiguity exists. | OpenAI helps resolve approximate city coordinates, while API calls and validation remain deterministic. |
| Preserve exploration without mixing it into runtime. | `workbench/` scripts document investigation steps without becoming part of the production path. |

The practical pattern to remember:

```text
staged agent -> narrow tools -> deterministic ranking -> validated final answer
```
