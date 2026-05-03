<!-- This file documents the purpose, workflow, and module responsibilities of the L1 People app. -->

# L1 People

L1 People solves the AI_devs `people` task. The app downloads people data from the course API, narrows the dataset with deterministic filters, asks OpenAI to classify jobs for the remaining candidates, and sends the final answer to the verification endpoint.

## Purpose

The app demonstrates a hybrid workflow:

- deterministic Python code handles data loading, filtering, payload building, and verification,
- OpenAI handles only the narrow classification step,
- structured output keeps the model response machine-readable,
- results are saved locally for later inspection.

## Workflow

1. Load configuration from environment variables.
2. Download the people CSV file into `data/L1_people/input/people.csv`.
3. Parse CSV rows into `PersonRecord` objects.
4. Filter people by gender, birth place, and age range.
5. Ask OpenAI to classify the remaining jobs with a fixed tag list.
6. Select people tagged as transport-related.
7. Build the answer payload for the `people` task.
8. Send the payload to the verification endpoint.
9. Save payload, verification response, and basic statistics in `data/L1_people/output/verification_result.json`.

## Main Modules

- `main.py`: app entry point.
- `config.py`: environment and path configuration.
- `data_loader.py`: CSV download and parsing.
- `filters.py`: deterministic candidate filtering.
- `classifier.py`: OpenAI call and structured classification parsing.
- `prompts.py`: prompt text and allowed classification tags.
- `models.py`: data structures shared by the workflow.
- `pipeline.py`: end-to-end orchestration.
- `output.py`: local result persistence.

## Required Configuration

Secrets and endpoint values are read from `.env`:

- `AI_DEVS_API_KEY`
- `OPENAI_API_KEY`
- `L1_PEOPLE_CSV_URL`
- `L1_VERIFY_API_URL`

Do not commit real values for these variables.

## Run

From the repository root, use the project virtual environment:

```powershell
.\venv\Scripts\python.exe -m src.apps.L1_people.main
```
