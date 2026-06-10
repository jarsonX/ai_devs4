# CLI entrypoint for the L10 drone workflow.

from __future__ import annotations

import json

from src.apps.L10_drone.config import load_app_config
from src.apps.L10_drone.workflow import run_drone_workflow


# Run the real bounded workflow against OpenAI and the Hub.
def main() -> None:
    config = load_app_config(require_hub=True, require_llm=True)
    result = run_drone_workflow(config)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
