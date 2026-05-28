## External API Safety Instructions

Use these instructions when making real OpenAI calls or other external API calls, including debug and inspection scripts.

## Secrets

- Never place secrets in source code, documentation, notes, markdown files, commit messages, logs, or app data files.
- Treat course FLAGS, task completion answers, and challenge verification outputs as secrets. Never place them in source code, documentation, notes, markdown files, commit messages, logs, or app data files.
- Treat API URLs, API keys, tokens, credentials, internal endpoints, and similar operational values as secrets unless the user explicitly says otherwise.
- Store secrets only in `.env` files or other dedicated secret stores approved by the user.
- Outside `.env`, use masked values or configuration names such as `API_BASE_URL`, `HUB_VERIFY_URL`, or `OPENAI_API_KEY`.
- Treat files listed in `.gitignore` as potentially secret-bearing and handle them with extra caution.
- If a generated payload would normally include a secret, save only a masked value, omit the secret, or store the secret only in `.env`.

## Approval And Guards

- Ask for approval before external API calls unless the user has already approved the specific action.
- Keep exploratory API usage small and explicit.
- Any debug, workbench, or inspection script that makes real OpenAI or external API calls must include a hard execution guard such as `max_iterations`, `max_model_requests`, or `max_tool_calls`.
- When the guard limit is reached, the script must stop with a clear guard-related error.
- Prefer configuration names in docs and logs. Do not echo raw secret values.
