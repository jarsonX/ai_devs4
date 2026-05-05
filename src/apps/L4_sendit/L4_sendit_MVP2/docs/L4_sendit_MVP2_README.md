# L4 Sendit MVP2

## Table Of Contents

- [Purpose](#purpose)
- [Workflow](#workflow)
- [Input Command](#input-command)
- [MVP2 Scope](#mvp2-scope)
- [Implementation Plan](#implementation-plan)
  - [Stage 1: AI Command Parser](#stage-1-ai-command-parser)
  - [Stage 2: Source Selection](#stage-2-source-selection)
  - [Stage 3: Text Fact Extraction](#stage-3-text-fact-extraction)
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

### Stage 2: Source Selection

Stage 2 is the second implementation step. It adds AI-assisted selection of local SPK reference files, but it must not extract facts or reason about the final declaration yet.

The reason for this stage is educational: a model can help reduce a broad local reference set to a small task-relevant context package, while deterministic code keeps file access, path validation, and downstream boundaries safe.

This design follows `_agent/references/L2_context_routing_and_tool_exposure.md`, `_agent/references/L2_query_transformation_context_and_optimization.md`, and `_agent/references/L1_structured_outputs_and_validation.md`.

#### Stage 2 Goal

Use the validated Stage 1 command and a deterministic inventory of `data/L4_sendit/references` to produce a validated source selection plan for later extraction stages.

Stage 2 should answer this narrow question:

```text
Which local SPK reference files should later extraction stages inspect for this shipment?
```

Stage 2 output is a source-selection artifact, not extracted facts.

#### Stage 2 Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/output/parsed_command.json` | Stage 1 | Must already pass command validation |
| `data/L4_sendit/references` file inventory | deterministic code | Include path, source type, size, and a short deterministic description when available |
| Optional reference hints | deterministic code | Filename-derived hints such as `zalacznik-E`, `trasy-wylaczone`, or `dodatkowe-wagony`; not full file contents |

The model should not receive full contents of every reference file. It should receive a compact inventory because Stage 2 is selecting sources, not reading or extracting them.

#### Stage 2 Candidate Inventory

The deterministic inventory should include the current local reference files:

| Path | Source type | Inventory hint |
|---|---|---|
| `data/L4_sendit/references/index.md` | markdown | main SPK documentation index and broad rules |
| `data/L4_sendit/references/zalacznik-C.md` | markdown | attachment C |
| `data/L4_sendit/references/zalacznik-D.md` | markdown | attachment D |
| `data/L4_sendit/references/zalacznik-E.md` | markdown | declaration template |
| `data/L4_sendit/references/zalacznik-F.md` | markdown | attachment F |
| `data/L4_sendit/references/zalacznik-G.md` | markdown | attachment G |
| `data/L4_sendit/references/zalacznik-H.md` | markdown | attachment H |
| `data/L4_sendit/references/dodatkowe-wagony.md` | markdown | additional wagon information |
| `data/L4_sendit/references/trasy-wylaczone.png` | image | disabled routes image/table |

Code must discover the actual files at runtime and reject model-selected paths that are not present in the current inventory. The table above documents the expected current learning dataset, not a permission to trust hard-coded model paths.

#### Stage 2 Output Schema

Stage 2 should produce:

```json
{
  "selected_sources": [
    {
      "path": "data/L4_sendit/references/index.md",
      "source_type": "markdown",
      "reason": "Contains broad SPK rules likely needed for route, category, and payment interpretation.",
      "intended_use": "text_fact_extraction",
      "confidence": 0.0
    }
  ],
  "rejected_sources": [
    {
      "path": "data/L4_sendit/references/zalacznik-C.md",
      "reason": "Not relevant to this shipment based on the inventory hints."
    }
  ],
  "missing_sources": [],
  "uncertainty_notes": []
}
```

Validation rules:

- `selected_sources` must be a non-empty list.
- Every selected `path` must exactly match a file discovered under `data/L4_sendit/references`.
- No absolute paths, parent traversal, URLs, generated paths, or paths outside `data/L4_sendit/references` are allowed.
- `source_type` must match the discovered file type: `markdown`, `image`, or `other`.
- `intended_use` must be one of `text_fact_extraction`, `image_fact_extraction`, `template_reference`, or `supporting_context`.
- `confidence` must be within `0.0` to `1.0`.
- `missing_sources` and `uncertainty_notes` must be lists.
- If a required source category is missing, the app must fail before Stage 3 instead of guessing.

Required source categories for the current workflow:

| Required category | Why it is needed | Expected source pattern |
|---|---|---|
| declaration template | Preserve final declaration format | `zalacznik-E.md` |
| broad SPK rules | Route/category/payment reasoning in later stages | `index.md` |
| disabled route evidence | Confirm route status for `Gdańsk` to `Żarnowiec` | `trasy-wylaczone.png` |
| wagon capacity | Calculate additional wagons deterministically | `dodatkowe-wagony.md` |
| WDP meaning | Keep WDP interpretation traceable | `zalacznik-G.md` |

#### Stage 2 Prompt Plan

Stage 2 prompt should be scoped to source selection only:

```text
Task:
Select local SPK reference files that later extraction stages should inspect.

Context:
<validated parsed command summary>
<deterministic reference inventory with path, type, size, and short hint>

Constraints:
- Choose only paths from the provided inventory.
- Do not extract facts from the references.
- Do not infer route codes, category, payment, wagons, or declaration text.
- Include a short reason and intended_use for each selected source.
- Report missing or uncertain source needs explicitly.
- Return only JSON matching the selected sources schema.

Output format:
<selected sources schema>
```

#### Stage 2 Boundaries

Stage 2 may use AI only to rank or choose from the deterministic local reference inventory.

Stage 2 must not:

- read full reference contents into the model,
- extract facts from markdown files,
- use vision/OCR on `trasy-wylaczone.png`,
- decide the final route, category, payment, WDP, or declaration text,
- write outside `data/L4_sendit/output`,
- submit anything to the Hub.

Deterministic code remains responsible for discovering reference files, building the inventory, checking selected paths, enforcing allowed source types, writing artifacts, and stopping on invalid or incomplete selection.

#### Stage 2 Guardrails

Every real model run must stay within the application model-call guard:

```text
DEFAULT_MAX_MODEL_REQUESTS = 1
```

Model output must be treated as untrusted until deterministic validation confirms:

- schema shape is valid,
- selected paths are known local inventory paths,
- required source categories are covered,
- selected source types match discovered file types,
- uncertainty and missing-source notes are preserved,
- no downstream extraction or reasoning fields were smuggled into the response.

#### Stage 2 Artifacts

Stage 2 should save:

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/reference_inventory.json` | Deterministically built local source inventory |
| `data/L4_sendit/output/selected_sources.json` | Validated source selection consumed by later stages |
| `data/L4_sendit/output/model_source_selection_raw.json` | Raw source selection model response without secrets |
| `data/L4_sendit/output/run_report.md` | Add source selection summary and validation results |

#### Stage 2 Acceptance Criteria

Stage 2 is complete when:

1. The app builds a deterministic inventory of files under `data/L4_sendit/references`.
2. The model receives only the parsed command summary and compact inventory, not full reference contents.
3. `selected_sources.json` contains only validated local reference paths.
4. The selected sources cover the required categories for template, broad rules, disabled route evidence, wagon capacity, and WDP meaning.
5. Invalid, unknown, absolute, URL, or out-of-directory paths fail before Stage 3.
6. `run_report.md` explains selected sources, rejected sources, missing sources, uncertainty, and validation status.
7. Stage 2 does not change declaration rendering or Hub submission behavior.

### Stage 3: Text Fact Extraction

Stage 3 is the third implementation step. It adds AI-assisted extraction of traceable facts from markdown reference files selected by Stage 2.

The reason for this stage is educational: a model can read selected text references and extract candidate facts with evidence, while deterministic code keeps file loading, source boundaries, schema validation, required-fact validation, and downstream decisions outside the model.

This design follows `_agent/references/L1_task_decomposition_and_pipeline_design.md`, `_agent/references/L1_prompt_design.md`, `_agent/references/L1_structured_outputs_and_validation.md`, and `_agent/references/L2_context_routing_and_tool_exposure.md`.

#### Stage 3 Goal

Use validated Stage 1 command data and validated Stage 2 selected markdown sources to extract structured text facts needed by later reasoning stages.

Stage 3 should answer this narrow question:

```text
What facts are explicitly supported by the selected markdown SPK references?
```

Stage 3 output is a text-fact evidence artifact, not a final declaration decision.

#### Stage 3 Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/output/parsed_command.json` | Stage 1 | Used only as task context for relevant fact targets |
| `data/L4_sendit/output/selected_sources.json` | Stage 2 | Must already pass source selection validation |
| selected markdown files | deterministic code | Load only selected local sources whose `source_type` is `markdown` |
| selected source metadata | deterministic code | Include path and intended use next to the text content |

Stage 3 should load selected markdown files such as:

| Path | Expected purpose |
|---|---|
| `data/L4_sendit/references/index.md` | broad SPK rules, category/payment rules, route exception rules |
| `data/L4_sendit/references/zalacznik-E.md` | declaration template structure |
| `data/L4_sendit/references/dodatkowe-wagony.md` | standard and additional wagon capacity |
| `data/L4_sendit/references/zalacznik-G.md` | WDP meaning |

Stage 3 must not load or analyze `data/L4_sendit/references/trasy-wylaczone.png`; image-based route evidence is reserved for Stage 4.

#### Stage 3 Fact Targets

Stage 3 should extract only text-supported facts. The current workflow needs these text fact targets before later stages can reason safely:

| Fact name | Source expectation | Purpose |
|---|---|---|
| `declaration_template_fields` | `zalacznik-E.md` | Preserve required declaration structure |
| `strategic_transport_category_rule` | `index.md` or another selected markdown rule source | Support later category reasoning for reactor fuel cassettes |
| `disabled_route_exception_rule` | `index.md` or another selected markdown rule source | Preserve the textual rule that may allow selected disabled routes by category |
| `system_funded_categories` | `index.md` or another selected markdown rule source | Support later payment reasoning |
| `standard_capacity_kg` | `dodatkowe-wagony.md` | Support deterministic wagon calculation |
| `additional_wagon_capacity_kg` | `dodatkowe-wagony.md` | Support deterministic wagon calculation |
| `wdp_meaning` | `zalacznik-G.md` | Keep WDP interpretation traceable |

If a target is not present in selected markdown, the model must add it to `missing_facts` instead of guessing.

#### Stage 3 Output Schema

Stage 3 should produce:

```json
{
  "facts": [
    {
      "name": "additional_wagon_capacity_kg",
      "value": "500",
      "unit": "kg",
      "source_path": "data/L4_sendit/references/dodatkowe-wagony.md",
      "evidence_note": "Short note identifying the relevant rule or section.",
      "evidence_quote": "Short exact evidence excerpt from the source.",
      "confidence": 0.0,
      "uncertainty_notes": []
    }
  ],
  "missing_facts": [],
  "conflicts": [],
  "source_coverage": [
    {
      "path": "data/L4_sendit/references/dodatkowe-wagony.md",
      "used": true,
      "notes": "Provided wagon capacity facts."
    }
  ]
}
```

Validation rules:

- `facts` must be a non-empty list.
- `name` must be one of the approved Stage 3 fact targets.
- `source_path` must exactly match a selected markdown source path from Stage 2.
- `source_path` must not point to image sources, unselected files, URLs, absolute paths, or paths outside `data/L4_sendit/references`.
- `evidence_quote` must be present, short, and found in the loaded source text.
- numeric facts such as `standard_capacity_kg` and `additional_wagon_capacity_kg` must parse to positive integers with `unit = "kg"`.
- `confidence` must be within `0.0` to `1.0`.
- `missing_facts`, `conflicts`, and `uncertainty_notes` must be preserved and reported.
- if required text fact targets are missing or conflicted, the app must fail before Stage 5 declaration reasoning.

#### Stage 3 Prompt Plan

Stage 3 prompt should be scoped to text extraction only:

```text
Task:
Extract explicit facts from selected markdown SPK references.

Context:
<validated parsed command summary>
<selected markdown source metadata>
<contents of selected markdown sources only>
<approved Stage 3 fact target list>

Constraints:
- Extract only facts explicitly supported by the provided markdown text.
- Include source_path, evidence_note, and a short exact evidence_quote for every fact.
- Do not use image sources.
- Do not use unselected files.
- Do not decide final route, category, payment, WDP, or declaration text.
- Do not guess missing facts. Add them to missing_facts.
- Preserve conflicts instead of resolving them silently.
- Return only JSON matching the extracted facts schema.

Output format:
<extracted facts schema>
```

#### Stage 3 Boundaries

Stage 3 may use AI only to extract facts from selected markdown text.

Stage 3 must not:

- select new sources,
- load or analyze image sources,
- use vision/OCR,
- infer facts from filenames alone,
- decide final route code or route status from `trasy-wylaczone.png`,
- calculate WDP or final wagon count,
- select the final shipment category or payment amount,
- render or submit the declaration.

Deterministic code remains responsible for loading selected markdown files, checking path boundaries, batching or chunking text if needed, validating evidence quotes against source text, validating required facts, writing artifacts, and stopping on invalid or incomplete extraction.

#### Stage 3 Guardrails

Every real model run must stay within the application model-call guard:

```text
DEFAULT_MAX_MODEL_REQUESTS = 1
```

If selected markdown content later becomes too large for one safe prompt, Stage 3 must be explicitly redesigned before implementation. Do not silently add multiple model calls or broad chunking outside this reviewed scope.

Model output must be treated as untrusted until deterministic validation confirms:

- schema shape is valid,
- facts use only approved names,
- every evidence source is a selected markdown file,
- evidence quotes are present in the source text,
- required fact targets are covered or explicitly missing,
- numeric values are parseable where required,
- conflicts and uncertainty are preserved.

#### Stage 3 Artifacts

Stage 3 should save:

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/text_extraction_context.json` | Selected markdown source metadata and content hashes used for extraction |
| `data/L4_sendit/output/extracted_text_facts.json` | Validated text facts with evidence |
| `data/L4_sendit/output/model_text_fact_extraction_raw.json` | Raw text extraction model response without secrets |
| `data/L4_sendit/output/extracted_facts.json` | Combined fact artifact, initially populated with text facts and later extended by Stage 4 |
| `data/L4_sendit/output/run_report.md` | Add text fact extraction summary and validation results |

#### Stage 3 Acceptance Criteria

Stage 3 is complete when:

1. The app loads only selected markdown sources from Stage 2.
2. The model receives only the parsed command summary, selected markdown metadata, selected markdown text, and approved fact targets.
3. `extracted_text_facts.json` contains validated facts with source paths and evidence quotes.
4. Evidence quotes are verified against the loaded source text before downstream use.
5. Required text fact targets are either present and valid or listed as missing with a blocking validation error.
6. Image-derived route evidence remains untouched for Stage 4.
7. Stage 3 does not change declaration rendering or Hub submission behavior.

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
      "intended_use": "text_fact_extraction",
      "confidence": 0.0
    }
  ],
  "rejected_sources": [],
  "missing_sources": [],
  "uncertainty_notes": []
}
```

Validation rules:

- `path` must point to an existing file under `data/L4_sendit/references`.
- `source_type` must be one of `markdown`, `image`, or `other`.
- `intended_use` must be one of `text_fact_extraction`, `image_fact_extraction`, `template_reference`, or `supporting_context`.
- `confidence` must be within `0.0` to `1.0`.
- Unknown paths are rejected.
- Required source categories must be covered before Stage 3 runs.

### Extracted Facts Schema

```json
{
  "facts": [
    {
      "name": "additional_wagon_capacity_kg",
      "value": "500",
      "unit": "kg",
      "source_path": "data/L4_sendit/references/dodatkowe-wagony.md",
      "evidence_note": "Short note identifying the relevant rule or section.",
      "evidence_quote": "Short exact evidence excerpt from the source.",
      "confidence": 0.0,
      "uncertainty_notes": []
    }
  ],
  "missing_facts": [],
  "conflicts": [],
  "source_coverage": [
    {
      "path": "data/L4_sendit/references/dodatkowe-wagony.md",
      "used": true,
      "notes": "Provided wagon capacity facts."
    }
  ]
}
```

Validation rules:

- Stage 3 text facts must use approved text fact names and selected markdown sources only,
- Stage 4 image facts may later extend the combined artifact with image-derived route evidence,
- every fact must have `source_path`, `evidence_note`, and `evidence_quote`,
- evidence sources must be selected local files of the correct source type for the stage,
- evidence quotes must be verified against loaded source text when the source is markdown,
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
| 2026-05-05 | MVP2 Stage 2: Source Selection | `_agent/instructions/llm_design_checklist.md` | PASS | Implement Stage 2 source selection only; fact extraction, vision/OCR, declaration reasoning, and Hub submission remain outside this boundary. |
| 2026-05-05 | MVP2 Stage 3: Text Fact Extraction | `_agent/instructions/llm_design_checklist.md` | PASS | Implement Stage 3 text fact extraction only; image/OCR extraction, final route/category/payment reasoning, declaration rendering, and Hub submission remain outside this boundary. |

### Stage 2 Checklist Evidence

Checklist scope: `MVP2 Stage 2: Source Selection`.

| Checklist item | Status | Evidence note |
|---|---|---|
| The application has a clearly defined goal and expected output. | YES | Stage 2 goal is to select local SPK reference files and write `selected_sources.json`; it does not extract facts. |
| The workflow is split into small steps when one model call would mix multiple responsibilities. | YES | Stage 2 is separated from Stage 1 parsing, Stage 3 text extraction, Stage 4 image extraction, and Stage 5 declaration reasoning. |
| Deterministic code is planned for stable logic, and LLM calls are reserved for language or reasoning tasks. | YES | Code discovers files, builds inventory, validates paths, writes artifacts, and stops on invalid selection; the model only ranks or chooses sources. |
| Each planned workflow step has a clear purpose. | YES | Stage 2 purpose is source selection from a compact inventory for later extraction stages. |
| Each LLM step has a reason for using a model instead of ordinary code. | YES | A model is useful for matching shipment intent to likely relevant reference files when filenames and hints are human-oriented. |
| The selected model for each step matches the expected difficulty of that step. | YES | Source selection uses `DEFAULT_SOURCE_SELECTION_MODEL = "gpt-5.4-mini"`, a lightweight model for a narrow, strongly validated choice. |
| Prompts are planned to be short, focused, and limited to the current step. | YES | Stage 2 prompt includes only parsed command summary, compact inventory, constraints, and the selected sources schema. |
| Structured outputs are planned wherever code will consume the result. | YES | Stage 2 defines a JSON schema with `selected_sources`, `rejected_sources`, `missing_sources`, and `uncertainty_notes`. |
| The design limits context to only what the current step needs. | YES | The model receives a compact inventory, not full reference contents or previous full reports. |
| The design limits tool exposure to only the tools needed for the current step. | YES | The model receives no filesystem, Hub, or write tools; code owns discovery, validation, and artifact writing. |
| The design avoids passing full history, full datasets, or irrelevant examples by default. | YES | Full markdown contents and image bytes are explicitly excluded from Stage 2. |
| The workflow includes batching or caching where repeated calls are likely. | YES | Existing caching plan caches source selection by command hash plus reference inventory hash, and requires validation before reuse. |
| The design includes validation before model output is used downstream. | YES | Stage 2 validation checks schema, known local paths, source types, required categories, and uncertainty fields before Stage 3. |
| The design treats model output as untrusted until validation passes. | YES | Stage 2 guardrails explicitly state that selected paths and source categories are untrusted until deterministic validation passes. |
| The design keeps authorization, permissions, and risky actions outside the model. | YES | Hub submission, file access, path checks, and writes remain deterministic code responsibilities. |
| The workflow handles missing required inputs without guessing important values. | YES | Missing source categories must be recorded and cause failure before Stage 3 instead of silent guessing. |

### Stage 3 Checklist Evidence

Checklist scope: `MVP2 Stage 3: Text Fact Extraction`.

| Checklist item | Status | Evidence note |
|---|---|---|
| The application has a clearly defined goal and expected output. | YES | Stage 3 goal is to extract explicit text-supported facts into `extracted_text_facts.json` and the combined `extracted_facts.json`. |
| The workflow is split into small steps when one model call would mix multiple responsibilities. | YES | Stage 3 is separated from source selection, image extraction, declaration reasoning, and Hub submission. |
| Deterministic code is planned for stable logic, and LLM calls are reserved for language or reasoning tasks. | YES | Code loads selected markdown, checks paths, validates evidence quotes, validates required facts, writes artifacts, and stops on invalid extraction; the model only extracts facts from text. |
| Each planned workflow step has a clear purpose. | YES | Stage 3 purpose is text fact extraction from selected markdown sources with evidence. |
| Each LLM step has a reason for using a model instead of ordinary code. | YES | A model is useful for reading selected prose references and mapping relevant passages to structured fact targets with evidence. |
| The selected model for each step matches the expected difficulty of that step. | YES | Text extraction uses `DEFAULT_TEXT_EXTRACTION_MODEL = "gpt-5.4-mini"`, suitable for selected markdown extraction with deterministic validation. |
| Prompts are planned to be short, focused, and limited to the current step. | YES | Stage 3 prompt includes parsed command summary, selected markdown metadata/content, approved fact targets, constraints, and schema only. |
| Structured outputs are planned wherever code will consume the result. | YES | Stage 3 defines structured facts with names, values, units, source paths, evidence notes, evidence quotes, confidence, missing facts, conflicts, and source coverage. |
| The design limits context to only what the current step needs. | YES | Stage 3 receives selected markdown sources only; image files, unselected files, full history, and Hub data are excluded. |
| The design limits tool exposure to only the tools needed for the current step. | YES | The model receives no filesystem, Hub, write, or submission tools; code owns loading, validation, and artifact writing. |
| The design avoids passing full history, full datasets, or irrelevant examples by default. | YES | Stage 3 excludes unselected references and image bytes; it uses selected markdown files from Stage 2 only. |
| The workflow includes batching or caching where repeated calls are likely. | YES | Existing caching plan caches text extraction by selected file content, and Stage 3 requires redesign before adding broad chunking or multiple model calls. |
| The design includes validation before model output is used downstream. | YES | Stage 3 validation checks schema, approved fact names, selected markdown source paths, evidence quotes, numeric values, missing facts, and conflicts before Stage 5. |
| The design treats model output as untrusted until validation passes. | YES | Stage 3 guardrails explicitly require deterministic validation before facts are used downstream. |
| The design keeps authorization, permissions, and risky actions outside the model. | YES | File access, path checks, writes, declaration rendering, and Hub submission stay outside the model. |
| The workflow handles missing required inputs without guessing important values. | YES | Missing fact targets must be listed in `missing_facts` and block later declaration reasoning when required facts are absent. |

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
| `.\data\L4_sendit\output\reference_inventory.json` | Deterministically discovered local reference inventory |
| `.\data\L4_sendit\output\selected_sources.json` | Validated AI-assisted source selection |
| `.\data\L4_sendit\output\model_source_selection_raw.json` | Raw AI source selector response without secrets |
| `.\data\L4_sendit\output\text_extraction_context.json` | Selected markdown metadata and content hashes used for text extraction |
| `.\data\L4_sendit\output\extracted_text_facts.json` | Validated Stage 3 text facts with source evidence |
| `.\data\L4_sendit\output\model_text_fact_extraction_raw.json` | Raw AI text fact extractor response without secrets |
| `.\data\L4_sendit\output\extracted_facts.json` | AI/deterministic extracted facts with evidence |
| `.\data\L4_sendit\output\declaration_data.json` | Structured declaration model with evidence and uncertainty |
| `.\data\L4_sendit\output\declaration.txt` | Final declaration string |
| `.\data\L4_sendit\output\verification_payload.json` | Hub payload without exposing secrets |
| `.\data\L4_sendit\output\hub_response.json` | Hub response saved only after explicit `--submit` |
| `.\data\L4_sendit\output\run_report.md` | Human-readable summary of decisions, validations, and risks |

No generated artifact should be written under `.\src\apps\L4_sendit`.

## Run

Stages 1-2 have a runnable implementation. Stage 1 uses AI only for command parsing. Stage 2 uses AI only for source selection from a deterministic local inventory. The app then reuses the deterministic MVP1-compatible pipeline for facts, declaration rendering, local validation, and optional Hub submission.

Run with a real guarded model call:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt
```

Run local validation with saved model-shaped JSON files instead of real API calls:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --mock-model-output-file .\data\L4_sendit\output\model_command_parse_raw.json --mock-source-selection-output-file .\data\L4_sendit\output\model_source_selection_raw.json
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

Current implemented Stage 1-2 files:

| Path | Responsibility |
|---|---|
| `__init__.py` | Define the MVP2 package |
| `config.py` | Load paths, model defaults, and model-call guard values |
| `models.py` | Define parsed command, reference inventory, selected source, and validation structures |
| `command_parser.py` | Run the guarded AI parser or validate a saved model-shaped JSON payload |
| `reference_inventory.py` | Build a deterministic inventory of local SPK reference files |
| `source_selector.py` | Run the guarded AI source selector or validate a saved model-shaped JSON payload |
| `validator.py` | Validate parsed command and selected source outputs before downstream use |
| `report_builder.py` | Render the Stage 1-2 run report |
| `main.py` | Run Stage 1-2 and reuse the deterministic MVP1-compatible declaration pipeline |
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
