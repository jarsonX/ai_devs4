# L25 Timetravel Development Notes

Execution plan for the AI agent implementing the application. The README owns
the product and external contracts; this file owns implementation order.

## Table Of Contents

- [Implementation Rules](#implementation-rules)
- [Implementation Plan](#implementation-plan)
- [Definition Of Done](#definition-of-done)

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
5. Use one process and a cooperative round-robin scheduler. One tick handles
   at most one bounded unit for the Supervisor, Backend Agent, or Frontend
   Agent. Do not introduce threads, subprocess workers, or long-lived WAL.
6. Agents communicate only through typed SQLite commands and observations.
   They keep separate prompts, model context, tool sets, and request guards.
   They never call one another directly.
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

1. Create `run_log.py` and `main.py`.
2. Implement the cooperative tick order: Supervisor, Backend Agent, Frontend
   Agent, Supervisor. Each tick must return control and update heartbeat state.
3. Provide offline default output plus explicit `--preflight`, `--simulate`,
   `--live`, and `--resume RUN_ID` modes. `--preflight` and `--simulate` must
   not contact OpenAI, Hub, or Easytools.
4. Build a fake Hub machine, fake agent clients, and local preview fixture that
   reproduce mode rotation, flux, battery consumption/replacement, arrival,
   tunnel, errors, and flag delivery.
5. Run the complete three-leg workflow, forced failures, and crash/resume
   paths against fakes.
6. Write safe reports under `data/L25_timetravel/runs/{run_id}/` and compact
   JSON to stdout. Never write secret-bearing request data to SQLite or logs.

**Checkpoint:** All offline tests pass; simulation completes all three legs;
default and preflight modes prove `network_used: false`; a killed simulation
resumes from SQLite without duplicate commands or activation.

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
2. Run local preflight first. Confirm required environment names, CA bundle,
   Edge launch, writable run directory, schema version, and guard values
   without printing secrets.
3. Create the run database before contacting external systems. Reconcile the
   actual machine state; never assume discovery state and never reset it.
4. Execute `--live` with one fresh browser context and all guards enabled.
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

## Definition Of Done

- Full-scope LLM design and optimization reviews are recorded as passed or
  have no blocking `NO` items.
- Default, preflight, simulation, and live modes have explicit and tested
  network boundaries.
- Offline specification, coordination, Hub, browser, supervisor, agent, and
  end-to-end tests pass.
- The live workflow completes all three legs with one audited activation per
  leg and no ambiguous retry.
- SQLite can resume an interrupted non-ambiguous run without duplicating work.
- Secrets and reusable browser authentication state exist only in `.env` or
  process memory.
- Raw Hub responses and flags exist only under `data/L25_timetravel/`.
- README describes the implemented application rather than the plan.
