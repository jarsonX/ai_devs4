# Runtime workflow for the L21 radiomonitoring app.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L21_radiomonitoring.attachment_router import (
    decode_attachment,
    parse_decoded_attachment,
)
from src.apps.L21_radiomonitoring.capture import (
    capture_signals,
    exchanges_to_dict,
    load_cached_signals,
    write_json,
)
from src.apps.L21_radiomonitoring.config import (
    AppConfig,
    build_safe_config_summary,
)
from src.apps.L21_radiomonitoring.extractors import (
    extract_candidates_from_structured,
    extract_candidates_from_text,
    score_text_relevance,
)
from src.apps.L21_radiomonitoring.llm_gateway import LlmGateway, ModelRequestGuard
from src.apps.L21_radiomonitoring.models import (
    AttachmentArtifact,
    CapturedSignal,
    EvidenceCandidate,
    FinalReport,
    LoggedExchange,
    response_contains_flag,
    summarize_signal_payload,
)
from src.apps.L21_radiomonitoring.solver import (
    EvidenceBundle,
    derive_report_from_evidence,
    filter_final_field_candidates,
    validate_final_report,
)
from src.apps.L21_radiomonitoring.verify_client import RadiomonitoringVerifyClient


# Return one UTC timestamp for report names and metadata.
def current_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# Convert all captured signal summaries into JSON-safe output.
def summarize_signals(signals: list[CapturedSignal]) -> list[dict[str, Any]]:
    return [
        {
            "sequence": signal.sequence,
            "kind": signal.kind,
            "raw_file": signal.raw_file,
            "summary": summarize_signal_payload(signal.payload),
        }
        for signal in signals
    ]


# Capture live Hub signals without model analysis.
def run_inspect(config: AppConfig) -> dict[str, Any]:
    if config.hub is None:
        raise ValueError("Hub config is required for inspect mode.")
    client = RadiomonitoringVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_verify_requests,
    )
    signals, exchanges = capture_signals(config, client)
    stamp = current_stamp()
    output_path = config.paths.output_dir / f"inspection_{stamp}.json"
    write_json(
        output_path,
        {
            "mode": "inspect",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": build_safe_config_summary(config),
            "request_count": client.request_count(),
            "signals": summarize_signals(signals),
            "exchanges": exchanges_to_dict(exchanges),
        },
    )
    return {
        "status": "inspection_ok",
        "signal_count": len(signals),
        "request_count": client.request_count(),
        "inspection_path": str(output_path.relative_to(config.paths.repo_root)),
        "signals": summarize_signals(signals),
    }


# Build evidence from cached or freshly captured signals.
def build_evidence_bundle(
    config: AppConfig,
    signals: list[CapturedSignal],
    llm: LlmGateway,
) -> tuple[EvidenceBundle, list[AttachmentArtifact]]:
    candidates: list[EvidenceCandidate] = []
    snippets: list[dict[str, str]] = []
    scored_snippets: list[tuple[int, dict[str, str]]] = []
    artifacts: list[AttachmentArtifact] = []

    for signal in signals:
        if signal.kind == "transcription":
            text = str(signal.payload.get("transcription", ""))
            source = f"signal:{signal.sequence}:transcription"
            score = score_text_relevance(text)
            candidates.extend(extract_candidates_from_text(text, source=source))
            if score > 0:
                scored_snippets.append((score, {"source": source, "text": text}))

        if signal.kind == "attachment":
            artifact = decode_attachment(config, signal)
            artifacts.append(artifact)
            source = f"signal:{signal.sequence}:attachment:{artifact.path}"
            parsed_value = parse_decoded_attachment(config, artifact)
            if parsed_value is not None:
                candidates.extend(
                    extract_candidates_from_structured(parsed_value, source=source)
                )
                for text in _structured_value_to_texts(parsed_value):
                    score = score_text_relevance(text)
                    if score > 0:
                        scored_snippets.append((score, {"source": source, "text": text}))
            elif artifact.route == "image":
                image_path = config.paths.repo_root / artifact.path
                extracted_text, image_candidates = llm.extract_from_image(
                    image_path,
                    source=source,
                )
                candidates.extend(image_candidates)
                extracted_path = config.paths.extracted_dir / f"{signal.sequence:03d}_image_extraction.json"
                write_json(
                    extracted_path,
                    {
                        "source": source,
                        "artifact": artifact.to_dict(),
                        "extracted_text": extracted_text,
                        "candidates": [candidate.to_dict() for candidate in image_candidates],
                    },
                )
                if extracted_text:
                    scored_snippets.append(
                        (
                            score_text_relevance(extracted_text) + 2,
                            {"source": f"{source}:vision_text", "text": extracted_text},
                        )
                    )
            elif artifact.route == "audio":
                audio_path = config.paths.repo_root / artifact.path
                transcript = llm.transcribe_audio(audio_path)
                audio_candidates = extract_candidates_from_text(
                    transcript,
                    source=source,
                    method="audio_transcription_regex",
                )
                candidates.extend(audio_candidates)
                extracted_path = config.paths.extracted_dir / f"{signal.sequence:03d}_audio_transcription.json"
                write_json(
                    extracted_path,
                    {
                        "source": source,
                        "artifact": artifact.to_dict(),
                        "transcript": transcript,
                        "candidates": [candidate.to_dict() for candidate in audio_candidates],
                    },
                )
                scored_snippets.append(
                    (
                        score_text_relevance(transcript) + 4,
                        {"source": f"{source}:audio_transcript", "text": transcript},
                    )
                )

    for _, snippet in sorted(scored_snippets, key=lambda item: item[0], reverse=True):
        snippets.append(snippet)

    candidates.extend(
        llm.extract_from_text_bundle(
            snippets,
            max_chars=config.runtime.max_model_input_chars,
        )
    )

    return EvidenceBundle(candidates=candidates, text_snippets=snippets), artifacts


