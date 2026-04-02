from __future__ import annotations

from typing import Any

from .agent import run_agent
from .config import get_config


def run_pipeline() -> dict[str, Any]:
    config = get_config()
    return run_agent(config)
