# L3_proxy Development Notes

## Implementation Plan

This section is the source of truth for implementation work on `L3_proxy`.
Follow it in order unless a later implementation detail proves that a step must be split or adjusted.
When a step is changed, update this section first so the plan and the work stay aligned.

1. Prepare configuration and the application file skeleton.
   Create or complete `config.py`, `models.py`, `session_store.py`, `package_api_client.py`, `tools.py`, `agent.py`, `pipeline.py`, and `main.py`.
   This step should stabilize the module boundaries before implementation details begin.

2. Implement application configuration.
   Add environment loading, runtime defaults, timeouts, and the main paths used by the app.
   Keep concrete default values in `Runtime Defaults`.

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
   Add a hybrid detector based on operator message content.
   Keep a deterministic pre-check for direct wording, but use a structured AI classifier for paraphrases and inflected wording.
   Store the validated result in session state through a flag such as `reactor_related_context_detected`.
   Backend code must validate classifier output before trusting it.

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
    Use `Verification Checklist` as the required local verification scope.

14. Expose the application publicly and perform end-to-end validation.
    Publish the local app through pinggy, test the real endpoint manually, and only then submit it to the course verification hub.
    Keep the real verification URL and API key in configuration through `.env` entries:
    - `AI_DEVS_API_KEY` for the hub API key,
    - `L3_PROXY_API_URL` for the packages API,
    - `L3_VERIFY_API_URL` for the hub verification endpoint.
    Submit the public endpoint with:
    ```powershell
    .\venv\Scripts\python.exe -m src.apps.L3_proxy.submit_verification "https://your-public-pinggy-url/"
    ```
    Use `--session-id` when a repeatable hub session ID is useful:
    ```powershell
    .\venv\Scripts\python.exe -m src.apps.L3_proxy.submit_verification "https://your-public-pinggy-url/" --session-id proxy-final-test-001
    ```
    The script must print the masked payload, HTTP status, and full hub response.
    The first debugging round should happen locally, not on the public URL.
    Public exposure is not required for most development work:
    - internal modules such as session handling, reactor-context detection, tool dispatch, and API integration can be tested without any HTTP server,
    - the HTTP contract can be tested on a local server bound to `localhost`,
    - a public URL is only required for the final end-to-end verification flow, when the external hub needs to send operator messages to the app over the internet.

## Runtime Defaults

- model: `gpt-5.4-mini`
- reasoning: `reasoning.effort = low`
- LLM input: system prompt plus compact `session_state` plus the last 5 conversation messages
- session persistence: one JSON file per `sessionID`
- tool loop limit: `5`
- LLM timeout: `30s`
- external API timeout: `10s`
- total request timeout: `45s`
- max HTTP request body: `32768 bytes`
- max `sessionID` length: `128 characters`
- max `msg` length: `4000 characters`
- external packages API integration: direct application client in `package_api_client.py`

## Design Guardrails

- Keep the HTTP entrypoint thin.
- Keep session persistence separate from agent orchestration.
- Keep raw external API access inside `package_api_client.py`.
- Keep tool execution inside `tools.py`.
- Keep hidden redirect enforcement in backend code, not only in prompts.
- Detect reactor-related package context from operator conversation content in MVP 1.
- Implement reactor-related detection as a hybrid backend-controlled flow:
  deterministic pre-check first, structured AI classification for ambiguous wording, backend validation before state updates.
- Do not treat `check_package` as authoritative proof of reactor-related contents unless later testing shows that the API exposes such data.
- Keep the LLM context compact: prompt plus compact state plus recent message window.
- Persist full conversation transcripts for debugging, but do not send the full transcript to the LLM by default.
- Keep technical logs separate from conversation transcripts.
- Mask secrets, API keys, and security codes in technical logs.
- Keep public endpoint exposure short-lived and reject oversized requests before model or tool execution.
- Do not add MCP to MVP 1 unless a concrete implementation problem justifies the extra complexity.
- MCP may be revisited later as a possible MVP 2 refactor if tool portability becomes useful.

## Verification Checklist

- After `config.py`:
  Verify that required environment variables, runtime defaults, paths, and limits are loaded correctly.

- After `session_store.py`:
  Create, load, update, and reload JSON session files for at least two independent `sessionID` values.

- After `package_api_client.py`:
  Verify request timeouts, response-shape validation, and error handling against the external API.

- After `tools.py`:
  Call each tool directly and confirm the output shape is JSON-serializable and stable.

- After reactor-related context detection:
  Verify positive and negative examples, including paraphrases such as package cores, and confirm the flag persists in compact session state.

- After hidden redirect enforcement:
  Verify that reactor-related redirects force the real destination to `PWR6132PL` without exposing it in operator-facing text.

- After `agent.py`:
  Confirm that:
  - only compact session state plus the last 5 messages are sent to the LLM,
  - missing business inputs trigger follow-up questions instead of invalid tool calls,
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

- Before public exposure:
  Confirm the local endpoint works, logs are safe, `.env` contains real secrets, and documentation does not contain real operational values.
  Confirm oversized HTTP bodies and oversized request fields are rejected before model or tool execution.

- During public verification:
  Keep the tunnel or deployed server alive while the hub runs the operator conversation test.

## Final Outcome

MVP 1 has passed course hub verification.

The final working implementation includes:

- a local HTTP endpoint exposed publicly through a short-lived `pinggy` tunnel,
- a submission helper that sends the public URL to `L3_VERIFY_API_URL`,
- bounded OpenAI tool orchestration for package checks and redirects,
- backend-enforced hidden redirects to `PWR6132PL`,
- destination-code normalization before calling the packages API,
- hybrid reactor-context detection:
  deterministic pre-check for direct wording plus structured AI classification for paraphrases and Polish inflection,
- request-size and field-length safeguards before model or tool execution,
- per-session transcript persistence and masked technical logs.

The main debugging lesson was that closed keyword lists were too brittle for recognizing reactor-related package descriptions.
The reliable pattern is:

1. let the model classify ambiguous natural language into a small structured schema,
2. validate that classification in backend code,
3. store only the validated compact decision in session state,
4. keep the side-effecting redirect rule enforced by deterministic backend code.

The second practical lesson was that prompt-only behavior is not enough for operational correctness.
Prompt changes helped with natural small talk, but successful task completion required backend fixes for destination normalization and hidden redirect enforcement.
