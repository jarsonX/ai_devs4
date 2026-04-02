from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import AppConfig
from .tools import Edu1Toolbox, TOOL_STAGE_GROUPS, build_tool_definitions


AGENT_STAGE_SEQUENCE = ["selection", "finalize"]
STAGE_LABELS = {
    "setup": "1/3",
    "selection": "2/3",
    "finalize": "3/3",
}


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


def log_event(message: str) -> None:
    print(f"[EDU1] {message}")


def summarize_raw_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    payload_sent = raw_data.get("payload_sent")
    answer = payload_sent.get("answer") if isinstance(payload_sent, dict) else None

    return {
        "topLevelKeys": sorted(raw_data.keys()),
        "payloadSentKeys": sorted(payload_sent.keys()) if isinstance(payload_sent, dict) else [],
        "answerCount": len(answer) if isinstance(answer, list) else None,
    }


def summarize_person_data(person_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": person_data.get("name"),
        "surname": person_data.get("surname"),
        "birthYear": person_data.get("birthYear"),
        "city": person_data.get("city"),
    }


def summarize_result_data(result_data: dict[str, Any]) -> dict[str, Any]:
    person = result_data.get("person")

    return {
        "selectedCity": result_data.get("selectedCity"),
        "person": summarize_person_data(person) if isinstance(person, dict) else None,
        "accessLevel": result_data.get("accessLevel"),
    }


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    if "rawData" in state and isinstance(state["rawData"], dict):
        summary["rawData"] = summarize_raw_data(state["rawData"])
    if "people" in state and isinstance(state["people"], list):
        summary["peopleCount"] = len(state["people"])
    if "cities" in state and isinstance(state["cities"], list):
        summary["cities"] = state["cities"]
    if "selectedCity" in state:
        summary["selectedCity"] = state["selectedCity"]
    if "selectedPerson" in state and isinstance(state["selectedPerson"], dict):
        summary["selectedPerson"] = summarize_person_data(state["selectedPerson"])
    if "accessLevel" in state:
        summary["accessLevel"] = state["accessLevel"]
    if "result" in state and isinstance(state["result"], dict):
        summary["result"] = summarize_result_data(state["result"])

    return summary


def summarize_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "load_people_data":
        return {}

    if tool_name == "extract_people_payload":
        raw_data = arguments.get("rawData")
        return {
            "rawData": summarize_raw_data(raw_data) if isinstance(raw_data, dict) else "<missing>",
        }

    if tool_name == "extract_unique_cities":
        people = arguments.get("people")
        return {
            "peopleCount": len(people) if isinstance(people, list) else "<invalid>",
        }

    if tool_name == "validate_selected_city":
        available_cities = arguments.get("availableCities")
        return {
            "selectedCity": arguments.get("selectedCity"),
            "availableCitiesCount": len(available_cities) if isinstance(available_cities, list) else "<invalid>",
        }

    if tool_name == "find_person_by_city":
        people = arguments.get("people")
        return {
            "city": arguments.get("city"),
            "peopleCount": len(people) if isinstance(people, list) else "<invalid>",
        }

    if tool_name == "get_access_level":
        return {
            "name": arguments.get("name"),
            "surname": arguments.get("surname"),
            "birthYear": arguments.get("birthYear"),
        }

    if tool_name == "build_final_result":
        person = arguments.get("person")
        return {
            "selectedCity": arguments.get("selectedCity"),
            "accessLevel": arguments.get("accessLevel"),
            "person": summarize_person_data(person) if isinstance(person, dict) else "<invalid>",
        }

    return {"argumentsKeys": sorted(arguments.keys())}


