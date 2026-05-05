# L3 Proxy Local MVP Verification Report

Generated at: 2026-04-29 17:09:56 +02:00

## Table Of Contents

- [Scope](#scope)
- [Commands](#commands)
- [Verified Areas](#verified-areas)
  - [Configuration](#configuration)
  - [Session Store](#session-store)
  - [Packages API Client](#packages-api-client)
  - [Tool Dispatch](#tool-dispatch)
  - [Reactor Context Detection](#reactor-context-detection)
  - [Agent Loop](#agent-loop)
  - [Pipeline](#pipeline)
  - [HTTP Handler](#http-handler)
  - [Technical Logging](#technical-logging)
- [Explicitly Not Tested](#explicitly-not-tested)
- [Current Assessment](#current-assessment)

## Scope

This report covers local MVP verification for `src/apps/L3_proxy`.

The verification intentionally avoided real external calls:

- no real OpenAI requests,
- no real packages API requests,
- no hub verification request,
- no public tunnel or public endpoint exposure.

Fake clients, fake HTTP sessions, and temporary runtime directories were used where needed.

## Commands

```powershell
.\venv\Scripts\python.exe -m compileall -q src/apps/L3_proxy
```

Result: passed.

A local inline smoke-test script was also executed with:

```powershell
.\venv\Scripts\python.exe -
```

Result: passed.

## Verified Areas

### Configuration

Status: passed.

Verified:

- runtime directories can be created,
- configured session, log, and output paths are usable,
- runtime limits and model settings can be read from an `AppConfig` instance.

### Session Store

Status: passed.

Verified:

- two independent sessions can be saved,
- two independent sessions can be reloaded,
- compact session state persists,
- transcript messages persist.

### Packages API Client

Status: passed with fake HTTP session.

Verified:

- `check_package` builds the expected action payload,
- `redirect_package` builds the expected action payload,
- request timeout comes from config,
- JSON response objects are returned,
- redirect confirmation is required.

Not verified:

- real network connectivity,
- real packages API response shape beyond the documented fake response.

### Tool Dispatch

Status: passed with fake package API client.

Verified:

- tool definitions expose `check_package` and `redirect_package`,
- tool definitions use the Responses API function-tool shape,
- tool outputs are stable `ToolExecutionResult` objects,
- normal redirects use the requested destination,
- reactor-related redirects force the real destination to `PWR6132PL`,
- the hidden destination is not exposed in the tool result payload.

### Reactor Context Detection

Status: passed.

Verified:

- neutral Polish operator messages do not set the reactor flag,
- reactor-related Polish operator messages set the reactor flag,
- Polish diacritics are normalized before matching,
- once detected, the reactor flag remains enabled in compact session state.

### Agent Loop

Status: passed with fake OpenAI client and fake toolbox.

Verified:

- model input can be built from compact state and recent messages,
- the model-visible state does not expose the backend reactor flag,
- function-call arguments are parsed,
- tool outputs are converted to Responses API `function_call_output` items,
- tool call inputs update compact session facts,
- redirect confirmation updates compact session state,
- the bounded loop stops when a final assistant response is returned,
- reasoning config is passed as `{"effort": "low"}` in the fake call.

Not verified:

- real OpenAI model behavior,
- naturalness or reliability of real model responses,
- real model behavior when business inputs are missing.

### Pipeline

Status: passed with fake agent runner.

Verified:

- payload validation uses `ProxyRequest`,
- existing session state is loaded,
- only the configured recent-message window is sent to the agent,
- user and assistant messages are appended to the transcript,
- updated compact state is saved,
- session separation works through independent session IDs,
- response shape is `{"msg": "..."}`.

### HTTP Handler

Status: passed with fake pipeline handler.

Verified:

- `POST /` with a JSON object can return `200`,
- malformed JSON returns `400`,
- validation errors return `400`,
- `GET /` returns `405`,
- responses are JSON-shaped.

Not verified:

- long-running local server behavior,
- real pipeline execution through the HTTP endpoint.

### Technical Logging

Status: passed.

Verified:

- request lifecycle events are written to `events.jsonl`,
- tool-call lifecycle events are written to `events.jsonl`,
- security code values are masked,
- full operator messages are not written into technical logs.

## Explicitly Not Tested

The following items were intentionally not tested in this verification round:

- real `.env` loading with operational secrets,
- real OpenAI requests,
- real packages API requests,
- real end-to-end package redirect,
- public endpoint exposure through ngrok, pinggy, or VPS,
- hub verification.

## Current Assessment

The local MVP implementation is ready for the next controlled verification stage.

Before public exposure, the project still needs:

- one real local run with valid `.env` values,
- one real packages API integration check,
- one real OpenAI tool-loop check,
- local HTTP endpoint verification with the real pipeline,
- review of generated runtime logs and session files.
