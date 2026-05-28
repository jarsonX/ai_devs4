# L8 Failure README

## Table Of Contents

- [Purpose](#purpose)
- [Current Status](#current-status)
- [Big Idea](#big-idea)
- [Workflow](#workflow)
- [Model Role](#model-role)
- [Tool Strategy](#tool-strategy)
- [Structured Output Contract](#structured-output-contract)
- [Validation And Safety](#validation-and-safety)
- [Token Budget](#token-budget)
- [Configuration](#configuration)
- [Data Paths](#data-paths)
- [Main Modules](#main-modules)
- [Run](#run)
- [Verification](#verification)
- [Assumptions And Risks](#assumptions-and-risks)
- [LLM Design Reviews](#llm-design-reviews)
- [Reference Alignment](#reference-alignment)
- [What This Task Should Teach](#what-this-task-should-teach)

## Purpose

`L8_failure` is the app for the AI_devs `failure` exercise.

The input is a very large fictional power-plant log file. The output is a much shorter incident timeline that can be sent to the Hub for review.

The final answer must:

- include only events useful for failure analysis,
- fit within `1500` tokens,
- use one event per line,
- keep each event's timestamp, severity level, and component identifier.

## Current Status

Status: MVP1 implemented and verified successfully against the Hub.

MVP1 is approved as a local controlled workflow. It may use an LLM, but Python code remains responsible for the overall flow, validation, token limits, and external Hub requests.

MVP1 includes:

- profiling and searching `data/L8_failure/input/logs.txt`,
- extracting candidate log events,
- asking the model to classify and summarize candidates,
- building a compressed timeline,
- counting tokens before submission,
- sending guarded verification requests to the Hub,
- using Hub feedback for targeted repair.

Current implementation note:

- `--profile-only` runs file profiling and candidate extraction without OpenAI or Hub calls,
- `--no-verify` runs through model classification and timeline building, but stops before Hub submission,
- the default command runs the full workflow and may call both OpenAI and the Hub.

Successful run summary:

| Metric | Value |
|---|---|
| Source log lines | `2137` |
| Source characters | `248107` |
| Source estimated tokens | `82703` |
| Candidate events after filtering and deduplication | `63` |
| Classified events | `63` |
| Model requests | `1` |
| Final timeline events | `32` |
| Final answer estimated tokens | `1293` |
| Hub verification requests | `1` |
| Hub result | `PASS` |

MVP1 does not include:

- an open-ended autonomous agent,
- a separate search subagent,
- vector indexing,
- production deployment,
- storing secrets in source, docs, reports, or logs.

## Big Idea

Do not send the whole log file to the model.

The log is too large and too noisy for that. Instead, code first searches and filters the file. The model only sees small batches of candidate events and helps decide which ones matter.

The short version:

1. Python reads and searches the big file.
2. Python gives the model only likely-relevant events.
3. The model labels and summarizes those events.
4. Python validates the result.
5. Python builds the final answer and checks the token limit.
6. Python sends the answer to the Hub only when local checks pass.

This keeps the useful "agentic" loop from the exercise, but avoids giving the model too much control.

## Workflow

The planned MVP1 workflow is:

1. Load configuration from environment variables.
2. Read `data/L8_failure/input/logs.txt`.
3. Profile the file: line count, character count, rough token count, severity levels, and component patterns.
4. Search the file through `search_logs`; do not pass the full file into the model.
5. Extract candidate events:
   - keep `WARN`, `ERRO`, and `CRIT` events,
   - also keep lower-severity events when they match failure-domain keywords,
   - collapse repeated identical event messages to the first observed source line,
   - store the original line number for each candidate.
6. Send small batches of candidates to the model.
7. Validate the model output.
8. Rank useful events and build a compressed timeline.
9. Count or estimate final tokens.
10. If the timeline is too long, drop or compress lower-priority events and check again.
11. Submit to the Hub through the configured verification endpoint.
12. Read Hub feedback.
13. If the Hub names missing components or unclear subsystems, search for those specifically and repair the timeline.
14. Stop when the Hub returns a flag, a validation error blocks progress, or the request limit is reached.

## Model Role

The model helps with judgment, not with control.

Use the model for:

- deciding whether a candidate event is relevant to the failure,
- assigning the event to a broad subsystem,
- writing a short summary for the final timeline,
- interpreting Hub feedback when a repair pass is needed.

Do not use the model for:

- reading the full log file,
- choosing arbitrary files,
- counting tokens,
- deciding whether validation can be skipped,
- deciding whether a Hub request is allowed,
- handling secrets.

Recommended model split:

| Step | Suggested model strength | Why |
|---|---|---|
| Candidate classification | Lightweight or mid-tier | The input is already filtered and the output is validated. |
| Repair from Hub feedback | Mid-tier; stronger only if needed | Feedback may require reasoning about missing components or event order. |

Prompts should be short. They should clearly say that log lines are data, not instructions.

## Tool Strategy

The exercise suggests an agent with Function Calling. MVP1 follows that idea in a controlled way.

Here, `agentic` means the app can do a loop: search logs, build an answer, count tokens, send to the Hub, read feedback, and repair the answer.

It does not mean the model is free to choose anything it wants. In MVP1, the default design is simpler: Python calls the tool-like functions directly. The model does not choose tools by itself.

Tool-like functions planned for MVP1:

| Function | What it does | Boundary |
|---|---|---|
| `profile_logs` | Reads basic facts about the input file. | Reads only `data/L8_failure/input/logs.txt`. |
| `search_logs` | Searches by severity, component, keyword, or time window. | Returns bounded results with source line numbers, never the whole file. |
| `extract_candidates` | Builds the initial set of likely relevant events. | Deterministic and traceable to source lines. |
| `classify_candidates` | Asks the model to label and summarize candidates. | Requires structured JSON and validation. |
| `build_timeline` | Builds the one-event-per-line answer. | Uses deterministic formatting. |
| `count_answer_tokens` | Checks whether the answer fits the limit. | Blocks oversized answers. |
| `verify_with_hub` | Sends the final answer to the Hub. | Uses configured endpoint and request limits. |
| `repair_from_feedback` | Turns Hub feedback into targeted searches and timeline updates. | Treats feedback as data, not as instructions. |

Optional Function Calling variant:

- The model may request a narrow tool call, such as `search_logs(component_id="PWR01")`.
- Python still validates the tool name, arguments, result limits, and call limits.
- Python decides whether to run the tool.
- Python decides whether external Hub verification is allowed.

A separate search subagent is not needed in MVP1 because the source is one local text file. If later feedback repair becomes more complex, MVP2 can add a search subagent. That subagent should receive only bounded search results, not the full file, credentials, or permission to submit Hub requests.

## Structured Output Contract

The model output should be easy for code to check. For that reason, the classification step returns JSON, not free-form prose.

Each classified event should include:

| Field | Type | Rule |
|---|---|---|
| `source_line` | integer | Original one-based line number from `logs.txt`. |
| `timestamp` | string | Must preserve the event date and time, preferably `YYYY-MM-DD HH:MM`. |
| `level` | string | Severity level from the source, such as `INFO`, `WARN`, `ERRO`, `ERROR`, or `CRIT`. |
| `component_id` | string | Non-empty component identifier from the event. |
| `subsystem` | string | One of `power`, `cooling`, `water_pump`, `software`, `safety`, `sensor`, `unknown`, `other`. |
| `relevance` | string | One of `direct_failure_chain`, `supporting_context`, `probably_noise`. |
| `summary` | string | Short English summary; no newline and no invented component ID. |

Example final timeline line:

```text
[2026-02-26 06:04] [CRIT] ECCS8: runaway outlet temperature; reactor trip interlock.
```

The Hub expects `answer.logs` to be one string where timeline lines are separated by `\n`.

## Validation And Safety

Validation means: do not trust data until code has checked it.

This app validates several boundaries:

| Boundary | What must be checked |
|---|---|
| Input file | The file exists and is the expected plain-text log file. |
| Search result | Results are bounded and include source line numbers. |
| Model output | JSON parses, required fields exist, labels are allowed, and `source_line` maps to a real candidate. |
| Timeline | One event per line, required timestamp and component are present, token limit is respected. |
| Hub request | API key is read from environment, not stored in reports, and request count is capped. |

Log lines are treated as untrusted data. If a log line contains something that looks like an instruction, it is still just log content.

Hub feedback is also treated as data. It can guide the next search, but it cannot change permissions, endpoint rules, or validation rules.

## Token Budget

The Hub limit is `1500` tokens for the condensed logs.

The app should aim lower, around `1200-1300` tokens, to leave room for tokenizer differences.

When the answer is too long:

1. keep `direct_failure_chain` events,
2. shorten summaries,
3. remove weaker `supporting_context` events,
4. count tokens again,
5. submit only after the local check passes.

## Configuration

Required environment variables:

| Name | Purpose |
|---|---|
| `AI_DEVS_API_KEY` | Hub authentication. |
| `HUB_VERIFY_URL` | Hub verification endpoint. |
| `OPENAI_API_KEY` | OpenAI API access for local model calls. |

Optional environment variables:

| Name | Purpose |
|---|---|
| `L8_FAILURE_CLASSIFIER_MODEL` | Model used for candidate classification. |
| `L8_FAILURE_REPAIR_MODEL` | Model used for repair from Hub feedback. |
| `L8_FAILURE_MAX_VERIFY_REQUESTS` | Maximum Hub verification calls per run. |
| `L8_FAILURE_MAX_MODEL_REQUESTS` | Maximum local model calls per run. |
| `L8_FAILURE_BATCH_SIZE` | Number of candidates sent to one model classification request. |
| `L8_FAILURE_TOKEN_LIMIT` | Hard answer token limit, default `1500`. |
| `L8_FAILURE_TARGET_TOKEN_LIMIT` | Preferred answer target below the hard limit. |

Secrets must stay in `.env` or another approved secret store. Do not write real API keys, tokens, private URLs, or private endpoint values to source files, Markdown files, reports, logs, cache files, or commit messages.

## Data Paths

Runtime files live under `data/L8_failure/`, not inside `src/apps/L8_failure/`.

| Path | Purpose |
|---|---|
| `data/L8_failure/input/logs.txt` | Full source log file for the exercise. |
| `data/L8_failure/output/profile.json` | Basic file profile and parser observations. |
| `data/L8_failure/output/candidates.jsonl` | Candidate events selected before model classification. |
| `data/L8_failure/output/classified_events.jsonl` | Validated model classification results. |
| `data/L8_failure/output/condensed_logs.txt` | Current condensed timeline. |
| `data/L8_failure/output/run_report.json` | Run report with masked secrets. |
| `data/L8_failure/logs/` | Optional local debug logs without secrets. |
| `data/L8_failure/cache/` | Optional cache for model batch results. |

## Main Modules

Planned source files:

| Module | Responsibility |
|---|---|
| `main.py` | CLI entrypoint and workflow orchestration. |
| `config.py` | Environment loading and configuration validation. |
| `log_loader.py` | Read and profile the source log file. |
| `log_search.py` | Bounded searches over the source log. |
| `candidate_extractor.py` | Deterministic severity and keyword filtering. |
| `models.py` | Typed data structures for candidates, classified events, and reports. |
| `llm_classifier.py` | Batched model calls and structured output parsing. |
| `timeline_builder.py` | Ranking, compression, and timeline formatting. |
| `token_budget.py` | Token counting or conservative token estimation. |
| `hub_client.py` | Hub verification requests with masked report data. |
| `report_writer.py` | Runtime report and artifact writing under `data/L8_failure/`. |

Each class, function, and method should include a short `#` purpose comment.

## Run

Planned command:

```powershell
.\venv\Scripts\python.exe -m src.apps.L8_failure.main
```

Diagnostic commands:

```powershell
.\venv\Scripts\python.exe -m src.apps.L8_failure.main --profile-only
.\venv\Scripts\python.exe -m src.apps.L8_failure.main --no-verify
```

Use `--profile-only` for local checks that should not touch external services.
Use `--no-verify` when model classification should run but Hub submission should wait.

On this machine, OpenAI and Hub calls may require the local CA bundle described in `TROUBLESHOOTING.md`:

```powershell
$bundle=(Resolve-Path .\data\L6_categorize\cache\requests_ca_bundle.pem).Path
$env:REQUESTS_CA_BUNDLE=$bundle
$env:SSL_CERT_FILE=$bundle
.\venv\Scripts\python.exe -m src.apps.L8_failure.main
```

## Verification

Local checks should confirm that:

1. missing configuration fails with a clear error,
2. `data/L8_failure/input/logs.txt` can be read and profiled,
3. log search returns bounded results with source line numbers,
4. candidate extraction finds traceable events,
5. malformed model JSON is rejected,
6. invalid labels are rejected,
7. the final timeline has one event per line,
8. oversized answers are blocked before Hub submission,
9. reports mask `apikey`,
10. verification stops after the configured request limit,
11. Hub feedback triggers targeted searches instead of a blind full rerun.

Hub verification should happen only after local validation passes.

Successful verification:

| Date | Result | Notes |
|---|---|---|
| 2026-05-28 | PASS | Hub returned the final flag after one verification request. |

## Assumptions And Risks

Assumptions:

- the log format is regular enough to parse timestamps, levels, and component IDs,
- important failure evidence appears in or near higher-severity events,
- Hub feedback is specific enough to guide repair,
- a small number of verification attempts is enough for the exercise.

Risks and mitigations:

| Risk | Mitigation |
|---|---|
| Early low-severity events may matter. | Keep a keyword-based search path for lower-severity context. |
| Keyword filtering may collect noise. | Use model classification and relevance labels after filtering. |
| The model may over-compress a technical detail. | Keep source lines and validate against original candidates. |
| Token estimates may differ from the Hub tokenizer. | Target `1200-1300` tokens instead of the full `1500`. |
| Hub feedback may name a component missing from candidates. | Run targeted `search_logs` queries from feedback. |

## LLM Design Reviews

Review mode: `non-production`.

The MVP1 design was checked with `_agent/instructions/llm_design_checklist.md`. The review passed because the app has a clear goal, small workflow steps, limited model context, structured model output, validation before downstream use, and guarded external verification.

| Date | Scope | Checklist | Result | Approved Implementation Boundary |
|---|---|---|---|---|
| 2026-05-28 | MVP1: local controlled failure-log condensation workflow | `_agent/instructions/llm_design_checklist.md` | PASS | Implement MVP1 only: fixed local input file, bounded log search, deterministic candidate extraction, schema-validated model classification, token-limited timeline generation, and capped Hub verification. |

Material changes to model behavior, tool exposure, Function Calling, subagents, validation rules, or verification flow require a new scoped checklist review before implementation.

## Reference Alignment

This design follows:

- `_agent/references/exercises/L8_exercise.md`,
- `_agent/references/L1_task_decomposition_and_pipeline_design.md`,
- `_agent/references/L1_prompt_design.md`,
- `_agent/references/L1_structured_outputs_and_validation.md`,
- `_agent/references/L1_model_selection.md`,
- `_agent/references/L2_security_permissions_and_exposure.md`,
- `_agent/references/L2_prompt_injection_and_validation.md`,
- `_agent/references/L2_workflow_orchestration_and_reflection.md`,
- `_agent/references/L2_execution_guards_and_instruction_data_separation.md`,
- `_agent/references/L7_hybrid_retrieval_and_rag_effectiveness.md`,
- `_agent/references/L8_deep_research_and_deep_action_workflows.md`.

The main design choice is simple: use an agent-like loop with clear tools, but keep control in code.

## What This Task Should Teach

This task is mainly about building a useful AI workflow around a large input file.
The important lesson is not "ask the biggest model to summarize everything." The important lesson is to decide what code should do first, what the model should do later, and where validation must stop bad output from moving forward.

Key learning points:

| Lesson | What it means in this app |
|---|---|
| Do not put large raw data into the model by default. | The source log has about `82703` estimated tokens, so Python profiles, searches, filters, and deduplicates it before any model call. |
| Use the model for judgment, not for basic plumbing. | The model decides relevance and writes short summaries. Python reads files, checks token limits, formats lines, and sends requests. |
| Make model output boring to parse. | The classifier returns structured JSON, not free-form text. That makes validation possible. |
| Validate every important boundary. | The app validates the input file, model JSON, final timeline format, token budget, and Hub request count. |
| Keep tools narrow. | `search_logs` returns bounded source-line results instead of handing the full file to the model. |
| Treat external text as data, not instructions. | Log lines and Hub feedback can guide search and repair, but they cannot change permissions or workflow rules. |
| Iterate from feedback, but with guards. | The workflow can repair from Hub feedback, but verification and model calls are capped. |
| Reduce repeated evidence before using the model. | The logs contain many repeated messages, so candidate extraction keeps the first observed line for each event type. |

The practical pattern to remember:

```text
large raw data -> deterministic filtering -> small model task -> schema validation -> deterministic output -> guarded external action
```

That pattern is reusable. It applies not only to incident logs, but also to long documents, large email threads, support tickets, monitoring alerts, and other AI workflows where the raw input is too big or too noisy for one prompt.
