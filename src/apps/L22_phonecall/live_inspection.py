# Minimal live Hub inspection entrypoints for L22 phonecall.

from __future__ import annotations

from typing import Any

from src.apps.L22_phonecall.audio_gateway import AudioGateway, AudioModelProtocol
from src.apps.L22_phonecall.config import AppConfig, build_safe_config_summary, ensure_runtime_directories
from src.apps.L22_phonecall.conversation_interpreter import ConversationInterpreter
from src.apps.L22_phonecall.hub_response import extract_operator_turn_input
from src.apps.L22_phonecall.models import CallReport, ConversationState, LoggedExchange, SpeechAct, response_contains_flag
from src.apps.L22_phonecall.openai_gateway import OpenAIAudioModel
from src.apps.L22_phonecall.response_planner import ResponsePlanner
from src.apps.L22_phonecall.run_log import CallRunLogger, TranscriptEntry
from src.apps.L22_phonecall.state_machine import ConversationSnapshot, mark_session_started, mark_speech_act_sent
from src.apps.L22_phonecall.verify_client import PhonecallVerifyClient, SessionProtocol


# Run exactly one live Hub start request and persist the raw response.
def inspect_live_start(config: AppConfig, *, session: SessionProtocol | None = None) -> dict[str, object]:
    if config.hub is None:
        raise ValueError("Hub config is required for live inspection.")
    ensure_runtime_directories(config.paths)
    logger = CallRunLogger(config.paths)
    client = PhonecallVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=1,
        session=session,
    )

    exchange = client.start()
    logger.save_hub_request(1, exchange.request)
    logger.save_hub_response(1, exchange)
    logger.save_call_report(
        CallReport(
            call_id=logger.call_id,
            final_state=ConversationState.STARTED,
            flag_found=response_contains_flag(exchange.response),
            turns=0,
            hub_requests_used=client.request_count(),
            mode="inspect-live",
        )
    )
    logger.save_call_transcript([], mode="inspect-live")

    return {
        "app": "L22_phonecall",
        "mode": "inspect-live",
        "status": "completed",
        "message": "Live Hub start inspection completed. Raw response is stored in runtime data.",
        "call_id": logger.call_id,
        "http_status": exchange.response.status_code,
        "response_payload_type": type(exchange.response.payload).__name__ if exchange.response.payload is not None else None,
        "response_keys": extract_payload_keys(exchange),
        "flag_found": response_contains_flag(exchange.response),
        "hub_requests_used": client.request_count(),
        "call_dir": relative_to_repo(config, logger.paths.call_dir),
        "report_path": relative_to_repo(config, logger.paths.report_path),
        "transcript_path": relative_to_repo(config, logger.paths.transcript_path),
        "config": build_safe_config_summary(config),
    }


