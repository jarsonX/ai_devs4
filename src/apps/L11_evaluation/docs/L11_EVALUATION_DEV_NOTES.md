# L11 Evaluation Dev Notes

## Table Of Contents

- [Implementation Notes](#implementation-notes)
- [Design Decisions](#design-decisions)
- [Implementation Plan](#implementation-plan)
- [LLM Design Review Preparation](#llm-design-review-preparation)
- [LLM Design Checklist Review](#llm-design-checklist-review)
- [LLM Optimization Checklist Review](#llm-optimization-checklist-review)
- [Debugging Notes](#debugging-notes)
- [Verification Notes](#verification-notes)
- [Open Questions](#open-questions)
- [Future Work](#future-work)

## Implementation Notes

Date: 2026-06-11

The exercise contains 10,000 JSON sensor files. The task explicitly warns that sending all records to an LLM would be expensive. The planned implementation should therefore scan all numeric and structural rules in Python first, then classify only unique operator notes with a model.

Important local references already inspected:

| Reference | Use |
| --- | --- |
| `_agent/references/exercises/L11_exercise.md` | Task contract, anomaly definitions, input path, and answer format. |
| `_agent/references/INDEX.md` | Reference map for L11 observability and eval design material. |
| `_agent/references/L11_observability_trace_and_prompt_versioning.md` | Logging, trace, prompt version, and cost visibility guidance. |
| `_agent/references/L11_eval_design_datasets_and_experiments.md` | Small eval design and score interpretation guidance. |
| `_agent/references/L11_eval_strategy_metrics_and_guardrails.md` | Split between evals, guardrails, deterministic controls, and model judgment. |
| `_agent/instructions/llm_design_gate.md` | Required gate before implementing a planned LLM workflow. |

No source implementation has started yet.

Update on 2026-06-12:

- `loader.py` now discovers JSON files in stable name order,
- file IDs are derived from file stems such as `0001.json -> 0001`,
- malformed JSON or non-object payloads are converted into deterministic `malformed_record` issues instead of crashing the batch,
- loaded records preserve `raw_payload` so Step 6 can still detect missing fields or suspicious types without guessing.

## Design Decisions

### Hybrid Pipeline Instead Of Agent Loop

Use a deterministic batch pipeline with one narrow model classification step.

Reason: the task has a stable input directory, explicit numeric rules, and no need for dynamic search, planning, or tool choice. An agent loop would add moving parts without adding useful intelligence. Very glamorous, very unnecessary.

### Deterministic Validation Owns Sensor Correctness

Sensor correctness should be computed by code:

- known sensor type mapping,
- active numeric range checks,
- inactive field zero checks,
- unknown sensor type detection,
- malformed JSON or missing field detection.

Reason: these are exact rules. Using a model here would add cost and uncertainty where a simple predicate is better.

### LLM Owns Only Operator Note Semantics

The model should classify unique note texts as:

- `claims_ok`,
- `claims_error`,
- `neutral_or_unclear`.

Reason: operator notes are natural language and can vary in phrasing. This is the one part of the task where semantic classification is useful.

### Classify Unique Notes, Not Files

The app should normalize notes, hash them, and classify only cache misses.

Reason: the task hint says repeated information exists. Local caching is the obvious cost reducer. The model's own provider-side cache is not enough because repeated runs should reuse local classifications too.

### Model Output Must Be Small

The model should return compact JSON only:

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

Reason: output tokens are comparatively expensive, and code only needs labels.

### Submission Must Be Explicit

Local scan and Hub submission should be separate CLI modes.

Reason: local analysis is cheap and repeatable. Hub calls are external, stateful course interactions and should not happen accidentally.

## Implementation Plan

This plan is the working reference for implementation after the LLM design checklist passes.

| Step | Scope | Done When | Verification |
| --- | --- | --- | --- |
| 1 | Run LLM design checklist for MVP1. | README records a passing design review for MVP1 scope. | Checklist has no `NO` items. |
| 2 | Create minimal package skeleton. | `src/apps/L11_evaluation/` has `__init__.py` and planned module files only where needed. | Import package with `.\venv\Scripts\python.exe`. |
| 3 | Add configuration. | Config loads `OPENAI_API_KEY`, `AI_DEVS_API_KEY`, and `HUB_VERIFY_URL`; app constants hold model and guard limits. | Config smoke check prints only secret-safe names and non-secret settings. |
| 4 | Add sensor rules and data models. | Sensor field mapping and valid ranges are represented once. | Unit tests cover every sensor type and boundary values. |
| 5 | Add loader. | Loader reads JSON files, extracts file IDs, and reports malformed files cleanly. | Run loader against a tiny fixture and the real input directory without model calls. |
| 6 | Add deterministic validator. | Validator identifies active range errors, inactive non-zero fields, unknown sensor types, and missing fields. | Unit tests cover valid records, invalid active values, inactive leaks, and multi-sensor records. |
| 7 | Add deterministic scan report. | Scan writes `deterministic_findings.json` under `data/L11_evaluation/output/`. | Full local scan runs without OpenAI or Hub calls. |
| 8 | Add note normalization and cache. | Unique normalized notes map to stable hashes and cached labels. | Cache round-trip test confirms repeated notes do not create repeated work. |
| 9 | Add curated note eval fixture. | A small local dataset covers obvious OK notes, obvious error notes, and unclear notes. | Eval runner verifies classifier prompt behavior before full classification. |
| 10 | Add LLM note classifier. | Classifier batches cache misses, calls OpenAI, validates structured output, and stores labels. | Run against curated fixture and a small real-note sample. |
| 11 | Add final resolver. | Resolver combines measurement status and note label into final `recheck` decisions. | Unit tests cover every contradiction and non-contradiction case. |
| 12 | Add final answer writer. | App writes `final_answer.json` without a real API key. | Validate local output JSON shape. |
| 13 | Add guarded Hub client. | Submission builds the real `/verify` payload with `apikey` from environment and logs only masked status. | Dry payload build uses fake key; real submission requires explicit approval. |
| 14 | Add CLI. | `--scan` runs local analysis; `--submit` performs guarded verification. | Run `--scan` locally and inspect outputs. |
| 15 | Run optimization checklist. | README records the post-implementation optimization review. | Checklist result is recorded before marking app complete. |

Step 1 completed on 2026-06-11. The LLM design checklist passed for MVP1 in `non-production` mode. Source implementation may start only inside the reviewed MVP1 boundary.

Step 2 completed on 2026-06-11. The minimal package skeleton contains `src/apps/L11_evaluation/__init__.py` only. Planned implementation modules are intentionally not created until their steps start, so empty placeholders do not obscure what is actually implemented.

Step 3 completed on 2026-06-11. `config.py` now loads app paths, `OPENAI_API_KEY`, `AI_DEVS_API_KEY`, and `HUB_VERIFY_URL` from environment variables. Model name, reasoning effort, batch size, model-call guard, verify guard, and request timeout are app-level constants.

Step 3 verification:

- `load_app_config(require_hub=False, require_llm=False)` built an app config successfully,
- `build_safe_config_summary(...)` printed only masked secret status, model name, guard limits, and repository-relative paths,
- `build_app_paths().sensors_dir` resolved to `data/L11_evaluation/input/sensors`.

Step 4 completed on 2026-06-11. `models.py` now defines shared data structures for sensor records, sensor issues, deterministic measurement findings, note classifications, and final local answers. `sensor_rules.py` now holds the central sensor-to-field mapping, valid inclusive ranges, sensor type parsing, active field lookup, inactive field lookup, and active-range checks.

Step 4 verification:

- `tests.L11_evaluation.test_sensor_rules` passed with 9 tests,
- tests covered every sensor type, every valid range boundary, out-of-range rejection, slash-separated sensor parsing, inactive field derivation, and core data model storage.

Step 5 completed on 2026-06-12. `loader.py` now reads sensor JSON files, extracts `file_id`, returns normalized `SensorRecord` objects for valid JSON objects, and reports malformed files as deterministic issues.

Step 5 verification:

- `tests.L11_evaluation.test_loader` passed with 6 tests,
- tests covered file discovery order, file ID extraction, valid JSON loading, wrong-type normalization with `raw_payload` preservation, malformed JSON reporting, and non-object JSON rejection,
- loader smoke check against `data/L11_evaluation/input/sensors/` loaded `9999` records and reported `0` malformed-file issues.

Step 6 completed on 2026-06-12. `deterministic_validator.py` now validates required fields, sensor-type parsing, active measurement ranges, and inactive non-zero leaks for every loaded record.

Step 6 verification:

- `tests.L11_evaluation.test_deterministic_validator` passed with 7 tests,
- tests covered valid single-sensor records, active out-of-range values, inactive non-zero leaks, valid multi-sensor records, missing required fields, unknown sensor types, and batch-order preservation,
- deterministic validation smoke check against `data/L11_evaluation/input/sensors/` processed `9999` records and found `46` invalid findings,
- issue breakdown from the smoke check: `24` `inactive_field_non_zero`, `22` `active_value_out_of_range`, `0` missing-field findings, and `0` unknown-sensor findings in the current local dataset.

Step 7 completed on 2026-06-12. `report_writer.py` now writes `deterministic_findings.json` as a stable local JSON artifact with summary counts, loader issues, and per-file deterministic findings.

Step 7 verification:

- `tests.L11_evaluation.test_report_writer` passed with 2 tests,
- tests covered summary aggregation and JSON file round-trip correctness,
- smoke write created `data/L11_evaluation/output/deterministic_findings.json`,
- smoke write summary: `9999` records, `46` invalid findings, `46` total issues, `0` loader issues.

Step 8 completed on 2026-06-12. `note_cache.py` now normalizes operator notes, maps them to stable SHA-256 hashes, loads and saves local cache entries, and identifies unique notes still missing from cache.

Step 8 verification:

- `tests.L11_evaluation.test_note_cache` passed with 3 tests,
- tests covered conservative normalization, repeated-note deduplication, cache round-trip, and uncached-note detection,
- smoke check against `data/L11_evaluation/input/sensors/` found `2032` unique normalized notes across `9999` records,
- smoke check wrote an empty initial cache file to `data/L11_evaluation/cache/operator_notes_cache.json` because classification has not started yet.

Step 9 completed on 2026-06-12. A curated fixture now lives in `data/L11_evaluation/references/operator_note_eval_fixture.json`, and `note_eval_fixture.py` loads the examples plus scores predicted labels before a full classification run.

Step 9 verification:

- `tests.L11_evaluation.test_note_eval_fixture` passed with 3 tests,
- tests covered fixture loading, balanced label coverage, deterministic accuracy scoring, and case indexing,
- smoke check loaded `9` curated examples from the committed fixture,
- smoke check label distribution: `3` `claims_ok`, `3` `claims_error`, `3` `neutral_or_unclear`,
- smoke check accuracy under perfect predictions: `1.0`.

Step 10 completed on 2026-06-12. `note_classifier.py` now batches normalized notes, builds a structured prompt, calls the OpenAI Responses API through an injectable client, validates JSON-schema output against the current batch, and returns cache-ready classifications.

Step 10 verification:

- `tests.L11_evaluation.test_note_classifier` passed with 7 tests,
- tests covered stable batching, response parsing, rejection of unknown or missing `note_id` values, fake-client batch classification, cache merging, and fixture-eval integration,
- fake-client smoke check on the curated fixture classified `9` notes and reached `1.0` accuracy,
- fake-client smoke check on a real-data sample classified `5` unique normalized notes without loader issues,
- no real OpenAI call was executed yet, so this step verifies the classifier pipeline and validation path, not live prompt quality.

Step 11 completed on 2026-06-12. `resolver.py` now combines deterministic findings and note classifications into final `recheck` decisions, adds contradiction issues for mismatched note claims, and refuses to guess when a file is missing note classification.

Step 11 verification:

- `tests.L11_evaluation.test_resolver` passed with 7 tests,
- tests covered invalid data plus `claims_ok`, valid data plus `claims_error`, neutral notes, deterministic-only anomalies, clean valid records, sorted final answers, and missing-classification failure,
- resolver smoke check with all notes forced to `neutral_or_unclear` produced `46` `recheck` IDs across `9999` records,
- the neutral-note smoke result matches the deterministic anomaly count, which confirms that neutral notes do not create extra anomalies by themselves.

Step 12 completed on 2026-06-12. `report_writer.py` now writes `final_answer.json` as a local non-secret payload with `task` plus `answer.recheck`, but still without any real API key.

Step 12 verification:

- `tests.L11_evaluation.test_report_writer` now passes with 4 tests,
- tests cover deterministic report summary, deterministic report round-trip, final answer payload shape, and final answer JSON round-trip,
- smoke write created `data/L11_evaluation/output/final_answer.json`,
- smoke write summary: task `evaluation`, `46` `recheck` IDs, `0` loader issues, no API key included.

Step 13 completed on 2026-06-12. `hub_client.py` now builds the real `/verify` payload from `HubConfig`, masks API keys for storage, preserves full Hub responses in ignored runtime logs, and enforces a bounded submit guard before any external request.

Step 13 verification:

- `tests.L11_evaluation.test_hub_client` passed with 5 tests,
- tests covered verify payload shape, API-key masking, verify-request guard behavior, fake-session submission flow, and full runtime Hub log payloads,
- dry smoke check built a verify payload with a fake key and `answer.recheck`,
- dry smoke check confirmed the masked payload uses `***REDACTED***` while the runtime log payload keeps the full fake Hub response,
- no real Hub request was executed in this step.

Step 14 completed on 2026-06-12. `main.py` now wires the full workflow into `--scan` and guarded `--submit` modes, writes `deterministic_findings.json`, `final_answer.json`, `operator_notes_cache.json`, and `run_report.json`, and prints a compact JSON summary to stdout.

Step 14 verification:

- `tests.L11_evaluation.test_main` passed with 3 tests,
- tests covered local scan mode, guarded submit mode with fake Hub feedback, and stdout summary shape,
- fake-classifier scan smoke check on the real dataset processed `9999` records and `2032` unique normalized notes,
- the same smoke run produced `46` `recheck` IDs and wrote `data/L11_evaluation/output/run_report.json`,
- no real OpenAI or Hub network call was executed in this step.

Step 15 completed on 2026-06-12. The completed MVP1 workflow was reviewed against `_agent/instructions/llm_optimization_checklist.md` in `non-production` mode, and the result was recorded in the README.

Step 15 review outcome:

- Result: PASS.
- Scope: full MVP1 workflow including deterministic scan, note cache, note classifier, resolver, local artifact writing, CLI orchestration, and guarded Hub submission.
- Follow-up: run one approved live OpenAI classification before treating the current local answer as semantically submission-ready.

## LLM Design Review Preparation

Planned review mode: `non-production`.

Planned review scope:

```text
MVP1 deterministic sensor scan plus cached operator-note classifier
```

Expected checklist evidence:

| Checklist Area | Planned Evidence |
| --- | --- |
| Goal and output | Final output is `answer.recheck`, a list of anomalous file IDs. |
| Workflow split | Loader, deterministic validator, note classifier, resolver, writer, optional submitter. |
| Deterministic logic | Numeric and structural sensor rules are all code-owned. |
| Model reason | Only operator note meaning requires language understanding. |
| Model selection | Use a small OpenAI model suitable for short text classification. |
| Prompt size | Send only unique notes and note IDs, never full sensor records. |
| Output size | Return label and optional confidence only. |
| Structured output | Validate returned JSON against allowed labels and known note IDs. |
| Context limits | No API keys, Hub endpoints, final answers, or full dataset in model context. |
| Caching | Persist note hash to label cache under `data/L11_evaluation/cache/`. |
| Validation | Treat model output as untrusted until schema and semantic checks pass. |
| Risky actions | Hub submission is deterministic, explicit, and outside model control. |

Review outcome:

- Result: PASS.
- Date: 2026-06-11.
- Approved boundary: implement deterministic scan, unique-note cache, `Operator Note Classifier`, schema validation, final resolver, local reports, and explicit guarded Hub submission only.
- Out of scope: agent loop, broad tool exposure, near-duplicate clustering beyond exact normalized notes, production job orchestration, and model-driven Hub submission.

## LLM Design Checklist Review

Review mode: `non-production`.

Review scope:

```text
MVP1 deterministic sensor scan plus cached operator-note classifier
```

Result: PASS. No checklist item is marked `NO`.

### Scope And Workflow

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The application has a clearly defined goal and expected output. | YES | The goal is to produce `answer.recheck`, a list of anomalous sensor file IDs for the `evaluation` Hub task. |
| The workflow is split into small steps when one model call would mix multiple responsibilities. | YES | The planned steps are loader, deterministic validator, note cache/classifier, resolver, writer, and optional guarded submitter. |
| Deterministic code is planned for stable logic, and LLM calls are reserved for language or reasoning tasks. | YES | Sensor ranges, inactive field checks, JSON loading, final anomaly resolution, and Hub payload building are code-owned; the model only classifies note semantics. |
| Each planned workflow step has a clear purpose. | YES | README and the implementation plan define one concrete responsibility for every planned module. |

### Model And Prompt Plan

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| Each LLM step has a reason for using a model instead of ordinary code. | YES | The only LLM step interprets English `operator_notes`, which may be varied, vague, or misleading. |
| The selected model for each step matches the expected difficulty of that step. | YES | MVP1 uses `gpt-5-mini` for short English classification; cheaper alternatives are deferred to a later optimization experiment. |
| Prompts are planned to be short, focused, and limited to the current step. | YES | The prompt will contain only the label definitions and a batch of unique note IDs with note text. |
| Token usage is intentionally limited for both model input and model output. | YES | Input is deduplicated unique notes, not 10,000 full records; output is compact JSON labels and optional confidence only. |
| Structured outputs are planned wherever code will consume the result. | YES | The classifier must return an `items` array with known `note_id`, allowed `label`, and optional confidence. |

### Context And Tools

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The design limits context to only what the current step needs. | YES | The model sees note IDs and note text only; it does not see sensor measurements, API keys, Hub endpoints, or final payloads. |
| The design limits tool exposure to only the tools needed for the current step. | YES | No model tools are planned for MVP1; Hub submission remains deterministic code outside the model. |
| The design avoids passing full history, full datasets, or irrelevant examples by default. | YES | The workflow explicitly avoids sending all 10,000 records and uses batches of unique notes. |
| The workflow includes batching, caching, or persisted intermediate results where repeated or long-running calls are likely. | YES | Normalized note hashes are cached in `data/L11_evaluation/cache/operator_notes_cache.json`; deterministic findings and final answers are persisted. |

### Runtime Performance And Task Lifecycle

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| Production-only: Long-running LLM, tool, media generation, or agent tasks have a planned progress or heartbeat mechanism. | N/A | Non-production local exercise; no UI or production job runner is planned. |
| Production-only: The user can understand what is happening while waiting for slow model, tool, media generation, or agent work. | N/A | Non-production local CLI; logs and reports are enough for MVP1. |
| Production-only: Long-running work can continue safely if the user closes the browser, loses connection, or leaves the application. | N/A | No browser or persistent production task lifecycle exists in MVP1. |
| Production-only: The workflow defines how task state, intermediate outputs, and final results are persisted. | N/A | Production requirement is out of scope; MVP1 still persists cache, deterministic findings, final answer, and logs for local debugging. |
| Production-only: The design supports pausing and resuming tasks when waiting for user approval, tool results, retries, or agent completion. | N/A | No production pause/resume behavior is planned; reruns reuse the note cache. |
| Production-only: User interaction during long-running work is planned, such as message queueing, cancellation, or opening a separate thread. | N/A | Non-production CLI workflow; no interactive UI queue is planned. |
| Production-only: UI state is not tightly coupled to backend execution state for long-running tasks. | N/A | No UI exists in MVP1. |
| Production-only: Event-driven or job-based orchestration is considered where a synchronous request/response flow would be fragile. | N/A | Local batch processing is acceptable for this exercise. |

### Validation And Safety

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The design includes validation before model output is used downstream. | YES | Classifier output must pass schema checks, known note ID checks, and allowed-label checks before cache writes or resolver use. |
| The design treats model output as untrusted until validation passes. | YES | Invalid batches stop before cache mutation, so a malformed response cannot silently influence the final answer. |
| The design keeps authorization, permissions, and risky actions outside the model. | YES | API keys are loaded from `.env`; Hub submission is deterministic, explicit, guarded, and unavailable to the model. |
| The workflow handles missing required inputs without guessing important values. | YES | Missing files, malformed records, unknown sensor types, missing fields, or invalid classifier output should become validation failures or explicit anomalies rather than guessed values. |

## LLM Optimization Checklist Review

Review mode: `non-production`.

Review scope:

```text
full MVP1 workflow including CLI, cache, resolver, and guarded Hub submission
```

Result: PASS. No checklist item is marked `NO`.

### Task Design

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The app solves a clearly defined task with a concrete expected output. | YES | The app produces `answer.recheck`, then optionally wraps it into the guarded Hub payload in `hub_client.py`. |
| The task is split into smaller steps when a single model call would mix multiple responsibilities. | YES | `main.py` orchestrates loader, deterministic validator, cache, classifier, resolver, report writing, and optional Hub submission as separate steps. |
| The workflow uses deterministic code for stable logic and reserves LLM calls for language or reasoning tasks. | YES | Numeric and structural anomalies are handled in `deterministic_validator.py`; only operator-note semantics go through `note_classifier.py`. |
| The system avoids asking the model to do multiple unrelated jobs in one step. | YES | The prompt asks only for note-label classification and confidence, never for anomaly resolution or payload construction. |
| The workflow is simple enough to explain step by step without hidden or unnecessary branches. | YES | The README workflow and `main.py` align closely; the only branch is whether uncached notes require the classifier and whether `--submit` is enabled. |

### Model Usage

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| Each LLM step has an explicit reason for using the selected model. | YES | `OperatorNoteClassifier` exists only because natural-language notes can imply correctness or error in varied wording. |
| Stronger and more expensive models are used only in steps that require stronger reasoning or better output quality. | YES | MVP1 uses `gpt-5-mini` in `config.py` for a short classification task rather than a larger model. |
| The app does not call the model when ordinary code, rules, or lookups would be enough. | YES | `run_scan_workflow()` executes deterministic validation first and never asks the model to inspect measurements. |
| Repeated model calls are explained by the workflow and are not caused by avoidable retries or weak step design. | YES | Calls happen only for cache misses, are bounded by `ModelRequestGuard`, and batch unique normalized notes. |

### Prompt Quality

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| Each prompt has a clear instruction, relevant context, constraints, and expected output format. | YES | `_build_input()` in `note_classifier.py` defines label meanings, ambiguity handling, note-ID constraints, and structured JSON output. |
| Prompts include only information needed for the current step. | YES | The prompt includes only `note_id` plus normalized note text. |
| The app avoids passing irrelevant history, data, or examples into prompts. | YES | No prior conversation, measurements, file IDs, or Hub data are sent to the model. |
| Ambiguous user requests are clarified, transformed, or decomposed before execution. | YES | The app does not forward user free text to the model; it transforms records into narrow note-classification batches. |

### Context Control

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| Only the context needed for the current step is sent to the model. | YES | `OperatorNoteBatchItem` keeps context to `note_id`, note hash, and normalized note; only `note_id` and note text go into the prompt. |
| Old conversation history is summarized or dropped when full detail is no longer needed. | N/A | This app is a stateless batch workflow, not a multi-turn conversational system. |
| Tool results are filtered before being added to the next model call. | YES | Deterministic findings are not inserted into prompts; only uncached normalized notes reach the classifier. |
| The app treats context as a limited and expensive resource. | YES | Unique-note deduplication and `NOTE_BATCH_SIZE` exist specifically to cap prompt size and failure blast radius. |

### Tool And Workflow Efficiency

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The tool list exposed to the model is limited to the tools needed for the current step. | YES | No model tools are exposed at all; the classifier is a plain structured Responses API call. |
| The workflow prefers fewer, higher-value tool calls over many small calls. | YES | One batch classifier call handles up to `NOTE_BATCH_SIZE` notes instead of one note per request. |
| Related operations are batched when possible. | YES | `build_note_batches()` groups sorted cache misses into stable batches. |
| Repeated external calls use caching when freshness requirements allow it. | YES | `operator_notes_cache.json` persists classifications across runs. |
| Each workflow step has a clear purpose and there are no obvious steps that can be removed without changing the result. | YES | Removing cache, validation, resolver, or run-report writing would either increase cost or reduce traceability. |

### Output Stability

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The model returns structured output whenever the result is consumed by code. | YES | The classifier requests `json_schema` output and parses `response.output_text` as JSON. |
| Output schemas are defined before execution. | YES | `OperatorNoteBatchPayload` and `OperatorNoteLabelPayload` define the accepted schema. |
| Model responses are validated before they are used downstream. | YES | `parse_note_classifier_response()` and `validate_note_batch_output()` reject empty, malformed, incomplete, duplicated, or unsupported outputs. |
| The app treats model output as untrusted input until validation passes. | YES | Cache mutation happens only after full batch validation. |

### Cost And Latency

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The number of LLM calls is intentionally minimized. | YES | Exact-note deduplication reduced `9999` records to `2032` unique notes before any live model call. |
| The number of tool calls is intentionally minimized. | YES | The pipeline is local and linear; the only external calls are bounded model batches and at most one guarded Hub submission per run. |
| Large prompts are avoided because they increase token usage, latency, and noise. | YES | Batch size is capped at `100`, and prompts exclude measurements and repeated note text. |
| Model output length is intentionally controlled to avoid unnecessary tokens, latency, and downstream noise. | YES | Output is limited to one label item per note with `note_id`, `label`, and `confidence`. |
| The app has clear places where cost, latency, retries, or token usage can be measured or logged. | YES | `run_report.json`, request guards, and batch boundaries make expensive steps visible and countable. |
| Expensive steps are easy to identify during debugging or review. | YES | The only expensive step is note classification for uncached notes, and its trigger is explicit in `run_scan_workflow()`. |

### Production Runtime Performance And Task Lifecycle

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| Production-only: Long-running LLM, tool, media generation, or agent tasks report progress or heartbeat state while work is running. | N/A | Local non-production CLI workflow. |
| Production-only: The user can understand what is happening while waiting for slow model, tool, media generation, or agent work. | N/A | Local non-production CLI workflow. |
| Production-only: The user can inspect partial or final artifacts during long-running work when the workflow supports it. | N/A | Local non-production CLI workflow. |
| Production-only: Long-running work can continue safely if the user closes the browser, loses connection, or leaves the application. | N/A | No browser or persistent production task lifecycle exists here. |
| Production-only: Task state, intermediate outputs, final results, and retry state are persisted where repeated work would be costly or fragile. | N/A | Production lifecycle is out of scope, though local cache and reports are persisted for reruns. |
| Production-only: Tasks can be paused and resumed after errors, user approval waits, tool results, retries, or agent completion. | N/A | Not a production job system. |
| Production-only: User interaction during long-running work is supported where relevant, such as message queueing, cancellation, or opening a separate thread. | N/A | Not relevant to this local batch workflow. |
| Production-only: UI state is not tightly coupled to backend execution state for long-running tasks. | N/A | No UI exists. |
| Production-only: Event-driven or job-based orchestration is used or explicitly justified where a synchronous request/response flow would be fragile. | N/A | Synchronous local batch execution is acceptable for this exercise. |

### Safety And Control

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| The model is responsible for interpretation and planning, not final authorization. | YES | The model classifies note semantics only; it does not authorize submission or final payload construction. |
| Sensitive or risky actions are protected by backend checks, not by model judgment alone. | YES | API keys come from `.env`, model requests are guarded, and Hub submission is guarded by deterministic code. |
| Retrieved or user-provided content is not mixed with system instructions in an unsafe way. | YES | The prompt explicitly says operator notes are untrusted data, not instructions. |
| The workflow stops or asks for missing required inputs instead of guessing important values. | YES | Missing LLM config, missing Hub config, malformed model output, or missing note classifications all fail loudly. |

### Review Validation

| Checklist Item | Status | Evidence |
| --- | --- | --- |
| There is no obvious LLM call that can be replaced with ordinary code without reducing required quality. | YES | Note semantics remain the only non-deterministic task; numeric and structural checks are already code-owned. |
| There is no obvious workflow step that can be removed without changing the result or reducing reliability. | YES | Cache, schema validation, resolver checks, and guarded submission each prevent a concrete failure mode. |
| There is no obvious context block that can be removed without making the current step weaker or less safe. | YES | Label definitions, ambiguity rule, and exact note-ID contract are the minimal context needed for safe classification. |
| The current workflow would still be understandable and maintainable if the application becomes larger. | YES | Responsibilities are already split into small modules with narrow interfaces. |
| Production-only: Long-running production work would remain understandable, resumable, and debuggable when multiple tasks are active at once. | N/A | Production orchestration is intentionally outside scope. |

## Debugging Notes

No implementation debugging has happened yet.

2026-06-12 loader note:

- the current local dataset loads `9999` JSON files, not `10000` as the exercise text claims, so treat the missing-file possibility as a real pre-submission check instead of decorative paranoia.

2026-06-12 validator note:

- if `sensor_type` cannot be parsed, the validator now stops before active/inactive measurement checks, because otherwise one bad type label creates noisy secondary issues that teach us nothing.

2026-06-12 note-cache note:

- exact normalization with whitespace collapse and `casefold()` reduced `9999` records to `2032` unique notes, so caching helps materially, but near-duplicate clustering is still a possible future optimization if classifier cost remains annoying.

2026-06-12 eval-fixture note:

- the fixture is deliberately small and obvious; its job is to catch prompt stupidity early, not to pretend nine hand-picked notes are a substitute for the real dataset.

2026-06-12 classifier note:

- batch-local `note_id` values must be validated against the exact batch order; otherwise even a perfectly labeled fake response can attach the right labels to the wrong notes and make the eval look broken for completely boring reasons.

2026-06-12 resolver note:

- the resolver now fails loudly on missing note classification because "probably neutral" is not a contract; it is just a lazy thought wearing a fake mustache.

2026-06-12 final-answer note:

- a locally written `final_answer.json` can be structurally correct while still being semantically provisional; file shape validation is not the same thing as task completion, no matter how much one might wish otherwise.

2026-06-12 hub-client note:

- there are now three separate things on purpose: the real in-memory verify payload, the masked payload safe for storage, and the full Hub response safe for ignored runtime logs. If those collapse into one object later, someone will eventually leak something stupid.

2026-06-12 CLI note:

- the CLI does not guess whether model or Hub access is allowed; `--scan` fails clearly when uncached notes exist without usable LLM config, and `--submit` still depends on explicit runtime approval for the real external call.

Expected first debugging targets:

- mojibake in exercise text is visible in one shell output, so use UTF-8 reads when exact Polish task text matters,
- JSON files may contain numeric values as integers or floats, so validation should compare numeric values carefully,
- `sensor_type` parsing should trim whitespace and reject unknown names instead of silently ignoring them,
- batch classifier failures should stop before cache writes unless the whole batch output validates.

## Verification Notes

Planned minimal test groups:

| Test Group | Purpose |
| --- | --- |
| `test_sensor_rules` | Prove sensor names, fields, and ranges are wired correctly. |
| `test_deterministic_validator` | Prove measurement anomalies are detected without LLM calls. |
| `test_note_cache` | Prove duplicate notes reuse cached labels. |
| `test_note_classifier_schema` | Prove bad model output is rejected. |
| `test_resolver` | Prove contradiction logic creates the right final anomaly list. |
| `test_answer_writer` | Prove local answer shape is compatible with the Hub contract without storing real API keys. |

Planned real-run verification order:

1. Run deterministic scan only.
2. Inspect count of measurement anomalies.
3. Inspect count of unique normalized notes.
4. Run note classifier on a small sample.
5. Run full note classification.
6. Generate final answer.
7. Submit to Hub only after explicit approval.

## Open Questions

- How many unique normalized notes exist in the real dataset?
- Are notes exact duplicates, near-duplicates, or mostly unique?
- Should low-confidence labels be routed to a manual review JSON before final submission?
- Should the app treat malformed JSON as a recheck anomaly or a hard input failure?
- Should unknown `sensor_type` be included in `recheck` or treated as a blocking data contract failure?

## Future Work

- Add near-duplicate note clustering if exact normalized hashing does not reduce model calls enough.
- Add a manual review report for ambiguous or low-confidence notes.
- Add a replay file for failed classifier batches containing prompt version, model, note IDs, and validation errors without secrets.
- Add cost summary after full classification: model calls, estimated input tokens, estimated output tokens, and cache hit rate.
- Add a small prompt-version field to cached classifications so a changed prompt can invalidate old labels cleanly.
