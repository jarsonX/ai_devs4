# EDU1

EDU1 is an educational app inspired by `L2_findhim`.
Its goal is to explain the core idea of an agent-style application without the full complexity of the reference app.

## Table Of Contents

- [Purpose](#purpose)
- [Current Business Goal](#current-business-goal)
- [Role Of OpenAI](#role-of-openai)
- [Expected Output](#expected-output)
- [Workflow Stages](#workflow-stages)
  - [1. Setup](#1-setup)
  - [2. Selection](#2-selection)
  - [3. Finalize](#3-finalize)
- [Responsibility Split](#responsibility-split)
- [Planned Tools](#planned-tools)
  - [Setup Tools](#setup-tools)
  - [Selection Tools](#selection-tools)
  - [Finalize Tools](#finalize-tools)
- [Tool Exposure Strategy](#tool-exposure-strategy)
- [Planned Agent State](#planned-agent-state)
- [Stage Completion Rules](#stage-completion-rules)
- [Selected City Validation Rule](#selected-city-validation-rule)
- [Planned Stage Flow](#planned-stage-flow)
- [Planned File Structure](#planned-file-structure)
- [File Responsibilities](#file-responsibilities)
- [Boundary Rules](#boundary-rules)
- [Planned Internal Contents](#planned-internal-contents)
- [Planned Functions And Contracts](#planned-functions-and-contracts)
  - [`models.py`](#modelspy)
  - [`config.py`](#configpy)
  - [`data_loader.py`](#dataloaderpy)
  - [`api_client.py`](#apiclientpy)
  - [`tools.py`](#toolspy)
  - [`agent.py`](#agentpy)
  - [`pipeline.py`](#pipelinepy)
  - [`main.py`](#mainpy)
- [Validation And Error Rules](#validation-and-error-rules)
- [Serialization Rule](#serialization-rule)
- [Assumptions](#assumptions)
- [Status](#status)
- [What This Task Should Teach](#what-this-task-should-teach)

## Purpose

The app is meant for learning:

- staged tool usage,
- limiting tool exposure at each stage,
- passing data between steps,
- separating code from model reasoning,
- keeping business logic simple while still using a staged agent workflow,
- validating model output before using it.

This app should mirror selected ideas from `L2_findhim`, but in a much smaller and easier-to-follow form.

## Current Business Goal

The app should:
1. load people data from `data/EDU1/input/data_people.json`,
2. extract the business payload from `payload_sent.answer`,
3. collect the unique city names from that list,
4. ask OpenAI to choose the city located farthest south from the provided list,
5. find the single person who comes from that city,
6. fetch that person's `accessLevel`,
7. produce the final result.

## Role Of OpenAI

OpenAI is not responsible for the whole task.
Its role is limited to a narrow decision:

- receive a closed list of city names,
- return exactly one city from that list,
- choose the city that is farthest south.

The model should not invent new city names or rewrite the provided values.
The model is not responsible for loading files, extracting payloads, or passing large raw payloads between deterministic steps.

## Expected Output

The business result should contain:
- the selected person,
- the selected city,
- the person's `accessLevel`.

## Workflow Stages

The app is currently planned as a 3-stage workflow:

### 1. Setup

Goal:
- load the JSON file,
- extract `payload_sent.answer`,
- convert raw data into a clean people list,
- collect unique city names.

This stage should be fully deterministic.
In the current implementation, this stage is executed directly by application code before the model-driven stages begin.

### 2. Selection

Goal:
- send the closed city list to OpenAI,
- receive one selected city,
- validate that the returned value belongs to the provided list,
- find the person from that city.

This is the only stage where OpenAI provides task-specific world knowledge.

### 3. Finalize

Goal:
- fetch `accessLevel` for the selected person,
- build the final result object.

This stage should use deterministic code and external API integration.

## Responsibility Split

The current design keeps responsibilities narrow:

- OpenAI chooses the southernmost city from a closed list.
- Application code performs deterministic setup, validates structure, validates model output, selects the person, calls the AI_devs API, and builds the final result.

This split keeps the agent useful without making it responsible for the entire business flow.

## Planned Tools

The current tool plan contains 7 tools grouped by workflow stage.

### Setup Tools

- `load_people_data`
  Loads the raw JSON object from `data/EDU1/input/data_people.json`.
- `extract_people_payload`
  Extracts `payload_sent.answer` and returns a clean list of people records.
- `extract_unique_cities`
  Collects the unique city names from the people list.

### Selection Tools

- `validate_selected_city`
  Checks whether the city selected by the model exists in the provided city list.
- `find_person_by_city`
  Returns the single person assigned to the selected city.

### Finalize Tools

- `get_access_level`
  Fetches `accessLevel` for the selected person from the AI_devs API.
- `build_final_result`
  Builds the final business result object.

## Tool Exposure Strategy

The model-driven agent should not see all tools at once.
Instead, each model-driven stage should expose only the tools needed for that stage:

- `selection`: `validate_selected_city`, `find_person_by_city`
- `finalize`: `get_access_level`, `build_final_result`

This follows the learning goal taken from `L2_findhim`:
- keep the workflow staged,
- reduce unnecessary tool choices,
- make each step easier to understand and debug.

The deterministic `setup` stage still uses the setup tools, but it is executed directly by application code instead of by the model.

## Planned Agent State

The current plan uses a small shared runtime state.
The state should contain only the values needed to move between stages:

- `rawData`
- `people`
- `cities`
- `selectedCity`
- `selectedPerson`
- `accessLevel`
- `result`

Each field represents one important milestone in the workflow.

## Stage Completion Rules

The current stage completion conditions are:

- deterministic `setup` is complete when `rawData`, `people`, and `cities` exist in state.
- `selection` is complete when `selectedCity` and `selectedPerson` exist in state.
- `finalize` is complete when `accessLevel` and `result` exist in state.

This keeps stage transitions explicit and easy to debug.

## Selected City Validation Rule

The model may propose a city during the `selection` stage, but the application should treat that value as untrusted until it is validated.

The agreed rule is:
- the raw model choice may appear in the transcript or debug log,
- `selectedCity` should be written to application state only after `validate_selected_city` confirms that the value belongs to the provided city list.

This keeps the runtime state limited to validated business data.

## Planned Stage Flow

The current high-level flow is:

1. `setup`
   - deterministic application code loads raw data
   - deterministic application code extracts people
   - deterministic application code extracts cities
2. `selection`
   - let the model choose a city from the closed list
   - validate the chosen city
   - find the matching person
3. `finalize`
   - fetch `accessLevel`
   - build the final result

This preserves the staged-agent pattern from `L2_findhim` in a simpler form.

## Planned File Structure

The current recommended file structure is:

- `EDU1_README.md`
  Project notes and design decisions.
- `main.py`
  Thin application entrypoint. It should call the pipeline runner.
- `pipeline.py`
  End-to-end application flow.
- `agent.py`
  Staged agent loop, tool exposure per stage, and runtime state handling.
- `tools.py`
  Tool definitions and deterministic tool execution.
- `config.py`
  Application configuration, paths, model name, and API settings.
- `models.py`
  Small data models used across the app.
- `data_loader.py`
  Local JSON loading and payload extraction logic.
- `api_client.py`
  AI_devs API integration for `accessLevel`.

The agreed entrypoint is `main.py`.
`pipeline.py` should still contain the main end-to-end flow, while `main.py` remains a thin wrapper.

## File Responsibilities

The current responsibility split is:

- `main.py`
  Thin entrypoint. It should only start the pipeline.
- `pipeline.py`
  High-level end-to-end flow. It should load config, run the agent, and return or print the final result.
- `agent.py`
  Agent orchestration. It should run the deterministic setup, define the model-driven stages, prompts, tool exposure, runtime state, and stage transitions.
- `tools.py`
  Tool definitions and tool execution. It should expose deterministic operations to the model and dispatch calls to application code.
- `data_loader.py`
  Local file input logic. It should load `data_people.json`, extract `payload_sent.answer`, validate the structure, and prepare clean people data.
- `api_client.py`
  AI_devs integration. It should fetch `accessLevel` and validate the basic response shape.
- `models.py`
  Small shared data models.
- `config.py`
  Application settings such as paths, API keys, model name, URLs, and iteration limits.

## Boundary Rules

The current design should keep these boundaries clear:

- `main.py` should not contain business logic.
- `pipeline.py` should not contain detailed tool logic or prompt logic.
- `agent.py` should orchestrate, not directly read files or call AI_devs endpoints.
- `tools.py` should execute operations, not control stage transitions.
- `data_loader.py` should handle local data only.
- `api_client.py` should handle remote API access only.

Prompts, stage order, and stage-specific instructions should live in `agent.py`.

## Planned Internal Contents

The current plan for each file is:

- `models.py`
  Should define small shared models such as `Person` and `FinalResult`.
- `config.py`
  Should define `AppConfig` and `get_config()`.
- `data_loader.py`
  Should contain local JSON loading, payload extraction, and city extraction logic.
- `api_client.py`
  Should contain the AI_devs client used to fetch `accessLevel`.
- `tools.py`
  Should contain tool stage groups, tool definitions, the toolbox class, and tool dispatch logic.
- `agent.py`
  Should contain stage order, prompts, stage completion checks, state updates, and the main agent loop.
- `pipeline.py`
  Should contain `run_pipeline()`.
- `main.py`
  Should contain `main()` and a standard `if __name__ == "__main__"` entry block.

## Planned Functions And Contracts

### `models.py`

- `Person`
  Fields: `name`, `surname`, `birth_year`, `city`
- `FinalResult`
  Fields: `selected_city`, `person`, `access_level`

### `config.py`

- `get_config() -> AppConfig`
  Returns the full application configuration.
  It should fail clearly when required settings are missing.

### `data_loader.py`

- `load_people_data(path: Path) -> dict[str, Any]`
  Loads the raw JSON object from disk.
- `extract_people_payload(raw_data: dict[str, Any]) -> list[Person]`
  Extracts and validates `payload_sent.answer`.
- `extract_unique_cities(people: list[Person]) -> list[str]`
  Returns unique city names, preferably in a stable order.

### `api_client.py`

- `Edu1ApiClient.get_access_level(name: str, surname: str, birth_year: int) -> int`
  Fetches and validates `accessLevel` from AI_devs.

### `tools.py`

- `build_tool_definitions(allowed_names: list[str] | None = None) -> list[dict[str, Any]]`
  Builds the tool definitions exposed to the model.
- `Edu1Toolbox.load_people_data() -> dict[str, Any]`
  Returns `{"rawData": ...}`.
- `Edu1Toolbox.extract_people_payload(raw_data: dict[str, Any]) -> dict[str, Any]`
  Returns `{"people": [...]}`.
- `Edu1Toolbox.extract_unique_cities(people: list[dict[str, Any]]) -> dict[str, Any]`
  Returns `{"cities": [...]}`.
- `Edu1Toolbox.validate_selected_city(selected_city: str, available_cities: list[str]) -> dict[str, Any]`
  Returns `{"isValid": bool, "selectedCity": str | None}`.
- `Edu1Toolbox.find_person_by_city(people: list[dict[str, Any]], city: str) -> dict[str, Any]`
  Returns `{"selectedPerson": {...}}`.
- `Edu1Toolbox.get_access_level(name: str, surname: str, birth_year: int) -> dict[str, Any]`
  Returns `{"accessLevel": int}`.
- `Edu1Toolbox.build_final_result(person: dict[str, Any], selected_city: str, access_level: int) -> dict[str, Any]`
  Returns `{"result": {...}}`.
- `Edu1Toolbox.execute(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]`
  Dispatches one tool call to the correct implementation.

### `agent.py`

- `is_stage_complete(stage_name: str, state: dict[str, Any]) -> bool`
  Checks whether a stage has produced its required state values.
- `extract_function_calls(response: Any) -> list[Any]`
  Extracts tool calls from the OpenAI response.
- `update_state_from_result(state: dict[str, Any], tool_name: str, result: dict[str, Any]) -> None`
  Updates runtime state with validated tool results.
- `build_stage_input(stage_name: str, state: dict[str, Any], is_first_stage: bool) -> list[dict[str, str]]`
  Builds the model input for the current stage.
- `execute_tool_calls(...) -> list[dict[str, str]]`
  Executes requested tools and returns tool outputs to the model.
- `run_agent(config: AppConfig) -> dict[str, Any]`
  Runs the full staged agent workflow and returns the final result.

### `pipeline.py`

- `run_pipeline() -> dict[str, Any]`
  Loads config, runs the agent, and returns the final result.

### `main.py`

- `main() -> None`
  Starts the application by calling `run_pipeline()`.

## Validation And Error Rules

The current agreed validation rules are:

- `payload_sent.answer` must exist and must be a list.
- Person records must contain the required fields.
- The model-selected city must be one of the provided cities.
- `selectedCity` should enter runtime state only after successful validation.
- `find_person_by_city` should fail when there is no match or more than one match.
- `get_access_level` should fail clearly when the API response shape is invalid.

## Serialization Rule

Inside domain-oriented code, shared models may be used for clarity.
At the tool boundary, data returned to the model should be JSON-serializable dictionaries and lists.

## Assumptions

- `data_people.json` contains metadata, but only `payload_sent.answer` matters for business logic.
- The provided city list is small and can be safely sent to OpenAI in one request.
- OpenAI should return one city name that already exists in the input list.
- Exactly one person should match the selected city.

## Status

This README documents the current agreed direction for EDU1.
Exact implementation details inside each file are still to be designed.

## What This Task Should Teach

This task is mainly about learning the shape of an agent-style application in a small, inspectable setting.
The important lesson is that an agent does not need to control every step; deterministic setup can prepare clean state, and the model can make one narrow decision from a closed list.

Key learning points:

| Lesson | What it means in this app |
|---|---|
| Start with a small agent problem. | EDU1 mirrors selected `L2_findhim` ideas without the full complexity of the original task. |
| Give the model a closed choice. | OpenAI chooses the southernmost city only from the provided city list. |
| Validate before updating state. | `selectedCity` should enter runtime state only after `validate_selected_city` accepts it. |
| Use staged tool exposure. | The model-driven stages see only the tools needed for selection or finalization. |
| Keep tool outputs JSON-serializable. | Tool boundaries use dictionaries and lists so model interactions remain easy to inspect. |
| Separate learning design from runtime code. | The README documents the intended boundaries before the implementation becomes more complex. |

The practical pattern to remember:

```text
deterministic setup -> closed model choice -> validation -> deterministic finalization
```
