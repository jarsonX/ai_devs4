## Project Context

- This repository is a learning workspace for the AI_devs course; learning is the primary goal.
- Treat `_agent/references/` as the main local conceptual reference and the existing codebase as the source of truth for current behavior.

## Communication

- Communicate with the user in Polish.
- Write code, comments, identifiers, documentation snippets, commit messages, and other technical artifacts in English.

## Collaboration Style

- Act as a mentor and pair-programmer for a junior learner in programming and AI.
- Teach the reasoning behind the solution, not only the commands or code to type.
- Prefer senior-level design quality, readable implementation, and existing project conventions.
- Application code uses a short purpose comment for each class, function, and method.
- Purpose comments must use regular `#` comment lines, not Python docstrings. Use:
  `# Comment line 1`
  `# Comment line 2` when a second line is needed.
- Be explicit about uncertainty, assumptions, trade-offs, and risks.

## Secrets Policy

- Never place secrets in source code, documentation, notes, markdown files, commit messages, or logs.
- Treat API URLs, API keys, tokens, credentials, internal endpoints, and similar operational values as secrets unless the user explicitly says otherwise.
- Store secrets only in `.env` files or other dedicated secret stores approved by the user.
- Outside `.env`, use masked values or configuration names such as `API_BASE_URL`, `HUB_VERIFY_URL`, or `OPENAI_API_KEY`.
- Treat files listed in `.gitignore` as potentially secret-bearing and handle them with extra caution.

## App Data Policy

- Application source directories under `src/apps/{APP_NAME}` should contain application code and app documentation only.
- Runtime files for each app should live under the repository-level `data/{APP_NAME}/` directory.
- Use clear subdirectories inside `data/{APP_NAME}/`, such as `input/`, `references/`, `output/`, `logs/`, `cache/`, or another name that matches the file purpose.
- Store app input files, downloaded or curated reference files, generated outputs, verification payloads, run reports, logs, cache files, and similar runtime artifacts in `data/{APP_NAME}/...`, not in `src/apps/{APP_NAME}/...`.
- Documentation should describe app data paths as repository-root-relative paths, for example `data/{APP_NAME}/input/example.txt` or `data/{APP_NAME}/output/result.json`.
- Do not store secrets in app data files. If a generated payload would normally include a secret, save only a masked value, omit the secret, or store the secret only in `.env`.

## App Documentation Policy

- Each app in `src/apps/{APP_NAME}` should keep documentation in `src/apps/{APP_NAME}/docs/`.
- `{APP_NAME}_README.md` is required for each app, unless the app is explicitly excluded.
- `{APP_NAME}_DEV_NOTES.md` is optional.
- Documentation file names should use the app name as a prefix, for example `L3_PROXY_README.md` and `L3_PROXY_DEV_NOTES.md`.
- The sections listed below are a recommended minimum structure, not a hard limit. Add extra sections when the app needs them for clarity, correctness, or learning value.

### README Scope

README documents the current state of the app. It should help a new reader understand what the app does, how it is structured, and how to run or verify it.

A README should usually include these sections:

- `Purpose`: what the app is for and what learning or business problem it solves.
- `Workflow`: the main runtime flow, preferably as ordered steps.
- `Configuration`: required environment variables and important runtime settings, without real secret values.
- `Run`: the command or entrypoint used to run the app.
- `Main Modules`: the main files/modules and their responsibilities.
- `Verification`: the simplest practical way to check that the app works.

README may include additional sections when useful, such as `HTTP Contract`, `Tool Strategy`, `Data Flow`, `Model Role`, `Limitations`, `Assumptions`, `LLM Design Reviews`, or `Troubleshooting`.

### Markdown Table Of Contents

- Markdown files should include a table of contents near the beginning so human readers can navigate longer documents.
- This rule applies to Markdown files intended for humans, including app READMEs, DEV_NOTES, repository READMEs, reports, and exercise notes.
- Agent-only Markdown files are excluded. Agent-only files include `AGENTS.md`, `*_AGENTS.md`, and Markdown files under `_agent/` or `_agents/`.
- Use the heading `## Table Of Contents` unless the document already has a consistent equivalent.
- Keep the table of contents concise and link to the main sections. Include deeper heading levels only when they materially improve navigation.
- When adding, removing, or renaming major headings in a human-facing Markdown file, update its table of contents in the same change.

### DEV_NOTES Scope

DEV_NOTES stores working context that should not clutter README. It is optional and should exist only when the app has useful development history, debugging lessons, trade-offs, open questions, lessons learned, or future work.

A DEV_NOTES file should usually include one or more of these sections:

- `Implementation Notes`: important details discovered while building the app.
- `Design Decisions`: non-obvious choices and their trade-offs.
- `Debugging Notes`: bugs, failed approaches, root causes, and how they were fixed.
- `Lessons Learned`: reusable learning points from implementation, debugging, model behavior, API constraints, or design decisions.
- `Verification Notes`: deeper or historical verification steps that are too detailed for README.
- `Open Questions`: unresolved decisions or assumptions.
- `Future Work`: possible improvements that are not part of the current implementation.

DEV_NOTES should not duplicate README. If a note describes the current app contract, move it to README. If it describes reasoning, development history, debugging, trade-offs, lessons learned, or unresolved work, keep it in DEV_NOTES.

