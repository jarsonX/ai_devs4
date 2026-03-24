# EDU1

EDU1 is an educational app inspired by `L02_findhim`.
Its goal is to explain the core idea of an agent-style application without the full complexity of the reference app.

## Purpose

The app is meant for learning:

- staged tool usage,
- limiting tool exposure at each stage,
- passing data between steps,
- separating code from model reasoning,
- keeping business logic simple while still using a staged agent workflow,
- validating model output before using it.

This app should mirror selected ideas from `L02_findhim`, but in a much smaller and easier-to-follow form.

## Current Business Goal

The app should:
1. load people data from `data/EDU1/data_people.json`,
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
- Application code loads data, validates structure, validates model output, selects the person, calls the AI_devs API, and builds the final result.

This split keeps the agent useful without making it responsible for the entire business flow.

## Assumptions

- `data_people.json` contains metadata, but only `payload_sent.answer` matters for business logic.
- The provided city list is small and can be safely sent to OpenAI in one request.
- OpenAI should return one city name that already exists in the input list.
- Exactly one person should match the selected city.

## Status

This README documents the current agreed direction for EDU1.
Implementation details, module structure, and tool definitions are still to be designed.
