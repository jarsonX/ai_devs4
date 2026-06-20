# L16 Okoeditor Development Notes

## Table Of Contents

- [Useful References](#useful-references)
- [Exploration Scope](#exploration-scope)
- [API Findings](#api-findings)
- [Web UI Findings](#web-ui-findings)
- [Design Decisions](#design-decisions)
- [Open Questions](#open-questions)
- [Implementation Plan](#implementation-plan)

## Useful References

Selected from `_agent/references/INDEX.md`:

| Reference | Use |
| --- | --- |
| `L3_api_constraint_audit_and_tool_wrapping.md` | Audit the raw API before designing the internal app contract. |
| `L12_AI_Scope_and_Automation_Boundaries.md` | Keep the final app deterministic instead of building another runtime LLM explorer with little extra learning value. |
| `_agent/instructions/external_api_safety.md` | Keep external exploration bounded, guarded, and TLS-prepared. |
| `_agent/instructions/course_runtime_data_and_leak_checks.md` | Avoid leaking raw course data, full responses, or credentials into docs. |

## Exploration Scope

Exploration date: 2026-06-20.

Goal:
Understand the real `okoeditor` write contract, confirm how the current OKO
state can be read, and design a deterministic implementation boundary before
any source code exists.

Boundaries used during exploration:

- small, manual, bounded request set;
- no source implementation yet;
- no real task-changing write was intentionally sent;
- no UI edits, no UI form submissions, and no browser-side mutations;
- final successful API responses should later be preserved in runtime logs,
  because the task may return a FLAG there;
- no credentials or raw course responses should be copied into docs.

Important limitation discovered during exploration:

- malformed `update` attempts can ban the API key, and the response claims that
  the ban must be removed through the web interface.

That means future implementation must treat write validation as a first-class
guard, not as afterthought error handling.

Implementation status update:

- deterministic source implementation completed;
- real dry-run completed successfully;
- first live apply failed at `done` because the incident ticket codes in the
  titles did not match the coding rules from the notes page;
- second live apply succeeded after correcting those codes;
- runtime artifacts were sanitized afterward so ordinary files do not retain raw
  API keys or raw FLAG values.

## API Findings

### Central `verify` Contract

Observed facts:

| Topic | Finding |
| --- | --- |
| Surface style | The explored `okoeditor` API is command-based, not resource-based. |
| Supported actions | `help`, `update`, `done`. |
| Missing actions | No grounded `read`, `list`, `create`, or `delete` action was exposed through `help`. |
| Write scope | `update` accepts `page`, `id`, `action`, and optional `title`, `content`, plus `done` only for tasks. |
| Verification style | `done` is a final completion check, not a mutation preview. |

Important design consequence:

- because there is no grounded `create`, the required `Komarowo` incident must
  be implemented by repurposing one existing incident record.

### `update` Safety Constraint

Observed facts:

| Topic | Finding |
| --- | --- |
| Record identity | `update` needs a 32-character hexadecimal record ID. |
| Page namespace | The same ID format appears across page types, but the request still needs the correct `page` value. |
| Failure risk | Invalid exploratory `update` calls triggered an API-key ban instead of ordinary field-level validation feedback. |
| Recovery note | The ban message stated that recovery must happen through the web interface. |

Important design consequence:

- the app must validate target existence and payload completeness before making
  any live `update` call.
- the app must preserve final raw API responses under `data/L16_okoeditor/...`
  so course completion artifacts are not lost.

## Web UI Findings

### Read Path

Observed facts:

| Topic | Finding |
| --- | --- |
| Read mechanism | Current system state is readable through an authenticated web session. |
| Auth inputs | The login form requires operator login, operator password, and the same access key used for the API. |
| Useful pages | Incidents, tasks, notes, and users are visible after login. |
| Task-relevant pages | Incidents and tasks are sufficient for this exercise; notes are optional context only. |
| User page | Users are readable but not needed for the current workflow. |
| Mutation policy | The UI is inspection-only for this task and must never be used to edit content manually. |

Important design consequence:

- the app must combine web reads with API writes.
- the implementation must treat every UI edit or delete affordance as forbidden,
  even if the HTML exposes such links.

### Route And HTML Behavior

Observed facts:

| Topic | Finding |
| --- | --- |
| Link reliability | The rendered HTML exposes root-looking links, but the reachable authenticated pages belong to the OKO web area and must be resolved relative to that base path. |
| Record IDs | Incident and task IDs are visible in detail-link URLs and can be parsed deterministically. |
| Detail pages | Detail pages expose enough text to classify targets without browser automation or OCR. |
| Edit links | Explored edit links were not a trustworthy automation surface and should be ignored because the task requires writes through API anyway. |

Important design consequence:

- implementation should use direct HTTP session reads and HTML parsing, not a
  browser driver and not UI edit actions.

### Grounded Task Targets

Observed facts without storing raw runtime data in docs:

- one incident explicitly references Skolwin and frames the sighting as
  possible human or vehicle activity;
- one task explicitly references Skolwin and is still marked not done;
- several unrelated incidents remain available as replacement candidates for a
  fabricated `Komarowo` human-movement report;
- at least one unrelated candidate should be chosen from lower-context,
  short-description incidents to minimize collateral semantic conflict.

Important design consequence:

- target resolution can be content-based and deterministic rather than driven by
  hardcoded IDs.

### Coding Note That Unblocked The Final Solve

Observed fact:

- the notes page `Metody kodowania incydentów` defined the exact incident code
  meanings:
  - `MOVE01` = człowiek
  - `MOVE02` = pojazd
  - `MOVE03` = pojazd + człowiek
  - `MOVE04` = zwierzęta

Important design consequence:

- reclassifying the Skolwin incident to animals required changing the title code
  to `MOVE04`, not merely rewriting the prose;
- creating the fake Komarowo human-movement incident required changing its code
  to `MOVE01`;
- the first live run failed because the app preserved the old codes, and the
  final `done` gate correctly rejected that.

## Design Decisions

### 1. Final Runtime Should Stay Deterministic

Reason:
The hard part of this task is not semantic interpretation.
It is contract discipline:

- reading HTML consistently;
- resolving the right records;
- avoiding write mistakes that can ban the key;
- verifying that the intended changes are really visible before `done`.

Those are deterministic responsibilities.
An LLM was useful for design-time exploration, but putting a model in the live
mutation loop would mostly add failure surface.

### 2. The App Must Use Hybrid I/O

Reason:
The explored API is not enough on its own.

- Reads come from the OKO web session.
- Writes go to the central `verify` API.

Pretending the task is single-interface CRUD would be false and would produce a
bad design immediately.

### 3. The Web UI Is A Read-Only Sensor, Not A Write Surface

Reason:
The user constraint is explicit and non-negotiable.
The UI exists only to let us inspect current state and resolve target IDs.

That means the implementation must:

- never submit edit forms in the UI;
- never automate UI mutations through a browser;
- never treat UI delete or edit links as operational options;
- perform every real content change through the central API only.

### 4. IDs Should Be Resolved At Runtime, Not Hardcoded

Reason:
The IDs are discoverable, but they are still external state.
Hardcoding them would turn a stable parser problem into a brittle historical
snapshot problem.

The implementation should:

1. fetch list pages;
2. follow or parse record links;
3. resolve targets by title and content rules;
4. only then build write payloads.

### 5. Dry-Run Must Be The Default Mode

Reason:
An invalid write can ban the key.

So the implementation should:

- plan the three mutations first;
- write a local report;
- require explicit `--apply` for live changes;
- re-read the changed records before sending `done`.

The live apply path should also persist:

- every write response in masked operational logs;
- the final raw `done` response in runtime data, because that is the most
  likely place where a FLAG will appear.

### 6. The Komarowo Incident Must Be A Replacement, Not A Creation

Reason:
No grounded create action was discovered.
The safest deterministic approach is to select one unrelated active incident and
overwrite its title plus content with a human-movement report near Komarowo.

Selection rule proposed for implementation:

- avoid the Skolwin incident itself;
- avoid already task-coupled Skolwin content;
- prefer a short, generic, unrelated incident with lower semantic stakes than a
  detailed long-form report that already describes a major destroyed city.

### 7. Title Codes Are Part Of The Business State, Not Mere Decoration

Reason:
The `done` gate proved that the code prefix in the incident title is a semantic
field, not cosmetic text.

That means the implementation must:

- treat the title code as structured state;
- override it when the classification changes;
- verify the final visible title, not only the body content.

## Open Questions

Remaining non-blocking questions:

- Does the web interface really expose a user-facing unban control, or is the
  ban message only partially truthful?
- Should the workflow keep a dedicated rule table for every known ticket code if
  the exercise is ever revisited with broader mutation scope?

## Implementation Plan

### Batch 0: Design And Contract Freeze

Status: Completed.

Goal:
Turn manual exploration into a stable deterministic app boundary.

Steps:

1. Read the exercise and repository instructions.
2. Explore the central API with bounded calls.
3. Explore the authenticated OKO web read path.
4. Record the grounded contract and the no-LLM runtime decision in docs.

Checkpoint:

- README and DEV_NOTES exist;
- the hybrid read/write contract is explicit;
- runtime LLM usage is classified as `No`.

### Batch 1: Session Bootstrap And HTML Fixture Capture

Status: Completed.

Goal:
Implement safe authenticated reads and save local fixtures for parser tests.

Steps:

1. Add config loading for OKO web credentials and URLs.
2. Build a guarded web session client with TLS preparation.
3. Fetch incidents and tasks pages in dry-run mode.
4. Save masked metadata plus HTML fixtures under `data/L16_okoeditor/cache/`.
5. Prepare the logging layout so later live runs can persist final API
   responses under runtime data without touching docs.

Checkpoint:

- the app can log in and fetch the required pages;
- saved fixtures support offline parser tests;
- runtime directories for later logs and outputs are ready;
- no raw secrets are written outside `.env`.

Stop for approval before continuing if:

- the planned read path requires broader scraping than currently designed;
- new external endpoints appear necessary.

### Batch 2: Deterministic Parsing And Target Resolution

Status: Completed.

Goal:
Resolve the exact records to update without hardcoded IDs.

Steps:

1. Parse list pages and extract record links plus visible metadata.
2. Fetch detail pages for candidate incidents and tasks.
3. Normalize titles, summaries, statuses, and body text into typed models.
4. Implement deterministic resolution rules for:
   - the Skolwin incident;
   - the Skolwin task;
   - a safe unrelated incident for Komarowo.

Checkpoint:

- the app produces a stable three-target plan from saved fixtures;
- unit tests prove target resolution without network writes.

### Batch 3: Write Payload Builder And Safety Guards

Status: Completed.

Goal:
Prepare valid update payloads while minimizing the risk of API-key bans.

Steps:

1. Add page-aware payload validators.
2. Build deterministic replacement text templates.
3. Add dry-run report output.
4. Require explicit `--apply` before any live `update`.
5. Define the runtime artifact names for write responses and the final `done`
   response.

Checkpoint:

- the app refuses incomplete payloads locally;
- no live write occurs in default mode;
- the dry-run report clearly shows all planned mutations.

Stop for approval before continuing if:

- implementation proposes any runtime LLM scope expansion;
- payload design requires wider content rewriting than the current task.

### Batch 4: Live Apply, Re-Read Verification, And `done`

Status: Completed.

Goal:
Execute the real task safely and stop if verification is incomplete.

Steps:

1. Send the three `update` requests in a deterministic order.
2. Re-read the affected pages and confirm the intended visible state.
3. Call `done` only if all three checks pass.
4. Persist the raw final `done` response under runtime data.
5. Write a final run report under runtime data.

Checkpoint:

- all required edits are visible in the post-write snapshot;
- `done` is sent only after deterministic verification;
- the raw final API response is preserved for later FLAG inspection;
- final task status is captured without leaking raw course data into docs.

Stop for approval before continuing if:

- the API key is still banned and recovery needs an unknown manual action;
- live behavior contradicts the explored contract in a way that changes the app
  architecture.

## Final Outcome

Final result:

- the task was solved on 2026-06-20 through API-only mutations;
- the decisive bug was incorrect incident ticket codes in rewritten titles;
- once the app switched Skolwin to `MOVE04` and Komarowo to `MOVE01`, the final
  `done` action succeeded;
- post-run sanitization removed raw API keys and raw FLAG values from ordinary
  working files.
