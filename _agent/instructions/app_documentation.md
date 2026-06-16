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
- `LLM Usage And Reviews`: whether the app uses or may use LLMs, and the status of required LLM design and optimization reviews.
- `Configuration`: required environment variables and important runtime settings, without real secret values.
- `Run`: the command or entrypoint used to run the app.
- `Main Modules`: the main files/modules and their responsibilities.
- `Verification`: the simplest practical way to check that the app works.
- `What This Task Should Teach`: required final section added when work on the app is complete. It should explain the main learning points of the task, using concrete lessons from the implemented app. This section must be the last section in the README.

README may include additional sections when useful, such as `HTTP Contract`, `Tool Strategy`, `Data Flow`, `Model Role`, `Limitations`, `Assumptions`, or `Troubleshooting`.

If creating the Mermaid flowchart would be misleading, harmful, or not recommended for the specific situation, stop before omitting it. Explain the reason to the user and ask whether the app README may skip the Mermaid flowchart.

## LLM Usage And Reviews

Every new app README must include an `LLM Usage And Reviews` section, even when the app does not use an LLM. When updating an existing app README that does not have this section, add it before continuing with app implementation or completion work. This section is the local source of truth for whether LLMs are planned, whether implementation may start, and whether the completed LLM workflow has been reviewed.

Use this minimum structure:

```md
## LLM Usage And Reviews

| Area | Status | Evidence |
| --- | --- | --- |
| LLM usage | Yes / No / Undecided | Short reason based on the planned workflow. |
| Design review | Pending / Passed / N/A | `_agent/instructions/llm_design_checklist.md`, scope, date, and result. |
| Optimization review | Pending / Passed / N/A | `_agent/instructions/llm_optimization_checklist.md`, scope, mode, date, and result. |
```

Set `LLM usage` to:

- `Yes` when the app includes or is expected to include a model call, prompt, tool-using model step, agent behavior, multimodal extraction, model output schema, or AI-assisted reasoning component.
- `Undecided` when the app may need an LLM but the design is not yet settled.
- `No` only when the app is expected to stay deterministic.

If `LLM usage` is `Yes` or `Undecided`, do not start source implementation for the app until the design review has passed. Discovery, reference reading, approved read-only API inspection, README design notes, and DEV_NOTES are allowed before the review. Application source modules, prompts, model-call scaffolding, agent-loop scaffolding, model tools, and runtime workflow code are not allowed before the review passes.

For LLM apps, README is the source of truth for the accepted design, approved scope, runnable contract, and LLM review status. If checklist evidence or trade-off notes become too detailed, summarize the result in README and move the detailed reasoning to DEV_NOTES.

After completing an LLM-powered app or materially changed LLM workflow, review the completed app with `_agent/instructions/llm_optimization_checklist.md` before declaring the work complete. Record the result in `LLM Usage And Reviews`. Any `NO` item should be listed as a blocking fix, accepted workbench limitation, or follow-up before production.

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

- `Implementation Plan`: required whenever DEV_NOTES exists; a batch-based plan for AI-agent implementation work.
- `Implementation Notes`: important details discovered while building the app.
- `Design Decisions`: non-obvious choices and their trade-offs.
- `Debugging Notes`: bugs, failed approaches, root causes, and how they were fixed.

DEV_NOTES should not duplicate README. If a note describes the current app contract, move it to README. If it describes reasoning, development history, debugging, trade-offs, or unresolved work, keep it in DEV_NOTES.

## DEV_NOTES Implementation Plan

When `{APP_NAME}_DEV_NOTES.md` exists, it must include an `Implementation Plan` section.
This section is the working plan for an AI coding agent and should be organized into batches rather than one long undifferentiated checklist.

Each batch should include:

- a short batch title, for example `Batch 1: App Skeleton And Data Access`;
- `Goal`: the outcome of the batch in plain English;
- `Steps`: ordered implementation steps that belong together;
- `Checkpoint`: the smallest practical verification before moving to the next batch.

The plan should help an agent make coherent changes without losing architecture discipline.
Use batches to group work by natural implementation boundaries such as app skeleton, data loading, parsing, model integration, response assembly, tests, verification helpers, and final public validation.

The plan should also state when the agent must stop for approval before continuing, for example:

- architecture changes;
- LLM usage or expanded LLM scope;
- dependency installation;
- external API calls;
- public exposure or deployment;
- destructive commands or irreversible data changes.

Keep the plan implementation-oriented.
Do not duplicate the README contract, HTTP examples, configuration tables, or accepted LLM review record unless the detail is needed to guide the next code change.
