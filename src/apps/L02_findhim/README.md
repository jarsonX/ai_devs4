## L02 FindHim

This app solves the AI_devs `findhim` task using an agent with OpenAI Function Calling.

### What it does

1. Loads suspects from the result of task `L01_people`.
2. Fetches power plant records from the course API.
3. Resolves approximate coordinates for power plant cities with OpenAI.
4. Combines plant codes with city coordinates.
5. Computes the shortest distance between each suspect's observed locations and the power plant cities.
6. Selects the best candidate by the smallest distance.
7. Fetches the candidate's `accessLevel`.
8. Builds the final answer and sends it to `/verify`.

### Main modules

- `agent.py`: agent loop using OpenAI Responses API and Function Calling
- `tools.py`: tool definitions and deterministic tool execution
- `api_client.py`: course API integration
- `city_resolver.py`: OpenAI-based city coordinate resolution
- `distance.py`: Haversine distance calculation
- `validator.py`: local validation before verification
- `pipeline.py`: end-to-end app execution

### Notes

- Secrets and private endpoints are loaded from `.env`.
- The agent orchestrates the workflow, but calculations and API handling stay deterministic in Python.
- `workbench/` contains exploration scripts used during development.
