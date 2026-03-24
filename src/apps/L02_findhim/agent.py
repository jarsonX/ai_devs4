"""This file runs the LLM agent that calls tools step by step to solve the FindHim task."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import AppConfig
from .tools import FindHimToolbox, TOOL_STAGE_GROUPS, build_tool_definitions


AGENT_STAGE_SEQUENCE = ["setup", "ranking", "finalize"]


SYSTEM_PROMPT = """
You are an agent solving the AI_devs task "findhim".

Your goal:
- identify the suspect who was closest to one of the power plants,
- get that suspect's access level,
- build the final answer object.

Rules:
- Use tools instead of guessing data.
- The final candidate must be selected by the shortest geographic distance.
- Use the power plant cities returned by the tools and resolve their representative coordinates.
- Do not invent any API responses, coordinates, or people data.
- Do not submit the final answer to /verify yourself. The pipeline will do that after local validation.
- Stop after you build the final answer object with the build_verification_answer tool.

Recommended workflow:
1. get_suspects
2. get_power_plants
3. resolve_power_plant_city_coordinates
4. combine_power_plants_with_coordinates
5. rank_suspects_by_distance
6. get_access_level for the best candidate
7. build_verification_answer

When you are done, return a JSON object that matches the required schema exactly.
""".strip()


STAGE_PROMPTS = {
    "setup": """
Current stage: setup.

Available tools in this stage let you:
- load suspects,
- fetch power plant records,
- resolve representative coordinates for the power plant cities,
- combine plant records with city coordinates.

Goal of this stage:
- finish with prepared powerPlantCities data that can be used for distance ranking.

Restrictions:
- do not try to rank suspects yet,
- do not fetch access levels yet,
- do not build the final answer yet.
""".strip(),
    "ranking": """
Current stage: ranking.

Use the available tool to rank all suspects by the shortest distance to the prepared power plant cities.

Goal of this stage:
- produce the ranking,
- identify the single bestCandidate by shortest distance.

Restrictions:
- do not fetch access levels yet,
- do not build the final answer yet.
""".strip(),
    "finalize": """
Current stage: finalize.

Use the available tools to:
1. fetch the access level for the bestCandidate,
2. build the final answer object.

