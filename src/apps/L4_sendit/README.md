# L4 Sendit

## Purpose

`L4_sendit` is a learning exercise for preparing a correctly formatted transport declaration for the fictional System Przesylek Konduktorskich (SPK). The goal is to read fragmented local documentation, extract the operational rules, and build the exact declaration string expected by the Hub task `sendit`.

The exercise focuses on careful document reading, cross-referencing included files, interpreting tabular data, and preserving strict output formatting.

## Workflow

1. Read the exercise brief in `docs/L4_exercise.md`.
2. Start from `data/L4_sendit/references/index.md`.
3. Follow the `include file="..."` references to the relevant attachments.
4. Extract the declaration format from `zalacznik-E.md`.
5. Determine the route code for `Gdansk` to `Zarnowiec`.
6. Determine the valid package category and payment amount.
7. Calculate the required additional wagon count for the declared weight.
8. Submit the final declaration as `answer.declaration` to the Hub `/verify` endpoint for task `sendit`.

## Configuration

The Hub request requires an API key. Do not store the key in source code or documentation.

Expected configuration name:

```text
AI_DEVS_API_KEY
```

The target endpoint should also be treated as configuration in application code:

```text
HUB_VERIFY_URL
```

## Current Findings

The local references currently provide most of the data needed to prepare the declaration:

- `zalacznik-E.md` defines the exact declaration template.
- `trasy-wylaczone.png` identifies the route `Gdansk - Zarnowiec` as `X-01`.
- `zalacznik-F.md` confirms the disabled direct route between `Gdansk` and `Zarnowiec`.
- `dodatkowe-wagony.md` defines the standard train capacity and additional wagon rules.
- `zalacznik-G.md` defines `WDP` as `Wagony Dodatkowe Platne`.
- `index.md` states that disabled routes to `Zarnowiec` may be used for category `A` and `B` shipments.

One referenced file, `zalacznik-A.md`, is not present locally. It does not appear to block this exercise because the required route code is available in `trasy-wylaczone.png`.

## Declaration Inputs

Known exercise inputs:

| Field | Value |
|---|---|
| Sender identifier | `450202122` |
| Origin point | `Gdansk` |
| Destination point | `Zarnowiec` |
| Weight | `2800 kg` |
| Budget | `0 PP` |
| Contents | `kasety z paliwem do reaktora` |
| Special notes | none |

Important derived values:

| Field | Value | Reason |
|---|---|---|
| Route | `X-01` | Listed in `trasy-wylaczone.png` as `Gdansk - Zarnowiec` |
| Category | likely `A` | Strategic shipments are System-funded and may use disabled Zarnowiec routes |
| Amount due | likely `0 PP` | Category `A` shipments are covered by the System |
| Additional wagons | likely `4` | `2800 kg - 1000 kg = 1800 kg`; each additional wagon carries `500 kg` |

The main remaining interpretation risk is the `WDP` field. It may mean the physical number of additional wagons (`4`) or only paid additional wagons (`0`) because category `A` shipments are exempt from additional wagon fees.

## Run

No runnable application code exists yet in this directory.

When an implementation is added, it should use the project virtual environment:

```powershell
.\venv\Scripts\python.exe -m src.apps.L4_sendit
```

The exact command may change once the app structure is created.

## Main Modules

Current files:

| Path | Responsibility |
|---|---|
| `docs/L4_exercise.md` | Original exercise brief |
| `README.md` | Current app-level summary and working interpretation |

Relevant reference files outside the app directory:

| Path | Responsibility |
|---|---|
| `data/L4_sendit/references/index.md` | Main SPK documentation and attachment index |
| `data/L4_sendit/references/zalacznik-E.md` | Declaration template |
| `data/L4_sendit/references/trasy-wylaczone.png` | Disabled routes table with route codes |
| `data/L4_sendit/references/dodatkowe-wagony.md` | Additional wagon rules |
| `data/L4_sendit/references/zalacznik-F.md` | Simplified network map |
| `data/L4_sendit/references/zalacznik-G.md` | Abbreviation glossary |

## Verification

For now, verification is manual:

1. Confirm that all declaration fields match `zalacznik-E.md`.
2. Confirm that the route is `X-01`.
3. Confirm that the category enables System-funded transport.
4. Confirm that no special notes are added.
5. Submit the declaration to `/verify` and inspect the Hub response.

If the Hub rejects the answer, use the returned error as the next debugging signal, especially for the ambiguous `WDP` field.
