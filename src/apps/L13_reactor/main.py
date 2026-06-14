# CLI entrypoint for the deterministic L13 reactor workflow.

from __future__ import annotations

import json

from src.apps.L13_reactor.config import load_app_config
from src.apps.L13_reactor.workflow import run_reactor_workflow


# Run the real bounded controller against the Hub.
def main() -> None:
    config = load_app_config()
    result = run_reactor_workflow(config)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