def summarize_tool_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    if "error" in result:
        return {"error": result["error"]}

    if tool_name == "load_people_data":
        return {
            "rawData": summarize_raw_data(result["rawData"]),
        }

    if tool_name == "extract_people_payload":
        people = result.get("people")
        return {
            "peopleCount": len(people) if isinstance(people, list) else "<invalid>",
        }

    if tool_name == "extract_unique_cities":
        return {
            "cities": result.get("cities"),
        }

    if tool_name == "validate_selected_city":
        return {
            "isValid": result.get("isValid"),
            "selectedCity": result.get("selectedCity"),
        }

    if tool_name == "find_person_by_city":
        person = result.get("selectedPerson")
        return {
            "selectedPerson": summarize_person_data(person) if isinstance(person, dict) else "<invalid>",
        }

    if tool_name == "get_access_level":
        return {
            "accessLevel": result.get("accessLevel"),
        }

    if tool_name == "build_final_result":
        result_data = result.get("result")
        return {
            "result": summarize_result_data(result_data) if isinstance(result_data, dict) else "<invalid>",
        }

    return {"resultKeys": sorted(result.keys())}


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
    log_event(f"Stage {STAGE_LABELS['setup']} setup started")

    setup_steps = [
        ("load_people_data", {}, lambda: toolbox.load_people_data()),
        (
            "extract_people_payload",
            lambda: {"rawData": state["rawData"]},
            lambda: toolbox.extract_people_payload(state["rawData"]),
        ),
        (
            "extract_unique_cities",
            lambda: {"people": state["people"]},
            lambda: toolbox.extract_unique_cities(state["people"]),
        ),
    ]

    for step_index, (tool_name, arguments_source, action) in enumerate(setup_steps, start=1):
        arguments = arguments_source() if callable(arguments_source) else arguments_source
        log_event(
            f"Stage {STAGE_LABELS['setup']} setup | Step {step_index} | Tool {tool_name}"
        )
        log_event(
            "Tool arguments: "
            + json.dumps(summarize_tool_arguments(tool_name, arguments), ensure_ascii=False)
        )

        result = action()
        update_state_from_result(state, tool_name, result)

        log_event(
            "Tool result: "
            + json.dumps(summarize_tool_result(tool_name, result), ensure_ascii=False)
        )
        log_event(
            "State summary: " + json.dumps(summarize_state(state), ensure_ascii=False)
        )

    log_event(f"Stage {STAGE_LABELS['setup']} setup completed")


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
    stage_name: str,
    global_iteration_number: int,
    stage_iteration_number: int,
) -> list[dict[str, str]]:
    tool_outputs: list[dict[str, str]] = []

    for function_call in function_calls:
        arguments = json.loads(function_call.arguments or "{}")
        log_event(
            f"Stage {STAGE_LABELS[stage_name]} {stage_name} | "
            f"Global iteration {global_iteration_number} | "
            f"Stage iteration {stage_iteration_number} | "
            f"Tool {function_call.name}"
        )
        log_event(
            "Tool arguments: "
            + json.dumps(
                summarize_tool_arguments(function_call.name, arguments),
                ensure_ascii=False,
            )
        )

        try:
            result = toolbox.execute(function_call.name, arguments)
        except Exception as error:
            result = {"error": str(error)}

        update_state_from_result(state, function_call.name, result)
        log_event(
            "Tool result: "
            + json.dumps(
                summarize_tool_result(function_call.name, result),
                ensure_ascii=False,
            )
        )
        log_event(
            "State summary: " + json.dumps(summarize_state(state), ensure_ascii=False)
        )

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
        log_event(f"Stage {STAGE_LABELS[stage_name]} {stage_name} started")
        stage_iterations = 0
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
            stage_iterations += 1
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
                stage_name=stage_name,
                global_iteration_number=total_iterations,
                stage_iteration_number=stage_iterations,
            )

            response = client.responses.create(
                model=config.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=stage_tools,
                parallel_tool_calls=False,
                max_tool_calls=1,
            )

        log_event(f"Stage {STAGE_LABELS[stage_name]} {stage_name} completed")

    if "result" not in state:
        raise ValueError("Agent finished without producing the final result.")

    log_event("Agent completed with final result")
    log_event(
        "Final result: " + json.dumps(summarize_result_data(state["result"]), ensure_ascii=False)
    )

    return state["result"]
