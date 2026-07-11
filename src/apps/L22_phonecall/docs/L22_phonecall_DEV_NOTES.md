# L22 Phonecall DEV Notes

## Table Of Contents

- [Resume Here](#resume-here)
- [Agent Rules](#agent-rules)
- [Batch Status](#batch-status)
- [Implementation Queue](#implementation-queue)
- [Review Checklist](#review-checklist)
- [Update Protocol](#update-protocol)
- [Decision Log](#decision-log)
- [Run Notes](#run-notes)

## Resume Here

Current batch: `Complete: Live Solve Done`.

Current status: `READY_FOR_LOCAL_IMPLEMENTATION`.

Next action:

1. Keep successful live artifacts under `data/L22_phonecall/calls/20260711T083231570349Z/`.
2. Treat real `--submit` orchestration as follow-up; the task was solved through bounded inspection modes.
3. Before future live reruns, review the wording fixes recorded below.

Do not do yet:

- do not implement prompt text beyond constants needed for CLI/config;
- do not implement OpenAI clients;
- do not make real Hub calls;
- do not make real OpenAI calls.

Last verified:

| Date | Check | Result |
| --- | --- | --- |
| 2026-07-11 | README created | Done |
| 2026-07-11 | DEV_NOTES rewritten for agent use | Done |
| 2026-07-11 | LLM design checklist | Passed for MVP scope |
| 2026-07-11 | Batch 1 smoke checks | Import, `--help`, and `--dry-run` passed |
| 2026-07-11 | Batch 2 tests | `unittest src.apps.L22_phonecall.workbench.test_state_and_guards` passed |
| 2026-07-11 | Batch 3 tests | `unittest ...test_state_and_guards ...test_run_log` passed |
| 2026-07-11 | Batch 4 tests | `unittest ...test_state_and_guards ...test_run_log ...test_verify_client` passed |
| 2026-07-11 | Batch 5 tests | `unittest ...test_state_and_guards ...test_run_log ...test_verify_client ...test_conversation_interpreter` passed |
| 2026-07-11 | Batch 6 tests | `unittest ...test_state_and_guards ...test_run_log ...test_verify_client ...test_conversation_interpreter ...test_response_planner` passed |
| 2026-07-11 | Batch 7 tests | `unittest ...test_state_and_guards ...test_run_log ...test_verify_client ...test_conversation_interpreter ...test_response_planner ...test_audio_gateway` passed |
| 2026-07-11 | Batch 8 tests | full local `unittest` suite passed; `--dry-run`, `--simulate-audio`, and `--submit` smoke checks passed |
| 2026-07-11 | Batch 9 tests | full local `unittest` suite passed with password, reason, and failure workflow regressions |
| 2026-07-11 | OpenAI adapter tests | full local `unittest` suite passed with fake OpenAI SDK adapter coverage |
| 2026-07-11 | Live inspection prep tests | full local `unittest` suite passed with fake live-start inspection and Hub response normalization coverage |
| 2026-07-11 | Successful live solve | bounded inspection run completed; Hub returned a flag and operator confirmed monitoring disabled |
| 2026-07-11 | Final local tests | full local `unittest` suite passed with 56 tests after live wording/parser fixes |

Source of truth:

| Topic | File |
| --- | --- |
| Accepted app design and LLM review status | `src/apps/L22_phonecall/docs/L22_phonecall_README.md` |
| Agent implementation progress and next action | `src/apps/L22_phonecall/docs/L22_phonecall_DEV_NOTES.md` |
| Runtime call artifacts | `data/L22_phonecall/...` |

## Agent Rules

These rules are for any agent resuming this work.

Hard gates:

1. If README design review is not `Passed`, stop before source implementation.
2. Ask for approval before real Hub calls.
3. Ask for approval before real OpenAI calls.
4. Ask for approval before dependency installation.
5. Store secrets only in `.env`.
6. Store runtime artifacts only under `data/L22_phonecall/...`.
7. Do not store raw Hub responses or flags outside `data/L22_phonecall/...`.
8. Keep source directories under `src/apps/L22_phonecall/...` for source and app docs only.

Implementation style:

- Use `.\venv\Scripts\python.exe` for Python commands.
- Add short purpose comments for every class, function, and method.
- Prefer deterministic code for state, guards, validation, and payload shape.
- Use model calls only behind explicit gateways and request guards.
- Validate every model output before downstream use.
- Keep Hub access outside model control.
- Use fake clients before live clients.

Completion rule:

- After each batch, update `Batch Status`, `Run Notes`, and the README if the app contract changed.

## Batch Status

Status values:

- `PENDING`: not started.
- `IN_PROGRESS`: actively being implemented.
- `DONE`: implemented and checkpoint passed.
- `BLOCKED`: cannot proceed without user approval, design change, or external state.
- `SKIPPED`: intentionally not needed, with reason in `Run Notes`.

| Batch | Status | Checkpoint | Main files |
| --- | --- | --- | --- |
| 0. Design Gate | DONE | README design review recorded as `Passed` | README |
| 1. Skeleton And Config | DONE | import smoke check and `--help` pass | `__init__.py`, `config.py`, `models.py`, `main.py` |
| 2. State And Guards | DONE | state and utterance unit tests pass | `state_machine.py`, `utterance_guard.py` |
| 3. Logging | DONE | fake call writes text/audio/log artifacts | `run_log.py` |
| 4. Hub Client | DONE | fake-session payload and masking tests pass | `verify_client.py` |
| 5. Interpreter | DONE | transcript fixture interpretation tests pass | `conversation_interpreter.py` |
| 6. Planner | DONE | planner and fallback tests pass | `response_planner.py` |
| 7. Audio Gateway | DONE | fake STT/TTS tests pass | `audio_gateway.py` |
| 8. Workflow | DONE | `--dry-run` and fake `--simulate-audio` pass | `workflow.py`, `main.py` |
| 9. Fixtures And Regression | DONE | full local fixture suite passes | tests and fixtures |
| 10. Live Inspection | DONE | real response shape documented | runtime artifacts, README/notes |
| 11. Live Solve | DONE | Hub accepts task or clear failure recorded | runtime artifacts, README |
| 12. Optimization Review | DONE | README records optimization review result | README |

Current blocker:

- No blocker for the solved run. Full `--submit` orchestration remains a follow-up, not needed for this completion.

## Implementation Queue

### Batch 0: Design Gate

Purpose: approve the LLM workflow before writing source code.

Actions:

1. Read README.
2. Read `_agent/instructions/llm_design_checklist.md`.
3. Review scope:
   `L22 phonecall MVP dynamic chained voice pipeline with state-machine-controlled conversation, logging, STT, interpreter, planner, utterance guard, TTS, and guarded Hub submission`.
4. Mark each checklist item `YES`, `NO`, or `N/A`.
5. If all required items pass, update README:
   - `Design review`: `Passed`;
   - date;
   - checklist path;
   - reviewed scope;
   - approved implementation boundary.
6. If any item is `NO`, update README design and rerun checklist.

Checkpoint:

- README design review says `Passed`.

Stop if:

- checklist produces any `NO`;
- review implies architecture, data-flow, or LLM-scope changes.

### Batch 1: Skeleton And Config

Purpose: create importable app scaffolding without external calls.

Actions:

1. Create `src/apps/L22_phonecall/__init__.py`.
2. Create `config.py`.
3. Create `models.py`.
4. Create `main.py` with CLI modes:
   - `--dry-run`;
   - `--simulate-audio`;
   - `--submit`.
5. Do not require secrets for `--help` or dry modes.

Checkpoint:

```powershell
.\venv\Scripts\python.exe -c "import src.apps.L22_phonecall; print('import ok')"
.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --help
```

Review focus:

- no external calls;
- no eager secret loading in dry modes;
- app constants live in `config.py`;
- source comments follow repo rules.

### Batch 2: State And Guards

Purpose: implement the deterministic safety core.

Actions:

1. Implement `state_machine.py`.
2. Implement `utterance_guard.py`.
3. Add deterministic fallback utterances.
4. Add unit tests for:
   - normal path;
   - password challenge;
   - reason challenge;
   - multiple passable roads;
   - no passable roads;
   - forbidden `Syjon` mention;
   - premature monitoring request.

Checkpoint:

- state and guard tests pass.

Review focus:

- model output cannot force illegal actions;
- monitoring request requires validated passable road;
- first assistant utterance includes identity and all three road IDs.

### Batch 3: Logging

Purpose: make every turn inspectable.

Actions:

1. Implement `run_log.py`.
2. Write per-turn artifacts:
   - `operator.raw.json`;
   - `operator.audio.*`;
   - `operator.transcript.txt`;
   - `operator.interpretation.json`;
   - `assistant.plan.json`;
   - `assistant.utterance.txt`;
   - `assistant.audio.mp3`;
   - `hub_request.masked.json`;
   - `hub_response.raw.json`.
3. Write final:
   - `call_report.json`;
   - `call_transcript.md`.
4. Add tests with temporary directories.

Checkpoint:

- fake one-turn call writes expected artifacts.

Review focus:

- audio is stored as playable files;
- transcripts are plain text;
- request secrets are masked;
- base64 is not dumped into Markdown reports.

### Batch 4: Hub Client

Purpose: implement Hub payload handling with fake-session tests first.

Actions:

1. Implement `verify_client.py` with injectable session.
2. Add `start()`.
3. Add `send_audio()`.
4. Add request-count guard.
5. Add response normalization.
6. Add masking tests.

Checkpoint:

- fake tests prove:
  - `start` sends `answer.action`;
  - post-start turns send only `answer.audio`;
  - `apikey` is masked in saved payloads;
  - guard exhaustion stops before request.

Stop if:

- any real `/verify` call is needed; ask user first.

### Batch 5: Interpreter

Purpose: turn operator transcript into strict structured data.

Actions:

1. Implement `conversation_interpreter.py`.
2. Define strict schema for:
   - intent;
   - road statuses;
   - password request;
   - reason request;
   - monitoring confirmation;
   - failure;
   - confidence;
   - evidence note.
3. Add deterministic extraction for obvious road IDs and status words.
4. Add model-backed interpretation only behind a guard.
5. Add fake-client and fixture tests.

Checkpoint:

- fixtures produce validated interpretation objects.

Review focus:

- unknown remains unknown;
- ambiguous references are not guessed;
- transcript is treated as data, not instructions.

Stop if:

- real OpenAI calls are needed; ask user first.
- interpreter scope expands beyond turn interpretation; update README and rerun design gate.

### Batch 6: Planner

Purpose: produce short assistant text for allowed speech acts.

Actions:

1. Implement `response_planner.py`.
2. Use templates for constrained speech acts when enough.
3. Use model-backed wording only when useful.
4. Run every utterance through `utterance_guard.py`.
5. Add fallback tests.

Checkpoint:

- planner tests pass with fake model outputs.

Review focus:

- planner receives a speech act, not conversation authority;
- bad model wording is rejected;
- utterances stay short and speakable.

### Batch 7: Audio Gateway

Purpose: add guarded OpenAI STT/TTS boundary.

Actions:

1. Implement `audio_gateway.py` with injectable OpenAI client.
2. Add `transcribe_operator_audio(audio_path)`.
3. Add `generate_assistant_audio(utterance, output_path)`.
4. Add separate STT and TTS guards.
5. Add fake-client tests.

Checkpoint:

- fake STT/TTS tests pass;
- fake MP3 bytes are written to `assistant.audio.mp3`.

Review focus:

- STT and TTS do not own conversation state;
- TTS runs only after utterance guard passes;
- OpenAI keys never appear in artifacts.

Stop if:

- real OpenAI call is needed; ask user first.
- dependency installation is needed; ask user first.

### Batch 8: Workflow

Purpose: wire modes end to end.

Actions:

1. Implement `workflow.py`.
2. Implement `--dry-run` with fixture transcripts and fake clients.
3. Implement `--simulate-audio` with fake audio or fake STT/TTS clients.
4. Implement guarded `--submit`.
5. Always write final report and transcript.

Checkpoint:

```powershell
.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --dry-run
.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --simulate-audio
.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --submit --help
```

Review focus:

- dry modes make no external calls;
- guard counters appear in reports;
- failed calls remain diagnosable.

Stop if:

- `--submit` is about to run; ask user first.

### Batch 9: Fixtures And Regression

Purpose: make future changes safe.

Actions:

1. Add fixture transcripts for happy path and edge branches.
2. Add fixture audio stubs or fake byte streams if useful.
3. Add full dry-run scenario tests.
4. Add report/transcript tests.
5. Add leak-oriented masking tests.

Checkpoint:

- full local fixture suite passes.

Review focus:

- tests cover password, reason, ambiguity, and failure branches;
- artifacts show what the bot heard, decided, said, and sent.

### Batch 10: Live Inspection

Purpose: inspect real Hub response shape with minimal external usage.

Actions:

1. Ask user for approval for real Hub and OpenAI calls.
2. Run smallest bounded live inspection.
3. Store artifacts under `data/L22_phonecall/calls/{call_id}/`.
4. Update README/notes with non-sensitive findings.

Checkpoint:

- real response shape is known and documented.

Stop if:

- response shape requires design change;
- more external calls are needed than approved.

### Batch 11: Live Solve

Purpose: complete the task with a guarded real run.

Actions:

1. Ask user for approval for solve attempt.
2. Run `--submit`.
3. Inspect artifacts after any failure.
4. Retry only with named cause and scoped fix.
5. Preserve successful Hub response under `data/L22_phonecall/...`.
6. Update README status and verification notes.

Checkpoint:

- Hub accepts task or failure reason is clear.

Stop if:

- guard is exhausted;
- call is burned and fix is unknown;
- architecture or model scope must change.

### Batch 12: Optimization Review

Purpose: finish according to repository LLM rules.

Actions:

1. Read `_agent/instructions/llm_optimization_checklist.md`.
2. Review completed workflow.
3. Record result in README `LLM Usage And Reviews`.
4. Update README `What This Task Should Teach`.
5. Run final local verification.

Checkpoint:

- README records optimization review result.

Review focus:

- app teaches dynamic voice control, not puzzle-specific audio hacks;
- runtime artifacts stay out of source;
- no secrets or raw course responses leaked outside `data/L22_phonecall/...`.

## Review Checklist

Use this when reviewing any batch.

| Area | Question |
| --- | --- |
| Current status | Does `Resume Here` match `Batch Status`? |
| Scope | Did the work stay inside README-approved design? |
| State control | Can model output force an illegal action? |
| Hub payload | Does `start` use `answer.action`, and later turns use only `answer.audio`? |
| Secrets | Are keys only in `.env` and masked in saved requests? |
| Text logs | Are transcripts and assistant utterances saved as text? |
| Audio logs | Are operator and assistant audio artifacts saved as files? |
| Model outputs | Are model outputs schema-validated before use? |
| Guards | Do Hub, STT, interpreter, planner, and TTS have hard limits? |
| Tests | Does the batch include the smallest useful verification? |

## Update Protocol

After each batch:

1. Update `Resume Here`.
2. Update `Batch Status`.
3. Add a short note under `Run Notes`.
4. Update README only if public app contract, review status, run command, or learning summary changed.
5. Keep raw Hub responses, flags, and runtime logs under `data/L22_phonecall/...`.

Run note format:

```md
### YYYY-MM-DD - Batch N

- Changed:
- Verified:
- Result:
- Next:
```

## Decision Log

### 2026-07-11 - Dynamic Audio

Production flow must generate assistant audio dynamically from the approved
utterance for the current turn. Pre-recorded production responses are rejected.
Fixture audio is allowed for tests.

### 2026-07-11 - Chained Voice Pipeline

The Hub is turn-based, so the app should use a chained pipeline:
STT -> interpretation -> state machine -> utterance guard -> TTS -> Hub audio.
Realtime speech-to-speech is not the default architecture for this task.

### 2026-07-11 - State Machine Authority

The model may interpret and phrase language, but deterministic code owns state,
allowed transitions, Hub calls, and completion checks.

### 2026-07-11 - Logs Are Productive Artifacts

Every run should preserve both text and audio for review. A failed call without
transcript, state, and audio artifacts is not useful enough to debug.

## Run Notes

### 2026-07-11 - Documentation Setup

- Changed: created README and rewrote DEV_NOTES for agent-first usage.
- Verified: documentation paths exist; no runtime tests were run.
- Result: implementation is blocked until Batch 0 passes.
- Next: run LLM design checklist against README.

### 2026-07-11 - Batch 0

- Changed: reviewed README design against `_agent/instructions/llm_design_checklist.md`.
- Verified: design review recorded as PASS in README.
- Result: source implementation may start inside the MVP boundary.
- Next: implement Batch 1 skeleton and config without external calls.

### 2026-07-11 - Batch 1

- Changed: added package skeleton, config loader, shared models, and placeholder CLI.
- Verified: import smoke check, `--help`, and `--dry-run`.
- Result: dry mode no longer loads Hub or OpenAI secret-bearing config.
- Next: implement state machine and utterance guard.

### 2026-07-11 - Batch 2

- Changed: added deterministic state machine, utterance guard, fallback utterances, and workbench tests.
- Verified: `.\venv\Scripts\python.exe -m unittest src.apps.L22_phonecall.workbench.test_state_and_guards`.
- Result: 10 local tests passed.
- Next: implement run logging and artifact writer.

### 2026-07-11 - Batch 3

- Changed: added `run_log.py` and workbench tests for text, JSON, audio, transcript, report, and masking artifacts.
- Verified: `.\venv\Scripts\python.exe -m unittest src.apps.L22_phonecall.workbench.test_state_and_guards src.apps.L22_phonecall.workbench.test_run_log`.
- Result: 11 local tests passed.
- Next: implement fake-tested Hub client.

### 2026-07-11 - Batch 4

- Changed: added `verify_client.py` with injectable session, guarded `start()` and `send_audio()`, response normalization, and masked request records.
- Verified: `.\venv\Scripts\python.exe -m unittest src.apps.L22_phonecall.workbench.test_state_and_guards src.apps.L22_phonecall.workbench.test_run_log src.apps.L22_phonecall.workbench.test_verify_client`.
- Result: 16 local tests passed; dry-run still avoids Hub and OpenAI secret-bearing config.
- Next: implement transcript interpreter with fake-client and fixture tests.

### 2026-07-11 - Batch 5

- Changed: added `conversation_interpreter.py` with deterministic transcript parsing, strict model-output validation, optional fake-client fallback, and request guard.
- Verified: `.\venv\Scripts\python.exe -m unittest src.apps.L22_phonecall.workbench.test_state_and_guards src.apps.L22_phonecall.workbench.test_run_log src.apps.L22_phonecall.workbench.test_verify_client src.apps.L22_phonecall.workbench.test_conversation_interpreter`.
- Result: 24 local tests passed; ambiguous road references are not guessed by deterministic parsing.
- Next: implement response planner and guard every utterance before TTS.

### 2026-07-11 - Batch 6

- Changed: added `response_planner.py` with deterministic templates, optional fake model wording, utterance guard validation, fallback on unsafe model output, and request guard.
- Verified: `.\venv\Scripts\python.exe -m unittest src.apps.L22_phonecall.workbench.test_state_and_guards src.apps.L22_phonecall.workbench.test_run_log src.apps.L22_phonecall.workbench.test_verify_client src.apps.L22_phonecall.workbench.test_conversation_interpreter src.apps.L22_phonecall.workbench.test_response_planner`.
- Result: 29 local tests passed; unsafe model wording falls back to deterministic text.
- Next: implement fake-tested audio gateway for STT and TTS file handling.

### 2026-07-11 - Batch 7

- Changed: added `audio_gateway.py` with injectable STT/TTS client, separate guards, transcript normalization, and MP3 byte writing.
- Verified: `.\venv\Scripts\python.exe -m unittest src.apps.L22_phonecall.workbench.test_state_and_guards src.apps.L22_phonecall.workbench.test_run_log src.apps.L22_phonecall.workbench.test_verify_client src.apps.L22_phonecall.workbench.test_conversation_interpreter src.apps.L22_phonecall.workbench.test_response_planner src.apps.L22_phonecall.workbench.test_audio_gateway`.
- Result: 34 local tests passed; fake audio gateway writes assistant audio files and stops before guard-exceeding calls.
- Next: wire local workflow and CLI modes with fake clients.

### 2026-07-11 - Batch 8

- Changed: added `workflow.py`, wired `main.py` to real local `--dry-run` and fake `--simulate-audio`, added submit approval gate, and made call IDs microsecond-granular to avoid artifact collisions.
- Verified: full local unittest suite; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --dry-run`; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --simulate-audio`; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --submit`.
- Result: 37 local tests passed; dry-run and simulated audio both completed to `MONITORING_CONFIRMED`; submit returned `approval_required` without external calls.
- Next: broaden local fixtures and regression coverage.

### 2026-07-11 - Batch 9

- Changed: expanded workflow regression tests for password challenge, reason challenge, and failed-call branch; workflow now stops failed calls without trying to plan `restart_session` audio in the burned call.
- Verified: full local unittest suite; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --dry-run`; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --simulate-audio`.
- Result: 40 local tests passed; password, reason, failure, dry-run, and simulated-audio branches are covered.
- Next: stop for approval before live inspection or real OpenAI/Hub integration.

### 2026-07-11 - OpenAI Adapter Prep

- Changed: added `openai_gateway.py` with real OpenAI SDK adapters for STT, TTS, interpreter structured output, and planner structured output; all are still behind injectable boundaries.
- Verified: full local unittest suite including `src.apps.L22_phonecall.workbench.test_openai_gateway`.
- Result: 44 local tests passed; no real OpenAI or Hub calls were made.
- Next: ask for approval before the smallest live Hub/OpenAI inspection.

### 2026-07-11 - Live Inspection Prep

- Changed: added `live_inspection.py` and CLI `--inspect-live` for exactly one guarded Hub `start` request with runtime artifact logging.
- Verified: full local unittest suite including `src.apps.L22_phonecall.workbench.test_live_inspection`; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --help`; `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --submit`.
- Result: 45 local tests passed; `--submit` still returns `approval_required`; no real Hub/OpenAI calls were made.
- Next: ask for approval before running `--inspect-live`.

### 2026-07-11 - Live Start Inspection

- Changed: ran one approved live Hub `start` inspection and added `hub_response.py` for conservative `msg` text versus base64 audio normalization.
- Verified: `.\venv\Scripts\python.exe -m src.apps.L22_phonecall.main --inspect-live`; full local unittest suite including `src.apps.L22_phonecall.workbench.test_hub_response`.
- Result: Hub returned HTTP 200 with payload keys `action`, `code`, `message`, and `msg`; `msg` was text, not audio; 49 local tests passed after adding response normalization.
- Next: prepare, but do not run without approval, an inspection that sends the first generated assistant audio turn.

### 2026-07-11 - Successful Live Solve

- Changed: iterated live wording and parser rules based on Hub hints and STT transcripts: clarified `Tymon` pronunciation, replaced fragile `zywnosci` with `jedzenia`, justified monitoring shutdown as a secret operation ordered by Zygfryd, used lowercase `barbakan`, and expanded parser handling for `RD-820`, `podobnie`, and `jedyne co zostalo`.
- Verified: bounded live run under `data/L22_phonecall/calls/20260711T083231570349Z/`.
- Result: Hub returned a flag in turn 007 and operator transcript confirmed monitoring was disabled.
- Next: record optimization review and final verification.

### 2026-07-11 - Optimization Review

- Changed: recorded `_agent/instructions/llm_optimization_checklist.md` review result in README.
- Verified: README `LLM Usage And Reviews` includes optimization review status; full local unittest suite passed with 56 tests.
- Result: review passed in non-production mode with follow-up to convert inspection commands into one-command `--submit`.
- Next: no required work for solved run.