Important:
- the powerPlant field must contain only the exact plant code, for example PWR1234PL,
- do not include the city name inside powerPlant,
- after the tools are done, return the final JSON response.
""".strip(),
}


def build_final_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["completed"],
            },
            "answer": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                    "accessLevel": {"type": "integer"},
                    "powerPlant": {"type": "string"},
                },
                "required": ["name", "surname", "accessLevel", "powerPlant"],
                "additionalProperties": False,
            },
            "bestCandidate": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                    "powerPlantCode": {"type": "string"},
                    "powerPlantCity": {"type": "string"},
                    "distanceKm": {"type": "number"},
                },
                "required": [
                    "name",
                    "surname",
                    "powerPlantCode",
                    "powerPlantCity",
                    "distanceKm",
                ],
                "additionalProperties": False,
            },
        },
        "required": ["status", "answer", "bestCandidate"],
        "additionalProperties": False,
    }


def extract_function_calls(response: Any) -> list[Any]:
    return [
        item
        for item in getattr(response, "output", [])
        if getattr(item, "type", "") == "function_call"
    ]


def update_state_from_result(state: dict[str, Any], tool_name: str, result: dict[str, Any]) -> None:
    if "error" in result:
        return

    if tool_name == "get_suspects":
        state["suspects"] = result["suspects"]
        return

    if tool_name == "get_power_plants":
        state["powerPlants"] = result["powerPlants"]
        return

    if tool_name == "resolve_power_plant_city_coordinates":
        state["cityCoordinates"] = result["cityCoordinates"]
        return

    if tool_name == "combine_power_plants_with_coordinates":
        state["powerPlantCities"] = result["powerPlantCities"]
        return

    if tool_name == "rank_suspects_by_distance":
        state["ranking"] = result["ranking"]
        state["bestCandidate"] = result["bestCandidate"]
        return

    if tool_name == "get_access_level":
        state["accessLevel"] = result["accessLevel"]
        return

    if tool_name == "build_verification_answer":
        state["answer"] = result["answer"]


def is_stage_complete(stage_name: str, state: dict[str, Any]) -> bool:
    if stage_name == "setup":
        required_keys = {"suspects", "powerPlants", "cityCoordinates", "powerPlantCities"}
        return required_keys.issubset(state)

    if stage_name == "ranking":
        required_keys = {"ranking", "bestCandidate"}
        return required_keys.issubset(state)

    return False


def build_stage_input(stage_name: str, is_first_stage: bool) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    if is_first_stage:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

    messages.append({"role": "user", "content": STAGE_PROMPTS[stage_name]})
    return messages


def execute_tool_calls(
    toolbox: FindHimToolbox,
    function_calls: list[Any],
    transcript: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[dict[str, str]]:
    tool_outputs: list[dict[str, str]] = []

    for function_call in function_calls:
        arguments = json.loads(function_call.arguments or "{}")
        try:
            result = toolbox.execute(function_call.name, arguments)
        except Exception as error:
            result = {"error": str(error)}

        update_state_from_result(state, function_call.name, result)
        transcript.append(
            {
                "tool": function_call.name,
                "arguments": arguments,
                "result": result,
            }
        )
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": function_call.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            }
        )

    return tool_outputs


def run_agent(config: AppConfig) -> dict:
    client = OpenAI(api_key=config.openai_api_key)
    toolbox = FindHimToolbox(config)
    response_format = {
        "format": {
            "type": "json_schema",
            "name": "findhim_agent_result",
            "schema": build_final_response_schema(),
            "strict": True,
        }
    }

    transcript: list[dict[str, Any]] = []
    state: dict[str, Any] = {}
    response: Any | None = None
    total_iterations = 0

    for stage_index, stage_name in enumerate(AGENT_STAGE_SEQUENCE):
        stage_tools = build_tool_definitions(TOOL_STAGE_GROUPS[stage_name])
        stage_input = build_stage_input(stage_name, is_first_stage=stage_index == 0)

        if response is None:
            response = client.responses.create(
                model=config.openai_model,
                input=stage_input,
                tools=stage_tools,
                text=response_format if stage_name == "finalize" else None,
            )
        else:
            response = client.responses.create(
                model=config.openai_model,
                previous_response_id=response.id,
                input=stage_input,
                tools=stage_tools,
                text=response_format if stage_name == "finalize" else None,
            )

        if stage_name != "finalize":
            while not is_stage_complete(stage_name, state):
                total_iterations += 1
                if total_iterations > config.max_agent_iterations:
                    raise ValueError(
                        f"Agent exceeded the maximum number of iterations ({config.max_agent_iterations})."
                    )

                function_calls = extract_function_calls(response)
                if not function_calls:
                    raise ValueError(
                        f"Stage '{stage_name}' ended before producing the required tool outputs."
                    )

                tool_outputs = execute_tool_calls(toolbox, function_calls, transcript, state)
                response = client.responses.create(
                    model=config.openai_model,
                    previous_response_id=response.id,
                    input=tool_outputs,
                    tools=stage_tools,
                )

            continue

        while True:
            total_iterations += 1
            if total_iterations > config.max_agent_iterations:
                raise ValueError(
                    f"Agent exceeded the maximum number of iterations ({config.max_agent_iterations})."
                )

            function_calls = extract_function_calls(response)
            if not function_calls:
                raw_json = response.output_text
                if not raw_json:
                    raise ValueError("Agent finished without tool calls and without a final JSON response.")

                data = json.loads(raw_json)
                data["iterationsUsed"] = total_iterations
                data["transcript"] = transcript
                return data

            tool_outputs = execute_tool_calls(toolbox, function_calls, transcript, state)
            response = client.responses.create(
                model=config.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=stage_tools,
                text=response_format,
            )

    raise ValueError("Agent finished without producing a final response.")
