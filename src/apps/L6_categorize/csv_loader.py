# CSV parsing helpers for the L6 categorize workflow.

from __future__ import annotations

import csv
from collections.abc import Sequence
from io import StringIO

from src.apps.L6_categorize.models import GoodsItem


CODE_COLUMN = "code"
DESCRIPTION_COLUMN = "description"


# Parse the Hub CSV text into typed goods items.
def parse_goods_items(csv_text: str) -> list[GoodsItem]:
    if not csv_text.strip():
        raise ValueError("CSV text is empty.")

    reader = csv.DictReader(StringIO(csv_text))
    fieldnames = reader.fieldnames
    if not fieldnames:
        raise ValueError("CSV header is missing.")

    ensure_required_columns(fieldnames)

    items: list[GoodsItem] = []

    for row_number, row in enumerate(reader, start=2):
        item_id = normalize_cell(row.get(CODE_COLUMN))
        description = normalize_cell(row.get(DESCRIPTION_COLUMN))

        if not item_id:
            raise ValueError(f"Missing item id in CSV row {row_number}.")
        if not description:
            raise ValueError(f"Missing description in CSV row {row_number}.")

        items.append(GoodsItem(item_id=item_id, description=description))

    if not items:
        raise ValueError("CSV does not contain any goods items.")

    return items


# Ensure the Hub CSV exposes the exact columns expected by this exercise.
def ensure_required_columns(fieldnames: Sequence[str]) -> None:
    missing_columns = [
        column
        for column in (CODE_COLUMN, DESCRIPTION_COLUMN)
        if column not in fieldnames
    ]

    if missing_columns:
        raise ValueError(f"Missing CSV columns: {missing_columns}.")


# Normalize a CSV cell value into a clean string.
def normalize_cell(value: str | None) -> str:
    if value is None:
        return ""

    return " ".join(value.strip().split())
