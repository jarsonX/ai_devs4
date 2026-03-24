"""This file connects all main steps: run the agent, validate the result, and send it for verification."""

from __future__ import annotations

from .agent import run_agent
from .api_client import FindHimApiClient
from .config import get_config
from .models import VerificationAnswer
from .output import save_run_artifact
from .validator import validate_agent_result


def run_pipeline() -> None:
    config = get_config()
    agent_status = run_agent(config)
    validation = validate_agent_result(config, agent_status)
    validated_answer = validation["validatedAnswer"]

    api_client = FindHimApiClient(config)
    verification_answer = VerificationAnswer(
        name=validated_answer["name"],
        surname=validated_answer["surname"],
        accessLevel=validated_answer["accessLevel"],
        powerPlant=validated_answer["powerPlant"],
    )
    verification_response = api_client.verify_answer(verification_answer)

    preview = {
        "stage": "verification_completed",
        "task": config.task_name,
        "model": config.openai_model,
        "max_agent_iterations": config.max_agent_iterations,
        "suspects_source_path": str(config.suspects_source_path),
        "agent_status": agent_status,
        "validation": validation,
        "verificationResponse": verification_response,
    }

    output_path = save_run_artifact(config.output_json_path, preview)

    print("L02_findhim verification completed.")
    print(f"Answer: {agent_status['answer']}")
    print(f"Validation: {validation['isValid']}")
    print(f"Verification response: {verification_response}")
    print(f"Output artifact: {output_path}")
