## Course Runtime Data And Leak Checks Instructions

Use these instructions when handling FLAGS, raw course API responses, Hub responses, runtime reports, commit messages, final summaries after external API runs, or leak-check work.

These instructions are subordinate to `AGENTS.md`. If any point appears to conflict with `AGENTS.md`, follow `AGENTS.md` and treat this file as an operational checklist for course-restricted data.

## Course Runtime Data

- FLAGS are not secrets in this repository policy.
- Store FLAGS, raw course API responses, full Hub responses, logs, and other learning artifacts under `data/{APP_NAME}/...`.
- Treat `data/{APP_NAME}/...` as approved runtime storage for course-restricted data.
- `data/{APP_NAME}/...` may contain FLAGS and raw course API responses without additional restrictions.
- FLAGS and raw course API responses may be shown to the user in chat without restriction.
- Do not over-redact Hub responses inside ignored runtime data just because they contain a FLAG or course feedback; preserve the full response there when it is useful.
- Never place raw FLAGS or raw course API responses in README, DEV_NOTES, source code, documentation, notes, markdown files, commit messages, reports, or published artifacts outside `data/{APP_NAME}/...`.
- When referencing successful verification outside `data/{APP_NAME}/...`, record only non-secret status such as `flag_found: true`, `Hub accepted`, or `task solved`.
- Retrieved records, mailbox contents, extracted candidate values, debugging observations, and non-sensitive summaries of course API behavior are regular local learning artifacts.

## Leak-Check Scope

- Before updating README, DEV_NOTES, reports, or commit messages after a run, check that no raw FLAG, raw course API response, API key, secret-bearing URL, private endpoint, or credential is included outside `data/{APP_NAME}/...`.
- Exclude `data/{APP_NAME}/...` from leak-check scope.
- Do not treat FLAGS shown in chat as leaks.
- Focus leak checks on changed files outside `data/{APP_NAME}/...`, especially source files, human-facing documentation, reports, commit messages, and generated artifacts intended for review or publication.

## Leak-Check Method

- Secret checks must not rely only on judgment or pattern recognition.
- When real secrets are loaded or available in the environment, scan relevant changed files outside `data/{APP_NAME}/...` for exact secret values and for short secret-derived markers, for example 4-6 character substrings from the real value.
- Do not print secret values or marker strings while scanning.
- If an exact secret match is found outside `.env`, stop immediately and inform the user.
- If a short secret-derived marker matches outside `data/{APP_NAME}/...`, treat it as a possible leak, do not disclose the marker, and ask the user to verify before continuing because short-marker matches can be false positives.
- Apply these checks especially before final responses after external API runs, documentation updates, report generation, or commit preparation.
