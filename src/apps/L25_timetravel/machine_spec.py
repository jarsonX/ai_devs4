# Deterministic CHRONOS-P1 rules and travel-plan construction.

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from src.apps.L25_timetravel.models import TargetDate, TravelLeg


MIN_YEAR = 1500
MAX_YEAR = 2499


# Calculate the documented temporal synchronization ratio.
def calculate_sync_ratio(target: TargetDate) -> float:
    weighted = target.day * 8 + target.month * 12 + target.year * 7
    return (weighted % 101) / 100


# Return the automatically rotating mode required for a target year.
def required_internal_mode(year: int) -> int:
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"Year {year} is outside CHRONOS-P1 range.")
    if year < 2000:
        return 1
    if year <= 2150:
        return 2
    if year <= 2300:
        return 3
    return 4


# Parse the authoritative year-to-PWR table from the machine documentation.
def load_pwr_table(path: Path) -> dict[int, int]:
    text = path.read_text(encoding="utf-8")
    table: dict[int, int] = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or len(cells) % 2 != 0:
            continue
        for index in range(0, len(cells), 2):
            year_text = cells[index]
            pwr_text = cells[index + 1]
            if not re.fullmatch(r"\d{4}", year_text):
                continue
            if not re.fullmatch(r"\d{1,2}", pwr_text):
                raise ValueError(f"Invalid PWR value for year {year_text}.")
            year = int(year_text)
            pwr = int(pwr_text)
            if year in table:
                raise ValueError(f"Duplicate PWR entry for year {year}.")
            if not 0 <= pwr <= 100:
                raise ValueError(f"PWR value for year {year} is outside 0-100.")
            table[year] = pwr
    expected = set(range(MIN_YEAR, MAX_YEAR + 1))
    missing = sorted(expected.difference(table))
    extra = sorted(set(table).difference(expected))
    if missing or extra:
        raise ValueError(
            f"PWR table coverage is invalid: missing={missing[:5]}, extra={extra[:5]}."
        )
    return table


# Look up the required protection value for one target year.
def pwr_for_year(year: int, table: dict[int, int]) -> int:
    try:
        return table[year]
    except KeyError as error:
        raise ValueError(f"No PWR value for year {year}.") from error


# Build the fixed three-leg task plan around one frozen current date.
def build_travel_plan(current_date: date, pwr_table: dict[int, int]) -> list[TravelLeg]:
    targets = [
        ("battery_jump", TargetDate(year=2238, month=11, day=5), False, True, False),
        (
            "return",
            TargetDate(
                year=current_date.year,
                month=current_date.month,
                day=current_date.day,
            ),
            True,
            False,
            False,
        ),
        ("tunnel", TargetDate(year=2024, month=11, day=12), True, True, True),
    ]
    return [
        TravelLeg(
            name=name,
            target=target,
            pta=pta,
            ptb=ptb,
            pwr=pwr_for_year(target.year, pwr_table),
            required_internal_mode=required_internal_mode(target.year),
            sync_ratio=calculate_sync_ratio(target),
            tunnel=tunnel,
        )
        for name, target, pta, ptb, tunnel in targets
    ]


# Calculate a validated stabilization value from model-extracted arithmetic.
def calculate_stabilization(left: int, operator: str, right: int) -> int:
    if operator == "+":
        value = left + right
    elif operator == "-":
        value = left - right
    elif operator == "*":
        value = left * right
    elif operator == "/":
        if right == 0 or left % right != 0:
            raise ValueError("Stabilization division must be exact and non-zero.")
        value = left // right
    else:
        raise ValueError(f"Unsupported stabilization operator: {operator!r}.")
    if not 0 <= value <= 1000:
        raise ValueError("Stabilization result is outside 0-1000.")
    return value
