from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def ensure_output_directory(path: Path) -> None:
    """Create output directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def save_verification_result(
    output_json_path: Path,
    payload: dict,
    verification_response: dict,
    statistics: dict,
) -> Path:
    """
    Save verification results to JSON file with metadata.
    
    Args:
        output_json_path: Path to save the JSON file
        payload: Payload that was sent to the verification API
        verification_response: Response from the verification API
        statistics: Pipeline statistics (counts)
    
    Returns:
        Path to the saved file
    """
    ensure_output_directory(output_json_path.parent)
    
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "statistics": statistics,
        "payload_sent": payload,
        "verification_response": verification_response,
    }
    
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    return output_json_path
