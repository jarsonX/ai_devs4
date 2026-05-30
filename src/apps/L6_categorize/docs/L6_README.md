# L6 Categorize README

## Table Of Contents

- [Purpose](#purpose)
- [Scope](#scope)
- [Workflow](#workflow)
- [Configuration](#configuration)
- [Token Budget](#token-budget)
- [Prompt Strategy](#prompt-strategy)
- [Data Paths](#data-paths)
- [Run Report](#run-report)
- [Main Modules](#main-modules)
- [Run](#run)
- [Verification](#verification)
- [LLM Design Status](#llm-design-status)
- [What This Task Should Teach](#what-this-task-should-teach)

## Purpose

`L6_categorize` is a small learning application for the AI_devs `categorize` exercise.
Its goal is to test short classification prompts against the hub workflow, where the hub model classifies each goods item as dangerous (`DNG`) or neutral (`NEU`).

The application does not perform the final classification locally. Local code only prepares prompts, sends them to the hub, records hub responses, and helps iterate on the prompt.

## Scope

The application should be a minimal CLI runner, not a production system.

The scope includes:

- loading required configuration from environment variables,
- resetting the hub task budget before a full attempt,
- downloading the latest CSV before each attempt,
- building one prompt per goods item from a fixed prompt template,
- sending one verification request per goods item,
- saving a simple run report for debugging and learning.

The scope intentionally excludes automatic prompt rewriting by a local LLM and autonomous retry loops.
Because the small runner succeeds, no larger agentic version is planned.

Current status: implemented and successfully verified against the Hub.

## Workflow

1. Load configuration from the local environment.
2. Send a reset prompt to the hub so the run starts from a clean budget state.
3. Download the latest `categorize.csv` from the hub.
4. Save the downloaded CSV to `data/L6_categorize/input/categorize_latest.csv`.
5. Parse the CSV `code` and `description` columns into goods items using a structured CSV parser.
6. For each goods item:
   - build a short prompt with the stable instruction prefix first,
   - append the item identifier and description at the end,
   - send the prompt to the hub verification endpoint,
   - collect the response.
7. Continue until all 10 goods items are submitted, unless the hub reports an immediate runtime failure such as budget exhaustion or another request-level error.
8. After all 10 goods items are successfully submitted, read the final hub response. The flag can appear only after the full set of 10 classifications is accepted.
9. Save a JSON run report to `data/L6_categorize/output/run_report.json`.

## Configuration

Required environment variables:

| Name | Purpose |
|---|---|
| `AI_DEVS_API_KEY` | API key used to authenticate hub requests. |
| `HUB_DATA_URL` | Complete data URL for downloading the current CSV. |
| `HUB_VERIFY_URL` | Hub verification endpoint. |

Secrets must stay in `.env` or another approved secret store. Source code, Markdown files, reports, logs, and commit messages must not contain real API keys or private operational endpoints.

## Token Budget

The full attempt has a shared budget of `1.5 PP` for all 10 verification requests.

| Token type | Cost |
|---|---|
| Each 10 input tokens | `0.02 PP` |
| Each 10 cached tokens | `0.01 PP` |
| Each 10 output tokens | `0.02 PP` |

If the budget is exceeded or any item is classified incorrectly, the next attempt must start from the beginning after sending the reset prompt.

## Prompt Strategy

The prompt should be short because the hub model has a very small context window. The stable instruction prefix should stay identical between requests, while variable item data should appear at the end to make prompt caching more effective.

Current prompt template:

```text
Return DNG only for weapons or explicit explosive/poison/radioactive/flammable danger. Reactor/fuel/cassette/core/uranium => NEU. Otherwise NEU. Reply only DNG/NEU. Item: {id} {description}
```

Design assumptions:

- Reactor-related goods are intentionally treated as `NEU` for this fictional course exercise.
- The hub model performs the actual classification based on the submitted prompt.
- Local code should not hardcode final labels for individual CSV rows.
- Failed hub responses should be used to refine the general prompt rule, not to add brittle item-specific hacks.

## Data Paths

Runtime files should live outside the application source directory:

| Path | Purpose |
|---|---|
| `data/L6_categorize/input/categorize_latest.csv` | Latest downloaded CSV for the current attempt. |
| `data/L6_categorize/output/run_report.json` | JSON report with prompts, item data, and hub responses. |

Hub-provided item data does not need special sensitive-data handling for this exercise, but secrets must still be excluded from all runtime artifacts.

## Run Report

`data/L6_categorize/output/run_report.json` should be a step-by-step execution log, not only a final summary.
Its main purpose is to show what the application sent, what the hub returned, and where a failed attempt stopped.

The report should include:

- run metadata, such as task name, start/end time, success flag, and error summary,
- a chronological `events` list,
- one event for the reset request and hub response,
- one event for the CSV download result,
- one event for saving the downloaded CSV,
- one event for parsing the CSV and item count,
- one event per item verification, including item data, submitted prompt, HTTP status, parsed hub payload, and raw hub response text,
- the final flag only if the hub returns one.

Secrets must be masked in report events. In particular, `apikey` must never be stored in the report, even though hub-provided goods data and prompts may be stored in full for debugging.

Example shape:

```json
{
  "task": "categorize",
  "success": false,
  "flag": null,
  "error_summary": "Budget exhausted after item 7.",
  "events": [
    {
      "step": "verify_item",
      "item_id": "7",
      "request": {
        "task": "categorize",
        "answer": {
          "prompt": "Classify item as..."
        },
        "apikey": "***REDACTED***"
      },
      "response": {
        "status_code": 200,
        "payload": {
          "message": "..."
        },
        "text": "{\"message\":\"...\"}"
      }
    }
  ]
}
```

## Main Modules

Source files:

| Module | Responsibility |
|---|---|
| `main.py` | CLI entrypoint and workflow orchestration. |
| `config.py` | Environment loading and configuration validation. |
| `hub_client.py` | HTTP communication with the hub data and verify endpoints. |
| `csv_loader.py` | CSV parsing from `code` and `description` columns into typed goods items. |
| `prompt_builder.py` | Prompt template management and item prompt construction. |
| `models.py` | Small typed data structures for goods items and run results. |

Each class, function, and method should include a short `#` purpose comment, following the repository instructions.

## Run

Command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L6_categorize.main
```

## Verification

After each implementation step, run the smallest practical check that confirms the newly added behavior works before continuing.

Verification should check that:

- configuration validation fails clearly when required values are missing,
- the CSV is downloaded and saved under `data/L6_categorize/input/`,
- exactly 10 goods items are parsed from a normal hub CSV,
- one prompt is sent per item,
- the run report is written under `data/L6_categorize/output/`,
- hub errors are preserved in the report for prompt iteration,
- the run report contains chronological events for reset, CSV download, parsing, and each item verification.

Successful Hub verification was completed with:

- `success: true`,
- `items_count: 10`,
- `verifications_count: 10`,
- `events_count: 14`,
- final flag returned by the Hub and stored in `data/L6_categorize/output/run_report.json`.

## LLM Design Status

Review mode: `non-production`.

This small runner intentionally skips `_agent/instructions/llm_design_checklist.md`.

Rationale:

- the application is local, small, and one-off,
- it does not implement a local LLM workflow or autonomous agent loop,
- the hub model performs the actual classification based on the submitted prompt,
- local code only downloads input data, submits prompts, and records responses,
- the implementation is intentionally lightweight and does not introduce production LLM architecture.

If the scope grows to include automatic prompt rewriting, autonomous retries, or a local model-driven workflow, the design should be reviewed with `_agent/instructions/llm_design_checklist.md` before implementation.

## What This Task Should Teach

This task is mainly about prompt iteration under a tight external budget.
The important lesson is that a small runner can be enough when the local app does not need to classify items itself; its job is to control inputs, keep prompts short, and preserve evidence from each Hub response.

Key learning points:

| Lesson | What it means in this app |
|---|---|
| Keep the prompt short and stable. | The fixed instruction prefix stays small so the Hub model has room for the item data and can benefit from caching. |
| Put variable data at the end. | Each request appends the item identifier and description after the stable rule text. |
| Let the remote model do the classification. | Local code sends prompts and records responses instead of hardcoding labels for individual rows. |
| Reset before full attempts. | A new attempt starts with a reset prompt because budget and scoring state are shared across the 10 items. |
| Save chronological run evidence. | The run report records reset, CSV download, parsing, and every item verification event. |
| Keep the scope small when it works. | No autonomous prompt rewriter is needed because the lightweight runner already solved the exercise. |

The practical pattern to remember:

```text
budget reset -> fresh CSV -> short cached prompt -> per-item verification -> chronological report
```
