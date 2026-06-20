# Deterministic OKO editor workflow with read-only web inspection and API writes.

from __future__ import annotations

from typing import Any, Protocol

from src.apps.L16_okoeditor.config import AppConfig, build_safe_config_summary, ensure_runtime_directories
from src.apps.L16_okoeditor.models import (
    OkoState,
    RecordDetail,
    TargetSelection,
    UpdateInstruction,
    VerifyResponse,
    WorkflowResult,
    dataclass_to_dict,
    redact_record_for_reports,
)
from src.apps.L16_okoeditor.payloads import build_update_plan, validate_update_plan
from src.apps.L16_okoeditor.report_writer import (
    write_final_response,
    write_html_snapshot,
    write_json,
    write_plan_report,
)
from src.apps.L16_okoeditor.run_log import RunLog, append_event, create_run_log
from src.apps.L16_okoeditor.snapshot_parser import parse_detail_page, parse_list_page
from src.apps.L16_okoeditor.target_resolution import resolve_targets
from src.apps.L16_okoeditor.verify_client import response_contains_flag, response_summary_for_log


# Define the read-only web behavior needed by the workflow so tests can use fakes.
class OkoReaderProtocol(Protocol):
    # Start the read-only web session.
    def login(self) -> None:
        ...

    # End the read-only web session.
    def logout(self) -> None:
        ...

    # Return the list page HTML for one page namespace.
    def fetch_list_html(self, page: str) -> str:
        ...

    # Return the detail page HTML for one page namespace and record id.
    def fetch_detail_html(self, page: str, record_id: str) -> str:
        ...

    # Build the detail URL used in normalized records.
    def build_detail_url(self, page: str, record_id: str) -> str:
        ...


# Define the verify behavior needed by the workflow so tests can use fakes.
class VerifyClientProtocol(Protocol):
    # Send one prepared update instruction.
    def send_update(self, instruction: UpdateInstruction) -> tuple[dict[str, Any], VerifyResponse]:
        ...

    # Send the final done action.
    def send_done(self) -> tuple[dict[str, Any], VerifyResponse]:
        ...


# Return secret values that must never be written to logs.
def secret_values_from_config(config: AppConfig) -> list[str]:
    secrets: list[str] = []
    if config.verify_api:
        secrets.append(config.verify_api.api_key)
    if config.oko_web:
        secrets.append(config.oko_web.access_key)
        secrets.append(config.oko_web.operator_password)
    return secrets


