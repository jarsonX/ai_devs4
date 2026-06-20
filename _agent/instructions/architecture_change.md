## Architecture Change Instructions

Use these instructions before larger changes to architecture, scope, data flow, external interfaces, or the learning approach.

## Decision Policy

- Use `_agent/instructions/change_and_approval_gates.md` as the source of truth for approval gates.
- Make only the assumptions needed for the current approved work.
- State assumptions that affect the result.
- Ask for approval before assumptions that affect architecture, scope, or learning value.
- Suggest improvements when they directly improve correctness, clarity, maintainability, or learning value.
- Do not implement optional improvements or scope expansions without explicit approval.
- Do not optimize only for speed if it harms course alignment, readability, or learning value.

## Before Changing The Design

Explain the practical options and trade-offs before making the change. Keep the explanation concise, but include enough detail for a junior learner to understand why the choice matters.

Good trade-off notes usually answer:

- What behavior or boundary changes?
- What gets simpler?
- What risk or cost increases?
- How will we verify the change?
