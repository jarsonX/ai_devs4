## App Documentation Instructions

Use these instructions when creating or updating documentation for an app under `src/apps/{APP_NAME}`.

## Core Rules

- Each app in `src/apps/{APP_NAME}` should keep documentation in `src/apps/{APP_NAME}/docs/`.
- `{APP_NAME}_README.md` is required for each app, unless the app is explicitly excluded.
- `{APP_NAME}_DEV_NOTES.md` is optional.
- Documentation file names should use the app name as a prefix, for example `L3_PROXY_README.md` and `L3_PROXY_DEV_NOTES.md`.
- Documentation should describe app data paths as repository-root-relative paths, for example `data/{APP_NAME}/input/example.txt`.
- Do not store secrets in documentation. Use masked values or configuration names instead.

## README Scope

README documents the current state of the app. It should help a new reader understand what the app does, how it is structured, and how to run or verify it.

A README should usually include these sections:

- `Purpose`: what the app is for and what learning or business problem it solves.
- `Workflow`: the main runtime flow, preferably as ordered steps.
- `Mermaid Logic Flow`: a Mermaid flowchart that shows the app's main decision and data flow. Every app README should include this section unless a flowchart would be misleading, harmful, or not recommended for the specific situation.
- `Configuration`: required environment variables and important runtime settings, without real secret values.
- `Run`: the command or entrypoint used to run the app.
- `Main Modules`: the main files/modules and their responsibilities.
- `Verification`: the simplest practical way to check that the app works.
- `What This Task Should Teach`: required final section added when work on the app is complete. It should explain the main learning points of the task, using concrete lessons from the implemented app. This section must be the last section in the README.

README may include additional sections when useful, such as `HTTP Contract`, `Tool Strategy`, `Data Flow`, `Model Role`, `Limitations`, `Assumptions`, `LLM Design Reviews`, or `Troubleshooting`.

If creating the Mermaid flowchart would be misleading, harmful, or not recommended for the specific situation, stop before omitting it. Explain the reason to the user and ask whether the app README may skip the Mermaid flowchart.

For LLM apps, README is the source of truth for the accepted design, approved scope, and runnable contract. If checklist evidence or trade-off notes become too detailed, summarize the result in README and move the detailed reasoning to DEV_NOTES.

## README Writing Style

Write for a junior learner returning to the project later: precise enough to implement from, but clear enough to understand without decoding architecture jargon.

Prefer:

- a short plain-English explanation before a complex contract, table, or workflow,
- tables for structured facts such as configuration, schemas, modules, data paths, tool contracts, and review records,
- concrete examples when a term may be misunderstood,
- plain words over architecture jargon where precision is not lost,
- explaining terms such as `agentic`, `guard`, `schema`, or `validation` when first used,
- describing why a design choice matters, not only what the rule is.

Avoid:

- replacing useful tables with long prose,
- making README read like a security audit or internal architecture spec,
- long uninterrupted checklists without context,
- unexplained phrases such as `state machine owns permissions`,
- duplicating detailed reasoning that belongs in DEV_NOTES.

## DEV_NOTES Scope

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
