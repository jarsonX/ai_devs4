# Local workflow orchestration for L22 phonecall modes.

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from src.apps.L22_phonecall.audio_gateway import AudioGateway
from src.apps.L22_phonecall.config import AppConfig, build_safe_config_summary, ensure_runtime_directories
from src.apps.L22_phonecall.conversation_interpreter import ConversationInterpreter
from src.apps.L22_phonecall.models import (
    ApiResponse,
    CallReport,
    ConversationState,
    LoggedExchange,
    response_contains_flag,
)
from src.apps.L22_phonecall.response_planner import ResponsePlanner
from src.apps.L22_phonecall.run_log import CallRunLogger, TranscriptEntry
from src.apps.L22_phonecall.state_machine import (
    ConversationSnapshot,
    apply_operator_interpretation,
    mark_session_started,
    mark_speech_act_sent,
)


DEFAULT_TRANSCRIPT_FIXTURE = (
    "RD224 jest zablokowana, RD472 zamknieta przez remont, a RD820 jest przejezdna.",
    "Monitoring na RD820 wylaczony, mozecie jechac.",
)


# Store the compact output returned by CLI modes.
@dataclass(frozen=True)
class WorkflowResult:
    mode: str
    status: str
    call_id: str | None
    final_state: ConversationState | None
    selected_roads: list[str]
    turns: int
    call_dir: str | None
    report_path: str | None
    transcript_path: str | None
    message: str

    # Convert the workflow result into JSON-safe CLI output.
    def to_dict(self, config: AppConfig) -> dict[str, object]:
        return {
            "app": "L22_phonecall",
            "mode": self.mode,
            "status": self.status,
            "message": self.message,
            "call_id": self.call_id,
            "final_state": self.final_state.value if self.final_state else None,
            "selected_roads": self.selected_roads,
            "turns": self.turns,
            "call_dir": self.call_dir,
            "report_path": self.report_path,
            "transcript_path": self.transcript_path,
            "config": build_safe_config_summary(config),
        }


# Provide deterministic audio behavior for local simulation only.
class LocalFakeAudioModel:
    # Store transcripts returned by fake STT and bytes returned by fake TTS.
    def __init__(self, transcripts: list[str] | tuple[str, ...]) -> None:
        self.transcripts = list(transcripts)
        self.transcribe_index = 0

    # Return the next fixture transcript for a saved fake operator audio file.
    def transcribe(self, *, audio_path: Path, model: str, language: str) -> str:
        if self.transcribe_index >= len(self.transcripts):
            raise ValueError("No fake transcript left for audio simulation.")
        transcript = self.transcripts[self.transcribe_index]
        self.transcribe_index += 1
        return transcript

    # Return deterministic fake MP3 bytes for one approved utterance.
    def synthesize(
        self,
        *,
        text: str,
        model: str,
        voice: str,
        response_format: str,
    ) -> bytes:
        return f"fake-{response_format}:{voice}:{text}".encode("utf-8")


# Run the local transcript workflow without external calls.
def run_dry_run(config: AppConfig) -> dict[str, object]:
    result = run_local_fixture_workflow(
        config,
        mode="dry-run",
        transcripts=DEFAULT_TRANSCRIPT_FIXTURE,
        simulate_audio=False,
    )
    return result.to_dict(config)


# Run the fake audio workflow without external calls.
def run_simulate_audio(config: AppConfig) -> dict[str, object]:
    result = run_local_fixture_workflow(
        config,
        mode="simulate-audio",
        transcripts=DEFAULT_TRANSCRIPT_FIXTURE,
        simulate_audio=True,
    )
    return result.to_dict(config)


# Return a safe CLI result for the live mode until explicit approval is handled outside the app.
def build_submit_blocked_result(config: AppConfig) -> dict[str, object]:
    result = WorkflowResult(
        mode="submit",
        status="approval_required",
        call_id=None,
        final_state=None,
        selected_roads=[],
        turns=0,
        call_dir=None,
        report_path=None,
        transcript_path=None,
        message="Live Hub/OpenAI execution is approval-gated and is not started by this local mode yet.",
    )
    return result.to_dict(config)


