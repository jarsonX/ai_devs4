# EDU1 Development Notes

This file stores implementation-oriented notes for EDU1.
It is separate from `EDU1_README.md`, which should stay focused on the app itself.

## Recommended Implementation Order

1. `models.py`
   Define the shared models first, especially `Person` and `FinalResult`.
   This gives the rest of the app a stable vocabulary.

2. `config.py`
   Add `AppConfig` and `get_config()`.
   This centralizes paths, API keys, model settings, and iteration limits.

3. `data_loader.py`
   Implement local JSON loading, payload extraction, people parsing, and unique city extraction.
   This is the simplest domain logic and gives fast feedback on the input data.

4. `api_client.py`
   Implement the AI_devs client for `accessLevel`.
   This isolates HTTP integration before the agent starts using it.

5. `tools.py`
   Implement tool groups, tool definitions, `Edu1Toolbox`, and tool dispatch.
   At this point the underlying local logic and API integration should already exist.

6. `agent.py`
   Implement deterministic setup first, then the model-driven stages, prompts, runtime state, stage completion checks, tool execution handling, and the main agent loop.
   This is the most complex module and should be built on top of finished tools.

7. `pipeline.py`
   Implement `run_pipeline()` to load config, run the agent, and return the final result.
   This file should stay thin and high-level.

8. `main.py`
   Implement the entrypoint last.
   It should only call `run_pipeline()`.

## Verification Suggestions

- After `models.py`:
  Check imports and readability.

- After `config.py`:
  Verify that `get_config()` returns complete settings and fails clearly on missing values.

- After `data_loader.py`:
  Run the loader against `data/EDU1/data_people.json` and confirm the parsed people list and city list.

- After `api_client.py`:
  Fetch `accessLevel` for a known person and verify the response shape.

- After `tools.py`:
  Call each toolbox method directly and confirm the JSON-serializable output format.

- After `agent.py`:
  Run the staged flow and confirm that:
  - deterministic setup prepares `rawData`, `people`, and `cities` before the model-driven stages start,
  - the stages advance in the expected order,
  - the model-selected city is validated,
  - `selectedCity` enters state only after validation.

- After `pipeline.py`:
  Run `run_pipeline()` and confirm the final result object.

- After `main.py`:
  Run the app through the normal entrypoint.

## Design Guardrails

- Keep `main.py` thin.
- Keep `pipeline.py` high-level.
- Keep prompts and stage logic in `agent.py`.
- Keep deterministic setup in application code, not in the model loop.
- Keep execution logic in `tools.py`.
- Keep local file handling in `data_loader.py`.
- Keep remote API handling in `api_client.py`.
- Keep runtime state limited to validated business data.
