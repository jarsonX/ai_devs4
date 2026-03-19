from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import AppConfig
from .tools import FindHimToolbox, build_tool_definitions


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
- Do not submit the final answer to /verify in this run.
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


def run_agent(config: AppConfig) -> dict:
    client = OpenAI(api_key=config.openai_api_key)
    toolbox = FindHimToolbox(config)
    tools = build_tool_definitions()
    response_format = {
        "format": {
            "type": "json_schema",
            "name": "findhim_agent_result",
            "schema": build_final_response_schema(),
            "strict": True,
        }
    }

    transcript: list[dict[str, Any]] = []
    response = client.responses.create(
        model=config.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Solve the task and stop after producing the final answer object. "
                    "Use tools for data access and calculations."
                ),
            },
        ],
        tools=tools,
        text=response_format,
    )

    for iteration in range(1, config.max_agent_iterations + 1):
        function_calls = extract_function_calls(response)
        if not function_calls:
            raw_json = response.output_text
            if not raw_json:
                raise ValueError("Agent finished without tool calls and without a final JSON response.")

            data = json.loads(raw_json)
            data["iterationsUsed"] = iteration
            data["transcript"] = transcript
            return data

        tool_outputs: list[dict[str, str]] = []
        for function_call in function_calls:
            arguments = json.loads(function_call.arguments or "{}")
            try:
                result = toolbox.execute(function_call.name, arguments)
            except Exception as error:
                result = {"error": str(error)}
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

        response = client.responses.create(
            model=config.openai_model,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools,
            text=response_format,
        )

    raise ValueError(
        f"Agent exceeded the maximum number of iterations ({config.max_agent_iterations})."
    )
