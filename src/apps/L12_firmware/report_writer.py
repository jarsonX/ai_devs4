# Runtime report persistence for the firmware workbench.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Save full course feedback under ignored runtime data for human inspection.
def save_run_report(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path
