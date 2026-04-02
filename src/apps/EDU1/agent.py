from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import AppConfig
from .tools import Edu1Toolbox, TOOL_STAGE_GROUPS, build_tool_definitions


AGENT_STAGE_SEQUENCE = ["selection", "finalize"]


SYSTEM_PROMPT = """
You are an agent solving the EDU1 task.

Your goal:
- prepare the people data,
- choose the city located farthest south from a closed list of Polish cities,
- validate that chosen city with a tool,
- find the matching person,
- fetch that person's access level,
- build the final business result.

Rules:
- The setup stage is already prepared by deterministic application code before you start.
- Use tools instead of guessing data.
- OpenAI is responsible only for choosing the southernmost city from the provided list.
- Do not invent city names, people, or access levels.
- Treat tool outputs as the source of truth.
- selectedCity becomes valid application state only after the validate_selected_city tool confirms it.
- Stop after the build_final_result tool produces the final result.
""".strip()


STAGE_PROMPTS = {
    # SELECTION
    "selection": """
Current stage: selection.

Goal of this stage:
1. choose the city located farthest south from the provided closed list,
2. validate the chosen city with the validate_selected_city tool,
3. find the matching person with the find_person_by_city tool.

Rules:
- choose exactly one city from the provided list,
- do not invent or rewrite city names,
- do not write selectedCity into application state unless validation succeeds,
- do not fetch access levels yet,
- do not build the final result yet.
""".strip(),
    # FINALIZE
    "finalize": """
Current stage: finalize.

Goal of this stage:
- fetch the selected person's access level,
- build the final business result.

Use only the available tools.
Do not invent any values.
Stop after build_final_result succeeds.
""".strip(),
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

    if tool_name == "load_people_data":
        state["rawData"] = result["rawData"]
        return

    if tool_name == "extract_people_payload":
        state["people"] = result["people"]
        return

    if tool_name == "extract_unique_cities":
        state["cities"] = result["cities"]
        return

    if tool_name == "validate_selected_city":
        if result.get("isValid") and isinstance(result.get("selectedCity"), str):
            state["selectedCity"] = result["selectedCity"]
        return

    if tool_name == "find_person_by_city":
        state["selectedPerson"] = result["selectedPerson"]
        return

    if tool_name == "get_access_level":
        state["accessLevel"] = result["accessLevel"]
        return

    if tool_name == "build_final_result":
        state["result"] = result["result"]


def is_stage_complete(stage_name: str, state: dict[str, Any]) -> bool:
    if stage_name == "selection":
        required_keys = {"selectedCity", "selectedPerson"}
        return required_keys.issubset(state)

    if stage_name == "finalize":
        required_keys = {"accessLevel", "result"}
        return required_keys.issubset(state)

    raise ValueError(f"Unsupported stage: {stage_name}")


def run_deterministic_setup(toolbox: Edu1Toolbox, state: dict[str, Any]) -> None:
    setup_result = toolbox.load_people_data()
    update_state_from_result(state, "load_people_data", setup_result)

    people_result = toolbox.extract_people_payload(state["rawData"])
    update_state_from_result(state, "extract_people_payload", people_result)

    cities_result = toolbox.extract_unique_cities(state["people"])
    update_state_from_result(state, "extract_unique_cities", cities_result)


def build_stage_input(
    stage_name: str,
    state: dict[str, Any],
    is_first_stage: bool,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    if is_first_stage:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

    content = STAGE_PROMPTS[stage_name]

    if stage_name == "selection":
        content += "\n\nCurrent validated state:\n"
        content += json.dumps(
            {
                "cities": state["cities"],
                "people": state["people"],
            },
            ensure_ascii=False,
            indent=2,
        )

    if stage_name == "finalize":
        content += "\n\nCurrent validated state:\n"
        content += json.dumps(
            {
                "selectedCity": state["selectedCity"],
                "selectedPerson": state["selectedPerson"],
            },
            ensure_ascii=False,
            indent=2,
        )

    messages.append({"role": "user", "content": content})
    return messages


def execute_tool_calls(
    toolbox: Edu1Toolbox,
    function_calls: list[Any],
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

        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": function_call.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            }
        )

    return tool_outputs


def run_agent(config: AppConfig) -> dict[str, Any]:
    client = OpenAI(api_key=config.openai_api_key)
    toolbox = Edu1Toolbox(config)
    state: dict[str, Any] = {}
    response: Any | None = None
    total_iterations = 0

    run_deterministic_setup(toolbox, state)

    for stage_index, stage_name in enumerate(AGENT_STAGE_SEQUENCE):
        stage_tools = build_tool_definitions(TOOL_STAGE_GROUPS[stage_name])
        stage_input = build_stage_input(
            stage_name=stage_name,
            state=state,
            is_first_stage=stage_index == 0,
        )

        if response is None:
            response = client.responses.create(
                model=config.openai_model,
                input=stage_input,
                tools=stage_tools,
                parallel_tool_calls=False,
                max_tool_calls=1,
            )
        else:
            response = client.responses.create(
                model=config.openai_model,
                previous_response_id=response.id,
                input=stage_input,
                tools=stage_tools,
                parallel_tool_calls=False,
                max_tool_calls=1,
            )

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

            tool_outputs = execute_tool_calls(
                toolbox=toolbox,
                function_calls=function_calls,
                state=state,
            )

            response = client.responses.create(
                model=config.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=stage_tools,
                parallel_tool_calls=False,
                max_tool_calls=1,
            )

    if "result" not in state:
        raise ValueError("Agent finished without producing the final result.")

    return state["result"]
