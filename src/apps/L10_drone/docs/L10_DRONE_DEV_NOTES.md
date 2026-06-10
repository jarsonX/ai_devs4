# L10 Drone DEV NOTES

## Table Of Contents

- [Implementation Plan](#implementation-plan)
- [Design Decisions](#design-decisions)
- [Debugging Notes](#debugging-notes)
- [Logging Plan](#logging-plan)
- [Validation Plan](#validation-plan)
- [Verification Plan](#verification-plan)
- [Open Questions](#open-questions)
- [Future Work](#future-work)

## Implementation Plan

This plan is the working reference for implementing `L10_drone`. Keep it updated when steps are completed or deliberately changed.

### Step 0: Design Gate

Status: completed on 2026-06-10.

Goal: approve the LLM-assisted workflow before source implementation.

Tasks:

1. Review the README design with `_agent/instructions/llm_design_checklist.md`.
2. Record the passed review in `L10_DRONE_README.md`.
3. Do not create source modules, prompts, model-call scaffolding, or runtime workflow code before the review passes.

Verification:

- README `LLM Usage And Reviews` has `Design review` marked `Passed`.

Review result:

| Checklist Area | Result | Evidence |
| --- | --- | --- |
| Scope and workflow | YES | The goal is to produce Hub `answer.instructions` for task `drone`; deterministic code owns config, validation, logging, and Hub calls; the model only plans and repairs instructions. |
| Model and prompt plan | YES | One `Drone Mission Planner` step uses `gpt-5-mini` with compact local API docs, mission facts, latest feedback, and structured JSON output. |
| Context and tools | YES | The model receives no API keys and no full run history; repair context is limited to previous instructions, latest Hub feedback, attempt count, and compact docs. |
| Production lifecycle items | N/A | MVP1 is a local course exercise, not a deployed user-facing workflow. JSONL logs provide sufficient local traceability. |
| Validation and safety | YES | The design validates model output before Hub submission, masks secrets in logs, enforces attempt limits, and keeps authorization outside the model. |

### Step 1: Inspect Local Inputs

Status: completed on 2026-06-10.

Goal: confirm exact local artifact names and shapes.

Tasks:

1. List files in `data/L10_drone/input/`.
2. Confirm the map file exists as `drone.png` or update docs if the name differs.
3. Confirm the drone API documentation HTML file name.
4. Inspect only the local HTML API documentation needed for the instruction grammar.

Verification:

- Known input paths are documented in README.
- No external download is needed.

### Step 2: Create Minimal Package Skeleton

Status: completed on 2026-06-10.

Goal: create only the modules needed for the bounded workflow.

Planned files:

| File | Purpose |
| --- | --- |
| `src/apps/L10_drone/__init__.py` | Mark the app as a package. |
| `src/apps/L10_drone/config.py` | Environment loading, paths, constants, and guard limits. |
| `src/apps/L10_drone/api_docs.py` | Local HTML loading and compact documentation extraction. |
| `src/apps/L10_drone/planner.py` | LLM planner call and structured output parsing. |
| `src/apps/L10_drone/validation.py` | Instruction plan validation. |
| `src/apps/L10_drone/hub_client.py` | Hub `/verify` request handling. |
| `src/apps/L10_drone/run_log.py` | JSONL event logging and secret masking. |
| `src/apps/L10_drone/workflow.py` | Attempt and repair loop. |
| `src/apps/L10_drone/main.py` | CLI entrypoint. |

Verification:

```powershell
.\venv\Scripts\python.exe -c "import src.apps.L10_drone; print('import ok')"
```

### Step 3: Implement Configuration

Status: completed on 2026-06-10.

Goal: centralize paths, secrets, constants, and limits.

Required environment variables:

- `OPENAI_API_KEY`
- `AI_DEVS_API_KEY`
- `HUB_VERIFY_URL`

Regular constants:

- `TASK_NAME = "drone"`
- `POWER_PLANT_CODE = "PWR6132PL"`
- `DAM_COLUMN = 2`
- `DAM_ROW = 4`
- `MAX_VERIFY_ATTEMPTS = 5`
- `PLANNER_MODEL = "gpt-5-mini"`

Verification:

- config load fails clearly when required secrets are missing,
- config exposes repository-relative paths for logs and input artifacts.

### Step 4: Implement JSONL Logging

Status: completed on 2026-06-10.

Goal: make every important decision visible before building the full loop.

Tasks:

1. Create a timestamped log file in `data/L10_drone/logs/`.
2. Append one JSON object per event.
3. Mask API keys and auth-bearing URLs before writing events.
4. Keep logs readable enough for learning, not optimized for production observability.

Verification:

- unit test or small local check confirms events append correctly,
- masked request payload does not contain raw `AI_DEVS_API_KEY` or `OPENAI_API_KEY`.

### Step 5: Implement API Documentation Loading

Status: completed on 2026-06-10.

Goal: give the model a compact and relevant API documentation context.

Tasks:

1. Load local HTML from `data/L10_drone/input/`.
2. Convert it to plain text using a structured parser where practical.
3. Keep function names, parameters, examples, and warnings.
4. Avoid passing irrelevant page noise to the model.

Verification:

- local check prints or saves a compact documentation excerpt for inspection,
- no external network call is made.

### Step 6: Implement Planner Structured Output

Status: completed on 2026-06-10.

Goal: get model output that code can safely consume.

Planned planner output:

```json
{
  "instructions": ["instruction1", "instruction2"],
  "change_summary": "Short explanation.",
  "uses_reset": false
}
```

Planner inputs:

- compact API docs,
- task name,
- power plant code,
- dam sector column and row,
- previous instructions for repair attempts,
- latest Hub feedback for repair attempts,
- attempt number and max attempts.

Verification:

- fake model response parses correctly,
- malformed response produces a validation error instead of a Hub request.

### Step 7: Implement Instruction Validation

Status: completed on 2026-06-10.

Goal: prevent obviously bad model output from reaching the Hub.

Checks:

- `instructions` exists,
- `instructions` is a non-empty list,
- every instruction is a non-empty string,
- instruction count stays within a small limit,
- `change_summary` is present and short,
- `uses_reset` is boolean,
- no secret-like values appear in instructions.

Verification:

- tests cover valid plan, empty plan, non-string instruction, overlong plan, and secret-like value.

### Step 8: Implement Hub Client

Status: completed on 2026-06-10.

Goal: send the exact Hub payload and preserve feedback.

Payload shape:

```json
{
  "apikey": "from AI_DEVS_API_KEY",
  "task": "drone",
  "answer": {
    "instructions": ["..."]
  }
}
```

Tasks:

1. Send POST request to `HUB_VERIFY_URL`.
2. Return status code and parsed response body where possible.
3. Preserve raw text when JSON parsing fails.
4. Provide a masked request copy for logging.

Verification:

- fake Hub client can return success, error, invalid JSON, and flag-like payloads.

### Step 9: Implement Bounded Workflow

Status: completed on 2026-06-10.

Goal: connect planner, validation, Hub client, and logs.

Loop:

1. Log `run_started`.
2. Ask planner for initial instructions.
3. Validate plan.
4. Log `agent_plan` and `validation_result`.
5. Send Hub request.
6. Log `hub_request` and `hub_response`.
7. Stop on flag.
8. Stop on validation failure.
9. Stop on max attempts.
10. Stop if repair repeats the same instruction list.
11. Otherwise pass Hub feedback into the next planner call.

Verification:

- fake planner plus fake Hub tests cover solved first attempt, solved after repair, validation failure, repeated no-change repair, and max-attempt blocked status.

### Step 10: Real Run

Status: completed on 2026-06-10.

Goal: run the actual task after local verification passes.

Tasks:

1. Confirm logs directory is empty enough to identify the new run.
2. Run the entrypoint:

```powershell
.\venv\Scripts\python.exe -m src.apps.L10_drone.main
```

3. Inspect the JSONL log after the run.
4. If Hub feedback rejects the attempt, use the log to decide whether to adjust prompt, docs extraction, validation, or constants.

Verification:

- First real run stopped as `blocked` with a clear logged reason.
- Second real run returned a Hub success flag on attempt `1`; the flag value is intentionally omitted from documentation.
- Successful run log: `data/L10_drone/logs/run_20260610_184104.jsonl`.

### Step 11: Post-Implementation Review

Status: completed on 2026-06-10.

Goal: record what we learned and close the LLM workflow properly.

Tasks:

1. Run `_agent/instructions/llm_optimization_checklist.md`.
2. Record the result in README.
3. Update `What This Task Should Teach`.
4. Capture any debugging lessons here in DEV_NOTES.

Verification:

- README reflects current implementation and review status.

Review result:

| Checklist Area | Result | Evidence |
| --- | --- | --- |
| Task design | YES | The app solves a concrete Hub payload task and splits local docs loading, planning, validation, Hub submission, and logging into separate modules. |
| Model usage | YES | The only LLM step is `Drone Mission Planner`; deterministic code owns mission constants, guards, validation, and Hub calls. |
| Prompt quality | YES | The prompt includes compact API docs, mission facts, latest feedback, output schema, and explicit constraints against invented destination IDs. |
| Context control | YES | The model receives compact local docs, previous instructions, latest Hub feedback, and attempt metadata only. |
| Tool and workflow efficiency | YES | The successful run used one model call and one Hub call after prompt and validation tightening. |
| Output stability | YES | Planner output uses a JSON schema and is validated before any Hub request. |
| Cost and latency | YES | Attempts are capped at `MAX_VERIFY_ATTEMPTS = 5`; JSONL logs show each model and Hub step. |
| Production runtime items | N/A | MVP1 is a local course exercise, not a deployed production workflow. |
| Safety and control | YES | API keys are never sent to the model, logs mask secrets and flag values, and backend validation blocks unsafe or invented mission values. |
| Review validation | YES | No blocking optimization changes remain; only optional prompt cleanup or deterministic fallback could be added later. |

## Design Decisions

- Do not use vision in MVP1. The dam sector is manually confirmed as column `2`, row `4`, and adding a vision step would complicate the app without helping the current learning goal.
- Do not download task artifacts. The app starts from local files already saved under `data/L10_drone/input/`.
- Use one model-assisted planner/repair step, not a multi-agent system.
- Keep authorization and Hub submission in deterministic code.
- Do not add a dry-run mode in MVP1. The initial implementation should keep one narrow execution path.
- Do not create a separate summary report. JSONL logs are the learning and debugging artifact.

## Debugging Notes

### First Real Run: Invented Destination Object IDs

Status: fixed in planner prompt and validation.

The first real run completed five guarded attempts and stopped as `blocked`. The JSONL log showed a useful failure pattern:

- attempts 1-3 used invented destination objects such as `DAM0001PL` and `DAM6132PL`,
- the Hub responded with `I don't know that location.`,
- attempt 4 used `setDestinationObject(PWR6132PL)` and reached new feedback: `If we send the drone without a return instruction, we will lose it forever.`,
- attempt 5 added `set(return)` but regressed to `DAM6132PL`.

Root cause:

- The prompt told the model to target the dam, but did not make the distinction strong enough between the known map object `PWR6132PL` and the dam sector `set(2,4)`.
- Validation checked shape and secrets, but did not enforce mission-specific facts.

Fix:

- Strengthened the planner prompt: never invent destination object IDs; use `setDestinationObject(PWR6132PL)` and `set(2,4)`.
- Added mission-specific validation for `setDestinationObject(PWR6132PL)`, `set(2,4)`, `set(destroy)`, `set(return)`, and `flyToLocation`.
- Added tests for invented destination objects and missing mission requirements.

Verification:

```powershell
.\venv\Scripts\python.exe -m unittest tests.L10_drone.test_workflow
```

Result: `12` tests passed.

### Second Real Run: Solved

Status: completed.

After the prompt and validation fix, the second real run solved the task on the first attempt.

Successful instructions:

```text
setDestinationObject(PWR6132PL)
set(2,4)
set(10m)
set(engineON)
set(100%)
set(destroy)
set(return)
flyToLocation
```

Hub response:

- success; flag value intentionally omitted from documentation.

Log:

```text
data/L10_drone/logs/run_20260610_184104.jsonl
```

Follow-up fix:

- The successful run originally exposed the flag value in README and DEV_NOTES.
- Logging was changed so Hub feedback stores `flag_found` and redacted response text instead of the raw flag value.
- Documentation must not include raw flag values.

### Documentation Secret Handling Incident

Status: fixed.

What happened:

- The successful Hub response included a task flag.
- That value was copied into README and DEV_NOTES while recording the successful run.
- The runtime logger also stored the raw Hub response and terminal flag value.

Root cause:

- The implementation treated Hub feedback as a local learning artifact, but did not distinguish between ordinary feedback and secret-bearing verification outputs.
- The documentation update copied the successful result too literally instead of recording only the non-secret success state.
- The logger preserved raw Hub response text for debugging, which is useful for errors but unsafe for secret-bearing success payloads.

Fix:

- README and DEV_NOTES now omit the flag value.
- Existing L10 drone JSONL logs were redacted.
- `hub_response_for_log` now stores redacted Hub response text plus `flag_found`.
- `run_finished` now stores `flag_found`, not the flag value.
- Tests now assert that flag-like values do not appear in workflow logs.

Lesson:

- Verification outputs should be treated as secret-bearing by default when they prove task completion.
- Human-facing documentation should record outcome, status, and non-secret evidence only.
- Logs may preserve enough context to debug behavior, but secret-like success markers must be redacted before storage.

## Logging Plan

The log should be detailed enough to explain the run after the fact.

Minimum event fields:

| Field | Purpose |
| --- | --- |
| `timestamp` | When the event happened. |
| `run_id` | Timestamp-based identifier shared by all events in one run. |
| `attempt` | Attempt number, or `null` for run-level events. |
| `event` | Event type such as `agent_plan` or `hub_response`. |
| `data` | Event-specific payload. |

Important event payloads:

| Event | Data |
| --- | --- |
| `run_started` | model name, max attempts, known sector, input file paths |
| `agent_plan` | instructions, change summary, uses reset |
| `validation_result` | passed flag and issue list |
| `hub_request` | masked Hub payload |
| `hub_response` | status code, parsed body or raw body |
| `run_finished` | terminal status and reason |

## Validation Plan

Treat model output as untrusted until validation passes.

Initial validation is intentionally simple. Do not overbuild this before seeing the actual drone instruction grammar.

Required checks:

- structured planner response parses,
- instructions list is present,
- instructions list is non-empty,
- each instruction is a string,
- no instruction contains a raw secret value,
- planner explanation fields are present,
- repair attempts do not repeat the exact previous instruction list.

Possible later checks after reading the API docs:

- instruction names belong to the documented grammar,
- required parameters are present,
- `hardReset` is only used after a clear recovery reason,
- target sector coordinates appear in the expected instruction format.

## Verification Plan

Preferred verification order:

1. Import check.
2. Unit tests for logging and validation.
3. Fake planner and fake Hub workflow tests.
4. Real model call only after fake workflow passes.
5. Real Hub call only after planner output and logs look reasonable.

Do not skip fake workflow tests. They are where loop bugs show up without spending API calls or mutating task state.

## Open Questions

- What is the exact local HTML file name under `data/L10_drone/input/`?
- Which planner model should MVP1 use?
- Does the drone API instruction grammar allow direct sector targeting, movement commands, or both?
- How should the app detect a flag robustly across possible Hub response shapes?
- Should `hardReset` be blocked unless the Hub feedback explicitly suggests bad accumulated state?

## Future Work

- Add a vision validation step only if the manually confirmed sector becomes doubtful.
- Add stricter instruction grammar validation after the API docs are understood.
- Add a compact human-readable log viewer only if JSONL becomes annoying during debugging.
- Add a dry-run mode only if repeated local testing becomes painful without it.
