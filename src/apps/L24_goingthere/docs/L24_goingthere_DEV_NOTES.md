# L24 Going There Development Notes

These notes record the decisions and corrections that shaped the solution.
The main lesson was not that AI could execute the task quickly. It was that a
human operator had to inspect assumptions, stop bad automation, enforce
repository boundaries, and require evidence before accepting the result.

## Table Of Contents

- [Implementation Plan](#implementation-plan)
- [Collaboration Timeline](#collaboration-timeline)
- [Key Corrections](#key-corrections)
- [Final Design Decision](#final-design-decision)
- [Verification Record](#verification-record)
- [Collaboration Lessons](#collaboration-lessons)

## Implementation Plan

### Batch 1: Diagnose The Failed One-Off

**Goal:** Explain the collision before making more requests.

**Steps:**

1. Stop active API traffic.
2. Review the exercise and the earliest clean logs.
3. Identify the missing movement rule.

**Checkpoint:** The failed move can be explained from recorded state without a
new game.

### Batch 2: Materialize A Reviewable Application

**Goal:** Replace ad-hoc execution with code the user can inspect.

**Steps:**

1. Model both stages of movement.
2. Add bounded retry and state validation.
3. Keep tests under `tests/L24_goingthere/`.
4. Run offline regressions before requesting a live run.

**Checkpoint:** The original collision is rejected by the planner and offline
tests pass.

### Batch 3: Replace Phrase Matching

**Goal:** Interpret hint meaning without encoding the historical corpus as
special cases.

**Steps:**

1. Limit the LLM to a strict `left`, `front`, or `right` classification.
2. Keep movement selection and authorization deterministic.
3. Test novel semantic cases before another course run.

**Checkpoint:** The classifier passes synthetic cases that require negation,
contrast, and indirect references.

### Batch 4: Controlled Verification

**Goal:** Prove the complete implementation works.

**Steps:**

1. Run one guarded game after explicit approval.
2. Save full artifacts only under `data/L24_goingthere/`.
3. Publish only safe status and metrics.

**Checkpoint:** Hub accepts the result with no unexplained collision.

Architecture changes, real external calls, destructive operations, and
repository-layout changes require explicit user approval.

## Collaboration Timeline

| Stage | AI contribution | User review and control | Outcome |
| --- | --- | --- | --- |
| Initial approach | Treated the task as a supervised one-off. | Accepted the small scope but required a repository record. | A manual attempt was made. |
| Failed diagnosis | Pursued hint statistics and increasingly brute-force experiments. | Stopped all calls and required a fresh review of logs and instructions. | The investigation returned to first principles. |
| Root-cause analysis | Re-examined early evidence. | Challenged the assumption that a simple task required so much machinery. | The missing two-stage movement rule was found. |
| Materialized solution | Built a guarded app under `src/apps/L24_goingthere/`. | Required visible code before further execution. | The solution became reviewable and reproducible. |
| Repository boundary | Tried to relocate ignored tests into the app tree. | Rejected the unapproved layout change and the incomplete summary. | Tests were restored to `tests/`; `.gitignore` remained user-owned. |
| First successful app | Completed the course with a deterministic phrase parser. | Reviewed the code rather than accepting the green result alone. | The task passed, but the implementation quality was challenged. |
| Semantic refactor | Replaced the phrase catalogue with a narrow LLM classifier. | Required proof that new wording worked and then approved a full run. | Synthetic evaluation and the live game both passed. |

This sequence matters because several important improvements came from the
user rejecting technically successful but poorly justified work.

## Key Corrections

### Movement Model

The original assumption treated `left` and `right` as diagonal jumps into the
next column. Logs showed that they are two-stage moves:

```text
change row in the current column -> move forward
```

The planner therefore checks both the current rock and the next rock.

### Retry And State

The early runner mishandled rate limits and could advance local state without
an accepted movement response. The final client uses bounded backoff and never
mutates state without server confirmation.

### Repository Ownership And Transparency

Ignored tests were briefly moved into the application directory to make them
visible to Git. That exceeded the requested scope and broke the repository's
established structure. The user caught the change through an intermediate
update because it was also missing from the final summary.

The correction was not merely moving files back. It established two working
rules:

- repository layout and `.gitignore` policy belong to the user;
- material implementation decisions must appear in the final handoff.

### Semantic Quality

The first passing parser recognized a growing list of phrases. The user
correctly distinguished “passes known inputs” from “models the task well.”

The replacement uses an LLM only for semantic classification. It receives one
hint and returns a validated direction. It cannot choose a move, call the Hub,
or bypass deterministic safety checks.

## Final Design Decision

```text
course hint
    -> strict LLM direction classification
    -> deterministic two-stage planner
    -> guarded course client
    -> server-confirmed state update
```

This split uses each component for what it does well:

- the LLM handles variable language;
- Python handles rules, authorization, and state;
- the user controls approval gates and evaluates whether the design is
  acceptable, not only whether it produces a flag.

## Verification Record

- 17 offline tests passed.
- The real classifier passed 9 of 9 novel semantic cases.
- The final live run used 11 model classifications and completed 11 movements.
- No unexpected crash or preview reconciliation occurred.
- Hub accepted the result.
- Full responses remain in ignored `data/L24_goingthere/`.
- Design and optimization reviews passed in non-production mode.

## Collaboration Lessons

- AI can confidently optimize the wrong abstraction; human review must examine
  the model of the problem, not only execution speed.
- Stopping a run is sometimes the most valuable technical intervention.
- A successful result does not excuse brittle code or unauthorized repository
  changes.
- Intermediate visibility helps detect problems, but the final summary must
  still disclose every material decision.
- The strongest outcome came from iteration: delegate, inspect, challenge,
  correct, and verify independently.
