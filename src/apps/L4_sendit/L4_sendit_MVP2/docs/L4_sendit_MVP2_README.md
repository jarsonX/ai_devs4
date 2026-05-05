# L4 Sendit MVP2

## Table Of Contents

- [Purpose](#purpose)
- [Workflow](#workflow)
- [Input Command](#input-command)
- [MVP2 Scope](#mvp2-scope)
- [Implementation Plan](#implementation-plan)
  - [Stage 1: AI Command Parser](#stage-1-ai-command-parser)
- [Model Selection Plan](#model-selection-plan)
- [Prompt Plan](#prompt-plan)
- [Structured Output Schemas](#structured-output-schemas)
  - [Command Schema](#command-schema)
  - [Selected Sources Schema](#selected-sources-schema)
  - [Extracted Facts Schema](#extracted-facts-schema)
  - [Declaration Data Schema](#declaration-data-schema)
- [Context And Tool Plan](#context-and-tool-plan)
- [Batching And Caching Plan](#batching-and-caching-plan)
- [LLM Design Reviews](#llm-design-reviews)
- [Declaration Language](#declaration-language)
- [AI Role](#ai-role)
- [Configuration](#configuration)
- [Data Locations](#data-locations)
- [Run](#run)
- [Main Modules](#main-modules)
- [Verification](#verification)

## Purpose

`L4_sendit_MVP2` extends the MVP1 pipeline with AI-assisted command parsing, source selection, multimodal extraction, and uncertainty reporting.

The goal is to show where AI adds value without replacing deterministic validation, formatting, persistence, and optional Hub submission.

## Workflow

1. Load a concise command from `.\data\L4_sendit\input\command.txt`.
2. Use AI or a fallback parser to convert the command into structured shipment data.
3. Load local SPK references from `.\data\L4_sendit\references`.
4. Use AI-assisted source selection to identify relevant markdown and image references.
5. Extract the declaration template from `zalacznik-E.md`.
6. Extract route, payment, category, wagon, and abbreviation facts from selected documents.
7. Use a vision-capable model or OCR for image references such as `trasy-wylaczone.png`.
8. Build a structured declaration model with evidence and uncertainty.
9. Validate the model locally with deterministic checks.
10. Render the exact declaration text required by the Hub.
11. Save intermediate artifacts, final output, and a run report.
12. Submit to the Hub only when explicitly requested.

## Input Command

The runtime command file lives in `.\data\L4_sendit\input\command.txt`. The `data` directory is intentionally ignored by Git, so the canonical command content is documented here for GitHub readers.

```text
Prepare a SPK transport declaration for task sendit.

Shipment data:
- sender identifier: 450202122
- origin point: Gdańsk
- destination point: Żarnowiec
- weight: 2800 kg
- budget: 0 PP
- contents: kasety z paliwem do reaktora
- special notes: none

Use the local SPK documentation from .\data\L4_sendit\references.
Return the complete declaration text formatted exactly like the declaration template from the documentation.
```

## MVP2 Scope

| Area | MVP2 behavior |
|---|---|
| AI usage | Bounded and inspectable |
| Command parsing | AI-assisted natural-language extraction with structured output |
| Image handling | Vision or OCR extraction from `trasy-wylaczone.png` |
| Fact extraction | AI-assisted extraction from selected references |
| Reasoning | AI may propose interpretations; code keeps evidence and uncertainty |
| Validation | Deterministic checks remain mandatory |
| Output | Files saved under `.\data\L4_sendit\output` |

## Implementation Plan

MVP2 should be implemented as small stages. Each stage must keep the working MVP1 behavior intact and add one AI-assisted capability behind a clear boundary.

| Stage | Goal | AI role | Deterministic owner | Output |
|---|---|---|---|---|
| 1. AI Command Parser | Convert the operational command into validated structured shipment data. | Extract fields from natural language into a schema. | Validate schema, required fields, types, and semantic basics. | `parsed_command.json`, command parsing section in `run_report.md` |
| 2. Source Selection | Select relevant SPK reference files for the current command. | Rank or choose likely relevant text/image sources. | Load files, check paths, reject unknown or missing references. | `selected_sources.json`, loaded references section |
| 3. Text Fact Extraction | Extract route, payment, category, wagon, and abbreviation facts from markdown files. | Extract candidate facts with evidence snippets and uncertainty. | Validate required facts and evidence references. | `extracted_facts.json` |
| 4. Image Fact Extraction | Extract disabled-route information from `trasy-wylaczone.png`. | Read image/table content with vision or OCR. | Validate extracted route against expected route/category logic. | image evidence in `extracted_facts.json` |
| 5. Reasoned Declaration Model | Combine command data and extracted facts into declaration data. | Propose interpretations and uncertainty notes. | Calculate wagons, validate decisions, render declaration. | `declaration_data.json`, `declaration.txt` |
| 6. Hub Submission | Reuse guarded MVP1 submission behavior. | None. | Mask payload, submit only with `--submit`, save Hub response. | `verification_payload.json`, `hub_response.json` |

### Stage 1: AI Command Parser

Stage 1 is the first implementation step. It replaces the fixed-format MVP1 command parser with an AI-assisted parser, but nothing else in the pipeline should become AI-driven yet.

The reason for starting here is educational: command parsing is language-heavy, low-risk when validated, and easy to compare against the known MVP1 output.

#### Stage 1 Goal

Read `data/L4_sendit/input/command.txt` and produce structured shipment data that can be consumed by the existing deterministic pipeline.

The parser must extract:

| Field | Type | Required | Notes |
|---|---|---|---|
| `sender_identifier` | string | yes | Expected current value: `450202122` |
| `origin_point` | string | yes | Preserve Polish characters, for example `Gdańsk` |
| `destination_point` | string | yes | Preserve Polish characters, for example `Żarnowiec` |
| `weight_kg` | integer | yes | Normalize `2.8 tony` or `2800 kg` to kilograms |
| `budget_pp` | integer | yes | Normalize `0 PP` to `0` |
| `contents` | string | yes | Preserve Polish wording |
| `special_notes` | string | yes | Normalize no notes to `none` |
| `confidence` | number | yes | Range `0.0` to `1.0` |
| `missing_fields` | list[string] | yes | Empty when all required fields are present |
| `uncertainty_notes` | list[string] | yes | Empty when no parsing uncertainty remains |

#### Stage 1 Boundaries

Stage 1 may use AI only for command parsing.

Stage 1 must not:

- select SPK reference files dynamically,
- extract facts from `index.md` or attachments,
- use vision/OCR,
- change route/category/payment reasoning,
- change declaration rendering,
- submit to the Hub automatically.

MVP1 deterministic logic remains responsible for static facts, wagon calculation, local validation, declaration rendering, artifact writing, and guarded Hub submission.

#### Stage 1 Guardrails

Every real model run must have an explicit small guard:

```text
DEFAULT_MAX_MODEL_REQUESTS = 1
```

The guard lives in `config.py` because it is an application safety setting, not a secret. If the limit is reached, the app should fail with a clear guard-related error instead of retrying indefinitely.

Model output must be treated as untrusted until deterministic validation confirms:

- required fields are present,
- field types are correct,
- `weight_kg` and `budget_pp` are normalized integers,
- `confidence` is within `0.0` to `1.0`,
- `missing_fields` and `uncertainty_notes` are lists,
- Polish values are preserved.

This follows the schema-first validation approach from `_agent/references/L1_structured_outputs_and_validation.md`.

#### Stage 1 Artifacts

Stage 1 should save:

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/parsed_command.json` | Validated structured command used by the pipeline |
| `data/L4_sendit/output/model_command_parse_raw.json` | Raw model response for inspection, without secrets |
| `data/L4_sendit/output/run_report.md` | Parsing summary, validation results, and uncertainty notes |

#### Stage 1 Acceptance Criteria

Stage 1 is complete when:

1. The app can parse the current command with AI into the same core shipment values MVP1 used.
2. Invalid or incomplete model output fails before downstream use.
3. `parsed_command.json` contains the validated schema fields listed above.
4. `run_report.md` explains whether AI parsing had missing fields or uncertainty.
5. The final declaration remains equivalent to the Hub-accepted MVP1 declaration.
6. No model call can exceed the configured request limit.

## Model Selection Plan

MVP2 should use the smallest capable model for each step. Model names are configured as explicit application defaults in `config.py`, not in `.env`, because model choice is a design decision rather than a secret. If provider capabilities, pricing, or course constraints change, update these defaults intentionally with the related README note.

| Step | Planned model class | Config default | Reason | Validation strength |
|---|---|---|---|---|
| AI Command Parser | lightweight text model | `DEFAULT_COMMAND_PARSE_MODEL = "gpt-5.4-mini"` | Narrow extraction from one command is simple and strongly validated. | high |
| Source Selection | lightweight text model | `DEFAULT_SOURCE_SELECTION_MODEL = "gpt-5.4-mini"` | The model ranks a small list of local reference filenames and summaries. | high |
| Text Fact Extraction | lightweight or mid-strength text model | `DEFAULT_TEXT_EXTRACTION_MODEL = "gpt-5.4-mini"` | Extraction may span longer markdown files, but facts must include evidence. | medium-high |
| Image Fact Extraction | vision-capable model | `DEFAULT_VISION_EXTRACTION_MODEL = "gpt-5.4-mini"` | The step must read image/table content from `trasy-wylaczone.png`. | medium |
| Reasoned Declaration Model | mid-strength text model | `DEFAULT_REASONING_MODEL = "gpt-5.5"` | The model may propose interpretations and uncertainty notes from extracted facts. | medium |

The code should keep the step name and selected default visible in reports so cost and latency can be reviewed later.

This plan follows `_agent/references/L1_model_selection.md`: simple and strongly validated steps use lighter models; ambiguous or multimodal steps get stronger capability only where needed.

## Prompt Plan

Each prompt should be short, scoped to one step, and shaped as:

```text
Task:
Context:
Constraints:
Output format:
```

Prompts must not include full conversation history, unrelated reference files, secrets, or Hub credentials.

| Step | Prompt type | Required context | Hard constraints | Output format |
|---|---|---|---|---|
| AI Command Parser | extraction | raw `command.txt` only | preserve Polish text, normalize units, do not infer missing required values | command schema |
| Source Selection | classification/ranking | command summary plus local reference inventory | choose only existing local paths, explain relevance briefly | selected sources schema |
| Text Fact Extraction | extraction | selected markdown files only | quote or identify evidence location, do not use unselected files | extracted facts schema |
| Image Fact Extraction | multimodal extraction | selected image file plus target route | extract only visible information, report uncertainty | image fact schema |
| Reasoned Declaration Model | synthesis | validated command plus validated extracted facts | keep deterministic calculations in code, preserve uncertainty notes | declaration data schema |

Stage 1 prompt outline:

```text
Task:
Extract shipment fields from the command into the required JSON schema.

Context:
<contents of data/L4_sendit/input/command.txt>

Constraints:
- Preserve Polish characters and wording.
- Normalize weight to integer kilograms.
- Normalize budget to integer PP.
- Use special_notes = "none" when the command says there are no notes.
- Do not guess missing required values. Add them to missing_fields.
- Return only JSON matching the schema.

Output format:
<command schema fields from Stage 1>
```

This plan follows `_agent/references/L1_prompt_design.md`: one task per prompt, minimal context, explicit constraints, and explicit output format.

## Structured Output Schemas

All model outputs consumed by code must be validated before downstream use.

### Command Schema

Defined in `Stage 1: AI Command Parser`.

### Selected Sources Schema

```json
{
  "selected_sources": [
    {
      "path": "data/L4_sendit/references/index.md",
      "source_type": "markdown",
      "reason": "Contains route and fee rules.",
      "confidence": 0.0
    }
  ],
  "missing_sources": [],
  "uncertainty_notes": []
}
```

Validation rules:

- `path` must point to an existing file under `data/L4_sendit/references`.
- `source_type` must be one of `markdown`, `image`, or `other`.
- `confidence` must be within `0.0` to `1.0`.
- Unknown paths are rejected.

### Extracted Facts Schema

```json
{
  "facts": [
    {
      "name": "route_code",
      "value": "X-01",
      "evidence_source": "data/L4_sendit/references/trasy-wylaczone.png",
      "evidence_note": "Visible disabled route entry for Gdańsk - Żarnowiec.",
      "confidence": 0.0,
      "uncertainty_notes": []
    }
  ],
  "missing_facts": [],
  "conflicts": []
}
```

Validation rules:

- required fact names must include route, route status, category rule, funding rule, wagon capacity, and WDP meaning before final reasoning,
- every fact must have an evidence source,
- evidence sources must be selected local files,
- conflicts must be preserved and reported instead of silently resolved.

### Declaration Data Schema

```json
{
  "sender_identifier": "450202122",
  "origin_point": "Gdańsk",
  "destination_point": "Żarnowiec",
  "route_code": "X-01",
  "category": "A",
  "contents": "kasety z paliwem do reaktora",
  "declared_weight_kg": 2800,
  "wdp": 4,
  "special_notes": "brak",
  "amount_due_pp": 0,
  "evidence": {},
  "uncertainty_notes": []
}
```

Validation rules:

- deterministic code calculates `wdp` and wagon capacity,
- deterministic code validates route/category/payment consistency,
- declaration rendering consumes this schema only after validation passes.

This plan follows `_agent/references/L1_structured_outputs_and_validation.md`: model output is untrusted until schema and semantic validation pass.

## Context And Tool Plan

MVP2 should pass only the context needed by the current step.

| Step | Context allowed | Context excluded |
|---|---|---|
| AI Command Parser | raw command text | SPK references, previous full run reports, Hub response |
| Source Selection | parsed command summary, reference file inventory, optional short index summary | full contents of all references |
| Text Fact Extraction | selected markdown files | unselected markdown files, image files |
| Image Fact Extraction | selected image file and target route | unrelated images or full markdown contents |
| Reasoned Declaration Model | validated command and validated facts | raw unvalidated model responses |

The model should not receive filesystem write tools, Hub submission tools, API keys, or authorization decisions. Code owns file loading, path checks, artifact writing, and Hub submission.

## Batching And Caching Plan

MVP2 should avoid repeated model calls when a result can be reused safely.

| Step | Batching/caching rule | Freshness rule |
|---|---|---|
| AI Command Parser | cache by command file content hash | invalidate when `command.txt` changes |
| Source Selection | cache by command hash plus reference inventory hash | invalidate when command or reference list changes |
| Text Fact Extraction | batch selected markdown files when prompt size stays small and traceable | invalidate when selected file content changes |
| Image Fact Extraction | cache by image file hash and target route | invalidate when image file changes |
| Reasoned Declaration Model | cache by validated command plus extracted facts hash | invalidate when command or facts change |

Every cached artifact must still pass deterministic validation before reuse.

## LLM Design Reviews

| Date | Scope | Checklist | Result | Approved Implementation Boundary |
|---|---|---|---|---|
| 2026-05-05 | Full MVP2 workflow design | `_agent/instructions/llm_design_checklist.md` | PASS | Implement MVP2 stages according to this README; each material design change requires a new checklist review. |

## Declaration Language

The generated SPK declaration must be written in Polish because the SPK documentation, declaration template, route names, and declared contents use Polish.

Technical code, module names, comments, and documentation stay in English, but values rendered into the declaration should preserve Polish wording such as `Gdańsk`, `Żarnowiec`, and `kasety z paliwem do reaktora`.

## AI Role

AI should be used where the task is language-heavy, ambiguous, or multimodal:

- parsing a natural-language command into structured shipment data,
- selecting relevant reference files from the documentation index,
- extracting facts from long or fragmented documentation,
- reading image-based documentation such as disabled-route tables,
- explaining uncertainty when a field has more than one plausible interpretation.

Deterministic code should own stable operations:

- loading files from known paths,
- calculating additional wagons,
- checking required fields,
- validating route/category/payment consistency,
- rendering the declaration from a template,
- saving output files,
- sending the optional verification request.

## Configuration

Secrets and private endpoint configuration are loaded from `.env`:

```text
AI_DEVS_API_KEY
HUB_VERIFY_URL
OPENAI_API_KEY
```

Model names and model-call limits are application settings in `config.py`:

```text
DEFAULT_COMMAND_PARSE_MODEL
DEFAULT_SOURCE_SELECTION_MODEL
DEFAULT_TEXT_EXTRACTION_MODEL
DEFAULT_VISION_EXTRACTION_MODEL
DEFAULT_REASONING_MODEL
DEFAULT_MAX_MODEL_REQUESTS
```

Do not store real API keys, tokens, private URLs, or credentials in source files, docs, logs, committed output, or model configuration constants.

## Data Locations

All runtime files should live under the repository-level `.\data\L4_sendit` directory.

| Path | Purpose |
|---|---|
| `.\data\L4_sendit\input\command.txt` | Operational command received by the app |
| `.\data\L4_sendit\references\index.md` | Main local SPK documentation entry point |
| `.\data\L4_sendit\references\*` | Local SPK attachments and supporting reference files |
| `.\data\L4_sendit\output\parsed_command.json` | Parsed command data |
| `.\data\L4_sendit\output\model_command_parse_raw.json` | Raw AI command parser response without secrets |
| `.\data\L4_sendit\output\selected_sources.json` | Validated AI-assisted source selection |
| `.\data\L4_sendit\output\extracted_facts.json` | AI/deterministic extracted facts with evidence |
| `.\data\L4_sendit\output\declaration_data.json` | Structured declaration model with evidence and uncertainty |
| `.\data\L4_sendit\output\declaration.txt` | Final declaration string |
| `.\data\L4_sendit\output\verification_payload.json` | Hub payload without exposing secrets |
| `.\data\L4_sendit\output\hub_response.json` | Hub response saved only after explicit `--submit` |
| `.\data\L4_sendit\output\run_report.md` | Human-readable summary of decisions, validations, and risks |

No generated artifact should be written under `.\src\apps\L4_sendit`.

## Run

Stage 1 has a runnable implementation. It uses AI only for command parsing, then reuses the deterministic MVP1 pipeline for facts, declaration rendering, local validation, and optional Hub submission.

Run with a real guarded model call:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt
```

Run local validation with a saved model-shaped JSON file instead of a real API call:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --mock-model-output-file .\data\L4_sendit\output\model_command_parse_raw.json
```

Optional submission:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --submit
```

The `--submit` flag should be the only path that sends a real request to the Hub.

## Main Modules

Planned modules:

| Path | Responsibility |
|---|---|
| `config.py` | Load secret/private endpoint configuration, runtime paths, model defaults, and model-call limits |
| `models.py` | Define command, extracted fact, declaration, and validation data structures |
| `command_parser.py` | Convert the operational command into structured shipment data |
| `reference_loader.py` | Load local documentation and discover included reference files |
| `source_selector.py` | Select relevant reference files for the current command |
| `fact_extractor.py` | Extract text-based facts from markdown references |
| `image_fact_extractor.py` | Extract facts from image references with vision or OCR |
| `reasoning.py` | Combine shipment data and extracted facts into a declaration model |
| `declaration_builder.py` | Render the final declaration text from the template |
| `validator.py` | Check required fields, calculations, formatting, and known consistency rules |
| `hub_client.py` | Submit the final payload to the Hub when explicitly requested |
| `output.py` | Save declaration text, structured data, payload, and debug reports |

Current implemented Stage 1 files:

| Path | Responsibility |
|---|---|
| `__init__.py` | Define the MVP2 package |
| `config.py` | Load Stage 1 paths, model settings, and model-call guard values |
| `models.py` | Define the AI parsed command schema and parser result structures |
| `command_parser.py` | Run the guarded AI parser or validate a saved model-shaped JSON payload |
| `validator.py` | Validate parsed command output before downstream use |
| `report_builder.py` | Render the Stage 1 run report |
| `main.py` | Run Stage 1 and reuse the deterministic MVP1 declaration pipeline |
| `docs/L4_sendit_MVP2_README.md` | MVP2 design and implementation notes |

## Verification

Local verification should run before any Hub submission:

1. Confirm that AI output matches the expected structured schema.
2. Confirm that the app records evidence for derived facts.
3. Confirm that Polish declaration values remain in Polish.
4. Confirm that image extraction found or preserved the route evidence.
5. Confirm that deterministic validation passes before rendering.
6. Confirm that no model call loop can exceed the configured request limit.
7. Confirm that final declaration field order and separators match the template.

Hub verification should be explicit and guarded by `--submit`.
