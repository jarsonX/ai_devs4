## Debugging Workflow Instructions

Use these instructions when a command fails, a test breaks, runtime behavior is unclear, or the app returns an unexpected result.

## First Step

- If a problem, failure, or unclear error appears, check `TROUBLESHOOTING.md` in the repository root first.
- Use the troubleshooting file as the first local map for known environment, SSL, dependency, API, or course-specific issues.
- If it does not cover the issue, continue with the focused debugging workflow below.

## Workflow

- Name the most likely cause first.
- Test one explicit hypothesis at a time.
- Prefer small checks that isolate the failure boundary.
- Explain errors simply when the underlying mechanism may be unclear to a junior learner.
- Do not use shortcuts or hacks that reduce code quality or learning value.
- After a fix, explain the root cause and how to recognize similar issues later.

## Guarded Debug Scripts

Any debug, workbench, or inspection script that makes real OpenAI or external API calls must include a hard execution guard such as:

- `max_iterations`,
- `max_model_requests`,
- `max_tool_calls`.

The default exploratory limit must be small and explicit. When the limit is reached, the script must stop with a clear guard-related error.