# Run live start, send the first assistant audio turn, and persist the response shape.
def inspect_live_first_audio_turn(
    config: AppConfig,
    *,
    session: SessionProtocol | None = None,
    audio_model: AudioModelProtocol | None = None,
) -> dict[str, object]:
    if config.hub is None:
        raise ValueError("Hub config is required for live first-turn inspection.")
    if config.openai is None and audio_model is None:
        raise ValueError("OpenAI config or injected audio model is required for live first-turn inspection.")

    ensure_runtime_directories(config.paths)
    logger = CallRunLogger(config.paths)
    client = PhonecallVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=2,
        session=session,
    )
    audio_gateway = build_inspection_audio_gateway(config, audio_model=audio_model)

    start_exchange = client.start()
    logger.save_hub_request(1, start_exchange.request)
    logger.save_hub_response(1, start_exchange)

    decision = mark_session_started(ConversationSnapshot())
    planner = ResponsePlanner()
    plan = planner.plan(
        decision.speech_act,
        max_words=config.runtime.max_utterance_words,
    )
    turn_number = 2
    logger.save_assistant_plan(turn_number, plan)
    logger.save_assistant_utterance(turn_number, plan.utterance)
    assistant_audio_path = logger.turn_paths(turn_number).file("assistant.audio.mp3")
    audio_gateway.generate_assistant_audio(plan.utterance, assistant_audio_path)

    audio_base64 = encode_audio_file(assistant_audio_path)
    audio_exchange = client.send_audio(audio_base64)
    logger.save_hub_request(turn_number, audio_exchange.request)
    logger.save_hub_response(turn_number, audio_exchange)

    operator_input = extract_operator_turn_input(audio_exchange)
    operator_kind = "none"
    operator_audio_path = None
    operator_text = None
    if operator_input.has_audio():
        operator_kind = "audio"
        operator_audio_path = logger.save_operator_audio(
            turn_number,
            operator_input.audio_bytes or b"",
            extension=operator_input.audio_extension,
        )
    elif operator_input.has_text():
        operator_kind = "text"
        operator_text = operator_input.text or ""
        logger.save_operator_transcript(turn_number, operator_text)

    snapshot = mark_speech_act_sent(decision.snapshot, decision.speech_act)
    logger.save_call_report(
        CallReport(
            call_id=logger.call_id,
            final_state=snapshot.state,
            flag_found=response_contains_flag(start_exchange.response)
            or response_contains_flag(audio_exchange.response),
            turns=1,
            hub_requests_used=client.request_count(),
            mode="inspect-live-first-turn",
            tts_requests_used=audio_gateway.tts_requests_used(),
        )
    )
    logger.save_call_transcript(
        [
            TranscriptEntry(
                turn_number=turn_number,
                operator_text=operator_text,
                assistant_text=plan.utterance,
                state=snapshot.state.value,
                operator_audio_path=operator_audio_path,
                assistant_audio_path=assistant_audio_path,
            )
        ],
        mode="inspect-live-first-turn",
    )

    return {
        "app": "L22_phonecall",
        "mode": "inspect-live-first-turn",
        "status": "completed",
        "message": "Live first audio turn inspection completed. Raw responses are stored in runtime data.",
        "call_id": logger.call_id,
        "final_state": snapshot.state.value,
        "http_status": audio_exchange.response.status_code,
        "response_payload_type": (
            type(audio_exchange.response.payload).__name__ if audio_exchange.response.payload is not None else None
        ),
        "response_keys": extract_payload_keys(audio_exchange),
        "operator_input_kind": operator_kind,
        "operator_source_field": operator_input.source_field,
        "operator_audio_path": relative_to_repo(config, operator_audio_path) if operator_audio_path else None,
        "operator_text_present": bool(operator_text),
        "flag_found": response_contains_flag(start_exchange.response)
        or response_contains_flag(audio_exchange.response),
        "hub_requests_used": client.request_count(),
        "tts_requests_used": audio_gateway.tts_requests_used(),
        "call_dir": relative_to_repo(config, logger.paths.call_dir),
        "report_path": relative_to_repo(config, logger.paths.report_path),
        "transcript_path": relative_to_repo(config, logger.paths.transcript_path),
        "config": build_safe_config_summary(config),
    }


# Transcribe one saved operator audio artifact and persist interpretation output.
def transcribe_saved_operator_audio(
    config: AppConfig,
    *,
    call_id: str,
    turn_number: int,
    audio_model: AudioModelProtocol | None = None,
) -> dict[str, object]:
    if config.openai is None and audio_model is None:
        raise ValueError("OpenAI config or injected audio model is required for transcription.")
    logger = CallRunLogger(config.paths, call_id=call_id)
    audio_path = find_operator_audio_path(config, call_id=call_id, turn_number=turn_number)
    audio_gateway = build_inspection_audio_gateway(config, audio_model=audio_model, max_tts_requests=0)

    transcript = audio_gateway.transcribe_operator_audio(audio_path)
    logger.save_operator_transcript(turn_number, transcript)

    interpreter = ConversationInterpreter()
    interpretation = interpreter.interpret(
        transcript,
        context={
            "conversation_state": ConversationState.ASKED_ROAD_STATUS.value,
        },
    )
    logger.save_operator_interpretation(turn_number, interpretation)
    logger.rebuild_call_transcript_from_artifacts(mode="inspect-live-manual")

    return {
        "app": "L22_phonecall",
        "mode": "inspect-transcribe-operator",
        "status": "completed",
        "message": "Saved operator audio was transcribed and interpreted.",
        "call_id": call_id,
        "turn_number": turn_number,
        "audio_path": relative_to_repo(config, audio_path),
        "transcript_path": relative_to_repo(config, logger.turn_paths(turn_number).file("operator.transcript.txt")),
        "interpretation_path": relative_to_repo(
            config,
            logger.turn_paths(turn_number).file("operator.interpretation.json"),
        ),
        "intent": interpretation.intent.value,
        "confidence": interpretation.confidence.value,
        "road_statuses": interpretation.road_statuses.to_dict(),
        "stt_requests_used": audio_gateway.stt_requests_used(),
        "interpreter_requests_used": interpreter.model_requests_used(),
        "config": build_safe_config_summary(config),
    }


