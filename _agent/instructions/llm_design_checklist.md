# LLM App Design Checklist

Use this checklist before implementation to review whether the planned LLM application is designed in a lean, safe, and maintainable way.

Choose one review mode before answering the checklist:
- `production` for user-facing, persistent, deployed, long-running, or reliability-sensitive applications,
- `non-production` for local exercises, prototypes, one-off scripts, and learning workflows where production runtime guarantees are intentionally out of scope.

Mark each item as:
- `YES` if the design clearly satisfies the rule,
- `NO` if the design is missing it,
- `N/A` if the item does not apply to the planned application.

Items marked `Production-only` must be reviewed in `production` mode. In `non-production` mode, mark them `N/A` with a short note unless the planned application still includes production-like runtime behavior.

For every item, add a short design note:
- mention the planned component, step, tool, model, or rule,
- do not answer with `YES`, `NO`, or `N/A` alone.

## Scope And Workflow

- [ ] The application has a clearly defined goal and expected output.
- [ ] The workflow is split into small steps when one model call would mix multiple responsibilities.
- [ ] Deterministic code is planned for stable logic, and LLM calls are reserved for language or reasoning tasks.
- [ ] Each planned workflow step has a clear purpose.

## Model And Prompt Plan

- [ ] Each LLM step has a reason for using a model instead of ordinary code.
- [ ] The selected model for each step matches the expected difficulty of that step.
- [ ] Prompts are planned to be short, focused, and limited to the current step.
- [ ] Token usage is intentionally limited for both model input and model output.
- [ ] Structured outputs are planned wherever code will consume the result.

## Context And Tools

- [ ] The design limits context to only what the current step needs.
- [ ] The design limits tool exposure to only the tools needed for the current step.
- [ ] The design avoids passing full history, full datasets, or irrelevant examples by default.
- [ ] The workflow includes batching, caching, or persisted intermediate results where repeated or long-running calls are likely.

## Runtime Performance And Task Lifecycle

- [ ] Production-only: Long-running LLM, tool, media generation, or agent tasks have a planned progress or heartbeat mechanism.
- [ ] Production-only: The user can understand what is happening while waiting for slow model, tool, media generation, or agent work.
- [ ] Production-only: Long-running work can continue safely if the user closes the browser, loses connection, or leaves the application.
- [ ] Production-only: The workflow defines how task state, intermediate outputs, and final results are persisted.
- [ ] Production-only: The design supports pausing and resuming tasks when waiting for user approval, tool results, retries, or agent completion.
- [ ] Production-only: User interaction during long-running work is planned, such as message queueing, cancellation, or opening a separate thread.
- [ ] Production-only: UI state is not tightly coupled to backend execution state for long-running tasks.
- [ ] Production-only: Event-driven or job-based orchestration is considered where a synchronous request/response flow would be fragile.

## Validation And Safety

- [ ] The design includes validation before model output is used downstream.
- [ ] The design treats model output as untrusted until validation passes.
- [ ] The design keeps authorization, permissions, and risky actions outside the model.
- [ ] The workflow handles missing required inputs without guessing important values.

## Quick Rule Of Thumb

Prefer:
- smaller context,
- fewer calls,
- simpler steps,
- deterministic code for stable logic,
- visible progress for long-running production work,
- resumable job state for production workflows,
- validation around every important boundary.

Avoid:
- one large prompt for everything,
- using the model where code is enough,
- exposing all tools all the time,
- sending unnecessary context,
- tying production task execution directly to UI session state,
- forcing long-running production work into fragile synchronous flows,
- leaving output validation for later.