# Run the shared local fixture workflow and write reviewable artifacts.
def run_local_fixture_workflow(
    config: AppConfig,
    *,
    mode: str,
    transcripts: list[str] | tuple[str, ...],
    simulate_audio: bool,
) -> WorkflowResult:
    ensure_runtime_directories(config.paths)
    logger = CallRunLogger(config.paths)
    interpreter = ConversationInterpreter()
    planner = ResponsePlanner()
    audio_gateway = build_local_audio_gateway(config, transcripts) if simulate_audio else None

    snapshot = mark_session_started(ConversationSnapshot()).snapshot
    entries: list[TranscriptEntry] = []
    hub_requests_used = 1
    flag_found = False

    for turn_number, fixture_transcript in enumerate(transcripts, start=1):
        operator_audio_path = None
        assistant_audio_path = None
        logger.save_operator_raw(turn_number, build_fake_operator_payload(fixture_transcript, simulate_audio))

        if audio_gateway is not None:
            operator_audio_path = logger.save_operator_audio(turn_number, f"fake-operator-{turn_number}".encode())
            transcript = audio_gateway.transcribe_operator_audio(operator_audio_path)
        else:
            transcript = fixture_transcript
        logger.save_operator_transcript(turn_number, transcript)

        interpretation = interpreter.interpret(transcript)
        logger.save_operator_interpretation(turn_number, interpretation)
        decision = apply_operator_interpretation(snapshot, interpretation)
        snapshot = decision.snapshot

        if snapshot.state == ConversationState.FAILED:
            entries.append(
                TranscriptEntry(
                    turn_number=turn_number,
                    operator_text=transcript,
                    assistant_text=None,
                    state=snapshot.state.value,
                    operator_audio_path=operator_audio_path,
                    assistant_audio_path=None,
                )
            )
            break

        plan = planner.plan(
            decision.speech_act,
            roads=snapshot.selected_roads,
            max_words=config.runtime.max_utterance_words,
        )
        logger.save_assistant_plan(turn_number, plan)
        logger.save_assistant_utterance(turn_number, plan.utterance)

        if audio_gateway is not None:
            assistant_audio_path = logger.turn_paths(turn_number).file("assistant.audio.mp3")
            audio_gateway.generate_assistant_audio(plan.utterance, assistant_audio_path)
        else:
            assistant_audio_path = logger.save_assistant_audio(turn_number, build_dry_audio_bytes(plan.utterance))

        assistant_audio_bytes = assistant_audio_path.read_bytes()
        fake_request = build_fake_audio_request(assistant_audio_bytes)
        fake_exchange = build_fake_exchange(turn_number, fake_request)
        logger.save_hub_request(turn_number, fake_request)
        logger.save_hub_response(turn_number, fake_exchange)
        flag_found = flag_found or response_contains_flag(fake_exchange.response)
        hub_requests_used += 1

        sent_snapshot = mark_speech_act_sent(snapshot, decision.speech_act)
        if snapshot.state not in {ConversationState.MONITORING_CONFIRMED, ConversationState.FAILED}:
            snapshot = sent_snapshot

        entries.append(
            TranscriptEntry(
                turn_number=turn_number,
                operator_text=transcript,
                assistant_text=plan.utterance,
                state=snapshot.state.value,
                operator_audio_path=operator_audio_path,
                assistant_audio_path=assistant_audio_path,
            )
        )
        if snapshot.state in {ConversationState.MONITORING_CONFIRMED, ConversationState.FAILED}:
            break

    report = CallReport(
        call_id=logger.call_id,
        final_state=snapshot.state,
        flag_found=flag_found,
        turns=len(entries),
        hub_requests_used=hub_requests_used,
        mode=mode,
        stt_requests_used=audio_gateway.stt_requests_used() if audio_gateway else 0,
        interpreter_requests_used=interpreter.model_requests_used(),
        planner_requests_used=planner.model_requests_used(),
        tts_requests_used=audio_gateway.tts_requests_used() if audio_gateway else 0,
        selected_roads=list(snapshot.selected_roads),
    )
    logger.save_call_report(report)
    logger.save_call_transcript(entries, mode=mode)

    return WorkflowResult(
        mode=mode,
        status="completed" if snapshot.state == ConversationState.MONITORING_CONFIRMED else "stopped",
        call_id=logger.call_id,
        final_state=snapshot.state,
        selected_roads=list(snapshot.selected_roads),
        turns=len(entries),
        call_dir=relative_to_repo(config, logger.paths.call_dir),
        report_path=relative_to_repo(config, logger.paths.report_path),
        transcript_path=relative_to_repo(config, logger.paths.transcript_path),
        message="Local fixture workflow completed without external calls.",
    )


# Build the fake audio gateway used by local simulation.
def build_local_audio_gateway(config: AppConfig, transcripts: list[str] | tuple[str, ...]) -> AudioGateway:
    return AudioGateway(
        client=LocalFakeAudioModel(transcripts),
        stt_model=config.openai.stt_model if config.openai else "fake-stt",
        tts_model=config.openai.tts_model if config.openai else "fake-tts",
        tts_voice=config.openai.tts_voice if config.openai else "fake-voice",
        tts_response_format=config.openai.tts_response_format if config.openai else "mp3",
        operator_language=config.runtime.operator_language,
        max_stt_requests=config.runtime.max_stt_requests,
        max_tts_requests=config.runtime.max_tts_requests,
    )


# Build a fake operator payload for logs.
def build_fake_operator_payload(transcript: str, simulate_audio: bool) -> dict[str, object]:
    if simulate_audio:
        return {"source": "local_fixture", "audio": "<fake-operator-audio>", "transcript_hint": transcript}
    return {"source": "local_fixture", "transcript": transcript}


# Build deterministic fake audio bytes for dry-run artifacts.
def build_dry_audio_bytes(utterance: str) -> bytes:
    return f"dry-run-audio:{utterance}".encode("utf-8")


# Build a fake Hub audio request without dumping raw base64 into Markdown transcripts.
def build_fake_audio_request(audio_bytes: bytes) -> dict[str, object]:
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    return {
        "task": "phonecall",
        "answer": {
            "audio": encoded_audio,
        },
    }


# Build one fake logged Hub exchange for local fixture runs.
def build_fake_exchange(turn_number: int, request: dict[str, object]) -> LoggedExchange:
    return LoggedExchange(
        sequence=turn_number + 1,
        action="audio",
        request=request,
        response=ApiResponse(
            status_code=200,
            payload={"code": 0, "message": "local fixture response"},
            text="local fixture response",
        ),
    )


# Return a repository-relative path for compact CLI output.
def relative_to_repo(config: AppConfig, path: Path) -> str:
    try:
        return str(path.relative_to(config.paths.repo_root)).replace("\\", "/")
    except ValueError:
        return str(path)
