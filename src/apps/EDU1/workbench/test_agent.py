from __future__ import annotations

from dataclasses import replace
from pprint import pprint

from src.apps.EDU1.agent import run_agent
from src.apps.EDU1.config import get_config


TEST_AGENT_MAX_ITERATIONS = 12


def main() -> None:
    config = get_config()
    if config.max_agent_iterations > TEST_AGENT_MAX_ITERATIONS:
        config = replace(config, max_agent_iterations=TEST_AGENT_MAX_ITERATIONS)

    pprint(run_agent(config))


if __name__ == "__main__":
    main()
