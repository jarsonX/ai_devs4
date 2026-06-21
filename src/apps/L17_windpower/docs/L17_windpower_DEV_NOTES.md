# L17 Windpower DEV_NOTES

## Table Of Contents

- [Implementation Plan](#implementation-plan)
- [Implementation Notes](#implementation-notes)
- [API Exploration Notes](#api-exploration-notes)
- [Response Contracts](#response-contracts)
- [Weather And Power Findings](#weather-and-power-findings)
- [Implementation Risks](#implementation-risks)

## Implementation Plan

### Batch 1: Deterministic API Client And Contracts

Goal: Build a small guarded client for the `windpower` task without using an LLM.

Steps:

1. Load `AI_DEVS_API_KEY` and `HUB_VERIFY_URL` from `.env`.
2. Create a typed wrapper for `start`, `get`, `getResult`, `unlockCodeGenerator`, `config`, and `done`.
3. Mask `apikey` in every stored or printed request payload.
4. Normalize API responses by `sourceFunction`, because queued results are returned in completion order, not request order.

Checkpoint: Unit tests or a fake-session smoke test prove that async results can be collected by source name without relying on queue order.

### Batch 2: Timed Orchestration

Goal: Finish all required live API work inside the 40-second service window.

Steps:

1. Call `start`.
2. Immediately queue `get` for `weather`, `turbinecheck`, and `powerplantcheck`.
3. Poll `getResult` until all three source reports are collected or the local deadline is close.
4. Derive required config points from the collected reports.
5. Queue all required `unlockCodeGenerator` calls as early as possible.
6. Poll `getResult` until all unlock codes are collected.
7. Submit one batch `config` payload containing every schedule point.
8. Submit `done`.

Checkpoint: A dry fake clock test proves the workflow queues independent async work before waiting for results.

### Batch 3: Solver Logic

Goal: Convert weather, turbine, and power-plant reports into minimal safe configuration.

Steps:

1. Mark every forecast slot with `windMs > cutoffWindMs` as a storm shutdown point.
2. Use `pitchAngle: 90` and `turbineMode: "idle"` for shutdown points.
3. Select a non-storm slot that can cover `powerDeficitKw` using documented wind yield and pitch yield.
4. Consider `pitchAngle: 0` and `45` for production, then choose the earliest point whose estimated power range covers the live deficit.
5. Always set minutes and seconds to `00:00` in config hours.

Checkpoint: Given the explored forecast, the solver selects all storm slots and a valid production slot around 6.6 m/s wind.

### Batch 4: Runtime Artifacts And Verification

Goal: Keep useful debugging evidence without leaking secrets into source or docs.

Steps:

1. Store raw Hub/API responses only under `data/L17_windpower/...` if they are needed.
2. Store documentation and run summaries outside `data/` only with secrets and raw course responses removed.
3. Run a leak check on changed files outside `data/L17_windpower/...` before finalizing.

Checkpoint: Changed source/docs contain no API key, no raw Hub response dump, and no raw generated unlock code.

Stop for approval before adding dependencies, introducing an LLM workflow, exposing a public endpoint, or running repeated live submissions beyond a bounded implementation test.

## Implementation Notes

Implementation completed locally on 2026-06-21.

Added modules:

| Module | Notes |
| --- | --- |
| `config.py` | Loads Hub config, runtime guards, app paths, and TLS environment setup. |
| `api_client.py` | Wraps Hub actions and masks `apikey` in stored requests. |
| `models.py` | Defines shared workflow, report, and config-point data objects. |
| `solver.py` | Implements deterministic storm detection, power estimation, and production-slot selection. |
| `workflow.py` | Runs the timed queue/poll/sign/config/done workflow with a local deadline. |
| `run_log.py` | Writes masked JSONL runtime events under `data/L17_windpower/logs/`. |
| `main.py` | Provides `--check-config` and explicit `--submit` modes. |

Verification performed:

| Check | Result |
| --- | --- |
| `.\venv\Scripts\python.exe -m unittest tests.L17_windpower.test_api_client tests.L17_windpower.test_solver tests.L17_windpower.test_workflow` | Passed, 5 tests. |
| `.\venv\Scripts\python.exe -m src.apps.L17_windpower.main --check-config` | Passed, printed a secret-safe config summary. |

Live verification:

| Check | Result |
| --- | --- |
| `.\venv\Scripts\python.exe -m src.apps.L17_windpower.main --submit` | Passed on 2026-06-21; Hub accepted the configuration, `flag_found: true`, elapsed time `26.23` seconds. |

The accepted live schedule used:

| Timestamp | Wind | Pitch | Mode | Reason |
| --- | ---: | ---: | --- | --- |
| `2026-06-22 18:00:00` | `25.0` | `90` | `idle` | Storm shutdown. |
| `2026-06-22 20:00:00` | `5.9` | `45` | `production` | Covers the smaller live deficit without overusing pitch `0`. |
| `2026-06-25 18:00:00` | `22.0` | `90` | `idle` | Storm shutdown. |
| `2026-06-26 18:00:00` | `28.0` | `90` | `idle` | Storm shutdown. |

Implementation correction from live testing:

- The first production solver considered only pitch `0`, which failed when the live power deficit dropped to `3-4 kW` and the best usable wind was `5.9 m/s`.
- The solver now considers production pitch `0` and `45`, and maps near-threshold wind speeds to the closest documented wind-yield bracket.
- A client bug also surfaced: `WindpowerApiClient.config` was shadowed by an instance attribute named `config`. The attribute is now named `hub_config`, and `tests/L17_windpower/test_api_client.py` guards the batch config method.

## API Exploration Notes

Exploration date: 2026-06-21.

The API is accessed through `HUB_VERIFY_URL` with this envelope:

```json
{
  "apikey": "<AI_DEVS_API_KEY>",
  "task": "windpower",
  "answer": {
    "action": "..."
  }
}
```

Safe exploration performed:

| Step | Result |
| --- | --- |
| `help` | Returned action list and confirmed `start` is required before the live workflow. |
| `get` with `param: "documentation"` | Returned documentation directly; it is not queued. |
| `start` | Opened a 40-second service window. |
| `get weather`, `get turbinecheck`, `get powerplantcheck` | All three were queued successfully. |
| `getResult` polling | Returned completed queued responses one at a time and removed each retrieved item from the queue. |
| `unlockCodeGenerator` | Queued successfully and later returned a 32-character lowercase hex unlock code with echoed signed parameters. |

Important behavior:

- `getResult` has no request parameter. It returns whichever queued report is ready first.
- A `getResult` response with no ready item uses code `11` and should not be treated as fatal.
- A completed queued item uses `sourceFunction`, which is the reliable discriminator.
- The observed report order was `powerplantcheck`, `turbinecheck`, then `weather`, even though requests were queued as `weather`, `turbinecheck`, `powerplantcheck`.
- In the observed run, all three reports arrived after roughly 26 seconds, leaving little room for slow sequential unlock generation.
- The generated `unlockCode` is tied to the signed params. The echoed values normalized numeric fields to strings like `"6.6"` and `"0.0"`.
- Do not save generated unlock codes in docs. They belong only in memory or ignored runtime data when needed for debugging.

## Response Contracts

### `help`

Returns the available actions:

| Action | Notes |
| --- | --- |
| `start` | Starts a new service window and initializes task state. |
| `get` | Requires `param`; queued for `weather`, `turbinecheck`, and `powerplantcheck`; direct for `documentation`. |
| `getResult` | Returns one completed queued response and removes it from the queue. |
| `config` | Accepts either one config point or a batch `configs` object. |
| `unlockCodeGenerator` | Requires `startDate`, `startHour`, `windMs`, and `pitchAngle`; result is async. |
| `done` | Validates final configuration and returns the flag on success. |

### `documentation`

Useful fields:

| Field | Observed value |
| --- | --- |
| `ratedPowerKw` | `14` |
| `safety.cutoffWindMs` | `14` |
| `safety.minOperationalWindMs` | `4` |
| Allowed pitch settings | `0`, `45`, `90` |
| Shutdown pitch | `90`, because yield is `0` and blades do not resist severe wind. |
| Production pitch | `0` maximizes capture; `45` is useful when the live deficit is smaller and pitch `0` would overshoot the expected range. |

Wind yield from documentation:

| Wind | Yield |
| --- | --- |
| `4 m/s` | `10-15%` |
| `6 m/s` | `30-40%` |
| `8 m/s` | `60-70%` |
| `10 m/s` | `90-100%` |
| `12-14 m/s` | `100%` |
| `14+ m/s` | damage |

### `powerplantcheck`

Observed fields from exploration:

| Field | Observed value |
| --- | --- |
| `mode` | `StandBy` |
| `cooling` | `within norm` |
| `firmware` | `operational` |
| `powerDeficitKw` | `4-5` |
| `producedPowerKw` | `0` |

Live verification later returned `powerDeficitKw: 3-4`, which is why production pitch selection must be dynamic instead of hard-coded to `0`.

### `turbinecheck`

Observed fields:

| Field | Observed value |
| --- | --- |
| `status` | Turbine operates correctly. |
| `bladePitchAngleDeg` | `0` |
| `battery` | `low` |

The low battery note matters because the app should configure only required moments instead of long continuous operation.

### `weather`

Observed fields:

| Field | Observed value |
| --- | --- |
| `intervalHours` | `2` |
| `forecastDays` | `7` |
| `unit.windMs` | `m/s` |

Each forecast item has:

```json
{
  "timestamp": "YYYY-MM-DD HH:00:00",
  "windMs": 6.6,
  "precipitationMm": 0,
  "temperatureC": 30
}
```

## Weather And Power Findings

Storm shutdown points from the explored forecast:

| Timestamp | `windMs` | Required config |
| --- | ---: | --- |
| `2026-06-22 18:00:00` | `25` | `pitchAngle: 90`, `turbineMode: "idle"` |
| `2026-06-25 18:00:00` | `22` | `pitchAngle: 90`, `turbineMode: "idle"` |
| `2026-06-26 18:00:00` | `28` | `pitchAngle: 90`, `turbineMode: "idle"` |

Likely production candidates:

| Timestamp | `windMs` | Reason |
| --- | ---: | --- |
| `2026-06-22 20:00:00` | `6.6` | At 14 kW rated power and `30-40%` wind yield, pitch `0` gives about `4.2-5.6 kW`, matching the `4-5 kW` deficit. |
| `2026-06-24 20:00:00` | `6.6` | Same expected output as above. |

Solver rule after live verification:

- Use all three shutdown points.
- Use one production point with `turbineMode: "production"` and a pitch selected from `0` or `45`.
- Prefer the earliest valid production point whose estimated output overlaps the live deficit range.
- In the accepted live run, `2026-06-22 20:00:00` used `windMs: 5.9`, `pitchAngle: 45`, and covered a `3-4 kW` deficit.

## Implementation Risks

- The 40-second window is tight. Queue everything that can run independently before waiting.
- Sequential unlock generation for four config points may be too slow if done after all reports arrive. The implementation should compute config points quickly and queue all unlock generators back-to-back.
- `getResult` consumes each completed result once. Losing a response means the workflow has to restart the service window.
- Batch `config` is safer than multiple single `config` calls because it reduces request count after unlock codes are ready.
- Do not assume forecast values are stable between sessions. The solver should use live `weather` output, not hard-coded timestamps.
- Do not rely on a fixed report completion order. Use `sourceFunction`.
