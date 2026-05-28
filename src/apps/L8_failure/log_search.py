# Bounded log search tools for finding evidence without loading the full file into the model.

from __future__ import annotations

from dataclasses import asdict

from src.apps.L8_failure.models import LogEvent, SearchResult


DEFAULT_SEARCH_LIMIT = 80


# Check whether one event matches all explicit query filters.
def event_matches_query(
    event: LogEvent,
    *,
    levels: set[str] | None = None,
    component_ids: set[str] | None = None,
    keywords: set[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> bool:
    if levels is not None and event.level not in levels:
        return False
    if component_ids is not None and event.component_id not in component_ids:
        return False
    if start_time is not None and event.timestamp < start_time:
        return False
    if end_time is not None and event.timestamp > end_time:
        return False
    if keywords is not None:
        haystack = f"{event.component_id} {event.message}".lower()
        if not any(keyword.lower() in haystack for keyword in keywords):
            return False

    return True


# Return a bounded result set for a tool-like search query.
def search_logs(
    events: list[LogEvent],
    *,
    levels: set[str] | None = None,
    component_ids: set[str] | None = None,
    keywords: set[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
) -> SearchResult:
    if limit < 1:
        raise ValueError("Search limit must be >= 1.")

    matches = [
        event
        for event in events
        if event_matches_query(
            event,
            levels=levels,
            component_ids=component_ids,
            keywords=keywords,
            start_time=start_time,
            end_time=end_time,
        )
    ]

    query = {
        "levels": sorted(levels) if levels is not None else None,
        "component_ids": sorted(component_ids) if component_ids is not None else None,
        "keywords": sorted(keywords) if keywords is not None else None,
        "start_time": start_time,
        "end_time": end_time,
        "limit": limit,
    }
    return SearchResult(
        query=query,
        total_matches=len(matches),
        returned_matches=min(len(matches), limit),
        events=matches[:limit],
    )


# Convert search results into small dicts that are safe to pass to the model.
def events_for_model(events: list[LogEvent]) -> list[dict[str, object]]:
    return [
        {
            "source_line": event.source_line,
            "timestamp": event.timestamp,
            "level": event.level,
            "component_id": event.component_id,
            "message": event.message,
        }
        for event in events
    ]


# Convert a search result into JSON-friendly data for reports.
def search_result_to_dict(result: SearchResult) -> dict[str, object]:
    return {
        "query": result.query,
        "total_matches": result.total_matches,
        "returned_matches": result.returned_matches,
        "events": [asdict(event) for event in result.events],
    }
