# L25 Timetravel Development Notes

Implementation history for the completed application. The README owns the
current runtime and external contracts; this file preserves the original batch
plan, review evidence, deviations, and debugging lessons.

## Table Of Contents

- [Implementation Outcome](#implementation-outcome)
- [Implementation Rules](#implementation-rules)
- [LLM Design Review Record](#llm-design-review-record)
- [LLM Optimization Review Record](#llm-optimization-review-record)
- [Implementation Plan](#implementation-plan)
- [Debugging Notes](#debugging-notes)
- [Definition Of Done](#definition-of-done)

## Implementation Outcome

The course task is solved. Guarded live run `20260718T113838Z` completed all
three travel legs with exactly three confirmed activations, 34 Hub requests,
and `flag_found: true`. Raw course responses and the flag remain only under
`data/L25_timetravel/runs/20260718T113838Z/`.

Completed verification:

- default dry-run loaded the machine table without network access;
- `--simulate` completed the full fake workflow in phase `COMPLETED`;
- `--check-models` passed two stabilization and two frontend schema cases;
- `--submit` completed the guarded live workflow;
- the final response and screenshot independently confirmed the accepted
  tunnel result;
- post-run exact-secret and short-marker checks found no leak in changed code.

The implementation intentionally differs from parts of the original plan:

- the Supervisor calls both bounded agents sequentially instead of running a
  queued cooperative scheduler;
- SQLite persists phases, observations, events, and activation leases, but the
  CLI does not expose resume;
- reporting is assembled in `main.py` and `supervisor.py`; no separate
  `run_log.py` exists;
- the verification boundary is offline simulation plus bounded model and live
  checks; a dedicated `tests/L25_timetravel/` suite was not created.

These are current code facts, not future promises. Any resume or queued-worker
work is a new scope and requires a design decision rather than documentation
wishful thinking.

## Implementation Rules

1. Read these sources in order before editing source code:
   - `AGENTS.md` and applicable `_agent/instructions/` files;
   - `src/apps/L25_timetravel/docs/L25_timetravel_README.md`;
   - `data/L25_timetravel/input/timetravel.md`;
   - API and UI discovery summaries under
     `data/L25_timetravel/output/`.
2. Do not create application source until Batch 0 passes the LLM design gate.
3. Do not change the accepted architecture without user approval.
4. Use the installed stack: Python 3.11, OpenAI Responses API, Pydantic 2,
   standard-library `sqlite3`, `requests`, and synchronous Playwright with the
   `msedge` channel. Do not add Agents SDK, `aiosqlite`, Selenium, another
   model provider, or any package without approval.
5. Use one process and sequential Supervisor orchestration. Do not introduce
   threads, subprocess workers, or long-lived WAL without a new design review.
6. Agents keep separate prompts, model context, capabilities, and request
   guards. The Supervisor calls them directly and persists authoritative
   phases, observations, events, and leases in SQLite.
7. Keep stable rules, arithmetic, phase transitions, authorization, retries,
   readiness checks, and terminal decisions deterministic. Treat all model
   output as untrusted until schema and value validation pass.
8. Use OpenAI models only. Keep model names and normal limits in `config.py`,
   not `.env`. Keep all secrets and operational endpoints in `.env`.
9. Apply the repository TLS/CA setup before every real OpenAI or Hub call.
   Never disable certificate verification.
10. Keep source and docs under `src/apps/L25_timetravel/`, tests under
    `tests/L25_timetravel/`, and runtime state under
    `data/L25_timetravel/`. Never import production code from the discovery
    workbench under `data/`.
11. Use short English purpose comments for every class, function, and method;
    do not use purpose docstrings.
12. Default CLI behavior must be offline and non-mutating. Live mode must be
    explicit.
13. Never expose `reset` as a normal agent tool. Never retry an activation
    automatically. An ambiguous activation moves the run to `BLOCKED` after
    reconciliation evidence is saved.
14. Preserve unrelated worktree changes. In particular, do not overwrite or
    normalize `.env.example`, requirements, or documentation incidentally.
15. Stop for approval before dependency installation, architecture or scope
    changes, real OpenAI or Hub calls, authenticated live-browser use, any
    activation, reset, destructive action, or public exposure.

## LLM Design Review Record

Review date: `2026-07-18`. Mode: `non-production`. Scope: full dual-agent L25
workflow. Result: `PASS`.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Clear goal and expected output | YES | Three reconciled legs ending with `flag_found: true`. |
| Workflow split into small steps | YES | Supervisor phases and one bounded agent command per tick. |
| Deterministic code for stable logic | YES | Python owns rules, arithmetic, state, authorization, and completion. |
| Clear purpose per workflow step | YES | README phases and DEV NOTES batch checkpoints. |
| Reason for each LLM step | YES | Variable stabilization language, narrow tool selection, and changed-DOM recovery. |
| Model matches difficulty | YES | Cost-sensitive `gpt-5.6-luna`, low reasoning. |
| Short focused prompts | YES | Role prompt plus current command, observation, and last error only. |
| Token usage limited | YES | Compact context, small output cap, no full history. |
| Structured outputs | YES | Strict `BackendDecision`, `StabilizationExpression`, and `FrontendDecision`. |
| Context limited per step | YES | No raw DB, credentials, full logs, or unrelated artifacts. |
| Tool exposure limited | YES | Separate command-scoped backend and frontend tool sets. |
| No full history or datasets | YES | `store=False`; state is reconstructed from typed current records. |
| Repeated work persisted | YES | Commands, observations, decisions, and outcomes use SQLite idempotency. |
| Production progress mechanism | N/A | Local non-production exercise; heartbeat still planned. |
| Production waiting visibility | N/A | Local CLI; compact status events still planned. |
| Production disconnected continuation | N/A | No deployed client/server session. |
| Production state persistence | N/A | Non-production; SQLite persistence is still required for safety. |
| Production pause and resume | N/A | Non-production; explicit resume is still planned. |
| Production user interaction queue | N/A | Single local run with approval before live execution. |
| Production UI/backend decoupling | N/A | External preview is a controlled tool, not the app UI. |
| Production event-driven orchestration | N/A | Cooperative scheduler is sufficient for one local run. |
| Validation before downstream use | YES | Pydantic plus phase, permission, value, version, and digest checks. |
| Model output treated as untrusted | YES | Invalid or stale decisions are rejected and recorded. |
| Authorization outside model | YES | Supervisor and atomic activation leases own risky actions. |
| Missing required inputs handled | YES | Preflight fails closed; no important value is guessed. |

## LLM Optimization Review Record

Review date: `2026-07-18`. Mode: `non-production`. Scope: completed L25
workbench, including offline simulation, bounded model evaluation, and the
solved live workflow. Result: `PASS WITH ACCEPTED WORKBENCH LIMITATIONS`; no
blocking fix remains for the course task.

Every `NO` below has the same classification: **accepted workbench limitation**
for the solved learning exercise and **follow-up before production**. The
Frontend Agent's routine state-to-action decisions can be ordinary Python. In
the solved run that boundary used 14 model calls, so preserving it teaches the
two-agent architecture but is not the cheapest production design.

| Checklist item | Result | Evidence |
| --- | --- | --- |
| Task has a concrete output | YES | Completion requires three reconciled legs and `flag_found: true`. |
| Task is split into smaller steps | YES | `TimetravelSupervisor` prepares, waits, activates, and verifies each leg separately. |
| Stable logic is deterministic | YES | `machine_spec.py`, `supervisor.py`, and `browser_tools.py` own arithmetic, rules, readiness, and authorization. |
| Model steps avoid unrelated jobs | YES | Stabilization extraction and frontend action selection use separate prompts and schemas. |
| Workflow is explainable | YES | The three-leg phase sequence maps directly to persisted state transitions. |
| Each LLM step has a reason | YES | Backend handles variable Polish hints; frontend demonstrates bounded model-guided UI control. |
| Strong model use is limited to need | YES | One configured model with low reasoning and small outputs serves both narrow local roles. |
| Ordinary code replaces model where sufficient | NO | Frontend ports, PWR, and mode selection could be derived directly from `TravelLeg`. |
| Repeated model calls are unavoidable | NO | The 14 frontend calls are bounded and explained, but several are avoidable in a production design. |
| Prompts state instruction and format | YES | `llm_gateway.py` supplies narrow instructions and Pydantic `text_format` schemas. |
| Prompts contain only relevant context | YES | Calls receive one hint or one goal/observation/error payload. |
| Irrelevant history is excluded | YES | No chat transcript, raw database rows, or discovery archive enters prompts. |
| Ambiguity is handled before execution | YES | Structured schemas plus agent-side value checks reject unsupported actions. |
| Current-step context only | YES | `choose_frontend_action` serializes one leg and one current observation. |
| Old history is summarized or dropped | YES | The gateway is stateless and uses no accumulated conversation history. |
| Tool results are filtered | YES | Models receive typed snapshots and bounded errors, not raw browser or Hub payloads. |
| Context is treated as limited | YES | Hint length, output tokens, and model request counts have hard limits. |
| Tool exposure is narrow | YES | Models return typed decisions; activation and raw browser access remain outside model control. |
| Calls are few and high-value | NO | One frontend correction per model call is clear but not call-optimal. |
| Related operations are batched | YES | Both PT ports change together; backend writes stay sequential because Hub validation is stateful. |
| External calls use caching when valid | N/A | Readiness and rotating mode require fresh Hub and DOM observations. |
| Every workflow step has a purpose | YES | Preparation, cross-check, lease, activation, and reconciliation protect distinct failure boundaries. |
| Structured model output is used | YES | `StabilizationExpression` and `FrontendDecision` are strict Pydantic models. |
| Schemas exist before execution | YES | Schemas are declared in `models.py` and passed directly to Responses API parsing. |
| Model responses are validated | YES | Gateway type checks and agent-specific target checks run before downstream actions. |
| Model output is untrusted | YES | Invalid values produce bounded correction or failure; the model never grants activation. |
| LLM calls are intentionally minimized | NO | Backend calls are sparse, but the frontend learning loop still made 14 calls in the live run. |
| Tool calls are intentionally minimized | YES | Hub polling and DOM rereads are tied to freshness and non-idempotent safety checks. |
| Large prompts are avoided | YES | Live prompts were roughly 250-590 input tokens per call. |
| Output length is controlled | YES | `MAX_MODEL_OUTPUT_TOKENS = 256`; observed outputs remained below that cap. |
| Cost and latency are measurable | YES | The run report stores request sequence and input/output/total token counts. |
| Expensive steps are identifiable | YES | Records separate `stabilization` and `frontend_decision` purposes. |
| Production progress heartbeat | N/A | Local non-production CLI; no deployed long-running service. |
| Production waiting visibility | N/A | Local non-production CLI; final evidence is persisted per run. |
| Production partial artifact inspection | N/A | Runtime evidence exists, but interactive production inspection is out of scope. |
| Production disconnected continuation | N/A | No deployed client/server job boundary. |
| Production persistent retry state | N/A | SQLite persists safety state, but full production resume is not implemented. |
| Production pause and resume | N/A | The CLI intentionally exposes no resume mode. |
| Production user interaction queue | N/A | One local approved run has no multi-user interaction queue. |
| Production UI/backend decoupling | N/A | The external preview is a controlled tool, not this app's frontend. |
| Production event-driven orchestration | N/A | Sequential orchestration is accepted for one local course run. |
| Model does not authorize actions | YES | Supervisor state and a one-time lease authorize each activation. |
| Risky actions have code checks | YES | Fresh Hub/DOM agreement, digest binding, expiry, and single consumption are deterministic. |
| Untrusted content is isolated | YES | The stabilization prompt labels the hint as data and constrains the extracted shape. |
| Missing inputs fail closed | YES | Required environment values and CA bundle are validated before external work. |
| No replaceable LLM call remains | NO | Routine frontend decision calls are replaceable without reducing course-task quality. |
| No removable workflow step remains | NO | The frontend model-choice layer could be removed while retaining deterministic browser safety. |
| No removable context remains | YES | Both prompts already contain only the current semantic input and validation context. |
| Workflow remains maintainable | YES | Model, Hub, browser, domain, persistence, and supervisor boundaries are separate modules. |
| Production multi-task lifecycle is robust | N/A | Multi-task production operation is outside the non-production review scope. |

## Implementation Plan

### Batch 0: Pass The LLM Design Gate

**Goal:** Open the source implementation boundary for the full dual-agent
workflow.

**Steps:**

1. Review the README design in `non-production` mode with
   `_agent/instructions/llm_design_checklist.md`.
2. Fix the README before coding if the review lacks exact model purposes,
   output schemas, prompt context, tool exposure, guard limits, validation, or
   missing-input behavior.
3. Mark every checklist item `YES`, `NO`, or `N/A` with evidence. Any `NO`
   blocks implementation.
4. Record a passing review in README with date, scope `full dual-agent L25
   workflow`, mode, result, and approved boundary.

**Checkpoint:** README records `Design review | Passed` for the full workflow.
No application source file exists before this checkpoint.

### Batch 1: Build The Deterministic Domain Core

**Goal:** Represent configuration and machine rules without network, browser,
SQLite, or model calls.

**Steps:**

1. Create `__init__.py`, `config.py`, `models.py`, and `machine_spec.py`.
2. In `config.py`, define immutable secret-bearing configs, normal runtime
   limits, repository paths, required environment loading, and TLS setup.
   Load secrets only for an explicitly selected mode.
3. In `models.py`, define strict Pydantic models and enums for phases, roles,
   commands, observations, backend/frontend snapshots, travel legs,
   configuration digests, leases, events, and terminal results. Forbid extra
   fields.
4. In `machine_spec.py`, implement date validation, Sync Ratio, required
   `internalMode`, PT direction, tunnel rules, and travel-leg construction.
5. Parse the PWR table from
   `data/L25_timetravel/input/timetravel.md`; validate complete year coverage
   and value ranges instead of copying the table into source.
6. Freeze `currentDate` once per run and build the three legs from that value.

**Checkpoint:** `tests/L25_timetravel/test_machine_spec.py` and model/config
tests pass offline for boundary years, the observed 2026 plan, invalid dates,
and malformed PWR input.

### Batch 2: Implement SQLite Coordination

**Goal:** Make workflow state durable and enforce role boundaries without
agent-accessible SQL.

**Steps:**

1. Create `coordination.py` with schema initialization for the tables named in
   README.
2. Enable foreign keys and a busy timeout. Use the default rollback journal,
   short transactions, and `BEGIN IMMEDIATE` for command claiming, state
   transitions, and lease consumption.
3. Expose separate Supervisor, Backend Agent, and Frontend Agent adapters with
   only role-permitted methods.
4. Enforce state versions, command expiry, idempotency keys, immutable
   observations, one-time leases, and append-only safe events.
5. Make run creation and resume reconciliation explicit. Never infer success
   from the last event alone.

**Checkpoint:** Coordination tests prove atomic claiming, stale-version
rejection, lease expiry and single consumption, role restrictions, rollback,
and crash-safe reload from a temporary database.

### Batch 3: Implement The Guarded Hub Boundary

**Goal:** Provide typed backend operations with bounded traffic and safe
timeout reconciliation.

**Steps:**

1. Create `hub_client.py` using one `requests.Session`, verified TLS, explicit
   timeout, a total-request guard, and masked exchange records.
2. Implement only `help`, `getConfig`, and the five accepted `configure`
   parameters. Keep `reset` absent.
3. Validate HTTP status, domain code, and response schema before returning a
   backend snapshot.
4. Require a fresh standby snapshot before `configure`.
5. Retry read-only calls only under the configured policy. After an ambiguous
   `configure`, call `getConfig` and compare the requested field before any
   retry.
6. Preserve bounded `needConfig` text as untrusted semantic input.

**Checkpoint:** Fake-session tests cover observed success/error codes,
standby enforcement, request limits, masking, malformed responses, transient
read failures, and ambiguous-write reconciliation. No live request is made.

### Batch 4: Implement Deterministic Browser Tools

**Goal:** Reproduce the discovered login and DOM contract without giving the
model credentials or arbitrary browser access.

**Steps:**

1. Create `browser_tools.py` around synchronous Playwright and installed Edge.
2. Implement fresh-context login through only the approved hosts. Select
   Easytools password mode explicitly; read credentials inside the login
   helper; never return or persist them, cookies, or storage state.
3. Implement narrow tools for snapshot, PT-A, PT-B, PWR, mode, bounded
   evidence capture, and session close using selectors from the UI summary.
4. Verify each write immediately and again after a server poll. Return typed
   frontend snapshots only.
5. Implement activation as one non-retriable method that requires an
   unexpired lease, atomically consumes it, rechecks path and full DOM
   readiness, clicks `#orb` once, and records pre/post evidence.
6. Reject unexpected navigation, selector ambiguity, dead battery, stale
   state, same-date warning, dangerous orb state, or any attempt to activate
   without the exact lease-bound digest.

**Checkpoint:** Playwright fixture tests cover login redirects and password
mode, host rejection, control persistence, rotating `internalMode`, battery
states, toast/flag extraction, readiness, lease rejection, and exactly one
activation click. No authenticated live browser is used.

### Batch 5: Implement The Supervisor

**Goal:** Execute the README phase machine and keep all consequential authority
outside both models.

**Steps:**

1. Create `supervisor.py` with one transition handler per documented phase.
2. Generate versioned commands for one leg at a time. Require standby before
   backend configuration and before preparing a new leg.
3. Calculate Sync Ratio, PWR, required mode, PT states, and configuration
   digest deterministically.
4. Accept stabilization operands/operator from the Backend Agent, calculate
   the result in Python, validate `0-1000`, then issue the configure command.
5. Require fresh backend and frontend observations for the same state version
   and digest before issuing a short one-time activation lease.
6. Set snapshot age and lease TTL as tested constants shorter than the
   observed mode window. Recheck all conditions at lease consumption.
7. Verify arrival, battery replacement, return, tunnel battery threshold, and
   final flag through reconciled observations.
8. On ambiguous activation, persist evidence and mark `BLOCKED`; do not create
   another lease automatically.

**Checkpoint:** Pure supervisor tests cover every legal phase transition,
wrong/stale observations, mode rollover, expired lease, battery failure,
ambiguous activation, crash resume, and terminal completion guards.

### Batch 6: Add The Two Model-Guided Agents

**Goal:** Add separate bounded OpenAI agents without moving authorization or
stable logic into prompts.

**Steps:**

1. Create `llm_gateway.py`, `backend_agent.py`, and `frontend_agent.py` using
   OpenAI Responses API with `store=False`, strict Pydantic outputs, low output
   limits, injectable clients, and per-agent request/tool guards.
2. Give each agent only the current typed command, compact current observation,
   relevant error, and its own narrow tool definitions. Do not pass shared
   chat history or raw SQLite rows.
3. Backend Agent model duties: interpret bounded stabilization language,
   choose among permitted backend tools, and classify bounded recovery.
4. Frontend Agent model duties: choose among permitted browser tools and
   classify ambiguous DOM failures. Keep selectors and normal state parsing
   deterministic.
5. Publish all accepted actions and observations through the role adapter.
   Reject schema-valid actions that violate command kind, phase, value range,
   tool permissions, or state version.
6. Execute a supervisor-authorized `ACTIVATE_ONCE` command immediately through
   the guarded browser method after a final deterministic recheck; do not put
   model latency between lease validation and the click.

**Checkpoint:** Fake-model tests prove prompt/context separation, tool
separation, structured-output rejection, request/tool limits, no model-held
credentials, no direct phase transition, and no activation without a lease.

### Batch 7: Assemble The Offline Application

**Goal:** Produce a resumable CLI and full fake end-to-end proof before any
external call.

**Steps:**

1. Create `main.py` and keep secret-safe report assembly at the CLI boundary.
2. Implement the cooperative tick order: Supervisor, Backend Agent, Frontend
   Agent, Supervisor. Each tick must return control and update heartbeat state.
3. Provide an offline default readiness report plus explicit `--simulate`,
   `--check-models`, and `--submit` modes. Default and `--simulate` must not
   contact OpenAI, Hub, or Easytools.
4. Build a fake Hub machine, fake agent clients, and local preview fixture that
   reproduce mode rotation, flux, battery consumption/replacement, arrival,
   tunnel, errors, and flag delivery.
5. Run the complete three-leg workflow against fakes and require exactly three
   activations, a found simulated flag, and terminal phase `COMPLETED`.
6. Write safe reports under `data/L25_timetravel/runs/{run_id}/` and compact
   JSON to stdout. Never write secret-bearing request data to SQLite or logs.

**Checkpoint:** Simulation completes all three legs and default mode proves
`network_used: false`. Resume remains outside the implemented CLI contract.

### Batch 8: Validate The Real Model Boundary

**Goal:** Prove both agent schemas and recovery behavior with bounded OpenAI
calls while keeping Hub and live browser state untouched.

**Steps:**

1. Stop and request approval for real OpenAI calls.
2. Prepare TLS before creating the OpenAI client.
3. Run a small synthetic evaluation for stabilization wording, permitted tool
   choice, changed-selector classification, and invalid-action refusal.
4. Enforce explicit model/tool/request limits and record only safe usage and
   validated outputs under `data/L25_timetravel/output/`.
5. Fix failures offline; request new approval before repeating real calls.
6. Run `_agent/instructions/llm_optimization_checklist.md` in
   `non-production` mode and record the result in README. Any `NO` must be
   classified before continuing.

**Checkpoint:** Synthetic cases pass within guards, no Hub or authenticated
browser call occurred, and README records the optimization review result.

### Batch 9: Run Guarded Live Verification

**Goal:** Complete the three real legs once and preserve enough evidence to
audit every consequential action.

**Steps:**

1. Stop and request explicit approval for OpenAI, Hub, authenticated browser,
   browser mutations, and activation.
2. Run the default dry-run first. Confirm required environment names, CA bundle,
   Edge launch, writable run directory, schema version, and guard values
   without printing secrets.
3. Create the run database before contacting external systems. Reconcile the
   actual machine state; never assume discovery state and never reset it.
4. Execute `--submit` with one fresh browser context and all guards enabled.
5. On any ambiguous activation, stop as `BLOCKED`; do not click again.
6. Save raw Hub responses and any flag only under `data/L25_timetravel/`.
7. Run exact-secret and short-marker leak checks on changed files outside
   `data/L25_timetravel/`.
8. Update README with the final CLI contract, actual modules, verification,
   review evidence, completion status, and the final `What This Task Should
   Teach` section. Outside runtime data, record only safe success status.

**Checkpoint:** Hub accepts the final result, `flag_found: true` is persisted,
all three outcomes are reconciled, no blind retry or reset occurred, and the
final run report references the complete evidence trail.

## Debugging Notes

### Protected-Page Login Link

The first live attempt failed before any Hub or OpenAI request. The protected
page still exposed one correct Easytools login link, but the CSS selector
assumed that `redirect` appeared in a fixed query-string position.

The fix in `browser_tools.py` parses each visible link and requires the approved
host, `/login` path, and a `redirect` query key. The lesson is boring and useful:
a URL is structured data, not a string decoration for CSS.

### Host Command Timeout After Successful Completion

The solved live process ran slightly longer than the surrounding command
runner's 64-second wait. The runner reported a timeout, but the application
finished about one second later and had already closed its workflow with a
complete `run_report.json`, three activation responses, and three screenshots.

After a host-side timeout, inspect the newest run directory before starting
another process. A second blind run could repeat non-idempotent work even when
the first run already succeeded.

## Definition Of Done

| Requirement | Result | Evidence or limitation |
| --- | --- | --- |
| LLM design review recorded | Complete | Passed in non-production mode before implementation. |
| LLM optimization review recorded | Complete | Passed with explicitly classified workbench limitations and no blocking fix. |
| Offline network boundary | Complete | Default and `--simulate` report `network_used: false`. |
| Bounded real-model evaluation | Complete | Four schema cases passed under two requests per agent. |
| Three-leg live workflow | Complete | Run `20260718T113838Z` used exactly one confirmed activation per leg. |
| Terminal course result | Complete | Hub accepted; `flag_found: true` persisted under app runtime data. |
| Ambiguous activation policy | Complete | Browser raises a distinct ambiguous error and Supervisor persists `BLOCKED`. |
| Secret and course-data placement | Complete | Secrets stay in `.env`/memory; raw responses and flag stay under `data/L25_timetravel/`. |
| README reflects current code | Complete | Commands, modules, verification, limitations, and learning summary are current. |
| Dedicated unit/integration test suite | Not implemented | Accepted course-workbench limitation; offline simulation is the current automated proof. |
| Interrupted-run resume | Not implemented | SQLite helpers exist, but the CLI has no resume contract. |
