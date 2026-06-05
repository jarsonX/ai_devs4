# L9 Mailbox Dev Notes

## Table Of Contents

- [Implementation Notes](#implementation-notes)
- [Design Decisions](#design-decisions)
- [Implementation Plan](#implementation-plan)
- [Lessons Learned](#lessons-learned)

## Implementation Notes

### Zmail `help` API Inspection

Date: 2026-06-05

The first external API inspection called the zmail API with the `help` action. The API key was loaded from `AI_DEVS_API_KEY` in `.env` and was not written to disk. The API endpoint should be represented in code and documentation by a configuration name such as `ZMAIL_API_URL`, not by a raw operational URL.

The `help` response reported:

| Field | Value |
| --- | --- |
| `ok` | `true` |
| `mode` | `read_only` |
| `description` | Gmail API. All actions are read-only. |

Available actions:

| Action | Purpose | Parameters |
| --- | --- | --- |
| `help` | Shows available actions and required parameters. | No parameters beyond authentication and action selection. |
| `getInbox` | Returns a list of threads in the mailbox. | `page` optional integer >= 1, default `1`; `perPage` optional integer from `5` to `20`, default `5`. |
| `getThread` | Returns `rowID` and `messageID` values for a selected thread, without message body. | `threadID` required numeric thread identifier. |
| `getMessages` | Returns one or more messages by `rowID` or `messageID`. | `ids` required; accepts a numeric `rowID`, a 32-character `messageID`, or an array of those values. |
| `search` | Searches messages with full-text query syntax and Gmail-like operators. | `query` required; supports words, quoted phrases, `-exclude`, `from:`, `to:`, `subject:`, `subject:"phrase"`, `subject:(phrase)`, `OR`, `AND`; missing operator means `AND`. Also supports optional `page` and `perPage` like `getInbox`. |
| `reset` | Resets the request counter for the current API key in service cache. | `action` only. Use only when explicitly needed during debugging. |

Design implication: the mailbox workflow should use a two-step read pattern. First search or list candidate threads/messages, then fetch full message bodies with `getMessages` before extracting facts. Message metadata alone is not enough evidence for final answers.

## Design Decisions

### Initial Workbench Direction

These decisions are working notes for the first implementation pass. They describe the agreed direction before building the actual workflow.

| Decision Area | Working Decision | Reason |
| --- | --- | --- |
| Agent shape | Start with one `Mailbox Investigator` agent, not a multi-agent system. | The task has one mailbox source, one objective, and three facts to find. A multi-agent topology would add coordination cost before it adds value. |
| Workflow style | Use a controlled agentic loop for the workbench. | The mailbox is active, so the workflow may need to search, read, observe partial results, reformulate queries, and retry. |
| Tool boundary | Expose narrow mailbox tools rather than a broad raw API tool in the main flow. | Narrow tools keep the model focused and make tool calls easier to validate and log. |
| Verification boundary | Let code validate the answer shape before any Hub submission. | Date, password presence, and confirmation code format can be checked deterministically before spending a submit attempt. |
| Active mailbox handling | Track inspected message identifiers and allow repeated searches within explicit limits. | New messages may arrive during the run, but the workbench still needs loop guards. |
| Runtime records | Store runtime reports under ignored `data/L9_mailbox/...`, including course API feedback, candidate values, final answers, Hub feedback, and FLAGS when useful for debugging. | Runtime artifacts should help learning and debugging while still excluding API keys, operational endpoints, and credentials that grant real external access. |
| Model choice | Use the OpenAI model `gpt-5-mini` for the workbench loop. | The repository uses OpenAI models by default, and the task is mostly search, retrieval, and extraction, not deep reasoning. |
| Result contract | Require structured findings with evidence identifiers, uncertainty, and status. | A structured result is easier to validate than narrative prose and helps preserve source traceability. |
| Hub feedback | Feed Hub feedback back into the loop only within a submit guard. | Feedback can guide continued search, but submit attempts must remain bounded. |
| Implementation scope | Start with a workbench, not a production app. | If the workbench solves the exercise, a productionized app may not be necessary. |

## Implementation Plan

This plan is the working reference for step-by-step implementation. Do not build the whole app in one pass. Each step should end with the smallest practical verification before moving on.

| Step | Scope | Done When | Verification |
| --- | --- | --- | --- |
| 1 | Create minimal package skeleton. | `src/apps/L9_mailbox/` has `__init__.py` and placeholder modules only where needed for the next step. | Import the package with `.\venv\Scripts\python.exe`. |
| 2 | Add configuration loading. | Config reads `AI_DEVS_API_KEY`, `ZMAIL_API_URL`, and `HUB_VERIFY_URL` from environment variables, while model name and guard limits live as app constants. | Run a config-only command that prints masked config names and guard values, never secrets. |
| 3 | Build read-only zmail client. | Client supports `search`, `getInbox`, `getThread`, and `getMessages`; `reset` stays debug-only. | Call `help` or a harmless read action through the client with masked logging. |
| 4 | Add deterministic validators. | Validator checks date format, non-empty password candidate, and `confirmation_code` format. | Run local validator tests or a small validation command with fake values. |
| 5 | Build workbench search helpers. | Workbench can run targeted queries, classify promising results, and fetch full messages for selected IDs. | Dry run search without extraction or submission; inspect the local workbench report. |
| 6 | Add structured extraction pass. | The model or extractor returns structured candidate values, evidence IDs, uncertainties, and next queries. | Run extraction on fetched messages and verify the result schema locally. |
| 7 | Add bounded investigator loop. | Loop can search, read, extract, retry, and stop as `solved`, `partial`, or `blocked` within iteration limits. | Dry run with submission disabled and guard counters visible in the report. |
| 8 | Add guarded Hub submission. | Submission is available only behind an explicit CLI flag and local validation. | Run a submit attempt only after user approval for the external call. |
| 9 | Update docs after the run. | README and dev notes reflect the actual implemented workflow and lessons learned. | Re-read docs and check that no API keys, operational endpoints, or credentials that grant real external access were stored outside `.env`. |

Step 1 completed on 2026-06-05. The package skeleton contains `src/apps/L9_mailbox/__init__.py`, and the package import was verified with the project virtual environment.

Step 2 completed on 2026-06-05. `config.py` now loads app paths, `AI_DEVS_API_KEY`, `ZMAIL_API_URL`, and `HUB_VERIFY_URL` from environment variables. Model selection and runtime guard limits are app-level constants, not `.env` values. The config check used process-local placeholder values and printed only a secret-safe summary.

Step 3 completed on 2026-06-05. `zmail_client.py` now supports read-only `help`, `getInbox`, `getThread`, `getMessages`, and `search` actions. The API advertises `reset`, but the client blocks unsupported actions through a read-only allowlist so `reset` cannot be called accidentally from the main client.

Step 3 verification:

- local payload checks passed with placeholder config values,
- `reset` was rejected by `build_zmail_payload`,
- one real `help` call through `ZmailClient` returned HTTP `200`, `ok: true`, mode `read_only`, and actions `getInbox`, `getMessages`, `getThread`, `help`, `reset`, `search`,
- the real call required `REQUESTS_CA_BUNDLE` with the existing repository CA bundle because Python `requests` hit the known Norton HTTPS inspection certificate issue.

Step 4 completed on 2026-06-05. `validator.py` now validates `date`, `password`, and `confirmation_code` candidates before any future Hub submission. The validator uses fake local test values only and does not store or require real challenge answers.

Step 4 verification:

- accepted a real calendar date in `YYYY-MM-DD` format,
- rejected an impossible date and a non-canonical date format,
- accepted a non-empty password candidate and rejected whitespace-only input,
- accepted a fake `SEC-` confirmation code with 32 alphanumeric characters,
- rejected a malformed confirmation code,
- validated full `MailboxAnswer` objects as valid or invalid with concrete error messages.

Step 5 completed on 2026-06-05. `workbench_search.py` now provides deterministic search helpers for the workbench:

- default targeted search queries,
- metadata scoring for promising results,
- safe candidate summaries with IDs, scores, and reasons,
- collection of IDs for later `getMessages` calls,
- full-message fetch helper that leaves storage decisions to callers,
- search report builder for local workbench debugging.

Step 5 verification:

- local fake mailbox data classified a relevant Proton/power-plant result as promising,
- local fake mailbox data rejected an irrelevant result,
- local fake report preserved enough metadata for debugging,
- one read-only dry run searched `from:proton.me`,
- the dry run returned HTTP `200` for search,
- the dry run technically fetched at most two promising messages,
- no extraction or Hub submission happened.

Step 6 completed on 2026-06-05. `extractor.py` now performs deterministic structured extraction from fetched message payloads. It extracts candidate `date`, `password`, and `confirmation_code` values in memory, keeps message IDs as evidence, builds a `MailboxAnswer`, runs local validation, and records uncertainties such as missing or multiple candidate values. This step did not add an LLM call.

Extraction output currently exposes a masked report and a value-bearing report. The debug view is a thin wrapper around the value-bearing report that adds a storage warning. With the updated repository policy, ignored runtime reports may include course API feedback, candidate values, final answers, Hub feedback, and FLAGS when useful for debugging. API keys, operational endpoints, and credentials that grant real external access must still stay out of files.

Step 6 verification:

- local fake message bodies produced structured candidates,
- the proposed answer selected the first candidate for each required field,
- multiple date candidates produced an uncertainty note,
- local validation accepted the complete fake answer,
- the debug extraction view exposed fake candidate values for human inspection.

Step 7 completed on 2026-06-05. The app now includes a bounded `Mailbox Investigator` loop with narrow mailbox tools and a local report writer. The model uses OpenAI Responses API function tools to choose mailbox actions one turn at a time, while deterministic code still owns payload validation, candidate extraction, answer validation, and the final `finish` guard. The loop can stop as `solved`, `partial`, or `blocked`, and it falls back to a deterministic blocked result when the model fails to produce a valid finish payload before the iteration guard.

Step 7 implementation details:

- `tools.py` now defines narrow agent tools for `search_messages`, `get_thread`, `get_messages`, `propose_answer`, and `finish`,
- the toolbox caches fetched messages in memory so repeated reads can reuse existing payloads during one bounded run,
- `finish` is validated by code, not trusted directly from the model,
- solved values must be grounded in fetched message text before the loop can stop as `solved`,
- `report_writer.py` writes a local JSON report with guard counters and runtime summary under `data/L9_mailbox/output/run_report.json`.

Step 7 verification:

- `tests.L9_mailbox.test_agent_loop` passed locally with a fake OpenAI client and a fake read-only mailbox client,
- the fake solved run searched, fetched, proposed an answer, finished as `solved`, and wrote a report,
- the fake blocked run exhausted the iteration guard and stopped as `blocked`,
- the report captured visible counters for iterations, model calls, and tool calls,
- no real OpenAI or zmail API call was needed for this Step 7 verification.

Step 8 completed on 2026-06-05. The app now includes guarded Hub submission behind an explicit CLI flag. Submission is available only when `main.py` is started with `--workbench --submit`, the answer is locally valid, the values are grounded in fetched message text, and the per-run submit guard still has remaining budget.

Step 8 implementation details:

- `hub_client.py` now builds mailbox verify payloads, masks API keys for reports, and enforces a bounded submit guard,
- `tools.py` now exposes `submit_answer` only in submission mode,
- `finish` cannot stop as `solved` in submission mode until an accepted Hub submission happens,
- `agent.py` now passes submission mode into the prompt, tool list, and toolbox,
- `main.py` now provides the workbench CLI with optional `--submit`.

Step 8 verification:

- `tests.L9_mailbox.test_agent_loop` passed locally with fake OpenAI, fake mailbox, and fake Hub clients,
- the fake submit run searched, fetched, proposed an answer, submitted it through `submit_answer`, and finished as `solved`,
- the fake guard test confirmed that submission mode cannot finish as `solved` before an accepted submit,
- no real OpenAI, zmail, or Hub request was made during Step 8 verification.

Step 9 completed on 2026-06-05. The app now includes a deterministic recovery pass and durable value-bearing runtime archives, and the first live `--workbench --submit` run solved the task without manual answer assembly.

Step 9 implementation details:

- `extractor.py` now gives higher priority to explicit confirmation-code corrections and multiline password patterns so the final proposal prefers corrected evidence over earlier broken values,
- `tools.py` now exposes deterministic recovery helpers that can expand suspicious threads, rerun targeted searches, rebuild an answer from the whole cached message corpus, and persist a full fetched-message archive,
- `report_writer.py` now writes both `run_report.json` and `fetched_messages.json` under `data/L9_mailbox/output/`,
- `agent.py` now tries deterministic recovery before ending as `partial` or `blocked`, and in submission mode it can submit the recovered answer without human intervention,
- the live run report now stores Hub feedback and the returned FLAG under ignored runtime data, which matches the repository learning-artifact policy.

Step 9 verification:

- `tests.L9_mailbox.test_agent_loop` passed locally with six tests after the recovery and persistence changes,
- the new recovery test confirmed that a weak model path can still solve the fake mailbox, submit through the fake Hub client, and persist full fetched messages,
- the real command `.\venv\Scripts\python.exe -m src.apps.L9_mailbox.main --workbench --submit --print-config` finished as `solved`,
- `data/L9_mailbox/output/run_report.json` now contains the returned Hub flag and raw submission feedback,
- `data/L9_mailbox/output/fetched_messages.json` now contains the full fetched message bodies used during the solved run.

Current next step: optional prompt and retrieval cleanup to reduce live iteration count, not a functional blocker.

## Lessons Learned

- Treat the mailbox API as a read-only search and retrieval tool family.
- Prefer targeted `search` queries over broad inbox scans once the first clues are known.
- Preserve source identifiers (`threadID`, `rowID`, `messageID`) in future runtime notes or reports so findings can be traced back without storing secrets.
- Do not store API keys, operational endpoints, or credentials that grant real external access outside `.env`.
- Course API feedback, candidate values, final answers, Hub feedback, and FLAGS may be stored under ignored `data/L9_mailbox/...` when useful for debugging and learning.
- Do not place course FLAGS, final answers, or Hub feedback in source code, documentation, notes, markdown files, commit messages, or published artifacts.
