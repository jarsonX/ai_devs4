# L03_proxy

L03_proxy is an educational app for the AI_devs course.
Its goal is to expose a public HTTP endpoint that behaves like a conversation-aware proxy assistant for a logistics operator.

The task scenario is simulated by the course.
There is no real-world interception or manipulation involved outside the exercise itself.

## Table Of Contents

- [Purpose](#purpose)
- [Current Business Goal](#current-business-goal)
- [Role Of The LLM](#role-of-the-llm)
- [Model Selection](#model-selection)
- [Expected HTTP Contract](#expected-http-contract)
- [External Package API](#external-package-api)
- [Workflow Stages](#workflow-stages)
- [Responsibility Split](#responsibility-split)
- [Planned Tools](#planned-tools)
- [Tool Exposure Strategy](#tool-exposure-strategy)
- [Planned Agent State](#planned-agent-state)
- [Stage Completion Rules](#stage-completion-rules)
- [Secret Redirect Rule](#secret-redirect-rule)
- [Planned Stage Flow](#planned-stage-flow)
- [Planned File Structure](#planned-file-structure)
- [File Responsibilities](#file-responsibilities)
- [Boundary Rules](#boundary-rules)
- [Planned Internal Contents](#planned-internal-contents)
- [Planned Functions And Contracts](#planned-functions-and-contracts)
- [Validation And Error Rules](#validation-and-error-rules)
- [Logging And Debugging Notes](#logging-and-debugging-notes)
- [Deployment Plan](#deployment-plan)
- [Hub Verification Submission](#hub-verification-submission)
- [Verification Plan](#verification-plan)
- [Assumptions](#assumptions)
- [Runtime Limits](#runtime-limits)
- [Status](#status)

## Purpose

The app is meant for learning:

- building a public HTTP endpoint,
- parsing JSON requests and returning JSON responses,
- keeping per-session conversation memory,
- integrating an LLM with tool calling,
- executing a bounded tool loop safely,
- connecting a conversational app to an external API,
- designing prompts that combine natural dialogue with task-specific hidden behavior.

## Current Business Goal

The app should:
1. receive operator messages in the expected HTTP JSON format,
2. maintain independent conversation history for each `sessionID`,
3. act like a natural human assistant in the conversation,
4. use package-related tools when the operator asks about shipment actions,
5. check package status through the external packages API,
6. redirect packages through the external packages API,
7. secretly override the redirect destination to `PWR6132PL` when the package concerns reactor core parts,
8. return a natural response that does not reveal the hidden redirect,
9. pass the redirect confirmation code back to the operator when applicable.

## Role Of The LLM

The LLM is not responsible for the whole application.
Its role should be limited to the conversational and decision-heavy parts of the workflow:

- understanding the operator message,
- using conversation history,
- deciding when to call tools,
- extracting package-related parameters from the conversation,
- producing natural operator-facing responses,
- following the hidden redirect rule for the reactor-related package case.

The model should not be responsible for:

- running the HTTP server,
- storing sessions,
- enforcing iteration limits,
- making raw HTTP calls directly,
- validating external API response structure,
- managing deployment or public exposure.

## Model Selection

The current MVP 1 model recommendation is:

- `gpt-5.4-mini`
  Default model for the bounded conversation plus tool-calling workflow.

The current MVP 1 reasoning recommendation is:

- `reasoning.effort = low`
  This should provide a good balance between quality, latency, and cost for a short-context, two-tool workflow.

If the model proves unreliable during real operator conversations, the next escalation path should be:

1. keep the same prompts and backend rules,
2. increase prompt clarity or state shaping if needed,
3. switch to a stronger model only if the smaller model still underperforms.

## Expected HTTP Contract

The endpoint is expected to receive:

```json
{
  "sessionID": "any-session-id",
  "msg": "Any operator message"
}
```

The endpoint is expected to return:

```json
{
  "msg": "Assistant response for the operator"
}
```

## External Package API

The external packages API is provided by the course organizer and is not exposed in the public repository.
The application should read its real address from configuration, for example from:

`L03_PROXY_API_URL`

It supports two actions:

- `check`
  Checks the current package status and location.
- `redirect`
  Redirects a package using `packageid`, `destination`, and the security `code`.

Important behavior:

- the security code is expected to appear during the conversation with the operator,
- a successful redirect returns a `confirmation` value,
- that confirmation must be passed back to the operator.

## Workflow Stages

The current agreed high-level plan is:

### 1. Intake

Goal:

- accept the HTTP request,
- validate the input shape,
- load or create session state for the provided `sessionID`.

### 2. Conversation And Tool Loop

Goal:

- send the system prompt, compact session state, and recent conversation window to the model,
- expose the available tools,
- execute tool calls when requested,
- repeat until the model returns a plain-text answer or the iteration limit is reached.

### 3. Response Finalization

Goal:

- persist the updated session history,
- return the final `msg` field to the caller.

## Responsibility Split

The current design direction keeps responsibilities narrow:

- The LLM should handle natural conversation, context use, tool selection, and response wording.
- Application code should handle HTTP input/output, session storage, tool execution, external API access, validation, logging, loop control, and backend enforcement of the hidden redirect rule.

## Planned Tools

The current task requires two tools:

- `check_package`
  Accepts `packageid` and checks package status.
- `redirect_package`
  Accepts `packageid`, `destination`, and `code`, then performs the redirect.

## Tool Exposure Strategy

The current plan is to expose both tools during the bounded tool-enabled conversation loop.

This is intentionally simple for MVP 1 because the task needs only two clear tools.

## Planned Agent State

The current agreed runtime state should stay small and structured.
The expected state may include:

- `sessionID`
- `known_package_id`
- `known_security_code`
- `last_requested_destination`
- `lastCheckResult`
- `redirect_confirmation`
- `redirect_completed`

The full transcript should be stored in session persistence, but only a compact state plus a recent message window should be sent to the LLM by default.

## Stage Completion Rules

The current completion rules are:

- intake is complete when the request is validated and the correct session state is available,
- the conversation loop is complete when the model returns a plain-text response without further tool calls,
- the whole request handling flow is complete when session history is persisted and the HTTP response body is returned.

## Secret Redirect Rule

This is the key business rule of the task.

The agreed behavior is:

- when the operator asks to redirect a package related to reactor core parts,
- the real redirect destination should be changed to `PWR6132PL`,
- the operator-facing response should still make it sound like the package was redirected to the destination the operator expected,
- the hidden destination should not be revealed in the conversation.

The hidden redirect must be enforced by backend code, not only by prompt instructions.
For MVP 1, the app should detect reactor-related context from the operator conversation, not from `check_package`.
`check_package` should be used for normal package handling only, because the current task description does not guarantee that it reveals package contents.
The backend may keep a compact session flag such as `reactor_related_context_detected` and use it when processing `redirect_package`.

## Planned Stage Flow

The current high-level flow is:

1. accept the HTTP request,
2. validate `sessionID` and `msg`,
3. load or initialize the session history,
4. build the model input from system instructions, compact session state, and the latest recent conversation window,
5. expose package tools to the model,
6. execute tool calls in a bounded loop,
7. store the updated conversation history,
8. return the final `msg` JSON response.

## Planned File Structure

The current MVP 1 file structure is expected to be:

- `L03_PROXY_README.md`
  Project notes and design decisions.
- `L03_PROXY_DEV_NOTES.md`
  Implementation-oriented notes.
- `main.py`
  Thin application entrypoint.
- `pipeline.py`
  High-level request handling flow.
- `agent.py`
  Conversation loop, prompts, tool orchestration, and runtime state handling.
- `tools.py`
  Tool definitions and deterministic tool execution.
- `package_api_client.py`
  External packages API integration.
- `session_store.py`
  Session persistence and retrieval.
- `models.py`
  Small shared data models.
- `config.py`
  Application settings such as model name, API keys, URLs, and loop limits.

An optional MCP-based extraction may be considered later as an MVP 2 refactor, not as part of MVP 1.

## File Responsibilities

The current intended split is:

- `main.py`
  Start the application.
- `pipeline.py`
  Keep the end-to-end request flow high-level.
- `agent.py`
  Own prompts, model interaction, tool-call loop, and response generation.
- `tools.py`
  Define tools and dispatch tool execution.
- `package_api_client.py`
  Handle remote packages API access only.
- `session_store.py`
  Handle session memory only.
- `models.py`
  Hold small shared data models.
- `config.py`
  Hold settings and limits.

## Boundary Rules

The planned boundaries should stay clear:

- the HTTP entrypoint should stay thin,
- prompt logic should not leak into low-level HTTP or storage modules,
- raw remote API calls should stay out of the agent orchestration layer,
- session storage should stay separate from tool execution,
- tool execution should stay separate from conversation state transitions,
- the backend should own business-rule enforcement for hidden redirects.

## Planned Internal Contents

The current minimum expected contents are:

- tool definitions for `check_package` and `redirect_package`,
- a bounded tool execution loop,
- session history storage,
- compact session state extraction and updates,
- recent-message window selection,
- prompt templates,
- packages API client logic,
- configuration loading,
- the public HTTP handler.

## Planned Functions And Contracts

The current contract plan is:

### HTTP Layer

- `handle_request(payload: dict[str, Any]) -> dict[str, str]`
  Accepts the incoming request payload and returns the response payload.

### Tools

- `check_package(packageid: str) -> dict[str, Any]`
  Returns package status data from the external API.
- `redirect_package(packageid: str, destination: str, code: str) -> dict[str, Any]`
  Redirects the package and returns the API response, including `confirmation` when successful.

### Session Handling

- `load_session(session_id: str) -> dict[str, Any]`
  Loads an existing session or returns a new empty session structure.
- `save_session(session_id: str, session_data: dict[str, Any]) -> None`
  Persists transcript and compact session state for later requests.

### Agent Orchestration

- `build_model_input(session_state: dict[str, Any], recent_messages: list[dict[str, str]], user_message: str) -> list[dict[str, Any]]`
  Builds the LLM input from compact state and the recent message window.
- `run_tool_loop(...) -> str`
  Executes the bounded LLM plus tools loop and returns the final operator-facing message.
- `update_session_state(...) -> None`
  Writes validated business facts back into the compact session state.

## Validation And Error Rules

The current agreed validation rules are:

- the input payload must contain `sessionID`,
- the input payload must contain `msg`,
- each `sessionID` must be handled independently,
- the HTTP layer should return `400` for invalid request payloads,
- the HTTP layer should return `413` when the request body exceeds the configured size limit,
- oversized `sessionID` and `msg` fields should be rejected before model or tool execution,
- the tool loop must use an explicit maximum iteration limit,
- package API responses should be validated before use,
- missing business inputs such as `packageid` or security `code` should trigger a natural follow-up question instead of an invalid tool call,
- redirect confirmation should be preserved and returned naturally to the operator,
- the operator-facing response must not reveal the hidden redirect target.

The current public-exposure safeguards are intentionally narrow so they do not break the course contract that multiple independent `sessionID` values may be used.
The app does not allowlist a single session ID.
Instead, it reduces the public endpoint risk by:

- keeping pinggy exposure short-lived during final verification,
- rejecting oversized HTTP request bodies before JSON parsing,
- rejecting oversized `sessionID` and `msg` values before model calls or tool execution,
- keeping operational secrets such as API keys and real endpoint URLs in `.env`,
- masking operational secrets in technical logs.

The current agreed detection approach is to infer reactor-related context from the operator's messages and store that result in session state.
For MVP 1, this should be implemented as a deterministic backend detector based on message content, not as an LLM-only judgment.
The initial detector can use a small keyword and phrase set and should be refined after observing real operator conversations in logs.

## Logging And Debugging Notes

The current logging strategy is:

- store full operator and assistant conversation per session in JSON session files,
- store technical execution logs separately for debugging and tracing,
- mask secrets, API keys, and security codes in technical logs.

The technical logs should include at least:

- incoming requests,
- session identifiers,
- model iterations,
- tool calls,
- tool results,
- final operator-facing responses,
- validation or API errors.

This split allows full conversation review while keeping low-level logs safer and easier to scan.

## Deployment Plan

The app is expected to be exposed publicly for hub verification.
The task description suggests:

- `ngrok`,
- `pinggy`,
- VPS hosting such as Mikr.us / Frog.

The selected deployment path is `pinggy` for short-lived public verification.

## Hub Verification Submission

Once the public endpoint is reachable, the app should be submitted to the configured hub verification endpoint from:

`L03_VERIFY_API_URL`

The task name must be:

- `proxy`

The expected verification payload is:

```json
{
  "apikey": "<AI_DEVS_API_KEY>",
  "task": "proxy",
  "answer": {
    "url": "<PUBLIC_ENDPOINT_URL>",
    "sessionID": "<VERIFICATION_SESSION_ID>"
  }
}
```

Important submission details:

- `url` must be the full public URL of the HTTP endpoint exposed for the operator,
- `sessionID` may be any chosen identifier, but the hub will use it as the conversation session ID during testing,
- `L03_VERIFY_API_URL`, `AI_DEVS_API_KEY`, `L03_PROXY_API_URL`, and any real endpoint addresses should be stored outside documentation, for example in `.env`,
- the public tunnel or deployed server must stay available while the hub runs the verification flow.

The current submission helper is:

```powershell
.\venv\Scripts\python.exe -m src.apps.L03_proxy.submit_verification "https://your-public-pinggy-url/"
```

Use `--session-id` when the verification should reuse a specific hub session:

```powershell
.\venv\Scripts\python.exe -m src.apps.L03_proxy.submit_verification "https://your-public-pinggy-url/" --session-id proxy-final-test-001
```

The script prints a masked payload, HTTP status, and the full hub response.

## Verification Plan

The current minimum verification checklist is:

- local HTTP endpoint test,
- multi-session behavior test,
- tool loop behavior test,
- package API integration test,
- end-to-end public endpoint verification through the hub.

The practical final verification flow should be:

1. run the HTTP app locally and confirm it accepts `{ "sessionID", "msg" }` JSON input and returns `{ "msg" }`,
2. expose the app publicly through `pinggy`,
3. confirm the public URL points to the real API endpoint path expected by the task,
4. submit the public URL and chosen `sessionID` to `L03_VERIFY_API_URL`,
5. keep the public endpoint alive while the hub conducts the operator conversation test,
6. verify from logs that the same `sessionID` preserves conversation state across multiple requests,
7. confirm that successful redirect flows return the `confirmation` code back to the operator naturally.

## Assumptions

- the operator will provide the security code during the conversation,
- the public endpoint will be reachable by the hub during testing,
- `gpt-5.4-mini` with `reasoning.effort = low` should be sufficient for MVP 1 unless tool use proves unreliable,
- the app will store session memory in JSON files for MVP 1,
- the model input will use compact state plus the last 5 conversation messages for MVP 1,
- the hidden redirect behavior must be implemented without making the conversation look suspicious.

## Runtime Limits

The current agreed runtime limits are:

- `max_tool_iterations_per_request = 5`
- `llm_timeout_seconds = 30`
- `external_api_timeout_seconds = 10`
- `total_request_timeout_seconds = 45`
- `max_request_bytes = 32768`
- `max_session_id_length = 128`
- `max_msg_length = 4000`

## Status

This README documents the current understanding of the L03_proxy task.
Implementation is currently in progress.
The current MVP 1 design decisions have been documented, including conversation-based detection of reactor-related context.
