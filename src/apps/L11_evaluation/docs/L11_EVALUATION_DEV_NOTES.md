# L11 Evaluation Dev Notes

## Table Of Contents

- [Implementation Notes](#implementation-notes)
- [Design Decisions](#design-decisions)
- [Implementation Plan](#implementation-plan)
- [LLM Design Review Preparation](#llm-design-review-preparation)
- [LLM Design Checklist Review](#llm-design-checklist-review)
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

## Debugging Notes

No implementation debugging has happened yet.

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
