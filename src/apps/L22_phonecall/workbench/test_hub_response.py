from __future__ import annotations

import base64
import unittest

from src.apps.L22_phonecall.hub_response import extract_operator_turn_input_from_response
from src.apps.L22_phonecall.models import ApiResponse


# Verify Hub payload normalization without live calls.
class HubResponseTests(unittest.TestCase):
    def test_text_msg_is_not_treated_as_audio(self) -> None:
        response = ApiResponse(
            status_code=200,
            payload={"msg": "Przez najblizsze 30 minut mozesz prowadzic rozmowe."},
            text="ok",
        )

        extracted = extract_operator_turn_input_from_response(response)

        self.assertEqual(extracted.text, "Przez najblizsze 30 minut mozesz prowadzic rozmowe.")
        self.assertFalse(extracted.has_audio())
        self.assertTrue(extracted.has_text())

    def test_audio_field_is_decoded(self) -> None:
        audio_bytes = b"ID3" + b"x" * 40
        response = ApiResponse(
            status_code=200,
            payload={"audio": base64.b64encode(audio_bytes).decode("ascii")},
            text="ok",
        )

        extracted = extract_operator_turn_input_from_response(response)

        self.assertEqual(extracted.audio_bytes, audio_bytes)
        self.assertEqual(extracted.audio_extension, "mp3")
        self.assertEqual(extracted.source_field, "audio")

    def test_base64_msg_is_decoded_as_audio(self) -> None:
        audio_bytes = b"RIFF" + b"x" * 40
        response = ApiResponse(
            status_code=200,
            payload={"msg": base64.b64encode(audio_bytes).decode("ascii")},
            text="ok",
        )

        extracted = extract_operator_turn_input_from_response(response)

        self.assertEqual(extracted.audio_bytes, audio_bytes)
        self.assertEqual(extracted.audio_extension, "wav")
        self.assertIsNone(extracted.text)

    def test_message_field_is_text_fallback(self) -> None:
        response = ApiResponse(
            status_code=200,
            payload={"message": "Phonecall session started."},
            text="ok",
        )

        extracted = extract_operator_turn_input_from_response(response)

        self.assertEqual(extracted.text, "Phonecall session started.")


if __name__ == "__main__":
    unittest.main()
