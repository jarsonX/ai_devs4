# Supported task registry for the L4 sendit MVP2 Stage 1 workflow.

from src.apps.L4_sendit.L4_sendit_MVP2.models import SupportedTaskDefinition


# === KNOWN_TASK: spk_transport_declaration ===================================
# This registry currently contains only the known course task implemented by
# MVP2. Add new SupportedTaskDefinition entries here when new task types gain
# their own deterministic executors later in the workflow.
# =============================================================================
SUPPORTED_TASKS: tuple[SupportedTaskDefinition, ...] = (
    SupportedTaskDefinition(
        task_name="spk_transport_declaration",
        task_goal="Prepare a validated SPK transport declaration.",
        expected_output_kind="declaration_text",
        result_kind="declaration_data",
        domain="spk_transport",
        required_input_fields=(
            "sender_identifier",
            "origin_point",
            "destination_point",
            "weight_kg",
            "budget_pp",
            "contents",
            "special_notes",
        ),
        documentation_need_names=(
            "declaration format",
            "route availability and route code",
            "category rules",
            "payment rules",
            "wagon allocation rules",
        ),
    ),
)


# Return supported tasks keyed by task name for deterministic validation.
def build_supported_task_map() -> dict[str, SupportedTaskDefinition]:
    return {task.task_name: task for task in SUPPORTED_TASKS}


# Return a compact task summary suitable for the Stage 1 prompt.
def build_supported_task_prompt_summary() -> list[dict[str, object]]:
    return [
        {
            "task_name": task.task_name,
            "task_goal": task.task_goal,
            "expected_output_kind": task.expected_output_kind,
            "result_kind": task.result_kind,
            "domain": task.domain,
            "required_input_fields": list(task.required_input_fields),
            "documentation_need_names": list(task.documentation_need_names),
        }
        for task in SUPPORTED_TASKS
    ]
