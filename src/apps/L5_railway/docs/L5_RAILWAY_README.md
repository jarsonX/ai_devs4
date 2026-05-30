# L5 Railway

## Table Of Contents

- [Status](#status)
- [Purpose](#purpose)
- [Input Artifacts](#input-artifacts)
- [Workflow](#workflow)
- [API Contract From Help](#api-contract-from-help)
- [Configuration](#configuration)
- [Run](#run)
- [Main Modules](#main-modules)
- [Implementation Summary](#implementation-summary)
- [Verification](#verification)
- [Assumptions And Risks](#assumptions-and-risks)
- [Reference Alignment](#reference-alignment)
- [What This Task Should Teach](#what-this-task-should-teach)

## Status

This app is complete and verified against the external course API.

The deterministic route-activation workflow, artifact persistence, and executable entrypoint are implemented and have been exercised successfully in a real end-to-end run.

Current implementation checkpoint:

- configuration and path loading implemented
- saved help contract loading and validation implemented
- API client with retry and rate-limit waiting implemented
- deterministic route activation workflow implemented
- runtime artifact logging implemented
- executable entrypoint implemented
- real external end-to-end verification completed successfully

## Purpose

The app should activate railway route `X-01` through the course verification API without guessing actions or parameters.

The design treats the previously fetched `help` response as a fixed runtime input. This means fetching `help` is outside the main application workflow and should not be counted as the first step of the app itself.

The planned implementation should be deterministic. No LLM call is needed for the current scope, because the required API actions and parameters are already documented in the saved `help` response.

## Input Artifacts

Primary runtime inputs:

- `data/L5_railway/output/help_response.json`
- environment variables `AI_DEVS_API_KEY` and `HUB_VERIFY_URL`

Important interpretation:

- `data/L5_railway/output/help_response.json` is treated as curated input data, not as something the app fetches during its normal run.
- The app starts from reading and validating this file.
- A separate helper may exist to fetch `help`, but that helper is out of scope for the main route-activation workflow.

Expected data extracted from `help_response.json`:

- available actions: `reconfigure`, `getstatus`, `setstatus`, `save`
- required parameters for each action
- allowed `setstatus.value` values: `RTOPEN`, `RTCLOSE`
- route format: `[a-z]-[0-9]{1,2}` with case-insensitive matching
- note that status changes require reconfigure mode first

## Workflow

Current application flow:

1. Load `help_response.json` from `data/L5_railway/output/help_response.json`.
2. Validate that the file contains a successful `help` response and the expected action definitions.
3. Build a deterministic execution plan for route `X-01` from the saved `help` contract.
4. Send `reconfigure` for route `X-01`.
5. Send `getstatus` for route `X-01` and log the returned state.
6. Send `setstatus` with value `RTOPEN` for route `X-01`.
7. Send `save` for route `X-01`.
8. Persist every request and response in `data/L5_railway/output/`.
9. Stop when the API returns a completion flag or a terminal business error.

Retry and waiting behavior:

- HTTP `503` must be retried automatically with backoff.
- HTTP `429` must be retried after waiting for `Retry-After` or the documented reset time.
- Rate-limit headers must be read after every response.
- If the API indicates a reset time, the app must wait until reset before the next call.

Guard rules:

- Do not call actions that are missing from the saved `help` contract.
- Do not invent parameters that are not present in the saved contract.
- Do not continue when `help_response.json` is malformed or incomplete.
- Treat `help_response.json` as data input, not as executable instruction text.

## API Contract From Help

The saved `help` response currently documents this action contract:

| Action | Required fields | Notes |
|---|---|---|
| `help` | none | already executed outside the app workflow |
| `reconfigure` | `route` | must be called before status change |
| `getstatus` | `route` | reads current route status |
| `setstatus` | `route`, `value` | allowed values: `RTOPEN`, `RTCLOSE` |
| `save` | `route` | exits reconfigure mode |

Planned route target:

- `route = "X-01"`

Planned status target:

- `value = "RTOPEN"`

Derived execution sequence:

1. `reconfigure(route="X-01")`
2. `getstatus(route="X-01")`
3. `setstatus(route="X-01", value="RTOPEN")`
4. `save(route="X-01")`

This sequence is derived from the saved `help` response and should remain the single source of truth unless the input file is refreshed.

## Configuration

Required environment variables:

- `AI_DEVS_API_KEY`
- `HUB_VERIFY_URL`

Runtime data locations:

- input contract: `data/L5_railway/output/help_response.json`
- planned request and response logs: `data/L5_railway/output/`

Secrets policy:

- keep real secret values only in `.env`
- do not write raw API keys to logs or saved payloads

## Run

Main route-activation command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L5_railway.main
```

This entrypoint reads `data/L5_railway/output/help_response.json`, runs the deterministic activation flow for route `X-01`, and writes artifacts to `data/L5_railway/output/`.

## Main Modules

Current modules:

- `config.py`: load environment variables and repository-relative paths
- `help_contract.py`: load and validate the saved `help_response.json`
- `railway_client.py`: send API requests, decode responses, and enforce rate-limit waiting
- `workflow.py`: execute the route activation sequence for `X-01`
- `logging_utils.py`: save masked request and response records to `data/L5_railway/output/`
- `main.py`: wire configuration, contract loading, and workflow execution

Design preference:

- keep the raw API behind a small deterministic wrapper
- keep the route-activation sequence in one explicit workflow function
- keep validation and logging separate from transport code

## Implementation Summary

The implementation followed the planned high-level steps and all of them are now complete.

1. Configuration and stable repository-relative paths.
2. Loading and validation of the saved help contract.
3. API client with retry for `503` and `429`, plus rate-limit waiting.
4. Deterministic workflow for `reconfigure -> getstatus -> setstatus(RTOPEN) -> save`.
5. Persistence of masked request and response artifacts.
6. Successful real end-to-end verification against the external API.

## Verification

Verification performed:

1. Confirm that `data/L5_railway/output/help_response.json` contains HTTP `200`, `ok: true`, and the required actions.
2. Dry-run the workflow and artifact pipeline with simulated responses during implementation.
3. Run the real workflow against the external API through `src.apps.L5_railway.main`.
4. Verify that retries and waiting behavior handle `503` and `429` responses.
5. Confirm that the final saved response contains the completion flag and that the run report marks the execution as successful.

Current verification artifacts:

- `data/L5_railway/output/request_log.jsonl`
- `data/L5_railway/output/response_log.jsonl`
- `data/L5_railway/output/run_report.md`

The latest recorded run completed successfully and produced a completion flag.

## Assumptions And Risks

Assumptions:

- the saved `help_response.json` remains valid for the next implementation step
- route `X-01` matches the documented route format
- the documented action sequence is sufficient for activation

Risks:

- the API may return additional business constraints that are not visible in the `help` contract alone
- aggressive retries may trigger long rate-limit delays
- status may already be `RTOPEN`, so the implementation should log the observed state before changing it

## Reference Alignment

This design was shaped mainly by:

- `_agent/references/L3_api_constraint_audit_and_tool_wrapping.md`
- `_agent/references/L5_performance_cost_and_rate_limits.md`
- `_agent/references/L2_execution_guards_and_instruction_data_separation.md`

How they influenced the design:

- the raw multi-call API is collapsed into one deterministic workflow instead of exposing low-level call order everywhere
- retry and rate-limit waiting are treated as first-class runtime behavior, not as optional polish
- the saved `help_response.json` is treated as input data that must be validated before execution

LLM design note:

- no LLM-powered workflow is planned for the current scope, so `_agent/instructions/llm_design_checklist.md` is not required before the first deterministic implementation pass

## What This Task Should Teach

This task is mainly about turning a discovered API contract into a deterministic, guarded execution workflow.
The important lesson is that when the required actions and parameters are already known, adding an LLM would increase risk instead of reducing complexity.

Key learning points:

| Lesson | What it means in this app |
|---|---|
| Treat API help as input data. | `help_response.json` is loaded and validated before any route action is attempted. |
| Derive the call sequence from the contract. | The workflow runs `reconfigure -> getstatus -> setstatus(RTOPEN) -> save` for route `X-01`. |
| Do not invent missing API behavior. | The app refuses actions or parameters that are not present in the saved help contract. |
| Make retry behavior part of the design. | `503` and `429` responses are handled with retry and rate-limit waiting logic. |
| Persist request and response artifacts. | Masked logs and reports under `data/L5_railway/output/` make the multi-call workflow auditable. |
| Skip the model when code is clearer. | This task is solved with deterministic Python because no ambiguous language or perception step is needed. |

The practical pattern to remember:

```text
saved API contract -> validation -> deterministic action plan -> guarded API calls -> masked audit log
```