# Send one approved speech act as audio in an existing live session.
def send_live_speech_act(
    config: AppConfig,
    *,
    call_id: str,
    turn_number: int,
    speech_act: SpeechAct,
    roads: list[str] | tuple[str, ...] = (),
    session: SessionProtocol | None = None,
    audio_model: AudioModelProtocol | None = None,
) -> dict[str, object]:
    if config.hub is None:
        raise ValueError("Hub config is required for live speech-act sending.")
    if config.openai is None and audio_model is None:
        raise ValueError("OpenAI config or injected audio model is required for live speech-act sending.")

    logger = CallRunLogger(config.paths, call_id=call_id)
    client = PhonecallVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=1,
        session=session,
    )
    audio_gateway = build_inspection_audio_gateway(config, audio_model=audio_model)
    planner = ResponsePlanner()
    plan = planner.plan(
        speech_act,
        roads=roads,
        max_words=config.runtime.max_utterance_words,
    )
    logger.save_assistant_plan(turn_number, plan)
    logger.save_assistant_utterance(turn_number, plan.utterance)
    assistant_audio_path = logger.turn_paths(turn_number).file("assistant.audio.mp3")
    audio_gateway.generate_assistant_audio(plan.utterance, assistant_audio_path)

    exchange = client.send_audio(encode_audio_file(assistant_audio_path))
    logger.save_hub_request(turn_number, exchange.request)
    logger.save_hub_response(turn_number, exchange)

    operator_input = extract_operator_turn_input(exchange)
    operator_kind = "none"
    operator_audio_path = None
    operator_text = None
    if operator_input.has_audio():
        operator_kind = "audio"
        operator_audio_path = logger.save_operator_audio(
            turn_number,
            operator_input.audio_bytes or b"",
            extension=operator_input.audio_extension,
        )
    elif operator_input.has_text():
        operator_kind = "text"
        operator_text = operator_input.text or ""
        logger.save_operator_transcript(turn_number, operator_text)

    logger.rebuild_call_transcript_from_artifacts(mode="inspect-live-manual")

    return {
        "app": "L22_phonecall",
        "mode": "inspect-send-speech-act",
        "status": "completed",
        "message": "One live speech act was sent as audio. Raw response is stored in runtime data.",
        "call_id": call_id,
        "turn_number": turn_number,
        "speech_act": speech_act.value,
        "http_status": exchange.response.status_code,
        "response_payload_type": type(exchange.response.payload).__name__ if exchange.response.payload is not None else None,
        "response_keys": extract_payload_keys(exchange),
        "operator_input_kind": operator_kind,
        "operator_source_field": operator_input.source_field,
        "operator_audio_path": relative_to_repo(config, operator_audio_path) if operator_audio_path else None,
        "operator_text_present": bool(operator_text),
        "flag_found": response_contains_flag(exchange.response),
        "hub_requests_used": client.request_count(),
        "tts_requests_used": audio_gateway.tts_requests_used(),
        "call_dir": relative_to_repo(config, logger.paths.call_dir),
        "config": build_safe_config_summary(config),
    }


# Build the audio gateway for one live inspection turn.
def build_inspection_audio_gateway(
    config: AppConfig,
    *,
    audio_model: AudioModelProtocol | None = None,
    max_tts_requests: int = 1,
) -> AudioGateway:
    if audio_model is None:
        if config.openai is None:
            raise ValueError("OpenAI config is required to build the real audio model.")
        audio_model = OpenAIAudioModel(config.openai)
    return AudioGateway(
        client=audio_model,
        stt_model=config.openai.stt_model if config.openai else "fake-stt",
        tts_model=config.openai.tts_model if config.openai else "fake-tts",
        tts_voice=config.openai.tts_voice if config.openai else "fake-voice",
        tts_response_format=config.openai.tts_response_format if config.openai else "mp3",
        operator_language=config.runtime.operator_language,
        max_stt_requests=config.runtime.max_stt_requests,
        max_tts_requests=max_tts_requests,
    )


# Encode one local assistant audio artifact for Hub transport.
def encode_audio_file(path: Any) -> str:
    import base64

    return base64.b64encode(path.read_bytes()).decode("ascii")


# Find a saved operator audio artifact for one turn.
def find_operator_audio_path(config: AppConfig, *, call_id: str, turn_number: int) -> Any:
    turn_dir = config.paths.calls_dir / call_id / f"turn_{turn_number:03d}"
    matches = sorted(turn_dir.glob("operator.audio.*"))
    if not matches:
        raise ValueError(f"No operator audio artifact found for {call_id} turn {turn_number}.")
    return matches[0]


# Return top-level payload keys without exposing raw runtime data in CLI output.
def extract_payload_keys(exchange: LoggedExchange) -> list[str]:
    if isinstance(exchange.response.payload, dict):
        return sorted(str(key) for key in exchange.response.payload.keys())
    return []


# Return a repository-relative path for compact CLI output.
def relative_to_repo(config: AppConfig, path: Any) -> str:
    try:
        return str(path.relative_to(config.paths.repo_root)).replace("\\", "/")
    except ValueError:
        return str(path)
