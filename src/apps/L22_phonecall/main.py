# CLI entrypoint for the L22 phonecall workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L22_phonecall.config import (
    ensure_runtime_directories,
    load_app_config,
)
from src.apps.L22_phonecall.models import SpeechAct
from src.apps.L22_phonecall.live_inspection import (
    inspect_live_first_audio_turn,
    inspect_live_start,
    send_live_speech_act,
    transcribe_saved_operator_audio,
)
from src.apps.L22_phonecall.workflow import build_submit_blocked_result, run_dry_run, run_simulate_audio


# Parse the small CLI used for dry, simulation, and live submission modes.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="L22 phonecall solution.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Run local transcript fixtures.")
    mode.add_argument(
        "--simulate-audio",
        action="store_true",
        help="Run local fake audio flow without external calls.",
    )
    mode.add_argument(
        "--inspect-live",
        action="store_true",
        help="Run one guarded live Hub start inspection.",
    )
    mode.add_argument(
        "--inspect-live-first-turn",
        action="store_true",
        help="Run live start plus one generated assistant audio turn.",
    )
    mode.add_argument(
        "--inspect-transcribe-operator",
        action="store_true",
        help="Transcribe one saved operator audio artifact.",
    )
    mode.add_argument(
        "--inspect-send-speech-act",
        action="store_true",
        help="Send one approved speech act as live audio.",
    )
    mode.add_argument(
        "--submit",
        action="store_true",
        help="Return the approval-gated submit placeholder.",
    )
    parser.add_argument("--call-id", help="Call ID used by inspection helper modes.")
    parser.add_argument("--turn-number", type=int, default=2, help="Turn number used by inspection helper modes.")
    parser.add_argument("--speech-act", choices=[item.value for item in SpeechAct], help="Speech act to send.")
    parser.add_argument("--roads", default="", help="Comma-separated road IDs for speech acts that need roads.")
    return parser.parse_args()


# Run the selected mode and print a compact JSON summary.
def main() -> None:
    args = parse_args()
    config = load_app_config(
        require_hub=bool(args.inspect_live or args.inspect_live_first_turn or args.inspect_send_speech_act),
        require_openai=bool(
            args.inspect_live_first_turn
            or args.inspect_transcribe_operator
            or args.inspect_send_speech_act
        ),
    )
    ensure_runtime_directories(config.paths)

    if args.dry_run:
        result = run_dry_run(config)
    elif args.simulate_audio:
        result = run_simulate_audio(config)
    elif args.inspect_live:
        result = inspect_live_start(config)
    elif args.inspect_live_first_turn:
        result = inspect_live_first_audio_turn(config)
    elif args.inspect_transcribe_operator:
        if not args.call_id:
            raise SystemExit("--call-id is required with --inspect-transcribe-operator.")
        result = transcribe_saved_operator_audio(
            config,
            call_id=args.call_id,
            turn_number=args.turn_number,
        )
    elif args.inspect_send_speech_act:
        if not args.call_id:
            raise SystemExit("--call-id is required with --inspect-send-speech-act.")
        if not args.speech_act:
            raise SystemExit("--speech-act is required with --inspect-send-speech-act.")
        result = send_live_speech_act(
            config,
            call_id=args.call_id,
            turn_number=args.turn_number,
            speech_act=SpeechAct(args.speech_act),
            roads=parse_roads(args.roads),
        )
    else:
        result = build_submit_blocked_result(config)

    print(json.dumps(result, ensure_ascii=False, indent=2))


# Parse a comma-separated roads argument into a clean list.
def parse_roads(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    main()
