# Deterministic Stage 5 routing for supported task executors.

from dataclasses import dataclass

from src.apps.L4_sendit.L4_sendit_MVP2.declaration_builder import build_declaration_task_result
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    EvidencePackage,
    SupportedTaskDefinition,
    TaskExecutionResult,
    TaskResult,
    TaskUnderstanding,
)
from src.apps.L4_sendit.L4_sendit_MVP2.validator import (
    raise_if_task_result_invalid,
    validate_task_result,
)


@dataclass(frozen=True)
# Store one deterministic executor contract for a supported task.
class TaskExecutorDefinition:
    task_name: str
    result_kind: str


# === KNOWN_TASK: spk_transport_declaration ===================================
# The current workflow implements only one task-specific executor. Add new
# entries here when future known tasks gain explicit deterministic executors.
# =============================================================================
EXECUTOR_REGISTRY: dict[str, TaskExecutorDefinition] = {
    "spk_transport_declaration": TaskExecutorDefinition(
        task_name="spk_transport_declaration",
        result_kind="declaration_data",
    )
}


# Execute the currently supported task with its deterministic executor.
def execute_task(
    task_understanding: TaskUnderstanding,
    evidence_package: EvidencePackage,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> TaskExecutionResult:
    executor_definition = EXECUTOR_REGISTRY.get(task_understanding.task_name)
    if executor_definition is None:
        raise ValueError(f"No executor is registered for task_name: {task_understanding.task_name}")

    task_result = _run_registered_executor(task_understanding, evidence_package, executor_definition)
    validation_results = validate_task_result(
        task_result=task_result,
        task_understanding=task_understanding,
        evidence_package=evidence_package,
        executor_definition=executor_definition,
        supported_tasks=supported_tasks,
    )
    raise_if_task_result_invalid(validation_results)

    return TaskExecutionResult(
        task_result=task_result,
        raw_model_response={
            "used_model": False,
            "executor": executor_definition.task_name,
            "result_kind": executor_definition.result_kind,
        },
    )


# Run the executor implementation selected by the deterministic registry.
def _run_registered_executor(
    task_understanding: TaskUnderstanding,
    evidence_package: EvidencePackage,
    executor_definition: TaskExecutorDefinition,
) -> TaskResult:
    if executor_definition.task_name == "spk_transport_declaration":
        return build_declaration_task_result(task_understanding, evidence_package)

    raise ValueError(f"Executor implementation is missing for task_name: {executor_definition.task_name}")
