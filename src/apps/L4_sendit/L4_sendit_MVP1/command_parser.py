# Deterministic command parser for the L4 sendit MVP1 learning stage.

import re

from src.apps.L4_sendit.L4_sendit_MVP1.models import ShipmentCommand


# === AI_BOUNDARY TODO ========================================================
# MVP2 should replace this fixed-format parser with a bounded AI parser that
# returns validated structured output and reports missing or ambiguous fields.
# =============================================================================
# Parse the known Stage 1 command format into structured shipment data.
def parse_command(command_text: str) -> ShipmentCommand:
    return ShipmentCommand(
        sender_identifier=_read_text_value(command_text, "sender identifier"),
        origin_point=_read_text_value(command_text, "origin point"),
        destination_point=_read_text_value(command_text, "destination point"),
        weight_kg=_read_int_value(command_text, "weight"),
        budget_pp=_read_int_value(command_text, "budget"),
        contents=_read_text_value(command_text, "contents"),
        special_notes=_read_text_value(command_text, "special notes"),
    )


# Read a text value from a simple '- field: value' command line.
def _read_text_value(command_text: str, field_name: str) -> str:
    match = re.search(rf"^- {re.escape(field_name)}:\s*(.+)$", command_text, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing command field: {field_name}")

    return match.group(1).strip()


# Read the first integer from a simple '- field: value' command line.
def _read_int_value(command_text: str, field_name: str) -> int:
    raw_value = _read_text_value(command_text, field_name)
    match = re.search(r"\d+", raw_value)
    if not match:
        raise ValueError(f"Command field has no integer value: {field_name}")

    return int(match.group(0))
