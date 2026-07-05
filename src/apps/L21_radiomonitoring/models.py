# Data models shared by the L21 radiomonitoring workflow.

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal


FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")
FINAL_FIELDS = {"cityName", "cityArea", "warehousesCount", "phoneNumber"}


# Store one decoded or raw Hub response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request and its full response for runtime data.
@dataclass(frozen=True)
class LoggedExchange:
    sequence: int
    action: str
    request: dict[str, Any]
    response: ApiResponse

    # Convert the exchange into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "action": self.action,
            "request": self.request,
            "response": {
                "status_code": self.response.status_code,
                "payload": self.response.payload,
                "text": self.response.text,
                "flag_found": response_contains_flag(self.response),
            },
        }


# Store one captured signal and where it was persisted.
@dataclass(frozen=True)
class CapturedSignal:
    sequence: int
    kind: Literal["control", "transcription", "attachment", "other"]
    action: str
    payload: dict[str, Any]
    raw_file: str

    # Convert the signal into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Store a decoded attachment and the route selected for it.
@dataclass(frozen=True)
class AttachmentArtifact:
    signal_sequence: int
    mime_type: str
    source_filesize: int | None
    decoded_size: int
    sha256: str
    path: str
    route: Literal["image", "audio", "json", "text", "csv", "unknown"]
    width: int | None = None
    height: int | None = None

    # Convert the attachment into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Store one extracted or inferred fact with provenance.
@dataclass(frozen=True)
class EvidenceCandidate:
    field: Literal["cityName", "cityArea", "warehousesCount", "phoneNumber", "other"]
    value: str
    source: str
    method: str
    confidence: Literal["high", "medium", "low"]
    note: str

    # Convert the candidate into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Store one complete final answer before Hub submission.
@dataclass(frozen=True)
class FinalReport:
    cityName: str
    cityArea: str
    warehousesCount: int
    phoneNumber: str

    # Convert the report into the Hub answer payload.
    def to_answer(self) -> dict[str, Any]:
        return {
            "action": "transmit",
            "cityName": self.cityName,
            "cityArea": self.cityArea,
            "warehousesCount": self.warehousesCount,
            "phoneNumber": self.phoneNumber,
        }

    # Convert the report into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Return whether one response contains a FLAG anywhere in visible content.
def response_contains_flag(response: ApiResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return FLAG_PATTERN.search(haystack) is not None


# Validate that the final city area is formatted exactly as required.
def city_area_is_valid(value: str) -> bool:
    if not re.fullmatch(r"\d+\.\d{2}", value):
        return False
    try:
        Decimal(value)
    except Exception:
        return False
    return True


# Validate that a phone number is stable enough for Hub submission.
def phone_number_is_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 7 and len(digits) <= 15


# Return compact summary data for a Hub signal payload.
def summarize_signal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "keys": sorted(payload),
        "code": payload.get("code"),
        "message": payload.get("message"),
    }
    if "transcription" in payload:
        text = str(payload.get("transcription", ""))
        summary.update(
            {
                "kind": "transcription",
                "text_len": len(text),
                "text_preview": text[:240],
            }
        )
    elif "attachment" in payload:
        attachment = str(payload.get("attachment", ""))
        summary.update(
            {
                "kind": "attachment",
                "meta": payload.get("meta"),
                "filesize": payload.get("filesize"),
                "base64_len": len(attachment),
            }
        )
    else:
        summary["kind"] = "other"
    return summary
