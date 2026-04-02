from __future__ import annotations

from typing import Any

from .agent import run_agent
from .config import get_config


def run_pipeline() -> dict[str, Any]:
    print("[EDU1] Pipeline started")
    config = get_config()
    print(
        f"[EDU1] Pipeline config loaded | model={config.openai_model} "
        f"| max_agent_iterations={config.max_agent_iterations}"
    )
    result = run_agent(config)
    print("[EDU1] Pipeline finished")
    return result
