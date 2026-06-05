## LLM Design Gate Instructions

Use these instructions before implementing a new or materially changed LLM-powered workflow, stage, model call, prompt, tool-using model step, agent behavior, multimodal extraction, model output schema, or AI-assisted reasoning component.

## Gate

- First define the design in the relevant app README under `src/apps/{APP_NAME}/docs/`.
- The README must include `LLM Usage And Reviews` with `LLM usage` set to `Yes` or `Undecided` before this gate is run.
- Review that design with `_agent/instructions/llm_design_checklist.md` before implementation.
- The checklist review scope must be explicit, for example `MVP2 Stage 1 only`, `full MVP2 workflow`, or `source selection step`.
- Do not implement outside the reviewed scope.
- If only one stage passed the checklist, later stages require their own checklist review before implementation.
- Every checklist item must be marked `YES`, `NO`, or `N/A` with a short evidence note.
- Any `NO` blocks implementation. First update the design, then rerun the checklist review.
- For an app whose planned solution depends on an LLM or agentic workflow, run this gate before creating or editing application source files, even when the first planned implementation steps are deterministic helpers.
- If the design is not yet known, stop at discovery and documentation. Do not create implementation modules as a way to discover the design.
- Small documentation edits, typo fixes, read-only analysis, and deterministic code changes inside an already approved design scope do not require a new checklist review unless they change the LLM design.

## Design Concerns

Treat these as design concerns, not implementation details to invent while coding:

- model output schemas,
- prompt plans,
- context boundaries,
- tool exposure,
- validation,
- missing-input handling,
- caching,
- authorization boundaries,
- guard limits for model or tool calls.

## README Review Record

Record each passed checklist review in the app README `LLM Usage And Reviews` section. The entry may be brief and does not need to include the full checklist details, but it must state the reviewed scope, checklist path, result, date, and approved implementation boundary.

Use this standard evidence format inside the existing `LLM Usage And Reviews` table or directly below it:

```md
| Design review | Passed | `_agent/instructions/llm_design_checklist.md`; YYYY-MM-DD; scope: MVP2 Stage 1: AI Command Parser; result: PASS; boundary: implement Stage 1 only. |
```

Use DEV_NOTES only for optional detailed reasoning, trade-offs, failed review notes, or historical review notes. The app README remains the source of truth for the current LLM design, approved implementation scopes, and runnable contract.

If detailed design notes live in DEV_NOTES, summarize the current accepted design and approval status in the app README instead of making DEV_NOTES the only source.
