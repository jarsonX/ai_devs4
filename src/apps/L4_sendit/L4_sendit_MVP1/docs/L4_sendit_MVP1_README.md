# L4 Sendit MVP1

## Purpose

`L4_sendit_MVP1` is a learning version of the SPK declaration app. It is intentionally simple, explicit, and deterministic.

The goal is not to build a production document-understanding system. The goal is to understand the shape of the pipeline before adding AI in MVP2.

## Learning Rationale

MVP1 should be more educational than clever. If a value can be written down explicitly for the first version, write it down explicitly and make the data flow visible.

| Principle | MVP1 meaning |
|---|---|
| Boring first | Prefer direct code over abstractions until the workflow is clear. |
| No AI yet | Do not use agents, model calls, OCR, or vision in MVP1. |
| Visible state | Save intermediate files so a beginner can inspect each step. |
| Manual facts allowed | Use manually confirmed facts, such as route `X-01` from `trasy-wylaczone.png`. |
| Validate before submit | Run local checks before any Hub request. |

## Closed Route Rule

The closed route status must not be ignored. It is part of the reasoning.

For this task, `trasy-wylaczone.png` identifies `Gdańsk - Żarnowiec` as disabled route `X-01`, and `index.md` says disabled routes around Żarnowiec may be used only for category `A` or `B` shipments. This is the reason MVP1 should choose category `A` for reactor fuel cassettes instead of treating the closed route as irrelevant.

Do not render this as a special note in the declaration. The exercise explicitly asks for no special notes.

## Learning Stages

MVP1 should be built in four small stages:

| Stage | Goal | Output |
|---|---|---|
| 1. Static MVP | Load known input and render a first `declaration.txt` with explicit facts. | `declaration.txt` |
| 2. Transparent Pipeline | Save what each step produced. | `parsed_command.json`, `extracted_facts.json`, `declaration_data.json`, `run_report.md` |
| 3. Local Validation | Check required fields, calculations, Polish declaration values, and template formatting. | validation section in `run_report.md` |
| 4. AI Boundary | Mark which parts will later move to MVP2 AI components. | documented TODOs, not model calls |

## Workflow

1. Load the operational command from `.\data\L4_sendit\input\command.txt`.
2. Parse required shipment fields with simple, readable rules.
3. Load known local references from `.\data\L4_sendit\references`.
4. Load the declaration template from `zalacznik-E.md`.
5. Use manually confirmed task facts, including route `X-01`.
6. Calculate additional wagons with plain Python arithmetic.
7. Build `declaration_data.json`.
8. Render `declaration.txt`.
9. Validate the result locally.
10. Save `run_report.md` explaining decisions and uncertainty.
11. Submit to the Hub only when explicitly requested with `--submit`.

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

## What MVP1 Is Not

| Not in MVP1 | Reason |
|---|---|
| AI command parsing | We first want to see the parser shape and expected JSON. |
| Vision/OCR for `trasy-wylaczone.png` | Route `X-01` can be manually confirmed for the learning version. |
| Dynamic source selection | Relevant files are known and can be listed explicitly. |
| Production-grade abstractions | They would hide the beginner-level learning path. |
| Automatic retry after Hub errors | First learn how to inspect and fix one run manually. |

## Declaration Language

The generated SPK declaration must be written in Polish because the SPK documentation, declaration template, route names, and declared contents use Polish.

Technical code, module names, comments, and documentation stay in English, but values rendered into the declaration should preserve Polish wording such as `Gdańsk`, `Żarnowiec`, and `kasety z paliwem do reaktora`.

## Current Facts

MVP1 may use these facts explicitly. They should still be saved with evidence in `extracted_facts.json` or `declaration_data.json`.

| Fact | Value | Evidence |
|---|---|---|
| Declaration template | Available | `zalacznik-E.md` |
| Route code | `X-01` | manually confirmed from `trasy-wylaczone.png` |
| Route status | disabled | `trasy-wylaczone.png` |
| Disabled-route exception | category `A` or `B` | `index.md`, Żarnowiec directive section |
| System-funded categories | `A` and `B` | `index.md`, fees section |
| Standard train capacity | `1000 kg` | `dodatkowe-wagony.md` |
| Additional wagon capacity | `500 kg` per wagon | `dodatkowe-wagony.md` |
| `WDP` meaning | paid additional wagons | `zalacznik-G.md` |

Known derived values for the current command:

