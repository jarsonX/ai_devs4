## Change And Approval Gates Instructions

Use these instructions when planning or performing work that may cross an approval gate, such as architecture changes, behavior-changing interface or data-flow changes, dependency installation, real external API calls, destructive commands, or scope changes.

These instructions are subordinate to `AGENTS.md`. If any point appears to conflict with `AGENTS.md`, follow `AGENTS.md` and treat this file as an operational decision rule for approvals and escalation.

## Proceed Without Extra Approval

- You may proceed without extra approval for local code, test, and documentation changes that are directly requested by the user.
- You may proceed without extra approval for local code, test, and documentation changes that are clearly necessary to complete the requested task.
- Keep these changes scoped to the current request and repository conventions.

## Ask For Approval First

- Ask for approval before architecture changes.
- Ask for approval before materially behavior-changing external interface or data-flow changes.
- Ask for approval before dependency installation.
- Ask for approval before real external or OpenAI API calls.
- Ask for approval before destructive commands.
- Ask for approval before scope expansion beyond the user request.

## How To Decide

- If the task can be completed with a local implementation change that fits the current structure, do it.
- If the change alters system boundaries, introduces side effects, spends money, reaches outside the repository, or meaningfully changes behavior beyond the request, stop and ask first.
- If a small local change reveals a larger architectural issue, explain the trade-offs before expanding scope.
- If approval was already given for multiple steps, continue through those approved steps unless a new risk appears.
