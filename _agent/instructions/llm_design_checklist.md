# LLM App Design Checklist

Use this checklist before implementation to review whether the planned LLM application is designed in a lean, safe, and maintainable way.

Mark each item as:
- `YES` if the design clearly satisfies the rule,
- `NO` if the design is missing it,
- `N/A` if the item does not apply to the planned application.

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
- [ ] Structured outputs are planned wherever code will consume the result.

## Context And Tools

- [ ] The design limits context to only what the current step needs.
- [ ] The design limits tool exposure to only the tools needed for the current step.
- [ ] The design avoids passing full history, full datasets, or irrelevant examples by default.
- [ ] The workflow includes batching or caching where repeated calls are likely.

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
- validation around every important boundary.

Avoid:
- one large prompt for everything,
- using the model where code is enough,
- exposing all tools all the time,
- sending unnecessary context,
- leaving output validation for later.