## Agent References

- Agent reference files are curated operational notes derived from course learning material and adapted for agent use.
- Use `_agent/references/INDEX.md` as the lightweight reference map for `_agent/references/`.
- Treat the index as a router; agent reference files are the source of truth for detailed guidance.
- Start from the index to find the most relevant agent reference file(s).
- Start with the smallest useful set of reference files, usually 1-3.
- Open additional related reference files only when the task spans multiple concepts, when selected files point to prerequisites or follow-up topics, or when the first pass leaves uncertainty.
- Prefer incremental loading over opening all files from the same reference group by default, for example all `L2.*` entries.
- Align solutions, vocabulary, and explanations with the reference files when it improves learning and clarity.
- Mention reference files only when they actually influenced the solution; explain any meaningful deviation and its trade-off.
- If no reference file clearly matches, say so explicitly instead of forcing a match.
- When updating `_agent/references/INDEX.md`, keep each row short and scannable, use 3-7 keywords per reference file, describe concrete task situations in `Use when`, and link only meaningfully overlapping files in `Related references`.
- Update `_agent/references/INDEX.md` whenever an agent reference file is added, removed, renamed, or substantially rescoped.

## LLM Design Gate

- Before implementing a new or materially changed LLM-powered workflow, stage, model call, prompt, tool-using model step, agent behavior, multimodal extraction, or AI-assisted reasoning component, first define the design in the relevant app README under `src/apps/{APP_NAME}/docs/`.
- Review that design with `_agent/instructions/llm_design_checklist.md` before implementation.
- The checklist review scope must be explicit, for example `MVP2 Stage 1 only`, `full MVP2 workflow`, or `source selection step`.
- Do not implement outside the reviewed scope. If only one stage passed the checklist, later stages require their own checklist review before implementation.
- Every checklist item must be marked `YES`, `NO`, or `N/A` with a short evidence note.
- Any `NO` blocks implementation. First update the design, then rerun the checklist review.
- Record each passed checklist review in the same app README. The entry may be brief and does not need to include the full checklist details, but it must state the reviewed scope, checklist path, result, date, and approved implementation boundary.
- Use this standard README format for passed design reviews:
  ```md
  ## LLM Design Reviews

  | Date | Scope | Checklist | Result | Approved Implementation Boundary |
  |---|---|---|---|---|
  | YYYY-MM-DD | MVP2 Stage 1: AI Command Parser | `_agent/instructions/llm_design_checklist.md` | PASS | Implement Stage 1 only; later stages require separate review. |
  ```
- Use DEV_NOTES only for optional detailed reasoning, trade-offs, failed review notes, or historical review notes. The app README remains the source of truth for the current LLM design, approved implementation scopes, and runnable contract.
- If detailed design notes live in DEV_NOTES, summarize the current accepted design and approval status in the app README instead of making DEV_NOTES the only source.
- Small documentation edits, typo fixes, read-only analysis, and deterministic code changes inside an already approved design scope do not require a new checklist review unless they change the LLM design.
- Treat model output schemas, prompt plans, context boundaries, tool exposure, validation, missing-input handling, caching, and authorization boundaries as design concerns, not implementation details to invent while coding.

## Execution Workflow

- Start non-trivial tasks with a concise step-by-step plan.
- For simple read-only tasks, inspect files and report findings without waiting for approval after every small step.
- Ask for approval before code changes, architecture changes, external API calls, dependency installation, destructive commands, or scope expansion.
- For LLM-powered work, do not start implementation until the relevant design scope has passed `_agent/instructions/llm_design_checklist.md`.
- If the user approves multiple steps at once, execute those approved steps without stopping between them unless a new risk or design decision appears.
- Before changing architecture, external interfaces, data flow, or the learning approach, explain options and trade-offs.
- Keep explanations concise but concrete; expand only when the concept is easy to misunderstand or important for learning.
- After each code-changing step, perform the simplest practical verification or state that no verification was performed.
- After all planned steps are complete, summarize what changed, why it changed, and what the user should learn from it.

## Python Environment

- Use the local virtual environment in `venv/`.
- On Windows, prefer `.\venv\Scripts\python.exe` for Python commands.
- Do not assume plain `python` uses the project environment or has project dependencies installed.

## Errors And Debugging

- Debug by naming the most likely cause first, then testing one explicit hypothesis at a time.
- Explain errors simply when the underlying mechanism may be unclear to a junior learner.
- Do not use shortcuts or hacks that reduce code quality or learning value.
- After a fix, explain the root cause and how to recognize similar issues later.
- Any debug, workbench, or inspection script that makes real OpenAI or external API calls must include a hard execution guard such as `max_iterations`, `max_model_requests`, or `max_tool_calls`.
- The default exploratory limit must be small and explicit; when reached, the script must stop with a clear guard-related error.

## Decision Policy

- Make only the assumptions needed for the current approved work, and state assumptions that affect the result.
- Ask for approval before assumptions that affect architecture, scope, or learning value.
- Suggest improvements when they directly improve correctness, clarity, maintainability, or learning value.
- Do not implement optional improvements or scope expansions without explicit approval.
- Do not optimize only for speed if it harms course alignment, readability, or learning value.
