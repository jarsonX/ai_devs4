from __future__ import annotations

import json
from pprint import pprint
from typing import Any

from openai import OpenAI

from ..agent import (
    AGENT_STAGE_SEQUENCE,
    build_stage_input,
    execute_tool_calls,
    extract_function_calls,
    is_stage_complete,
    run_deterministic_setup,
)
from ..config import get_config
from ..tools import Edu1Toolbox, TOOL_STAGE_GROUPS, build_tool_definitions

DEBUG_MAX_ITERATIONS = 12


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    if "rawData" in state:
        summary["rawData"] = "present"
    if "people" in state:
        summary["peopleCount"] = len(state["people"])
    if "cities" in state:
        summary["cities"] = state["cities"]
    if "selectedCity" in state:
        summary["selectedCity"] = state["selectedCity"]
    if "selectedPerson" in state:
        summary["selectedPerson"] = state["selectedPerson"]
    if "accessLevel" in state:
        summary["accessLevel"] = state["accessLevel"]
    if "result" in state:
        summary["result"] = state["result"]

    return summary


def main() -> None:
    config = get_config()
    client = OpenAI(api_key=config.openai_api_key)
    toolbox = Edu1Toolbox(config)

    state: dict[str, Any] = {}
    response: Any | None = None
    total_iterations = 0

    run_deterministic_setup(toolbox, state)
    print("=== DETERMINISTIC SETUP ===")
    pprint(summarize_state(state))
    print()

    for stage_index, stage_name in enumerate(AGENT_STAGE_SEQUENCE):
        print(f"=== STAGE START: {stage_name} ===")

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

        stage_iterations = 0

        while not is_stage_complete(stage_name, state):
            total_iterations += 1
            stage_iterations += 1

            if total_iterations > DEBUG_MAX_ITERATIONS:
                raise ValueError(
                    "Debug iteration guard reached. "
                    f"DEBUG_MAX_ITERATIONS={DEBUG_MAX_ITERATIONS}"
                )

            print(f"iteration global={total_iterations}, stage={stage_iterations}")

            function_calls = extract_function_calls(response)
            print(f"function_calls count: {len(function_calls)}")

            if not function_calls:
                print("response.output_text:")
                print(repr(response.output_text))
                print("response.output item types:")
                pprint([getattr(item, "type", "<missing>") for item in response.output])
                raise ValueError(
                    f"Stage '{stage_name}' ended before producing the required tool outputs."
                )

            for function_call in function_calls:
                print(f"tool name: {function_call.name}")
                print("tool arguments:")
                try:
                    pprint(json.loads(function_call.arguments or "{}"))
                except json.JSONDecodeError:
                    print(repr(function_call.arguments))

            tool_outputs = execute_tool_calls(
                toolbox=toolbox,
                function_calls=function_calls,
                state=state,
            )

            print("tool_outputs:")
            pprint(tool_outputs)
            print("state summary after tool execution:")
            pprint(summarize_state(state))
            print()

            response = client.responses.create(
                model=config.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=stage_tools,
                parallel_tool_calls=False,
                max_tool_calls=1,
            )

        print(f"=== STAGE END: {stage_name} (iterations: {stage_iterations}) ===")
        print()

    print("=== FINAL RESULT ===")
    pprint(state.get("result"))
    print()
    print(f"total_iterations: {total_iterations}")


if __name__ == "__main__":
    main()
