# L4 Sendit MVP2

## Table Of Contents

- [Purpose](#purpose)
- [Design Status](#design-status)
- [Runtime Goal](#runtime-goal)
- [Workflow](#workflow)
- [Stage Overview](#stage-overview)
- [Stage 1: Command Understanding](#stage-1-command-understanding)
- [Stage 2: Reference Inventory](#stage-2-reference-inventory)
- [Stage 3: Source Selection](#stage-3-source-selection)
- [Stage 4: Evidence Extraction](#stage-4-evidence-extraction)
- [Stage 5: Task Execution](#stage-5-task-execution)
- [Stage 6: Validation And Rendering](#stage-6-validation-and-rendering)
- [Stage 7: Reporting And Optional Submission](#stage-7-reporting-and-optional-submission)
- [Model Selection Plan](#model-selection-plan)
- [Prompt Plan](#prompt-plan)
- [Structured Output Schemas](#structured-output-schemas)
- [Context And Tool Plan](#context-and-tool-plan)
- [Batching And Caching Plan](#batching-and-caching-plan)
- [LLM Design Reviews](#llm-design-reviews)
- [Configuration](#configuration)
- [Data Locations](#data-locations)
- [Run](#run)
- [Main Modules](#main-modules)
- [Verification](#verification)

## Purpose

`L4_sendit_MVP2` is a command-driven SPK documentation workflow.

The application should read the operational command from `data/L4_sendit/input/command.txt`, determine what task must be completed, select the local documentation needed for that task from `data/L4_sendit/references`, extract evidence, execute the task, and produce validated output artifacts.

The learning goal is to show how an AI-assisted application can separate task understanding, source selection, evidence extraction, reasoning, validation, rendering, and optional external submission. AI may help with language-heavy, ambiguous, or multimodal work. Deterministic code owns file access, path validation, schemas, stable calculations, output writing, and submission guards.

The workflow is designed as a general command-driven application shape, but the currently planned executable task is `spk_transport_declaration`. Supporting additional command types requires explicit executor implementations for those tasks.

The design intentionally does not define a fixed file list for every task. A different design could map each task to a static set of required documents, but this MVP2 assumes a business requirement for dynamic document selection. The app should know what information must be found for a task, while remaining ready for documentation changes where the same information may appear in different attachments over time.

## Design Status

This README describes the intended MVP2 design. In this repository, `MVP2` means the AI-assisted command-driven version of `L4_sendit`. The design must not assume that every command needs WDP, wagon capacity, disabled-route evidence, or a declaration template. Those needs may appear only after the command has been understood and the current task has been identified.

The current design passed `_agent/instructions/llm_design_checklist.md` review on 2026-05-06 for the full MVP2 workflow.

Current implementation status:

- Stage 1 `Command Understanding` is implemented.
- Stage 2 `Reference Inventory` is implemented.
- Stage 3 `Source Selection` is implemented.
- Stage 4 `Evidence Extraction` is implemented.
- Stage 5 `Task Execution` is implemented for the currently supported known task.
- The shipment-category refinement for `spk_transport_declaration` is implemented.
- Later stages remain design-only.

Implemented refinements:

- Shipment category classification for `spk_transport_declaration` should move out of the Stage 5 executor and become an evidence-backed Stage 4 result.
- This refinement passed `_agent/instructions/llm_design_checklist.md` review on 2026-05-07 for the shipment-category flow in Stage 3 through Stage 5.
- This refinement is implemented: Stage 4 now produces `shipment_category`, and Stage 5 consumes that validated fact instead of applying a hard-coded keyword rule.
- A real end-to-end OpenAI run completed successfully after the refinement was implemented.
- Tasks that require interpreting declaration abbreviations or glossary terms should use a terminology-oriented documentation need instead of one hard-coded fact per acronym.
- This refinement passed `_agent/instructions/llm_design_checklist.md` review on 2026-05-07 for terminology evidence in Stage 3 through Stage 5.
- This refinement is implemented: Stage 3 can now select terminology-oriented sources, Stage 4 can now extract generic `resolved_terms` evidence, and Stage 5 can now consume that validated terminology evidence without adding acronym-specific fact names.
- A real end-to-end OpenAI run completed successfully after the terminology refinement was implemented and the remaining Stage 3 and Stage 4 blockers were corrected.

## Runtime Goal

The application should support this general runtime contract:

1. Read `data/L4_sendit/input/command.txt`.
2. Identify the task requested by the command.
3. Build a deterministic inventory of local reference files from `data/L4_sendit/references`.
4. Select documentation relevant to the identified task.
5. Extract task-relevant evidence from selected text and media sources.
6. Execute the requested task using validated command data and validated evidence.
7. Validate the result before rendering or submission.
8. Save inspectable artifacts under `data/L4_sendit/output`.
9. Submit externally only when explicitly requested.

The current implementation scope is narrower than the general contract: MVP2 is planned to understand and route commands in a general way, but it should execute only task types that have an explicit registered executor.

## Workflow

1. Load the command text from `data/L4_sendit/input/command.txt`.
2. Use AI to convert the command into a validated `TaskUnderstanding` object.
3. Build a deterministic inventory of available local SPK references.
4. Use AI to select sources for the identified task from the inventory only.
5. Validate selected source paths, types, and missing-source notes.
6. Extract evidence from selected sources according to the task and source modality.
7. Validate extracted evidence before downstream use.
8. Execute the identified task with a task-specific executor.
9. Validate the task result against the task contract.
10. Render final output files.
11. Write a run report with decisions, evidence, uncertainty, and validation results.
12. Submit to the Hub only when the command-line user passes `--submit`.

## Stage Overview

| Stage | Goal | AI role | Deterministic owner | Output |
|---|---|---|---|---|
| 1. Command Understanding | Determine what task the command requests and extract supplied inputs. | Classify task intent and extract command data into a schema. | Load command, validate schema, reject missing required task identity. | `task_understanding.json` |
| 2. Reference Inventory | Describe available local documentation. | None. | Discover files, detect type, size, path, and safe hints. | `reference_inventory.json` |
| 3. Source Selection | Choose sources needed for the identified task. | Select relevant files from inventory and explain documentation needs. | Validate paths, types, inventory membership, and missing-source handling. | `selected_sources.json` |
| 4. Evidence Extraction | Extract task-relevant facts from selected sources. | Extract text facts and media facts with evidence and uncertainty. | Load only selected files, validate evidence, preserve missing facts. | `evidence_package.json` |
| 5. Task Execution | Produce a task-specific structured result. | Propose interpretations only where rules are ambiguous. | Route to executor, perform stable calculations, keep unsupported claims out. | `task_result.json` |
| 6. Validation And Rendering | Validate and render the final deliverable. | None by default. | Validate result contract, render final text or payload. | `final_output.*` |
| 7. Reporting And Optional Submission | Save audit artifacts and optionally submit. | Summarize uncertainty only if needed. | Write report, mask secrets, submit only with `--submit`. | `run_report.md`, optional Hub artifacts |

## Stage 1: Command Understanding

Stage 1 reads the command and identifies the task before any documentation is selected.

The reason for this stage is architectural: source selection cannot be correct until the app knows what job the command asks it to perform.

### Goal

Produce a structured task description that downstream stages can use without rereading the raw command.

Stage 1 should answer:

```text
What task is requested, what output is expected, and what input data did the command provide?
```

### Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/input/command.txt` | deterministic code | Raw operational command |

### Output Schema

```json
{
  "task_name": "spk_transport_declaration",
  "task_goal": "Prepare a validated SPK transport declaration.",
  "expected_output_kind": "declaration_text",
  "domain": "spk_transport",
  "provided_inputs": {
    "sender_identifier": "450202122",
    "origin_point": "Gdańsk",
    "destination_point": "Żarnowiec",
    "weight_kg": 2800,
    "budget_pp": 0,
    "contents": "kasety z paliwem do reaktora",
    "special_notes": "none"
  },
  "documentation_needs": [
    {
      "need": "declaration format",
      "reason": "The command asks for a declaration text."
    }
  ],
  "success_criteria": [
    "The result must match the requested declaration format."
  ],
  "missing_inputs": [],
  "uncertainty_notes": [],
  "confidence": 0.0
}
```

The example above documents one possible command. It is not a fixed requirement for every command.

### Boundaries

Stage 1 may use AI only for command understanding.

Stage 1 must not:

- choose documentation files,
- extract facts from documentation,
- infer hidden SPK rules,
- calculate route, payment, wagon count, WDP, or other task results,
- render or submit the final output.

### Validation

Deterministic validation must confirm:

- `task_name`, `task_goal`, `expected_output_kind`, and `domain` are present,
- `provided_inputs` is an object,
- `documentation_needs`, `success_criteria`, `missing_inputs`, and `uncertainty_notes` are lists,
- `confidence` is within `0.0` to `1.0`,
- missing required information is reported instead of guessed.

If `task_name` or expected output cannot be identified, the app must stop before source selection.

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/task_understanding.json` | Validated task description |
| `data/L4_sendit/output/model_task_understanding_raw.json` | Raw model response without secrets |

## Stage 2: Reference Inventory

Stage 2 builds a deterministic inventory of local reference files. This stage has no model call.

The reason for this stage is safety: source selection should operate on a known list of local files, not on model-invented paths.

### Goal

Produce a compact inventory that allows Stage 3 to choose files without reading every document in full.

### Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/references` | deterministic code | Local documentation directory |

### Output Schema

```json
{
  "references": [
    {
      "path": "data/L4_sendit/references/index.md",
      "source_type": "markdown",
      "size_bytes": 44928,
      "hint": "main SPK documentation index and broad rules"
    }
  ]
}
```

Hints may describe filenames, attachment labels, source types, and short safe summaries. Hints must not hard-code task-specific requirements such as "must use this for WDP" unless the file itself clearly has that general purpose.

### Validation

Deterministic validation must confirm:

- references directory exists,
- every inventory path is repository-root-relative,
- every path stays under `data/L4_sendit/references`,
- source type is one of `markdown`, `image`, or `other`,
- inventory is non-empty.

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/reference_inventory.json` | Validated local source inventory |

## Stage 3: Source Selection

Stage 3 selects sources for the task identified in Stage 1.

The reason for this stage is contextual: the app should reduce a broad local reference set to a task-relevant package without assuming that all tasks need the same documents.

This design follows `_agent/references/L2_context_routing_and_tool_exposure.md`: expose only the knowledge resources needed for the current request.

### Goal

Use `task_understanding.json` and `reference_inventory.json` to choose local reference files for later extraction.

Stage 3 should answer:

```text
Which local reference files are needed to complete this identified task, and why?
```

### Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/output/task_understanding.json` | Stage 1 | Validated task identity and command data |
| `data/L4_sendit/output/reference_inventory.json` | Stage 2 | Validated local file inventory |

The model should receive the task understanding and compact inventory only. It should not receive full contents of every reference file.

This is a deliberate design choice. The app could be built with a deterministic task-to-files map, but MVP2 assumes that the documentation set may evolve. Stage 3 therefore reasons dynamically over the current inventory: it knows which documentation needs must be covered for the task, but it does not assume in advance which attachment names will satisfy those needs.

For `spk_transport_declaration`, the source-selection design should include documentation that covers shipment classification rules whenever the final declaration requires a shipment category. For the current SPK references, this means the selected package should include the source that defines shipment categories, not only route and capacity sources.

When the identified task requires interpreting abbreviations or glossary terms that appear in the declaration format or downstream task contract, the source-selection design should also include terminology sources. For the current SPK references, `zalacznik-G.md` is the obvious terminology source because it contains abbreviation expansions such as `WDP`.

### Output Schema

```json
{
  "selected_sources": [
    {
      "path": "data/L4_sendit/references/zalacznik-E.md",
      "source_type": "markdown",
      "documentation_need": "declaration format",
      "reason": "The task asks for a declaration text and this file appears to contain the template.",
      "intended_use": "format_reference",
      "confidence": 0.0
    }
  ],
  "rejected_sources": [
    {
      "path": "data/L4_sendit/references/zalacznik-C.md",
      "reason": "The inventory hint does not suggest relevance to the identified task."
    }
  ],
  "missing_sources": [],
  "uncertainty_notes": []
}
```

`documentation_need` must come from Stage 1 needs or map a Stage 1 need to a concrete source. Stage 3 must not expand the task scope. It may add a technical documentation need only when that need is required to complete the already identified task; uncertain needs must be preserved in `uncertainty_notes` or `missing_sources`.

### Boundaries

Stage 3 may use AI only to choose from the inventory.

Stage 3 must not:

- invent paths,
- use absolute paths, URLs, or parent traversal,
- extract facts from selected documents,
- decide final route, category, payment, wagon count, WDP, or declaration text,
- write outside `data/L4_sendit/output`,
- submit anything externally.

### Validation

Deterministic validation must confirm:

- `selected_sources` is non-empty unless `missing_sources` explains why the task cannot proceed,
- every selected and rejected path exactly matches an inventory path,
- selected `source_type` matches inventory source type,
- `documentation_need`, `reason`, and `intended_use` are present,
- missing source needs are preserved,
- uncertainty is preserved,
- no downstream facts or final answers are smuggled into the response.

The validator must not require a hard-coded source category such as `WDP meaning`. If WDP is needed for a specific command, that need must originate from task understanding, source selection reasoning, or later evidence requirements for that command.

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/selected_sources.json` | Validated task-specific source selection |
| `data/L4_sendit/output/model_source_selection_raw.json` | Raw model response without secrets |

## Stage 4: Evidence Extraction

Stage 4 extracts evidence from selected sources according to the identified task.

The reason for this stage is traceability: later task execution should use facts with source references and uncertainty, not unsupported model memory.

This design follows `_agent/references/L1_structured_outputs_and_validation.md`: model output is untrusted until schema and evidence validation pass.

### Goal

Create a validated evidence package that contains only facts supported by selected local sources.

Stage 4 should answer:

```text
What task-relevant facts are explicitly supported by the selected sources?
```

### Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/output/task_understanding.json` | Stage 1 | Defines the current task and known inputs |
| `data/L4_sendit/output/selected_sources.json` | Stage 3 | Defines allowed sources |
| selected local source files | deterministic code | Load only selected files |

### Output Schema

```json
{
  "facts": [
    {
      "name": "declaration_template_fields",
      "value": ["sender", "route", "category"],
      "source_path": "data/L4_sendit/references/zalacznik-E.md",
      "source_type": "markdown",
      "evidence_kind": "text_quote",
      "evidence_note": "The source lists required declaration fields.",
      "evidence_quote": "Short exact excerpt from the source.",
      "evidence_locator": null,
      "confidence": 0.0,
      "uncertainty_notes": []
    }
  ],
  "missing_facts": [],
  "conflicts": [],
  "source_coverage": [
    {
      "path": "data/L4_sendit/references/zalacznik-E.md",
      "used": true,
      "notes": "Provided declaration format evidence."
    }
  ]
}
```

Fact names should be derived from the task requirements and selected documentation needs. They must not be a fixed global list for every command.

`evidence_kind` must be one of:

- `text_quote` for evidence quoted from markdown text,
- `image_region` for evidence tied to a visible image/table area,
- `image_description` for visual evidence that can be described but not quoted exactly.

`evidence_quote` is required for markdown facts and optional for image facts. `evidence_locator` is optional for markdown facts and should be used for image facts when a row, column, region, or visible table entry can be identified.

For `spk_transport_declaration`, Stage 4 should produce an evidence-backed shipment classification fact when the declaration requires a category. The intended Stage 4 fact set for this task therefore includes:

- `shipment_category` as the proposed category symbol such as `A`
- category evidence from the classification rules source
- confidence and uncertainty notes when the mapping from shipment contents to category is interpretive rather than explicit

For tasks that require interpreting declaration abbreviations or glossary terms, Stage 4 should also produce terminology evidence in a reusable task-scoped form. This refinement is intentionally broader than `WDP` alone: the app should resolve only the abbreviations relevant to the current task, not assume that every command needs every glossary entry.

The implemented Stage 4 representation for this terminology evidence is a fact such as:

- `resolved_terms` with `value` as a list of strings formatted like `TERM = expansion`

For the current SPK references, one possible entry would be:

- `WDP = Wagony Dodatkowe Płatne (dołączane do standardowego składu)`

This keeps the schema generic enough to support future task-relevant abbreviations without introducing one hard-coded fact name per acronym.

This refinement follows `_agent/references/L1_task_decomposition_and_pipeline_design.md` and `_agent/references/L1_structured_outputs_and_validation.md`: the interpretation step belongs in the evidence-producing stage, and downstream code should consume only validated structured output.

### Boundaries

Stage 4 may use AI for:

- extracting facts from selected markdown text,
- extracting visible information from selected images,
- reporting uncertainty and conflicts.

Stage 4 must not:

- load unselected sources,
- select new sources,
- execute the final task,
- make unsupported domain decisions,
- render or submit the final output.

### Validation

Deterministic validation must confirm:

- every fact source path was selected in Stage 3,
- source type matches the selected source,
- markdown evidence quotes are present in the loaded text,
- image evidence includes enough location or description to inspect the claim,
- conflicts are preserved,
- required task evidence is present or listed in `missing_facts`,
- the app stops when missing evidence blocks safe execution.

For `spk_transport_declaration`, this means shipment category evidence must be present or explicitly reported missing before Stage 5 may build the declaration result.

For a task that depends on output terminology, this also means the required terminology evidence must be present or explicitly reported missing before Stage 5 may rely on the meaning of the corresponding output field.

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/evidence_package.json` | Validated facts with source evidence |
| `data/L4_sendit/output/model_evidence_extraction_raw.json` | Raw model response without secrets |
| `data/L4_sendit/output/evidence_context.json` | Selected source metadata, content hashes, and extraction scope |

## Stage 5: Task Execution

Stage 5 executes the identified task using validated command data and validated evidence.

The reason for this stage is separation of responsibility: source reading and evidence extraction should finish before the app decides the final answer.

This design follows `_agent/references/L1_task_decomposition_and_pipeline_design.md`: keep dependencies between steps explicit and validate model outputs before downstream use.

### Goal

Produce a structured task result that can be validated and rendered.

For the known `spk_transport_declaration` task, this stage may build declaration data. For another command, this stage should route to the executor that matches the identified task.

In the current planned scope, `spk_transport_declaration` is the concrete supported task. Additional command types require their own executor implementations before the app may execute them.

For the implemented declaration design, Stage 5 does not classify the shipment with a hard-coded keyword rule inside the executor. Instead, it reads a validated Stage 4 fact such as `shipment_category` and fails closed when that fact is missing or too uncertain for safe execution.

### Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/output/task_understanding.json` | Stage 1 | Task identity and command inputs |
| `data/L4_sendit/output/evidence_package.json` | Stage 4 | Validated source-backed facts |

### Output Schema

```json
{
  "task_name": "spk_transport_declaration",
  "result_kind": "declaration_data",
  "result": {
    "sender_identifier": "450202122",
    "origin_point": "Gdańsk",
    "destination_point": "Żarnowiec",
    "route_code": "X-01",
    "category": "A",
    "contents": "kasety z paliwem do reaktora",
    "declared_weight_kg": 2800,
    "wdp": 4,
    "special_notes": "brak",
    "amount_due_pp": 0
  },
  "evidence_links": [
    {
      "result_field": "route_code",
      "fact_name": "route_code_rule"
    }
  ],
  "uncertainty_notes": []
}
```

The example above is task-specific. Fields such as `wdp` may appear for a transport declaration only when the task and evidence require them.

### Boundaries

Stage 5 may use AI only for interpretation when validated evidence leaves more than one plausible answer.

Stage 5 should keep deterministic code responsible for:

- routing by `task_name`,
- selecting a registered executor for the task,
- stable arithmetic,
- schema conversion,
- required field checks,
- applying explicit validation rules,
- refusing unsupported outputs.

Shipment category assignment for `spk_transport_declaration` does not live in Stage 5 hard-coded keyword-matching code. Category interpretation now belongs to Stage 4 as a validated evidence-backed fact, with Stage 5 limited to consuming that fact.

Likewise, Stage 5 should not infer declaration terminology from local assumptions when that terminology is relevant to the task contract. If a field meaning depends on glossary evidence, Stage 5 should consume the validated terminology evidence produced earlier in the workflow.

For the current SPK declaration task, this means the executor continues to calculate the numeric `wdp` value deterministically and now links that result field to both wagon-capacity evidence and terminology evidence such as `resolved_terms` when the declaration output uses the abbreviation.

Stage 5 must not:

- read new documentation directly,
- rely on raw unvalidated model responses,
- invent evidence for missing facts,
- submit externally.

### Validation

Deterministic validation must confirm:

- `task_name` matches Stage 1,
- `task_name` maps to a registered executor before task execution begins,
- the selected executor declares the supported `result_kind`,
- the produced `result_kind` is supported by the selected executor,
- required result fields are present for that task,
- result fields have evidence links when evidence is required,
- stable calculations are reproducible in code,
- uncertainty is preserved.

For `spk_transport_declaration`, the validator should treat shipment category as an evidence-required field rather than a locally hard-coded executor detail.

For terminology-dependent fields, the validator should also treat the corresponding terminology evidence as part of the task evidence contract rather than as an implicit assumption inside the executor.

For the implemented terminology refinement, this means deterministic validation should confirm that:

- `resolved_terms` is present or explicitly reported missing when terminology evidence is required for the task,
- each retained terminology entry follows the `TERM = expansion` shape,
- the executor does not rely on undeclared abbreviation meaning when the task contract depends on that meaning.

If no executor is registered for the identified `task_name`, the app must fail with a clear unsupported-task error before task execution. The model must not invent a fallback executor, unsupported result shape, or synthetic final answer for an unsupported task.

<p style="color: #b45309;"><strong>Design note.</strong> The app could be designed so a general LLM tries to handle unsupported commands without a registered executor. This workflow intentionally does not do that, because it would give the model too much freedom, make validation weaker, and move too much execution responsibility from deterministic code to a probabilistic component. Please note that in a production setting, an unsupported command should not only fail fast. It should also be routed to a human operator for review and handling. That human handoff is not part of the current MVP2 scope, but it is the recommended business-oriented design for unsupported task types.</p>

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/task_result.json` | Validated structured result before rendering |
| `data/L4_sendit/output/model_task_execution_raw.json` | Raw model response when Stage 5 uses AI |

## Stage 6: Validation And Rendering

Stage 6 validates and renders the final deliverable.

The reason for this stage is reliability: the final output should be generated from a validated task result, not free-form model text.

### Goal

Create the final output requested by the command.

### Inputs

| Input | Owner | Notes |
|---|---|---|
| `data/L4_sendit/output/task_understanding.json` | Stage 1 | Expected output kind and success criteria |
| `data/L4_sendit/output/task_result.json` | Stage 5 | Validated structured task result |
| `data/L4_sendit/output/evidence_package.json` | Stage 4 | Evidence needed for format-sensitive rendering |

### Rendering Rules

For text outputs, deterministic code should render from a schema and template. For JSON outputs, deterministic code should serialize a validated model. For unsupported output kinds, the app should fail with a clear message.

For `spk_transport_declaration`, declaration text should be rendered from validated declaration data and the selected declaration format evidence.

### Validation

Deterministic validation must confirm:

- final output kind matches Stage 1,
- all required task-specific fields are present,
- formatting rules are satisfied,
- no raw secrets are included,
- output can be inspected before optional submission.

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/final_output.txt` | Final rendered text when the task produces text |
| `data/L4_sendit/output/final_output.json` | Final rendered JSON when the task produces JSON |
| `data/L4_sendit/output/declaration.txt` | Compatibility output for SPK declaration tasks |

## Stage 7: Reporting And Optional Submission

Stage 7 writes the run report and optionally submits the result.

The reason for this stage is operational safety: reporting and submission should be separated from reasoning and rendering.

### Goal

Save an audit trail and submit only when explicitly requested.

### Inputs

| Input | Owner | Notes |
|---|---|---|
| all validated stage artifacts | deterministic code | Used for reporting |
| `--submit` flag | user | Required for external submission |

### Rules

- The app must write a report for every run.
- Submission must be disabled by default.
- Submission must require `--submit`.
- API keys, tokens, private URLs, and credentials must never be written to source files, docs, committed artifacts, or reports.
- Payload artifacts must mask or omit secrets.

### Artifacts

| Path | Purpose |
|---|---|
| `data/L4_sendit/output/run_report.md` | Human-readable execution summary |
| `data/L4_sendit/output/verification_payload.json` | Optional masked submission payload |
| `data/L4_sendit/output/hub_response.json` | Optional response saved after explicit submission |

## Model Selection Plan

MVP2 should use the smallest capable model for each AI-assisted step. Model names are application settings in `config.py`, not secrets.

| Step | Planned model class | Config default | Concrete model | Reason | Validation strength |
|---|---|---|---|---|---|
| Command Understanding | lightweight text model | `DEFAULT_COMMAND_PARSE_MODEL` | `gpt-5.4-mini` | One command, structured task extraction, strongly validated. | high |
| Source Selection | lightweight text model | `DEFAULT_SOURCE_SELECTION_MODEL` | `gpt-5.4-mini` | Selects from compact local inventory only. | high |
| Text Evidence Extraction | lightweight text model | `DEFAULT_TEXT_EXTRACTION_MODEL` | `gpt-5.4-mini` | Reads selected markdown and returns evidence-backed facts. | medium-high |
| Vision Evidence Extraction | vision-capable model | `DEFAULT_VISION_EXTRACTION_MODEL` | `gpt-5.4-mini` | Reads selected image/table sources and returns inspectable visual evidence. | medium |
| Task Execution | mid-strength text model only when interpretation is needed | `DEFAULT_REASONING_MODEL` | `gpt-5.5` | May resolve ambiguity from validated evidence; deterministic code handles stable logic. | medium |

No model is needed for Reference Inventory, Validation And Rendering, or default Reporting And Optional Submission.

These concrete model values are part of the design. The matching `config.py` constants should use these defaults unless a later design review changes the model plan.

## Prompt Plan

Each prompt should be scoped to one stage:

```text
Task:
Context:
Constraints:
Output format:
```

Prompts must not include full conversation history, secrets, Hub credentials, raw `.env` values, unselected documents, or unrelated artifacts.

| Step | Prompt type | Required context | Hard constraints | Output format |
|---|---|---|---|---|
| Command Understanding | classification and extraction | raw command text only | identify task before source selection, do not infer documentation facts | task understanding schema |
| Source Selection | source ranking | task understanding plus reference inventory | choose only inventory paths, do not extract facts | selected sources schema |
| Evidence Extraction | extraction | task understanding plus selected source contents | use only selected files, include evidence, report missing facts | evidence package schema |
| Task Execution | synthesis | task understanding plus validated evidence | do not invent evidence, keep stable calculations in code | task result schema |

## Structured Output Schemas

All model outputs consumed by code must be validated before downstream use.

| Schema | Stage | Purpose |
|---|---|---|
| `TaskUnderstanding` | Stage 1 | Identify task, expected output, supplied inputs, documentation needs, success criteria, uncertainty |
| `ReferenceInventory` | Stage 2 | Deterministic list of available local files |
| `SelectedSources` | Stage 3 | Task-specific local documentation selection |
| `EvidencePackage` | Stage 4 | Source-backed facts, missing facts, conflicts, coverage |
| `TaskResult` | Stage 5 | Structured result ready for validation and rendering |

Validation should fail closed. A warning-only validation failure is not acceptable when downstream execution depends on the data.

## Context And Tool Plan

MVP2 should pass only the context needed by the current step.

| Step | Context allowed | Context excluded |
|---|---|---|
| Command Understanding | raw command text | SPK references, previous run reports, Hub data |
| Source Selection | task understanding, compact inventory | full reference contents, unlisted files |
| Evidence Extraction | selected source contents, task understanding | unselected files, full reference corpus |
| Task Execution | task understanding, validated evidence | raw model responses, unvalidated facts |
| Rendering | validated task result | model tools, raw source corpus |
| Submission | final output and masked config names | API keys, raw credentials |

The model should not receive filesystem write tools, Hub submission tools, API keys, private endpoint values, or authorization decisions.

## Batching And Caching Plan

MVP2 should avoid repeated model calls when a result can be reused safely.

| Step | Batching/caching rule | Freshness rule |
|---|---|---|
| Command Understanding | cache by command file content hash | invalidate when `command.txt` changes |
| Reference Inventory | cache by references directory listing and file metadata | invalidate when reference files change |
| Source Selection | cache by task understanding hash plus inventory hash | invalidate when task or inventory changes |
| Evidence Extraction | cache by selected source content hash plus task understanding hash | invalidate when selected files or task change |
| Task Execution | cache by task understanding hash plus evidence package hash | invalidate when task or evidence changes |

Every cached artifact must still pass deterministic validation before reuse.

## LLM Design Reviews

The table below records passed reviews only.

| Date | Scope | Checklist | Result | Approved Implementation Boundary |
|---|---|---|---|---|
| 2026-05-06 | MVP2 full workflow | `_agent/instructions/llm_design_checklist.md` | PASS | Implement the full MVP2 workflow described in this README; material LLM design changes require a new review. |
| 2026-05-07 | Shipment category refinement for `spk_transport_declaration` in Stage 3 through Stage 5 | `_agent/instructions/llm_design_checklist.md` | PASS | Implement only the shipment-category refinement described in this README: include classification-rule source selection, Stage 4 evidence-backed `shipment_category`, and Stage 5 consumption of validated category evidence. |
| 2026-05-07 | Terminology evidence refinement for declaration abbreviations in Stage 3 through Stage 5 | `_agent/instructions/llm_design_checklist.md` | PASS | Implement only the terminology-evidence refinement described in this README: allow terminology-oriented source selection, extract generic `resolved_terms` evidence, and let Stage 5 consume that evidence without hard-coding acronym-specific facts. |

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

All runtime files should live under `data/L4_sendit`.

| Path | Purpose |
|---|---|
| `data/L4_sendit/input/command.txt` | Operational command received by the app |
| `data/L4_sendit/references/*` | Local SPK documentation and attachments |
| `data/L4_sendit/output/task_understanding.json` | Validated Stage 1 task understanding |
| `data/L4_sendit/output/model_task_understanding_raw.json` | Raw Stage 1 model response without secrets |
| `data/L4_sendit/output/reference_inventory.json` | Deterministic local reference inventory |
| `data/L4_sendit/output/selected_sources.json` | Validated task-specific source selection |
| `data/L4_sendit/output/model_source_selection_raw.json` | Raw Stage 3 model response without secrets |
| `data/L4_sendit/output/evidence_context.json` | Evidence extraction scope and content hashes |
| `data/L4_sendit/output/evidence_package.json` | Validated source-backed evidence |
| `data/L4_sendit/output/model_evidence_extraction_raw.json` | Raw Stage 4 model response without secrets |
| `data/L4_sendit/output/task_result.json` | Validated task-specific structured result |
| `data/L4_sendit/output/model_task_execution_raw.json` | Raw Stage 5 model response when used |
| `data/L4_sendit/output/final_output.txt` | Final rendered text output, created only for text output tasks |
| `data/L4_sendit/output/final_output.json` | Final rendered JSON output, created only for JSON output tasks |
| `data/L4_sendit/output/declaration.txt` | Compatibility output for SPK declaration tasks |
| `data/L4_sendit/output/verification_payload.json` | Optional masked submission payload |
| `data/L4_sendit/output/hub_response.json` | Optional response saved after explicit `--submit` |
| `data/L4_sendit/output/run_report.md` | Human-readable summary of decisions, validations, and risks |

No generated artifact should be written under `src/apps/L4_sendit`.

## Run

The approved design is partially implemented. The current runnable interface covers Stage 1 through Stage 5.

Run with real guarded model calls:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt
```

Run with a mock Stage 1 response:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --mock-model-output-file .\data\L4_sendit\output\stage1_mock_task_understanding.json
```

Run with a mock Stage 3 response:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --mock-source-selection-output-file .\data\L4_sendit\output\stage3_mock_selected_sources.json
```

Run with a mock Stage 4 response:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --mock-evidence-output-file .\data\L4_sendit\output\stage4_mock_evidence_package.json
```

## Main Modules

Planned module responsibilities:

| Module | Responsibility |
|---|---|
| `config.py` | Resolve paths, model settings, guards, and secret-backed runtime configuration |
| `models.py` | Define task understanding, inventory, selection, evidence, task result, and validation structures |
| `task_understanding.py` | Implement Stage 1 command understanding |
| `reference_inventory.py` | Implement Stage 2 deterministic reference inventory |
| `source_selector.py` | Implement Stage 3 task-specific source selection |
| `fact_extractor.py` | Implement Stage 4 text and media evidence extraction |
| `task_executor.py` | Route Stage 5 execution by task name |
| `declaration_builder.py` | Implement the executor or executor helper for `spk_transport_declaration` |
| `validator.py` | Validate every stage boundary before downstream use |
| `report_builder.py` | Write run reports and uncertainty summaries |
| `main.py` | Orchestrate stages and optional submission |

## Verification

With the current implementation, the simplest verification is:

1. Run the app against `data/L4_sendit/input/command.txt` without `--submit`.
2. Confirm `task_understanding.json` identifies the requested task.
3. Confirm `selected_sources.json` contains only local inventory paths and no fixed global requirements.
4. Confirm `evidence_package.json` contains facts only from selected sources and preserves missing facts instead of guessing.
5. For the implemented shipment-category refinement, confirm `evidence_package.json` contains a validated `shipment_category` fact or explicitly reports why category evidence is missing.
6. Confirm `task_result.json` is produced only by the registered executor for the supported task and keeps interpretation risk in `uncertainty_notes`.
7. For the implemented shipment-category refinement, confirm the Stage 5 executor consumes validated category evidence instead of classifying the shipment with a hard-coded keyword rule.
8. Confirm `run_report.md` explains task identity, selected sources, extracted evidence, task result, uncertainty, and validation results.
9. Confirm unsupported `task_name` values fail before downstream execution with a clear task-registry error.
10. For the implemented terminology refinement, confirm terminology-dependent fields can be linked to a generic `resolved_terms` evidence fact instead of a one-off acronym-specific fact name.

The current repository state includes a successful real-model run for the supported task:

- `evidence_package.json` includes validated `shipment_category` and `system_funded_categories` evidence
- `task_result.json` links `category` to `shipment_category`
- `run_report.md` records a complete Stage 1-5 audit trail

The current repository state also includes a successful real-model verification of the terminology refinement:

- Stage 3 can select a source with `documentation_need` equal to `declaration terminology`
- Stage 4 can validate a generic `resolved_terms` fact shaped as `TERM = expansion`
- `task_result.json` can link `wdp` to both wagon-capacity facts and `resolved_terms`
- `run_report.md` confirms that the real OpenAI-powered run passed Stage 3, Stage 4, and Stage 5 validation with terminology evidence enabled

For later stages, keep the design sections in this README as the source of truth until implementation is added.
