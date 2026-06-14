# One-call inspection entrypoint for discovering the live reactor response contract.

from __future__ import annotations

import json

from src.apps.L13_reactor.config import ensure_runtime_directories, load_app_config
from src.apps.L13_reactor.hub_client import CommandGuard, HubClient
from src.apps.L13_reactor.run_log import append_command_event, create_run_log_path


# Send only the required start command and preserve the response for inspection.
def main() -> None:
    config = load_app_config()
    ensure_runtime_directories(config.paths)
    log_path = create_run_log_path(config.paths.logs_dir)
    client = HubClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        guard=CommandGuard(max_commands=1),
    )
    sequence, masked_request, response = client.send_command("start")
    append_command_event(
        log_path,
        sequence=sequence,
        command="start",
        masked_request=masked_request,
        response=response,
    )
    print(
        json.dumps(
            {
                "status_code": response.status_code,
                "payload": response.payload,
                "text": response.text,
                "log_path": str(log_path.relative_to(config.paths.repo_root)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
