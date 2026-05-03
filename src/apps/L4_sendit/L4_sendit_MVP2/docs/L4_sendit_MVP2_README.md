# L4 Sendit MVP2

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

Required configuration:

```text
AI_DEVS_API_KEY
HUB_VERIFY_URL
OPENAI_API_KEY
OPENAI_MODEL
```

Model-call limits should be explicit and small during development, for example:

```text
L4_SENDIT_MAX_MODEL_REQUESTS
```

Do not store real API keys, tokens, private URLs, or credentials in source files, docs, logs, or committed output.

## Data Locations

All runtime files should live under the repository-level `.\data\L4_sendit` directory.

| Path | Purpose |
|---|---|
| `.\data\L4_sendit\input\command.txt` | Operational command received by the app |
| `.\data\L4_sendit\references\index.md` | Main local SPK documentation entry point |
| `.\data\L4_sendit\references\*` | Local SPK attachments and supporting reference files |
| `.\data\L4_sendit\output\parsed_command.json` | Parsed command data |
| `.\data\L4_sendit\output\extracted_facts.json` | AI/deterministic extracted facts with evidence |
| `.\data\L4_sendit\output\declaration_data.json` | Structured declaration model with evidence and uncertainty |
| `.\data\L4_sendit\output\declaration.txt` | Final declaration string |
| `.\data\L4_sendit\output\verification_payload.json` | Hub payload without exposing secrets |
| `.\data\L4_sendit\output\run_report.md` | Human-readable summary of decisions, validations, and risks |

No generated artifact should be written under `.\src\apps\L4_sendit`.

## Run

No runnable implementation exists yet.

Planned command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt
```

Planned optional submission:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP2.main --command-file .\data\L4_sendit\input\command.txt --submit
```

The `--submit` flag should be the only path that sends a real request to the Hub.

## Main Modules

Planned modules:

| Path | Responsibility |
|---|---|
| `config.py` | Load environment configuration, runtime paths, and model-call limits |
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

Current files:

| Path | Responsibility |
|---|---|
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
