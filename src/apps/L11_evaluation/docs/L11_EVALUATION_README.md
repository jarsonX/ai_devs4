# L11 Evaluation README

## Table Of Contents

- [Purpose](#purpose)
- [Current Status](#current-status)
- [Task Summary](#task-summary)
- [Input Record Format](#input-record-format)
- [Design Direction](#design-direction)
- [Workflow](#workflow)
- [Mermaid Logic Flow](#mermaid-logic-flow)
- [Model Role](#model-role)
- [Evaluation Strategy](#evaluation-strategy)
- [LLM Usage And Reviews](#llm-usage-and-reviews)
- [Configuration](#configuration)
- [Data Layout](#data-layout)
- [Run](#run)
- [Main Modules](#main-modules)
- [Verification](#verification)
- [Assumptions And Risks](#assumptions-and-risks)
- [Open Questions](#open-questions)
- [What This Task Should Teach](#what-this-task-should-teach)

## Purpose

`L11_evaluation` is the application workspace for the AI_devs L11 `evaluation` exercise.

The task is to find all sensor files that contain anomalies. Some anomalies are numeric and structural, so ordinary code should detect them. Other anomalies depend on the meaning of `operator_notes`, so the app may use an LLM only for that narrow language-classification step.

The learning focus is cost-aware evaluation design: use deterministic validation for stable rules, reserve the model for semantic judgment, cache repeated model work, and keep the final answer traceable.

## Current Status

Status: design reviewed; source implementation may start inside the approved MVP1 boundary.

Completed:

- exercise description inspected from `_agent/references/exercises/L11_exercise.md`
- reference index inspected from `_agent/references/INDEX.md`
- L11 observability and eval references inspected
- high-level hybrid design selected: deterministic sensor validation plus cached note classification
- app documentation started
- LLM design checklist passed for MVP1 deterministic sensor scan plus cached note classification
- minimal package skeleton created with `src/apps/L11_evaluation/__init__.py`
- configuration loading implemented in `src/apps/L11_evaluation/config.py`
- sensor data models implemented in `src/apps/L11_evaluation/models.py`
- central sensor rule table implemented in `src/apps/L11_evaluation/sensor_rules.py`

Not implemented yet:

- deterministic sensor validator
- operator note classifier
- local cache, reports, logs, and final answer writer
- Hub verification client
- optimization review

Implementation is approved only for the reviewed MVP1 boundary: deterministic sensor scan, cached operator-note classifier, final resolver, local reports, and explicit guarded Hub submission.

## Task Summary

The input directory contains sensor JSON files:

```text
data/L11_evaluation/input/sensors/
```

Every file has the same measurement fields, but only fields matching `sensor_type` should be active. Inactive measurement fields must be exactly `0`.

Known active ranges:

| Sensor Type | Measurement Field | Valid Active Range |
| --- | --- | --- |
| `temperature` | `temperature_K` | `553` to `873` |
| `pressure` | `pressure_bar` | `60` to `160` |
| `water` | `water_level_meters` | `5.0` to `15.0` |
| `voltage` | `voltage_supply_v` | `229.0` to `231.0` |
| `humidity` | `humidity_percent` | `40.0` to `80.0` |

An output file should be marked for recheck when:

- an active measurement is outside its allowed range,
- an inactive measurement field is non-zero,
- the operator note claims the readings are OK but the measurements are invalid,
- the operator note claims there is an error but the measurements are valid.

The final Hub verification payload shape is:

```json
{
  "apikey": "tutaj-twoj-klucz",
  "task": "evaluation",
  "answer": {
    "recheck": ["0001", "0002", "0003"]
  }
}
```

The local `final_answer.json` should store only the non-secret `answer` content or a payload without a real API key. The real `apikey` must be loaded from `.env` only when the guarded Hub request is built.

## Input Record Format

Each sensor JSON file contains one record with all measurement fields present:

```json
{
  "sensor_type": "temperature/voltage",
  "timestamp": 1774064280,
  "temperature_K": 612,
  "pressure_bar": 0,
  "water_level_meters": 0,
  "voltage_supply_v": 230.4,
  "humidity_percent": 0,
  "operator_notes": "Readings look stable and within expected range."
}
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `sensor_type` | Active sensor name or slash-separated sensor combination, such as `temperature` or `temperature/voltage`. |
| `timestamp` | Unix timestamp for the reading. |
| `temperature_K` | Temperature reading in Kelvin. |
| `pressure_bar` | Pressure reading in bars. |
| `water_level_meters` | Water level reading in meters. |
| `voltage_supply_v` | Supply voltage reading in volts. |
| `humidity_percent` | Humidity reading in percent. |
| `operator_notes` | Operator note in English. |

All measurement fields are always present. Fields that do not belong to the active `sensor_type` must be `0`.

## Design Direction

MVP1 should be a local batch workflow, not an agent loop.

The key design split:

| Responsibility | Owner | Reason |
| --- | --- | --- |
| JSON loading and file ID extraction | Deterministic code | File names and JSON structure are stable. |
| Sensor type parsing | Deterministic code | `sensor_type` is a compact string contract. |
| Active range validation | Deterministic code | Numeric bounds are explicit. |
| Inactive field validation | Deterministic code | The rule is exact: inactive fields must be `0`. |
| Operator note meaning | LLM classifier | Notes are natural language and may be short, vague, or misleading. |
| Note deduplication and caching | Deterministic code | Repeated notes should not cause repeated model calls. |
| Final anomaly resolution | Deterministic code | The anomaly rules are explicit once measurement status and note label are known. |
| Hub submission | Deterministic code | Authentication, payload shape, and request limits must stay outside the model. |

The model should not receive all 10,000 files. It should receive unique note texts, grouped into batches, after deterministic validation has already classified the measurements for every file.

## Workflow

Planned MVP1 workflow:

1. Load configuration from environment variables and app constants.
2. Load all sensor JSON files from `data/L11_evaluation/input/sensors/`.
3. Extract `file_id` from the file name.
4. Parse `sensor_type` into active sensor names.
5. Validate each measurement record deterministically.
6. Write deterministic findings to `data/L11_evaluation/output/deterministic_findings.json`.
7. Normalize and hash unique `operator_notes`.
8. Load cached note classifications from `data/L11_evaluation/cache/operator_notes_cache.json`.
9. Classify only missing unique notes with a small OpenAI model.
10. Validate model output against the note classification schema.
11. Persist updated note classifications to cache.
12. Resolve final anomalies by combining measurement status and note classification.
13. Write `data/L11_evaluation/output/final_answer.json`.
14. If explicit submit mode is enabled, send the answer to Hub `/verify`.
15. Store masked run logs and non-secret status under `data/L11_evaluation/logs/`.

## Mermaid Logic Flow

```mermaid
flowchart TD
    A[Start L11_evaluation run] --> B[Load config and input paths]
    B --> C[Read sensor JSON files]
    C --> D[Validate measurements deterministically]
    D --> E[Extract and normalize operator notes]
    E --> F[Load note classification cache]
    F --> G{All unique notes cached?}
    G -- No --> H[Batch missing notes for LLM classification]
    H --> I[Validate structured model output]
    I --> J{Output valid?}
    J -- No --> K[Log validation failure and stop]
    J -- Yes --> L[Update note cache]
    G -- Yes --> M[Resolve final anomaly list]
    L --> M
    M --> N[Write final_answer.json]
    N --> O{Submit enabled?}
    O -- No --> P[Stop after local report]
    O -- Yes --> Q[Send guarded verify request]
    Q --> R[Write masked verification status]
```

## Model Role

The planned model step is named `Operator Note Classifier`.

It should receive batches of unique note texts, not full sensor records. Each note should have an internal `note_id` generated by code. The model should return only a compact structured classification:

```json
{
  "items": [
    {
      "note_id": "note_001",
      "label": "claims_ok",
      "confidence": "high"
    }
  ]
}
```

Allowed labels:

| Label | Meaning |
| --- | --- |
| `claims_ok` | The note says or strongly implies that readings are stable, valid, normal, or OK. |
| `claims_error` | The note says or strongly implies that something is wrong, invalid, suspicious, abnormal, or requires recheck. |
| `neutral_or_unclear` | The note does not make a clear correctness claim. |

The model must not receive API keys, Hub endpoints, final answers, or instructions to submit anything. It only classifies language.

## Evaluation Strategy

The workflow itself is an evaluation exercise, but the implementation should still have local checks.

Planned local checks:

| Area | Check Type | Purpose |
| --- | --- | --- |
| Sensor rule mapping | Deterministic unit tests | Catch wrong field-to-sensor mapping before scanning 10,000 files. |
| Active range validation | Deterministic unit tests | Verify boundary values and out-of-range values. |
| Inactive field validation | Deterministic unit tests | Verify that non-active measurements are rejected when non-zero. |
| Note classifier schema | Deterministic validation | Reject malformed model output before cache writes. |
| Note classifier behavior | Small curated eval set | Check obvious OK, obvious error, and unclear notes before a full run. |
| Final resolver | Deterministic unit tests | Confirm measurement status and note label combine into the right `recheck` decision. |

This is a local non-production app, so a large maintained eval suite is not planned for MVP1. A small curated note-label dataset is enough to protect the expensive semantic step from obvious prompt mistakes.

## LLM Usage And Reviews

| Area | Status | Evidence |
| --- | --- | --- |
| LLM usage | Yes | MVP1 plans one `Operator Note Classifier` model step for semantic classification of unique `operator_notes`. Deterministic code handles JSON parsing, numeric validation, inactive field checks, final anomaly resolution, and Hub submission. |
| Design review | Passed | `_agent/instructions/llm_design_checklist.md`; 2026-06-11; scope: MVP1 deterministic sensor scan plus cached operator-note classifier; mode: non-production; result: PASS; boundary: implement deterministic scan, unique-note cache, `Operator Note Classifier`, schema validation, final resolver, local reports, and explicit guarded Hub submission only. |
| Optimization review | Pending | `_agent/instructions/llm_optimization_checklist.md`; scope planned: completed MVP1 workflow after implementation and before declaring the app complete. |

## Configuration

Required environment variables:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Authenticates OpenAI calls for the `Operator Note Classifier`. |
| `AI_DEVS_API_KEY` | Authenticates Hub verification requests. |
| `HUB_VERIFY_URL` | Hub verification endpoint, expected to point at `/verify`. |

Regular app constants should live in `config.py`, not `.env`:

| Constant | Planned Value | Purpose |
| --- | --- | --- |
| `TASK_NAME` | `evaluation` | Hub task identifier. |
| `NOTE_CLASSIFIER_MODEL` | `gpt-5-mini` | Model for semantic note classification in MVP1. Cheaper alternatives can be tested later as an optimization experiment. |
| `REASONING_EFFORT` | `low` | Keeps the short note-classification step lightweight. |
| `NOTE_BATCH_SIZE` | `100` | Limits prompt size and failure blast radius. |
| `MAX_NOTE_CLASSIFICATION_CALLS` | `200` | Guard against accidental runaway model calls. |
| `MAX_VERIFY_REQUESTS` | `3` | Guard against repeated Hub submissions. |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Network timeout for future OpenAI and Hub calls. |
| `INPUT_SENSORS_DIR` | `data/L11_evaluation/input/sensors/` | Sensor JSON input directory. |

Secrets must live in `.env`. Do not put real secret values in source code, documentation, commit messages, reports, logs, or app data files.

## Data Layout

Runtime artifacts should live outside source code:

| Path | Intended Use |
| --- | --- |
| `data/L11_evaluation/input/sensors/` | Provided input sensor JSON files. |
| `data/L11_evaluation/cache/operator_notes_cache.json` | Local cache from normalized note hashes to model classifications. |
| `data/L11_evaluation/output/deterministic_findings.json` | Non-secret measurement validation summary. |
| `data/L11_evaluation/output/final_answer.json` | Final local answer payload without API key. |
| `data/L11_evaluation/logs/` | JSONL run logs with masked request payloads and non-secret statuses. |

Source code and app documentation belong under `src/apps/L11_evaluation/`.

Runtime data may contain extracted candidate classifications and non-secret summaries. It must not contain API keys, operational endpoints, raw FLAGS, or raw Hub success responses outside ignored runtime files.

## Run

No runnable entrypoint exists yet.

Planned local scan command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L11_evaluation.main --scan
```

Planned guarded submission command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L11_evaluation.main --submit
```

Submission should remain explicit. Running a local scan should never submit to Hub by accident.

## Main Modules

Planned module responsibilities:

| Module | Status | Responsibility |
| --- | --- | --- |
| `__init__.py` | Implemented | Marks `src.apps.L11_evaluation` as an importable Python package. |
| `config.py` | Implemented | Loads environment variables, app constants, model settings, guard limits, and data paths. |
| `models.py` | Implemented | Defines plain data structures for sensor records, validation findings, note labels, and final results. |
| `loader.py` | Planned | Reads sensor JSON files and extracts file IDs. |
| `sensor_rules.py` | Implemented | Stores sensor-to-field mapping, measurement fields, valid ranges, and sensor type parsing helpers. |
| `deterministic_validator.py` | Planned | Validates active ranges, inactive fields, unknown sensor types, and malformed records. |
| `note_classifier.py` | Planned | Batches unique notes, calls the OpenAI model, validates structured output, and updates cache. |
| `resolver.py` | Planned | Combines measurement validation and note labels into final anomaly decisions. |
| `report_writer.py` | Planned | Writes deterministic findings, final answer, and masked run summaries. |
| `hub_client.py` | Planned | Builds guarded Hub verification payloads and masks secrets in logs. |
| `main.py` | Planned | Provides CLI commands for local scan and explicit submission. |

## Verification

Current verification:

- package import passed after Step 2,
- config smoke check passed after Step 3 with masked secret status only,
- sensor input path resolved to `data/L11_evaluation/input/sensors/`,
- `tests.L11_evaluation.test_sensor_rules` passed after Step 4 with 9 local tests.

Planned verification sequence:

1. Run unit tests for `deterministic_validator.py`.
2. Run a local deterministic scan without OpenAI or Hub calls.
3. Inspect unique note count and cache hit behavior.
4. Run the curated note-classification eval set.
5. Run full local scan and write `final_answer.json`.
6. Submit to Hub only after explicit approval for the external call.
7. After implementation, run the LLM optimization checklist and record the result here.

## Assumptions And Risks

Current assumptions:

- Sensor file IDs are derived from JSON file names such as `0001.json`.
- `sensor_type` values are slash-separated combinations of known sensor names.
- Numeric fields are present in every file.
- `operator_notes` are in English, as stated in the task.
- Many operator notes repeat or are near-duplicates, so caching unique notes should reduce cost.

Current risks:

- Some notes may be sarcastic, vague, or domain-specific, making classification ambiguous.
- Near-duplicate notes may not hash to the same key unless normalization is chosen carefully.
- A too-large batch can make one malformed model response affect many notes.
- A too-small batch can increase cost and latency through excessive calls.
- If the final answer includes every numeric anomaly plus semantic contradiction incorrectly, Hub verification will fail without telling us exactly which file caused the mismatch.

## Open Questions

- Should `neutral_or_unclear` notes ever create an anomaly by themselves, or only avoid semantic contradiction checks?
- Should note normalization use exact normalized text only, or also a near-duplicate grouping pass?
- Which OpenAI model is cheapest while still reliable enough for short English note classification?
- Should the first implementation include a manual review report for low-confidence note labels?

## What This Task Should Teach

This task should teach that model calls are not a default analysis engine. Numeric rules, file contracts, inactive sensor checks, schema validation, caching, and Hub payload construction belong in deterministic code. The model earns its keep only where the input is natural language and the judgment is semantic.
