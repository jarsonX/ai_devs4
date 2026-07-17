# L12 Firmware Development Notes

## Table Of Contents

- [Current Status](#current-status)
- [API Exploration](#api-exploration)
- [Useful References](#useful-references)
- [Design Decisions](#design-decisions)
- [LLM Design Review](#llm-design-review)
- [LLM Optimization Review](#llm-optimization-review)
- [Implementation Notes](#implementation-notes)
- [Implementation Plan](#implementation-plan)

## Current Status

Steps 1-10 are complete. The app is now in solved workbench state.

What changed between the failed and successful live runs:

- the planner now keeps a projected post-edit `settings.ini` state for planning only;
- the guard still requires a real reread before any additional edit;
- the final runtime limits are now 30 model calls, 20 shell calls, and 150,000 total reported tokens;
- the successful live run on 2026-06-13 solved the task in 13 model calls and 13 tool calls.

## API Exploration

The approved `help` request succeeded. The shell API exposes a small custom command set, including `ls`, `cat`, `cd`, `pwd`, `editline`, `reboot`, and direct executable paths.

Important findings:

- commands are stateful and sequential;
- file editing uses `editline`, not a normal Linux editor;
- `find` searches the whole virtual filesystem and is unsafe for this task;
- `reboot` restores the VM state;
- the agent must inspect `.gitignore` before touching files in a directory.

## Useful References

Selected from `_agent/references/INDEX.md`:

| Reference | Use |
| --- | --- |
| `L2_execution_guards_and_instruction_data_separation.md` | Enforce permissions outside the model. |
| `L2_security_permissions_and_exposure.md` | Keep filesystem and command access at least privilege. |
| `L3_api_constraint_audit_and_tool_wrapping.md` | Wrap the unusual shell API safely. |
| `L3_safe_write_and_native_mcp_integration.md` | Require a fresh read before editing mutable configuration. |
| `L3_tool_family_and_response_contracts.md` | Keep two clear tools with actionable errors. |
| `L5_performance_cost_and_rate_limits.md` | Bound model calls, tokens, retries, and API calls. |
| `L6_agentic_rag_and_context_gathering.md` | Plan observation-driven exploration. |
| `L7_external_context_safety_and_rag_risks.md` | Treat VM content as untrusted data. |
| `L12_ai_scope_and_automation_boundaries.md` | Keep the agent narrow and deterministic where possible. |

## Design Decisions

- Use one agent and two tools: `run_shell_command` and `submit_answer`.
- Use `gpt-5.5` with `medium` reasoning and a short hard-bounded loop.
- Disable parallel tool calls.
- Validate commands and submissions in code.
- Allow one firmware password argument only when the exact safe literal appears at least twice as the sole `cooler.bin` argument in parsed command history.
- Use final hard limits of 30 model calls and 20 shell calls because the live troubleshooting path showed that 18/17 and 22/19 left too little recovery margin for a stateful tool loop.
- Allow 2,000 generated tokens per model call while using a 150,000 cumulative token cap so the higher turn budget remains internally consistent.
- Stop with a dedicated incomplete-response reason when OpenAI reports `status=incomplete`.
- Include verified operational facts in the prompt without including passwords, confirmation codes, FLAGS, or raw course responses.
- Build deterministic planner state from the current `settings.ini` snapshot, firmware directory listing, and parsed command history.
- Keep a projected post-edit `settings.ini` snapshot for planner decisions only; the guard still requires a fresh real reread before any further edit.
- Allow `rm` only for `/opt/firmware/cooler/cooler-is-blocked.lock` after that file is explicitly observed in the latest cooler directory listing.
- Require exactly one grounded password argument for `cooler.bin`; prompt guidance alone is not enough for that boundary.
- Test with fake clients before any real OpenAI or course API run.

## LLM Design Review

Review date: 2026-06-13. Mode: non-production. Scope: deterministic repair planner with projected post-edit settings state and final guard-limit increase. Result: PASS.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Clear goal and output | YES | Produce one grounded `ECCS-...` code and submit it for `firmware`. |
| Small workflow steps | YES | Exploration, configuration repair, binary execution, and submission happen as separate tool turns. |
| Deterministic stable logic | YES | Code owns validation, permissions, counters, token limits, and submission eligibility. |
| Clear step purpose | YES | Each model turn selects one next shell action or the final submission. |
| LLM use justified | YES | The shell path is unknown and requires adaptive reasoning from unexpected observations. |
| Model matches difficulty | YES | `gpt-5.5` with `medium` reasoning is chosen for adaptive investigation. |
| Focused prompts | YES | The prompt stays short and points the model at deterministic planner state instead of asking it to invent a configuration hypothesis. |
| Input and output tokens limited | YES | The revised caps are 30 model calls, 20 shell calls, 2,000 output tokens per call, and 150,000 total reported tokens. |
| Structured consumed output | YES | Both tools will use strict JSON schemas and deterministic argument validation. |
| Current-step context only | YES | Sequential tool results provide only the observation needed for the next decision. |
| Limited tool exposure | YES | The model receives only `run_shell_command` and `submit_answer`. |
| No irrelevant history | YES | Large raw logs and runtime reports stay outside model context. |
| Batching, caching, or persistence | N/A | The VM is stateful and actions cannot be safely batched or replayed; one final runtime report is sufficient for this short workbench. |
| Production progress mechanism | N/A | Non-production local CLI workflow. |
| Production waiting visibility | N/A | Non-production local CLI workflow. |
| Production disconnect survival | N/A | Non-production local CLI workflow. |
| Production state persistence | N/A | Non-production local CLI workflow. |
| Production pause and resume | N/A | Non-production local CLI workflow. |
| Production user interaction | N/A | Non-production local CLI workflow. |
| Production UI separation | N/A | No UI is planned. |
| Production event orchestration | N/A | A bounded synchronous CLI is appropriate for this one-off task. |
| Validate model output | YES | Commands, planner-produced edit lists, projected post-edit planner state, narrow lock-file removal, password provenance, and confirmation codes are validated before use. |
| Treat output as untrusted | YES | No model-selected command bypasses the deterministic command guard. |
| Permissions outside model | YES | Code parses command history, computes edits deterministically, keeps projected settings only for planner state, and authorizes deletion only for the exact observed lock file. |
| Missing inputs handled | YES | Missing secrets or endpoints stop startup with a clear error. |

Approved implementation boundary: keep the same two-tool design, add projected post-edit planner state without relaxing reread-before-edit enforcement, permit deletion only for the exact observed lock file, and raise limits only to 30 model calls, 20 shell calls, and 150,000 total reported tokens. Any broader change requires a new review.

## LLM Optimization Review

Review date: 2026-06-13. Mode: non-production. Scope: full bounded workbench workflow after post-edit planner repair and final guard-limit increase. Result: PASS.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Concrete task and output | YES | The workflow produces one grounded `ECCS-...` confirmation and optional Hub acceptance. |
| Appropriate decomposition | YES | Each model turn chooses one shell action or submission. |
| Deterministic stable logic | YES | Guards, state updates, schemas, limits, and authorization live in code. |
| No unrelated model jobs | YES | The model only plans the next investigation action. |
| Simple workflow | YES | Model, one tool, validated result, repeat, then stop. |
| Model use justified | YES | The unknown VM state requires adaptive reasoning. |
| Strong model used intentionally | YES | `gpt-5.5` is limited to the adaptive planning loop. |
| No avoidable model calls | YES | Parsing, validation, permissions, and reporting are deterministic. |
| Repeated calls justified | YES | Every next action depends on the previous shell observation. |
| Clear prompt | YES | `SYSTEM_PROMPT` states the goal, constraints, tools, and stop behavior. |
| Focused prompt context | YES | Initial context contains only task commands, limits, and run mode. |
| No irrelevant prompt history | YES | Only bounded tool outputs are chained through `previous_response_id`. |
| Ambiguity handling | N/A | The course task and expected output are fixed. |
| Current-step context | YES | Tool results contain the latest observation and compact guard state. |
| Old-history control | N/A | The loop is capped at 30 turns and prior observations remain relevant to the stateful VM. |
| Filtered tool results | YES | Model-facing API results are capped at 6,000 serialized characters. |
| Context treated as costly | YES | Prompt, command, output, turn, and total-token limits are explicit. |
| Limited tool list | YES | Non-submit mode exposes one tool; submit mode exposes two. |
| High-value tool calls | YES | Prompt instructs targeted sequential exploration and the guard blocks broad search. |
| Batching | N/A | Stateful shell actions must remain sequential. |
| External-call caching | N/A | VM freshness matters; replaying cached shell results would be unsafe. |
| No removable workflow step | YES | Every step plans, validates, executes, records, or terminates. |
| Structured model output | YES | All consumed output is strict Function Calling JSON. |
| Schemas defined first | YES | Pydantic schemas generate strict OpenAI tool definitions. |
| Output validation | YES | Pydantic and deterministic guards validate before execution. |
| Model output untrusted | YES | No command or submission bypasses backend checks. |
| LLM calls minimized | YES | Hard cap is 30, justified by the observed live troubleshooting path and still small enough for one bounded workbench run; the successful run used only 13 calls. |
| Tool calls minimized | YES | One tool per turn, shell cap 20, Hub cap 1, and the successful run used 13 tool calls. |
| Large prompts avoided | YES | One short system prompt and compact initial state are used. |
| Output length controlled | YES | Generated reasoning and visible output are capped at 2,000 tokens per call, with a separate 150,000 cumulative guard. |
| Usage measurable | YES | Reports record model calls, tool calls, total tokens, API histories, and failures. |
| Expensive steps visible | YES | Runtime reports separate model counters, shell history, and Hub history. |
| Production progress | N/A | Local non-production CLI. |
| Production waiting visibility | N/A | Local non-production CLI. |
| Production partial artifacts | N/A | Local non-production CLI writes one final runtime report. |
| Production disconnect survival | N/A | No persistent service or browser session. |
| Production task persistence | N/A | One short local run; final state is persisted for inspection. |
| Production pause and resume | N/A | Not required for the bounded workbench. |
| Production interaction | N/A | No interactive UI. |
| Production UI separation | N/A | No UI. |
| Production event orchestration | N/A | Synchronous execution is appropriate for this bounded exercise. |
| Model does not authorize | YES | `guards.py` and request guards own authorization. |
| Risky actions backend-protected | YES | Paths, writes, execution, submission provenance, and budgets are checked in code. |
| External context separated | YES | VM responses return as tool data and cannot redefine the system prompt. |
| Missing inputs stop safely | YES | Required environment values fail during config loading. |
| No replaceable LLM call | YES | The remaining model loop is the adaptive planning component. |
| No removable workflow step | YES | Removing validation, state updates, or reports would reduce safety or reliability. |
| No removable context block | YES | Prompt rules and compact current observations are required for safe planning. |
| Maintainable structure | YES | Config, clients, guards, tools, agent, reporting, and CLI have separate responsibilities. |
| Production multi-task lifecycle | N/A | Local non-production CLI. |

Follow-up classification: implementation complete, locally verified, and live verified. Remaining follow-up is optional cleanup only.

## Implementation Notes

- Shell and Hub clients use separate request guards.
- Request slots are consumed before network activity, including timed-out attempts.
- Timeouts, transport failures, invalid JSON, `403`, `429`, `503`, and other HTTP errors return structured recovery information.
- The clients preserve application payloads without guessing the meaning of their `code` field because the shell API uses non-zero codes for successful responses.
- Relative paths require a known `pwd`, and deeper directories require sequential parent listings.
- A listed directory containing `.gitignore` is frozen until its rules are loaded.
- Only `settings.ini` is writable, and every edit requires a fresh file snapshot with an existing line number.
- Only the exact firmware binary can execute; it requires exactly one argument, and that argument must appear at least twice as the sole argument in parsed command history.
- `repair_planner.py` converts observed settings, directory state, grounded history, and projected post-edit settings state into deterministic phases: inspect, remove lock, refresh settings, apply repairs, or execute binary.
- Lock-file deletion is authorized only for the exact observed `/opt/firmware/cooler/cooler-is-blocked.lock` path and updates remembered directory state immediately after success.
- Hub submission requires an exact 40-character `ECCS-...` code observed in shell output.
- Tool schemas use strict required-only objects with additional fields rejected.
- The model is forced to request exactly one tool per turn with parallel calls disabled.
- The loop stops on Hub acceptance, terminal tool failure, missing usage, incomplete provider response, model-call limit, or cumulative token limit.
- Full shell responses, confirmation codes, Hub feedback, and Hub FLAGS are preserved in ignored runtime reports under `data/L12_firmware/output/`.
- API keys remain masked in runtime request records.
- CLI mode is explicit: `--check-config` stays local, `--live` enables OpenAI and shell calls, and `--submit` additionally enables one Hub request.
- On this machine, live TLS requests may require setting `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` to the repository CA bundle documented in `TROUBLESHOOTING.md`.
- Integration tests cover settings snapshot invalidation, reread-before-edit, reboot state reset, model and token limits, HTTP limits, and successful fake Hub completion.
- Non-submit mode hides `submit_answer` and stops with status `ready` as soon as an `ECCS-...` code is observed.
- The successful live path was: inspect `/home/operator/.bash_history`, inspect `/opt/firmware/cooler`, read `.gitignore`, read `settings.ini`, run `cooler.bin admin1`, observe the confirmation, and submit once to the Hub.

## Implementation Plan

1. [Completed] Run the LLM design checklist for the bounded MVP and record the result in README.
2. [Completed] Add configuration, runtime paths, and hard model, token, shell, and submission limits.
3. [Completed] Implement shell and Hub HTTP clients with structured errors and request counters.
4. [Completed] Implement deterministic command, path, `.gitignore`, write, execution, and confirmation-code guards.
5. [Completed] Define strict schemas for `run_shell_command` and `submit_answer`.
6. [Completed] Implement the sequential Responses API loop with one tool call per turn.
7. [Completed] Add a CLI that requires explicit flags for live execution and Hub submission.
8. [Completed] Test guards, clients, tool dispatch, loop limits, and successful completion with fake clients.
9. [Completed] Run local tests and the non-production LLM optimization review.
10. [Completed] Perform a separately approved live run and store course responses only under ignored runtime data.