| Field | Value | Reason |
|---|---|---|
| Route | `X-01` | Direct disabled route from `Gdańsk` to `Żarnowiec` |
| Category | likely `A` | Reactor fuel cassettes fit strategic transport, and disabled Żarnowiec routes require category `A` or `B` |
| Amount due | likely `0 PP` | Category `A` shipments are covered by the System |
| Physical additional wagons | `4` | `2800 kg - 1000 kg = 1800 kg`; `ceil(1800 / 500) = 4` |

The main interpretation risk is `WDP`. MVP1 should keep this visible in `declaration_data.json` and `run_report.md`.

## Explain Mode

MVP1 should generate a readable `run_report.md` that explains the run.

Recommended report sections:

| Section | Purpose |
|---|---|
| `Parsed Command` | Show the shipment data read from the command. |
| `Loaded References` | Show which local documents were used. |
| `Derived Facts` | Show route, category, amount, and wagon decisions with evidence. |
| `Validation` | Show `OK`, `WARNING`, or `ERROR` checks before Hub submission. |
| `Uncertainty` | Explain the `WDP` ambiguity and chosen value. |
| `Closed Route Reasoning` | Explain that route `X-01` is disabled and therefore category `A` is intentional. |

Example validation lines:

```text
OK: command has required fields
OK: route code found
OK: closed route status handled by category A
OK: declaration template loaded
OK: no special notes rendered
WARNING: WDP interpretation is uncertain
```

## Configuration

Required configuration for optional Hub submission:

```text
AI_DEVS_API_KEY
HUB_VERIFY_URL
```

MVP1 must not require `OPENAI_API_KEY`.

Do not store real API keys, tokens, private URLs, or credentials in source files, docs, logs, or committed output.

## Data Locations

All runtime files should live under the repository-level `.\data\L4_sendit` directory.

| Path | Purpose |
|---|---|
| `.\data\L4_sendit\input\command.txt` | Operational command received by the app |
| `.\data\L4_sendit\references\index.md` | Main local SPK documentation entry point |
| `.\data\L4_sendit\references\*` | Local SPK attachments and supporting reference files |
| `.\data\L4_sendit\output\parsed_command.json` | Parsed command data |
| `.\data\L4_sendit\output\extracted_facts.json` | Known facts used by MVP1 |
| `.\data\L4_sendit\output\declaration_data.json` | Structured declaration model with evidence and uncertainty |
| `.\data\L4_sendit\output\declaration.txt` | Final declaration string |
| `.\data\L4_sendit\output\verification_payload.json` | Hub payload without exposing secrets |
| `.\data\L4_sendit\output\run_report.md` | Human-readable explanation of the run |

No generated artifact should be written under `.\src\apps\L4_sendit`.

## Run

No runnable implementation exists yet.

Planned command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP1.main --command-file .\data\L4_sendit\input\command.txt
```

Planned optional submission:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit.L4_sendit_MVP1.main --command-file .\data\L4_sendit\input\command.txt --submit
```

## Main Modules

Each module should do one small thing.

| Path | Responsibility |
|---|---|
| `config.py` | Load environment configuration and runtime paths. |
| `models.py` | Define simple data structures for command, facts, declaration, and validation. |
| `command_parser.py` | Convert `command.txt` into `parsed_command.json`. |
| `reference_loader.py` | Read known local reference files. |
| `fact_extractor.py` | Return explicit MVP1 facts with evidence. |
| `declaration_builder.py` | Render `declaration.txt` from declaration data. |
| `validator.py` | Produce local validation results. |
| `output.py` | Save JSON, declaration text, payload, and report files. |
| `hub_client.py` | Submit the final payload only when `--submit` is used. |

Current files:

| Path | Responsibility |
|---|---|
| `docs/L4_exercise.md` | Original course brief used only as developer learning context |
| `docs/L4_sendit_MVP1_README.md` | MVP1 learning design and implementation notes |

## Verification

Local verification should run before any Hub submission:

1. Confirm that the command contains all required shipment fields.
2. Confirm that Polish declaration values remain in Polish.
3. Confirm that the declaration template matches `zalacznik-E.md`.
4. Confirm that route `X-01` is used for `Gdańsk` to `Żarnowiec`.
5. Confirm that disabled route status is handled by selecting an allowed category.
6. Confirm that the selected category supports the route and `0 PP` amount.
7. Confirm that additional wagon calculation is sufficient for `2800 kg`.
8. Confirm that no special notes are rendered.
9. Confirm that final declaration field order and separators match the template.
10. Confirm that `run_report.md` explains decisions, closed-route reasoning, and uncertainty.

Hub verification should be explicit and guarded by `--submit`.
