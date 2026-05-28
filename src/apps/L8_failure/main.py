# CLI workflow for the L8 failure log-condensation exercise.

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from typing import Any

from src.apps.L8_failure.candidate_extractor import extract_candidates
from src.apps.L8_failure.config import (
    AppConfig,
    ensure_runtime_directories,
    load_app_config,
)
from src.apps.L8_failure.hub_client import (
    HubClient,
    VerifyRequestGuard,
    build_verify_payload,
    extract_flag,
    mask_payload_for_storage,
)
from src.apps.L8_failure.llm_classifier import LlmCandidateClassifier, ModelRequestGuard
from src.apps.L8_failure.log_loader import build_log_profile, load_log_events
from src.apps.L8_failure.log_search import search_logs
from src.apps.L8_failure.models import ClassifiedEvent, LogEvent
from src.apps.L8_failure.models import HubResponse, RunLogEntry, RunReport
from src.apps.L8_failure.report_writer import write_json_file, write_jsonl_file
from src.apps.L8_failure.timeline_builder import build_condensed_timeline
from src.apps.L8_failure.token_budget import ensure_token_limit


COMPONENT_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]{2,}\b")
IGNORED_FEEDBACK_TOKENS = {"FLG", "HTTP", "JSON", "WARN", "ERRO", "ERROR", "CRIT", "INFO"}


# Return a compact UTC timestamp for human-readable run reports.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# Build one chronological report event that explains what the workflow just did.
def make_event(
    step: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    response: HubResponse | None = None,
) -> RunLogEntry:
    return RunLogEntry(
        timestamp=utc_now_iso(),
        step=step,
        message=message,
        details=details or {},
        request=request,
        response=response,
    )


# Parse CLI flags that let local validation stop before external services.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Condense L8 failure logs for Hub verification.")
    parser.add_argument(
        "--profile-only",
        action="store_true",
        help="Only profile and extract candidates; do not call OpenAI or the Hub.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Run model classification and build output, but do not submit to the Hub.",
    )
    return parser.parse_args()


# Load config in the narrowest mode needed by the selected CLI flags.
def load_config_for_args(args: argparse.Namespace) -> AppConfig:
    return load_app_config(
        require_openai=not args.profile_only,
        require_hub=not args.profile_only and not args.no_verify,
    )


# Run the local file-reading and candidate-selection phase.
def run_local_extraction(config: AppConfig, report: RunReport) -> tuple[list[LogEvent], list[LogEvent]]:
    events, parse_failures, characters_count = load_log_events(config.paths.source_log_file)
    profile = build_log_profile(
        config.paths.source_log_file,
        events,
        parse_failures,
        characters_count,
    )
    report.profile = profile
    write_json_file(config.paths.profile_file, profile)
    report.events.append(
        make_event(
            "profile_logs",
            "Read and profiled the source log file.",
            details={
                "lines_count": profile.lines_count,
                "characters_count": profile.characters_count,
                "estimated_tokens": profile.estimated_tokens,
                "parse_failures": profile.parse_failures,
            },
        )
    )

    candidates = extract_candidates(events)
    report.candidates_count = len(candidates)
    write_jsonl_file(config.paths.candidates_file, candidates)
    report.events.append(
        make_event(
            "extract_candidates",
            "Selected candidate events for model review.",
            details={"candidates_count": len(candidates)},
        )
    )
    return events, candidates


# Run the model-backed classification and write validated events for inspection.
def run_model_classification(
    config: AppConfig,
    report: RunReport,
    classifier: LlmCandidateClassifier,
    guard: ModelRequestGuard,
    candidates: list[LogEvent],
) -> list[ClassifiedEvent]:
    classified_events = classifier.classify_candidates(
        candidates,
        batch_size=config.runtime.batch_size,
    )
    report.model_requests_used = guard.used_requests
    report.classified_events_count = len(classified_events)
    write_jsonl_file(config.paths.classified_events_file, classified_events)
    report.events.append(
        make_event(
            "classify_candidates",
            "Classified candidate relevance with the local model step.",
            details={
                "classified_events_count": len(classified_events),
                "model_requests_used": guard.used_requests,
            },
        )
    )
    return classified_events


# Build and persist the final candidate answer before any Hub request is sent.
def run_timeline_build(config: AppConfig, report: RunReport, classified_events: list[ClassifiedEvent]) -> str:
    condensed_logs, token_estimate, selected_events = build_condensed_timeline(
        classified_events,
        target_token_limit=config.runtime.target_token_limit,
        hard_token_limit=config.runtime.token_limit,
    )
    token_estimate = ensure_token_limit(condensed_logs, config.runtime.token_limit)
    report.condensed_token_estimate = token_estimate
    config.paths.condensed_logs_file.write_text(condensed_logs, encoding="utf-8")
    report.events.append(
        make_event(
            "build_timeline",
            "Built the condensed one-event-per-line timeline.",
            details={
                "selected_events_count": len(selected_events),
                "estimated_tokens": token_estimate,
                "path": str(config.paths.condensed_logs_file.relative_to(config.paths.repo_root)),
            },
        )
    )
    return condensed_logs


