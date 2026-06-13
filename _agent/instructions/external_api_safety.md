## External API Safety Instructions

Use these instructions when making real OpenAI calls or other external API calls, including debug and inspection scripts.

These instructions are subordinate to `AGENTS.md`. If any point appears to conflict with `AGENTS.md`, follow `AGENTS.md` and treat this file as an operational checklist for API calls.

## Relationship To AGENTS.md

- Use the `AGENTS.md` Safety Boundaries section as the source of truth for what is a secret, what is a local learning artifact, and where each value may be stored.
- Do not broaden the `AGENTS.md` secret definition only because a value came from an API response.
- Store task inputs, API feedback, retrieved records, FLAGS, final answers, and debugging observations only as local learning artifacts in ignored runtime data such as `data/{APP_NAME}/...` when they are useful for learning or debugging.
- Store real secrets only in `.env` files. Outside `.env`, use masked values or configuration names such as `API_BASE_URL`, `HUB_VERIFY_URL`, or `OPENAI_API_KEY`.
- If generated payloads, reports, or logs would normally include a secret or externally supplied operational endpoint, omit it, mask it, or refer to it by configuration name.

## TLS Preparation

- Before every real OpenAI API call, apply the TLS/CA environment setup from `TROUBLESHOOTING.md`.
- Set both `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` to the documented combined CA bundle before starting the Python process.
- Treat this as a proactive prerequisite, not as a recovery step after a certificate error.
- Keep TLS verification enabled. Never use `verify=False` or an equivalent verification bypass.

## Approval And Guards

- Ask for approval before real external API calls unless the user has already approved the specific action.
- Keep exploratory API usage small and explicit.
- Any debug, workbench, or inspection script that makes real OpenAI or external API calls must include a hard execution guard such as `max_iterations`, `max_model_requests`, or `max_tool_calls`.
- When the guard limit is reached, the script must stop with a clear guard-related error.
- Prefer configuration names in docs and logs. Do not echo raw secret values.
