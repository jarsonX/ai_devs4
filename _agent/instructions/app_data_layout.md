## App Data Layout Instructions

Use these instructions when handling app inputs, outputs, references, logs, cache files, reports, or verification payloads.

## Core Rules

- Application source directories under `src/apps/{APP_NAME}` should contain application code and app documentation only.
- Runtime files for each app should live under the repository-level `data/{APP_NAME}/` directory.
- Use clear subdirectories inside `data/{APP_NAME}/`, such as `input/`, `references/`, `output/`, `logs/`, `cache/`, or another name that matches the file purpose.
- Store app input files, downloaded or curated reference files, generated outputs, verification payloads, run reports, logs, cache files, and similar runtime artifacts in `data/{APP_NAME}/...`, not in `src/apps/{APP_NAME}/...`.
- Documentation should describe app data paths as repository-root-relative paths, for example `data/{APP_NAME}/input/example.txt` or `data/{APP_NAME}/output/result.json`.
- Do not store secrets in app data files.
- If a generated payload would normally include a secret, save only a masked value, omit the secret, or store the secret only in `.env`.
- FLAGS are not secrets in this repository policy. Course FLAGS, raw course API responses, and Hub responses are governed by `_agent/instructions/course_runtime_data_and_leak_checks.md` and may be stored under `data/{APP_NAME}/...`.

## Why This Matters

Keeping source code and runtime artifacts separate makes the app easier to review, test, archive, and clean. A junior reader should be able to answer two questions quickly:

- `src/apps/{APP_NAME}/...`: what code and app docs explain the app?
- `data/{APP_NAME}/...`: what files did the app read, create, cache, or report?