# Run the deterministic read-plan-apply workflow.
def run_okoeditor_workflow(
    config: AppConfig,
    *,
    apply_updates: bool,
    reader: OkoReaderProtocol,
    verify_client: VerifyClientProtocol | None = None,
    run_log: RunLog | None = None,
) -> WorkflowResult:
    ensure_runtime_directories(config.paths)
    active_log = run_log or create_run_log(config.paths.logs_dir)
    secrets = secret_values_from_config(config)
    plan_report_path = ""

    append_event(
        active_log,
        event="run_started",
        data={
            "apply_updates": apply_updates,
            "config": build_safe_config_summary(config),
        },
        secret_values=secrets,
    )

    try:
        reader.login()
        state = collect_current_state(config, reader=reader, run_log=active_log, secret_values=secrets)
        targets = resolve_targets(state)
        plan = build_update_plan(targets)
        validate_update_plan(plan, max_writes=config.runtime.max_planned_writes)

        plan_report_path = write_plan_report(
            config.paths,
            active_log.run_id,
            build_plan_report(state, targets, plan),
        )
        append_event(
            active_log,
            event="plan_built",
            data={"plan_report_path": plan_report_path, "planned_update_count": len(plan)},
            secret_values=secrets,
        )

        if not apply_updates:
            return finish_run(
                active_log,
                status="dry_run",
                reason="Dry-run plan built successfully. No live updates were sent.",
                apply_mode=False,
                planned_update_count=len(plan),
                plan_report_path=plan_report_path,
                secret_values=secrets,
            )

        if verify_client is None:
            raise ValueError("A verify client is required in apply mode.")

        for attempt, instruction in enumerate(plan, start=1):
            masked_request, response = verify_client.send_update(instruction)
            append_event(
                active_log,
                event="verify_update_request",
                attempt=attempt,
                data={"instruction": dataclass_to_dict(instruction), "request": masked_request},
                secret_values=secrets,
            )
            append_event(
                active_log,
                event="verify_update_response",
                attempt=attempt,
                data=response_summary_for_log(response),
                secret_values=secrets,
            )
            if response.status_code >= 400:
                return finish_run(
                    active_log,
                    status="update_failed",
                    reason=f"Verify update failed for {instruction.page}/{instruction.record_id}.",
                    apply_mode=True,
                    planned_update_count=len(plan),
                    plan_report_path=plan_report_path,
                    secret_values=secrets,
                )

        refreshed_details = refresh_updated_records(plan, reader=reader)
        refreshed_report_path = write_json(
            config.paths.output_dir / f"{active_log.run_id}_post_write_records.json",
            {
                f"{page}:{record_id}": redact_record_for_reports(detail)
                for (page, record_id), detail in refreshed_details.items()
            },
        )
        append_event(
            active_log,
            event="post_write_records_saved",
            data={"post_write_records_path": refreshed_report_path},
            secret_values=secrets,
        )
        mismatches = verify_applied_updates(plan, refreshed_details)
        if mismatches:
            mismatch_report_path = write_json(
                config.paths.output_dir / f"{active_log.run_id}_verification_mismatches.json",
                {"mismatches": mismatches},
            )
            append_event(
                active_log,
                event="post_write_verification_failed",
                data={"mismatch_report_path": mismatch_report_path, "mismatch_count": len(mismatches)},
                secret_values=secrets,
            )
            return finish_run(
                active_log,
                status="verification_failed",
                reason="Post-write verification did not match the expected visible state.",
                apply_mode=True,
                planned_update_count=len(plan),
                plan_report_path=plan_report_path,
                secret_values=secrets,
            )

        masked_request, done_response = verify_client.send_done()
        append_event(
            active_log,
            event="verify_done_request",
            data={"request": masked_request},
            secret_values=secrets,
        )
        append_event(
            active_log,
            event="verify_done_response",
            data=response_summary_for_log(done_response),
            secret_values=secrets,
        )
        final_response_path = write_final_response(config.paths, active_log.run_id, done_response.text)
        if done_response.status_code >= 400:
            return finish_run(
                active_log,
                status="done_failed",
                reason="Live updates were sent, but the final done action returned an error.",
                apply_mode=True,
                planned_update_count=len(plan),
                plan_report_path=plan_report_path,
                final_response_path=final_response_path,
                flag_found=response_contains_flag(done_response),
                secret_values=secrets,
            )
        return finish_run(
            active_log,
            status="solved" if response_contains_flag(done_response) else "done_submitted",
            reason="Live updates were applied and the final done action was sent.",
            apply_mode=True,
            planned_update_count=len(plan),
            plan_report_path=plan_report_path,
            final_response_path=final_response_path,
            flag_found=response_contains_flag(done_response),
            secret_values=secrets,
        )
    finally:
        try:
            reader.logout()
        except Exception as exc:
            append_event(
                active_log,
                event="logout_warning",
                data={"message": str(exc)},
                secret_values=secrets,
            )


# Fetch the current OKO state needed for deterministic planning.
def collect_current_state(
    config: AppConfig,
    *,
    reader: OkoReaderProtocol,
    run_log: RunLog,
    secret_values: list[str] | None = None,
) -> OkoState:
    incidents_html = reader.fetch_list_html("incydenty")
    tasks_html = reader.fetch_list_html("zadania")

    write_html_snapshot(config.paths, run_log.run_id, "incydenty_list", incidents_html)
    write_html_snapshot(config.paths, run_log.run_id, "zadania_list", tasks_html)

    incident_links = parse_list_page("incydenty", incidents_html, base_url=config.oko_web.base_url if config.oko_web else "")
    task_links = parse_list_page("zadania", tasks_html, base_url=config.oko_web.base_url if config.oko_web else "")

    append_event(
        run_log,
        event="list_pages_parsed",
        data={
            "incident_count": len(incident_links),
            "task_count": len(task_links),
        },
        secret_values=secret_values,
    )

    incident_details = tuple(fetch_detail_records("incydenty", incident_links, reader=reader, run_id=run_log.run_id, config=config))
    task_details = tuple(fetch_detail_records("zadania", task_links, reader=reader, run_id=run_log.run_id, config=config))

    append_event(
        run_log,
        event="detail_pages_parsed",
        data={
            "incident_detail_count": len(incident_details),
            "task_detail_count": len(task_details),
        },
        secret_values=secret_values,
    )

    return OkoState(
        incident_links=incident_links,
        task_links=task_links,
        incident_details=incident_details,
        task_details=task_details,
    )