# Synthesize, validate, and store a final answer from evidence candidates.
def solve_from_signals(
    config: AppConfig,
    signals: list[CapturedSignal],
) -> tuple[FinalReport, Path, EvidenceBundle, list[AttachmentArtifact]]:
    if config.openai is None:
        raise ValueError("OpenAI config is required for solve mode.")
    llm = LlmGateway(
        config.openai,
        guard=ModelRequestGuard(config.runtime.max_model_requests),
    )
    evidence_bundle, artifacts = build_evidence_bundle(config, signals, llm)
    final_candidates = filter_final_field_candidates(evidence_bundle.candidates)
    if not final_candidates:
        raise ValueError("No final-field evidence candidates were extracted.")

    derived_report = derive_report_from_evidence(
        final_candidates,
        evidence_bundle.text_snippets,
    )
    if derived_report is not None:
        final_report = derived_report
    else:
        proposed_report = llm.synthesize_final_report(
            final_candidates,
            max_chars=config.runtime.max_model_input_chars,
        )
        final_report = validate_final_report(proposed_report)

    stamp = current_stamp()
    output_path = config.paths.output_dir / f"solution_{stamp}.json"
    write_json(
        output_path,
        {
            "mode": "solve",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": build_safe_config_summary(config),
            "signals": summarize_signals(signals),
            "attachments": [artifact.to_dict() for artifact in artifacts],
            "text_snippet_count": len(evidence_bundle.text_snippets),
            "candidates": [
                candidate.to_dict() for candidate in evidence_bundle.candidates
            ],
            "final_candidates": [
                candidate.to_dict() for candidate in final_candidates
            ],
            "final_report": final_report.to_dict(),
        },
    )
    return final_report, output_path, evidence_bundle, artifacts


# Run solve mode against existing cached signals.
def run_solve(config: AppConfig) -> dict[str, Any]:
    signals = load_cached_signals(config)
    if not signals:
        raise ValueError("No cached signals found. Run inspect or submit first.")
    final_report, solution_path, evidence_bundle, artifacts = solve_from_signals(config, signals)
    return {
        "status": "solved_locally",
        "signal_count": len(signals),
        "attachment_count": len(artifacts),
        "candidate_count": len(evidence_bundle.candidates),
        "solution_path": str(solution_path.relative_to(config.paths.repo_root)),
        "final_report": final_report.to_dict(),
    }


# Run the full live capture, solve, and final Hub submission path.
def run_submit(config: AppConfig, *, from_cache: bool = False) -> dict[str, Any]:
    if config.hub is None:
        raise ValueError("Hub config is required for submit mode.")

    exchanges: list[LoggedExchange] = []
    client = RadiomonitoringVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_verify_requests,
    )

    if from_cache:
        signals = load_cached_signals(config)
        if not signals:
            raise ValueError("No cached signals found for --from-cache submit.")
    else:
        signals, exchanges = capture_signals(config, client)

    final_report, solution_path, evidence_bundle, artifacts = solve_from_signals(config, signals)
    transmit_exchange = client.transmit(final_report.to_answer())
    exchanges.append(transmit_exchange)
    final_response = transmit_exchange.response

    stamp = current_stamp()
    run_report_path = config.paths.output_dir / f"run_report_{stamp}.json"
    final_response_path = config.paths.output_dir / f"final_response_{stamp}.json"
    write_json(
        run_report_path,
        {
            "mode": "submit",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": build_safe_config_summary(config),
            "request_count": client.request_count(),
            "signals": summarize_signals(signals),
            "attachments": [artifact.to_dict() for artifact in artifacts],
            "candidate_count": len(evidence_bundle.candidates),
            "solution_path": str(solution_path.relative_to(config.paths.repo_root)),
            "final_report": final_report.to_dict(),
            "flag_found": response_contains_flag(final_response),
            "exchanges": exchanges_to_dict(exchanges),
        },
    )
    write_json(
        final_response_path,
        {
            "status_code": final_response.status_code,
            "payload": final_response.payload,
            "text": final_response.text,
            "flag_found": response_contains_flag(final_response),
        },
    )
    return {
        "status": "solved" if response_contains_flag(final_response) else "submitted",
        "flag_found": response_contains_flag(final_response),
        "request_count": client.request_count(),
        "signal_count": len(signals),
        "attachment_count": len(artifacts),
        "candidate_count": len(evidence_bundle.candidates),
        "solution_path": str(solution_path.relative_to(config.paths.repo_root)),
        "run_report_path": str(run_report_path.relative_to(config.paths.repo_root)),
        "final_response_path": str(final_response_path.relative_to(config.paths.repo_root)),
        "final_report": final_report.to_dict(),
        "final_payload": final_response.payload,
        "final_text": final_response.text,
    }


# Convert parsed structured values into compact model-readable strings.
def _structured_value_to_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (dict, list)):
        return [json.dumps(value, ensure_ascii=False)]
    return [str(value)]