# Extract known component IDs from Hub feedback so repair can search precisely.
def extract_feedback_components(feedback: Any, known_components: set[str]) -> set[str]:
    if isinstance(feedback, dict):
        values = feedback.values()
        return set().union(*(extract_feedback_components(value, known_components) for value in values))
    if isinstance(feedback, list):
        return set().union(*(extract_feedback_components(value, known_components) for value in feedback))
    if not isinstance(feedback, str):
        return set()

    found_components = set()
    for match in COMPONENT_PATTERN.finditer(feedback):
        token = match.group(0)
        if token in IGNORED_FEEDBACK_TOKENS:
            continue
        if token in known_components:
            found_components.add(token)
    return found_components


# Find new source events for components named by Hub feedback.
def find_repair_candidates(
    source_events: list[LogEvent],
    component_ids: set[str],
    already_classified_lines: set[int],
) -> list[LogEvent]:
    repair_candidates: list[LogEvent] = []
    for component_id in sorted(component_ids):
        result = search_logs(
            source_events,
            component_ids={component_id},
            limit=120,
        )
        repair_candidates.extend(
            event
            for event in result.events
            if event.source_line not in already_classified_lines
        )

    return sorted(
        {event.source_line: event for event in repair_candidates}.values(),
        key=lambda event: event.source_line,
    )


# Submit guarded Hub requests and repair the timeline when feedback names missing components.
def run_hub_verification_loop(
    config: AppConfig,
    report: RunReport,
    source_events: list[LogEvent],
    classified_events: list[ClassifiedEvent],
    classifier: LlmCandidateClassifier,
    model_guard: ModelRequestGuard,
) -> None:
    if config.hub is None:
        raise ValueError("Hub configuration is required for verification.")

    guard = VerifyRequestGuard(config.runtime.max_verify_requests)
    client = HubClient(config.hub, guard=guard)

    known_components = set(report.profile.component_ids) if report.profile else set()
    current_classified = list(classified_events)

    while guard.used_requests < guard.max_requests:
        condensed_logs = run_timeline_build(config, report, current_classified)
        request_payload = mask_payload_for_storage(build_verify_payload(config.hub, condensed_logs))
        response = client.verify_logs(condensed_logs)
        report.verify_requests_used = guard.used_requests
        report.events.append(
            make_event(
                "verify_with_hub",
                "Submitted condensed logs to the Hub verifier.",
                request=request_payload,
                response=response,
                details={"attempt": guard.used_requests},
            )
        )

        flag = extract_flag(response.payload) or extract_flag(response.text)
        if flag:
            report.flag = flag
            report.success = True
            return

        if response.status_code >= 400:
            report.error_summary = f"Hub verification failed with HTTP {response.status_code}."
            return

        feedback_components = extract_feedback_components(response.payload, known_components)
        feedback_components.update(extract_feedback_components(response.text, known_components))
        if not feedback_components:
            report.error_summary = "Hub verification finished without a flag and did not name known repair components."
            return

        already_classified_lines = {event.source_line for event in current_classified}
        repair_candidates = find_repair_candidates(
            source_events,
            feedback_components,
            already_classified_lines,
        )
        report.events.append(
            make_event(
                "repair_from_feedback",
                "Searched source logs for components named in Hub feedback.",
                details={
                    "feedback_components": sorted(feedback_components),
                    "repair_candidates_count": len(repair_candidates),
                },
            )
        )
        if not repair_candidates:
            report.error_summary = "Hub feedback named components, but no new source events were found."
            return

        new_classified_events = classifier.classify_candidates(
            repair_candidates,
            batch_size=config.runtime.batch_size,
        )
        report.model_requests_used = model_guard.used_requests
        current_classified.extend(new_classified_events)
        report.classified_events_count = len(current_classified)
        write_jsonl_file(config.paths.classified_events_file, current_classified)

    report.error_summary = "Hub verification guard reached before a flag was returned."


# Run the approved MVP1 workflow, stopping early for diagnostic CLI modes.
def run_workflow(config: AppConfig, report: RunReport, args: argparse.Namespace) -> None:
    source_events, candidates = run_local_extraction(config, report)
    if args.profile_only:
        report.error_summary = "Profile-only run completed before model classification."
        return

    if config.openai is None:
        raise ValueError("OpenAI configuration is required for model classification.")

    model_guard = ModelRequestGuard(config.runtime.max_model_requests)
    classifier = LlmCandidateClassifier(config.openai, guard=model_guard)
    classified_events = run_model_classification(
        config,
        report,
        classifier,
        model_guard,
        candidates,
    )
    if args.no_verify:
        run_timeline_build(config, report, classified_events)
        report.error_summary = "No-verify run completed before Hub submission."
        return

    run_hub_verification_loop(
        config,
        report,
        source_events,
        classified_events,
        classifier,
        model_guard,
    )


# CLI entrypoint that always writes a run report, even on failures.
def main() -> int:
    args = parse_args()
    config = load_config_for_args(args)
    ensure_runtime_directories(config.paths)

    report = RunReport(started_at=utc_now_iso())
    exit_code = 0

    try:
        run_workflow(config, report, args)
        if not report.success and not (args.profile_only or args.no_verify):
            exit_code = 1
    except Exception as error:
        report.error_summary = str(error)
        report.events.append(
            make_event(
                "runtime_error",
                "Workflow stopped because an unexpected error occurred.",
                details={
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )
        )
        exit_code = 1
    finally:
        report.ended_at = utc_now_iso()
        write_json_file(config.paths.run_report_file, report)

    print(f"Run report saved to {config.paths.run_report_file}")
    if report.flag:
        print(report.flag)
    elif report.error_summary:
        print(report.error_summary)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
