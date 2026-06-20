## New App Checklist

Use these instructions when creating a new app under `src/apps/{APP_NAME}`.

## Required Structure

This checklist is a routing summary. Detailed rules live in the referenced instruction files.

- Put application code under `src/apps/{APP_NAME}/`.
- Put app documentation under `src/apps/{APP_NAME}/docs/`.
- Create `src/apps/{APP_NAME}/docs/{APP_NAME}_README.md` unless the app is explicitly excluded.
- Include an `LLM Usage And Reviews` section in the app README and classify LLM usage as `Yes`, `No`, or `Undecided` before creating application source files.
- Include a Mermaid logic flowchart in the app README unless the app documentation instructions require stopping to ask the user before omitting it.
- Plan for a final `What This Task Should Teach` section in the app README, and complete it when the app work is finished.
- Use `src/apps/{APP_NAME}/docs/{APP_NAME}_DEV_NOTES.md` only when useful development context exists.
- Put runtime files under `data/{APP_NAME}/...`, using clear subdirectories such as `input/`, `references/`, `output/`, `logs/`, or `cache/`.

## Required Checks

- Read `_agent/instructions/app_documentation.md` before writing app docs.
- Read `_agent/instructions/app_data_layout.md` before creating runtime paths.
- If the app README classifies `LLM usage` as `Yes` or `Undecided`, read `_agent/instructions/llm_design_gate.md` and pass the design gate before creating or editing application source files.
- If the app makes real OpenAI or external API calls, read `_agent/instructions/external_api_safety.md`.

## Implementation Defaults

- Follow existing project conventions before introducing a new pattern.
- Add short purpose comments for each class, function, and method.
- Use `.\venv\Scripts\python.exe` for Python commands on Windows.
- After code-changing steps, run the simplest practical verification and report the result.
