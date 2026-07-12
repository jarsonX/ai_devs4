# CLI entrypoint for the deterministic L23 shellaccess workflow.

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L23_shellaccess.config import (
    MAX_VERIFY_REQUESTS,
    REQUEST_TIMEOUT_SECONDS,
    build_paths,
    load_hub_config,
    prepare_tls_environment,
)
from src.apps.L23_shellaccess.solver import (
    build_answer,
    build_submission_command,
    parse_city,
    parse_gps,
    parse_timeline_row,
)
from src.apps.L23_shellaccess.verify_client import ShellAccessClient, response_contains_flag


TIMELINE_COMMAND = "grep -i 'znaleziono ciało' /data/time_logs.csv"


# Parse the explicit live-submission switch.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic L23 shellaccess solution.")
    parser.add_argument("--submit", action="store_true", help="Explore and submit to the Hub.")
    return parser.parse_args()


# Write JSON runtime artifacts with stable UTF-8 formatting.
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Execute the evidence lookup and return a validated answer plus audit metadata.
def resolve_answer(client: ShellAccessClient) -> tuple[dict[str, object], list[dict[str, Any]]]:
    audit: list[dict[str, Any]] = []
    timeline_result = client.execute(TIMELINE_COMMAND, command_name="find_timeline_record")
    timeline = parse_timeline_row(timeline_result.output())
    audit.append({"step": "timeline", "location_id": timeline.location_id, "entry_id": timeline.entry_id})

    city_command = (
        "jq -r '.[] | select(.location_id == "
        f"{timeline.location_id}) | .name' /data/locations.json"
    )
    city = parse_city(client.execute(city_command, command_name="resolve_city").output())
    audit.append({"step": "city", "city": city})

    gps_command = (
        "jq -r '.[] | select(.entry_id == "
        f"{timeline.entry_id}) | [.latitude,.longitude,.type,.location_id,.entry_id] | @tsv' "
        "/data/gps.json"
    )
    gps = parse_gps(client.execute(gps_command, command_name="resolve_gps").output())
    audit.append({"step": "gps", "place_type": gps.place_type, "location_id": gps.location_id})
    return build_answer(timeline, city, gps), audit


# Run local validation without contacting the Hub.
def run_dry_run() -> dict[str, object]:
    answer = build_answer(
        parse_timeline_row("2024-11-13;W jaskini znaleziono ciało mężczyzny;219;954634"),
        parse_city("Grudziądz\n"),
        parse_gps("53.432303\t18.968774\tjaskinia\t219\t954634\n"),
    )
    return {"status": "dry_run_ok", "answer": answer, "command": build_submission_command(answer)}


# Run the guarded live workflow and preserve the raw Hub response in runtime data.
def run_submit() -> dict[str, object]:
    paths = build_paths()
    prepare_tls_environment(paths)
    client = ShellAccessClient(
        load_hub_config(),
        timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        max_requests=MAX_VERIFY_REQUESTS,
    )
    answer, audit = resolve_answer(client)
    final_result = client.execute(build_submission_command(answer), command_name="submit_answer")
    flag_found = response_contains_flag(final_result)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = paths.output_dir / f"run_report_{stamp}.json"
    write_json(
        report_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request_count": client.request_count,
            "answer": answer,
            "audit": audit,
            "flag_found": flag_found,
            "final_response": {
                "status_code": final_result.status_code,
                "payload": final_result.payload,
                "text": final_result.text,
            },
        },
    )
    return {
        "status": "solved" if flag_found else "submitted_not_accepted",
        "flag_found": flag_found,
        "answer": answer,
        "request_count": client.request_count,
        "report_path": str(report_path.relative_to(paths.repo_root)),
        "final_response": final_result.payload,
    }


# Run the selected mode and print its compact result.
def main() -> None:
    result = run_submit() if parse_args().submit else run_dry_run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
