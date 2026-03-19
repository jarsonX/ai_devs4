from __future__ import annotations

from .common import get_config_with_session, get_first_suspect, save_workbench_artifact


def main() -> None:
    config, session, timeout = get_config_with_session()
    suspect = get_first_suspect(config)

    payload = {
        "apikey": config.ai_devs_api_key,
        "name": suspect.name,
        "surname": suspect.surname,
        "birthYear": suspect.birth_year,
    }
    response = session.post(
        config.access_level_api_url,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    response_json = response.json()

    output_path = save_workbench_artifact(
        "access_level_response.json",
        {
            "step": "inspect_access_level_response",
            "suspect": {
                "name": suspect.name,
                "surname": suspect.surname,
                "birthYear": suspect.birth_year,
            },
            "request_payload": payload,
            "response_json": response_json,
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
