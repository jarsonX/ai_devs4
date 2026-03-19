from __future__ import annotations

from .common import get_config_with_session, save_workbench_artifact


def main() -> None:
    config, session, timeout = get_config_with_session()

    response = session.get(config.power_plants_url, timeout=timeout)
    response.raise_for_status()
    response_json = response.json()

    output_path = save_workbench_artifact(
        "power_plants_response.json",
        {
            "step": "inspect_power_plants_response",
            "response_json": response_json,
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
