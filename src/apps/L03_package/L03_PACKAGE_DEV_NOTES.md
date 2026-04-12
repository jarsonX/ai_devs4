# L03_package Development Notes

## Implementation Summary

- The current MVP 1 design uses a simple public HTTP application with a bounded LLM tool-calling loop.
- The app should keep independent conversation sessions in JSON files, one logical session per `sessionID`.
- The LLM should receive only a compact `session_state` plus the last 5 conversation messages, not the full transcript.
- The full transcript should still be persisted locally for debugging and review.
- The current MVP 1 model recommendation is `gpt-5.4-mini` with `reasoning.effort = low`.
- The external packages API should be accessed through a direct application client, not through MCP in MVP 1.
- The hidden redirect rule must be enforced by backend code, not only by prompt instructions.
- Reactor-related package detection should be based on operator conversation content in MVP 1, not on `check_package`.
- Reactor-related package detection should be implemented as a deterministic backend rule, with an initial keyword and phrase detector refined after real log review.
- Natural operator-facing communication and technical execution tracing are both required.
- MCP may be revisited later as a possible MVP 2 refactor if tool portability becomes useful.

## Recommended Implementation Order

1. `models.py`
   Define the small session and response models first so the rest of the app shares the same vocabulary.

2. `config.py`
   Add configuration loading for API keys, model settings, file paths, and runtime limits.

3. `session_store.py`
   Implement JSON-based session loading and saving before the agent logic begins.

4. `package_api_client.py`
   Implement the external packages API client with response validation and request timeouts.

5. `tools.py`
   Implement `check_package`, `redirect_package`, and tool dispatch.

6. `agent.py`
   Implement prompt construction, compact session-state handling, recent-message window selection, reactor-context detection support, and the bounded tool loop.

7. `pipeline.py`
   Implement the high-level request flow: validate input, load session, run the agent, persist state, return response.

8. `main.py`
   Implement the HTTP entrypoint last and keep it thin.

## Approved Implementation Plan

1. Prepare configuration and the application file skeleton.
   Create or complete `config.py`, `models.py`, `session_store.py`, `package_api_client.py`, `tools.py`, `agent.py`, `pipeline.py`, and `main.py`.
   This step should stabilize the module boundaries before implementation details begin.

2. Implement application configuration.
   Add environment loading, runtime limits, timeouts, the MVP 1 model selection, and the main paths used by the app.
   The current agreed defaults are:
   - model: `gpt-5.4-mini`
   - reasoning: `reasoning.effort = low`
   - `max_tool_iterations_per_request = 5`
   - `llm_timeout_seconds = 30`
   - `external_api_timeout_seconds = 10`
   - `total_request_timeout_seconds = 45`

3. Implement data models and session structure.
   Define the minimum models needed for request payloads, response payloads, compact session state, transcript entries, and tool results.
   Keep the shared state small and explicit.

4. Implement `session_store.py`.
   Add JSON-based session persistence with a clear split between:
   - full transcript storage,
   - compact `session_state` storage.
   Each `sessionID` should be isolated from the others.

5. Implement `package_api_client.py`.
   Add direct integration with the external packages API for:
   - `check`
   - `redirect`
   Include request timeouts, response-shape validation, and safe logging.

6. Implement `tools.py`.
   Add the tool definitions and deterministic dispatch for:
   - `check_package`
   - `redirect_package`
   This module should expose only JSON-serializable tool outputs.

7. Implement reactor-related context detection in backend code.
   Add a deterministic detector based on operator message content.
   Start with a small keyword and phrase set and store the result in session state, for example through a flag such as `reactor_related_context_detected`.
   Refine the detector later after reviewing real operator logs.

8. Implement backend enforcement for hidden redirects.
   When `redirect_package` is executed and the reactor-related flag is active, force the real destination to `PWR6132PL` in backend code.
   The operator-facing response must still sound natural and must not reveal the hidden destination.

9. Implement `agent.py`.
   Add:
   - the system prompt,
   - model input construction from compact state plus the last 5 messages,
   - the bounded tool-calling loop,
   - follow-up behavior for missing business inputs such as `packageid` or security `code`,
   - state updates based on validated tool results.

10. Implement `pipeline.py`.
    Add the high-level request flow:
    - validate the input payload,
    - load the session,
    - run the agent,
    - save the session,
    - return the final response payload.

11. Implement `main.py` and the HTTP endpoint.
    Add the public JSON endpoint with the agreed contract.
    Return `400` for invalid payloads and a valid JSON response for normal requests.

12. Implement logging and debug tracing.
    Keep two separate observability layers:
    - full conversation transcript inside session files,
    - technical execution logs with masking for secrets, API keys, and security codes.
    The logs should make it easy to inspect both the operator conversation and the matching internal app flow.

13. Run scenario-based MVP 1 verification.
    Verify at least:
    - normal conversation,
    - package check flow,
    - package redirect flow,
    - missing `packageid`,
    - missing security `code`,
    - reactor-related context detection,
    - multi-session separation,
    - iteration-limit and timeout behavior.

14. Expose the application publicly and perform end-to-end validation.
    Publish the local app through a tunnel or VPS, test the real endpoint manually, and only then submit it to the course verification hub.
    The first debugging round should happen locally, not on the public URL.

## MVP 1 Runtime Profile

- model: `gpt-5.4-mini`
- reasoning: `reasoning.effort = low`
- LLM input: system prompt plus compact `session_state` plus the last 5 conversation messages
- session persistence: JSON files
- tool loop limit: `5`
- LLM timeout: `30s`
- external API timeout: `10s`
- total request timeout: `45s`

## Verification Suggestions

- After `config.py`:
  Verify that required environment variables and limits are loaded correctly.

- After `session_store.py`:
  Create, load, update, and reload a JSON session file for one `sessionID`.

- After `package_api_client.py`:
  Verify request timeouts, response validation, and error handling against the external API.

- After `tools.py`:
  Call each tool directly and confirm the output shape is JSON-serializable and stable.

- After `agent.py`:
  Confirm that:
  - only compact session state plus the last 5 messages are sent to the LLM,
  - missing business inputs trigger follow-up questions instead of invalid tool calls,
  - reactor-related context can be detected from conversation content and persisted in session state,
  - the chosen model and reasoning setting are stable enough for the short-context tool loop,
  - the tool loop stops at the configured iteration limit,
  - the final assistant response is natural.

- After `pipeline.py`:
  Confirm end-to-end request handling for:
  - normal conversation,
  - missing `packageid`,
  - missing security code,
  - multi-session separation.

- After `main.py`:
  Verify the HTTP contract, status codes, and JSON responses through the real endpoint.

## Design Guardrails

- Keep the HTTP entrypoint thin.
- Keep session persistence separate from agent orchestration.
- Keep raw external API access inside `package_api_client.py`.
- Keep tool execution inside `tools.py`.
- Keep hidden redirect enforcement in backend code, not only in prompts.
- Do not treat `check_package` as authoritative proof of reactor-related contents unless later testing shows that the API actually exposes such data.
- Keep reactor-related detection deterministic in MVP 1, even if the LLM helps maintain conversation flow.
- Keep the LLM context compact: prompt plus state plus recent window.
- Keep full transcripts for debugging, but mask secrets and codes in technical logs.
- Do not add MCP to MVP 1 unless a concrete implementation problem justifies the extra complexity.