# Fetch and parse all detail pages for one list of links.
def fetch_detail_records(
    page: str,
    links: tuple[Any, ...],
    *,
    reader: OkoReaderProtocol,
    run_id: str,
    config: AppConfig,
) -> list[RecordDetail]:
    details: list[RecordDetail] = []
    for link in links:
        html = reader.fetch_detail_html(page, link.record_id)
        write_html_snapshot(config.paths, run_id, f"{page}_{link.record_id}", html)
        details.append(
            parse_detail_page(
                page,
                link.record_id,
                html,
                url=reader.build_detail_url(page, link.record_id),
            )
        )
    return details


# Build one dry-run report that explains the chosen targets and writes.
def build_plan_report(
    state: OkoState,
    targets: TargetSelection,
    plan: tuple[UpdateInstruction, ...],
) -> dict[str, Any]:
    return {
        "incident_count": len(state.incident_links),
        "task_count": len(state.task_links),
        "targets": {
            "skolwin_incident": redact_record_for_reports(targets.skolwin_incident),
            "skolwin_task": redact_record_for_reports(targets.skolwin_task),
            "komarowo_candidate": redact_record_for_reports(targets.komarowo_candidate),
        },
        "plan": dataclass_to_dict(plan),
    }


# Re-read the updated records after live apply mode finishes.
def refresh_updated_records(
    plan: tuple[UpdateInstruction, ...],
    *,
    reader: OkoReaderProtocol,
) -> dict[tuple[str, str], RecordDetail]:
    refreshed: dict[tuple[str, str], RecordDetail] = {}
    for instruction in plan:
        html = reader.fetch_detail_html(instruction.page, instruction.record_id)
        refreshed[(instruction.page, instruction.record_id)] = parse_detail_page(
            instruction.page,
            instruction.record_id,
            html,
            url=reader.build_detail_url(instruction.page, instruction.record_id),
        )
    return refreshed


# Verify that the refreshed details match the deterministic expectations.
def verify_applied_updates(
    plan: tuple[UpdateInstruction, ...],
    refreshed_details: dict[tuple[str, str], RecordDetail],
) -> list[str]:
    mismatches: list[str] = []
    for instruction in plan:
        detail = refreshed_details[(instruction.page, instruction.record_id)]
        title_text = detail.title.casefold()
        body_text = detail.body_text.casefold()

        for expected in instruction.expected_title_substrings:
            if expected.casefold() not in title_text:
                mismatches.append(
                    f"Missing title text '{expected}' in {instruction.page}/{instruction.record_id}."
                )
        for expected in instruction.expected_body_substrings:
            if expected.casefold() not in body_text:
                mismatches.append(
                    f"Missing body text '{expected}' in {instruction.page}/{instruction.record_id}."
                )
        if instruction.expected_done is not None and detail.is_done != instruction.expected_done:
            mismatches.append(
                f"Unexpected done state for {instruction.page}/{instruction.record_id}: "
                f"expected {instruction.expected_done}, got {detail.is_done}."
            )
    return mismatches


# Log and return one terminal workflow result.
def finish_run(
    run_log: RunLog,
    *,
    status: str,
    reason: str,
    apply_mode: bool,
    planned_update_count: int,
    plan_report_path: str,
    final_response_path: str | None = None,
    flag_found: bool = False,
    secret_values: list[str] | None = None,
) -> WorkflowResult:
    append_event(
        run_log,
        event="run_finished",
        data={
            "status": status,
            "reason": reason,
            "apply_mode": apply_mode,
            "planned_update_count": planned_update_count,
            "plan_report_path": plan_report_path,
            "final_response_path": final_response_path,
            "flag_found": flag_found,
        },
        secret_values=secret_values,
    )
    return WorkflowResult(
        status=status,
        reason=reason,
        apply_mode=apply_mode,
        planned_update_count=planned_update_count,
        run_log_path=str(run_log.path),
        plan_report_path=plan_report_path,
        final_response_path=final_response_path,
        flag_found=flag_found,
    )
