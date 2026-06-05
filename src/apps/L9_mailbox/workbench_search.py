# Deterministic search helpers for the L9 mailbox workbench.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.apps.L9_mailbox.zmail_client import ZmailClient, ZmailResponse


DEFAULT_SEARCH_QUERIES = (
    "from:proton.me",
    "Wiktor",
    "elektrownia OR power",
    "security OR bezpiecze\u0144stwo OR atak",
    "password OR has\u0142o OR credentials",
    "SEC-",
)
PROMISING_THRESHOLD = 2
HIGH_PRIORITY_THRESHOLD = 5

PROMISING_SIGNALS = (
    ("proton.me", 3, "proton sender or reference"),
    ("wiktor", 3, "Wiktor reference"),
    ("elektrownia", 2, "power plant term"),
    ("power", 2, "power term"),
    ("plant", 2, "plant term"),
    ("reactor", 2, "reactor term"),
    ("energy", 2, "energy term"),
    ("security", 2, "security term"),
    ("bezpiecze\u0144stwo", 2, "security term"),
    ("bezpieczenstwo", 2, "security term"),
    ("attack", 2, "attack term"),
    ("atak", 2, "attack term"),
    ("password", 2, "password term"),
    ("has\u0142o", 2, "password term"),
    ("haslo", 2, "password term"),
    ("credentials", 2, "credentials term"),
    ("sec-", 3, "confirmation code prefix"),
)
TEXT_FIELDS = (
    "from",
    "to",
    "sender",
    "subject",
    "snippet",
    "preview",
    "summary",
    "thread",
    "threadTitle",
)
THREAD_ID_FIELDS = ("threadID", "threadId", "thread_id")


# Store one normalized search result without full message body content.
@dataclass(frozen=True)
class MailSearchCandidate:
    source_query: str
    row_id: int | str | None
    message_id: str | None
    thread_id: int | str | None
    score: int
    reasons: tuple[str, ...]
    is_promising: bool
    is_high_priority: bool


# Store one search response summary and the promising candidates it produced.
@dataclass(frozen=True)
class SearchBatch:
    query: str
    status_code: int
    result_count: int
    candidates: tuple[MailSearchCandidate, ...]


# Store enough search state for a workbench report without storing message bodies.
@dataclass(frozen=True)
class SearchRunSummary:
    batches: tuple[SearchBatch, ...]


# Extract text used only for routing decisions from a search result object.
def collect_search_text(record: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for field_name in TEXT_FIELDS:
        value = record.get(field_name)
        if isinstance(value, str):
            parts.append(value)

    return " ".join(parts).lower()


# Read one possible ID field from a search result while tolerating API naming variants.
def get_first_present(record: Mapping[str, Any], field_names: Sequence[str]) -> Any:
    for field_name in field_names:
        if field_name in record:
            return record[field_name]

    return None


# Normalize an unknown zmail search payload into a list of metadata records.
def extract_records(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]

    if not isinstance(payload, Mapping):
        return []

    for field_name in ("results", "messages", "threads", "items", "data"):
        value = payload.get(field_name)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]

    return []


# Score one metadata record to decide whether its full message body is worth fetching.
def score_promising_record(
    record: Mapping[str, Any],
    *,
    suspicious_thread_ids: set[int | str] | None = None,
) -> tuple[int, tuple[str, ...]]:
    search_text = collect_search_text(record)
    score = 0
    reasons: list[str] = []

    for needle, points, reason in PROMISING_SIGNALS:
        if needle in search_text:
            score += points
            if reason not in reasons:
                reasons.append(reason)

    thread_id = get_first_present(record, THREAD_ID_FIELDS)
    if suspicious_thread_ids and thread_id in suspicious_thread_ids:
        score += 2
        reasons.append("belongs to already suspicious thread")

    return score, tuple(reasons)


# Convert one raw search metadata record into a safe candidate summary.
def build_candidate(
    record: Mapping[str, Any],
    *,
    source_query: str,
    suspicious_thread_ids: set[int | str] | None = None,
) -> MailSearchCandidate:
    score, reasons = score_promising_record(
        record,
        suspicious_thread_ids=suspicious_thread_ids,
    )

    row_id = get_first_present(record, ("rowID", "rowId", "row_id"))
    message_id = get_first_present(record, ("messageID", "messageId", "message_id"))
    thread_id = get_first_present(record, THREAD_ID_FIELDS)

    return MailSearchCandidate(
        source_query=source_query,
        row_id=row_id,
        message_id=message_id if isinstance(message_id, str) else None,
        thread_id=thread_id,
        score=score,
        reasons=reasons,
        is_promising=score >= PROMISING_THRESHOLD,
        is_high_priority=score >= HIGH_PRIORITY_THRESHOLD,
    )


# Run one search query and summarize only safe metadata needed by the workbench.
def search_once(
    client: ZmailClient,
    query: str,
    *,
    page: int = 1,
    per_page: int = 5,
    suspicious_thread_ids: set[int | str] | None = None,
) -> SearchBatch:
    response = client.search(query, page=page, per_page=per_page)
    records = extract_records(response.payload)
    candidates = tuple(
        build_candidate(
            record,
            source_query=query,
            suspicious_thread_ids=suspicious_thread_ids,
        )
        for record in records
    )

    return SearchBatch(
        query=query,
        status_code=response.status_code,
        result_count=len(records),
        candidates=candidates,
    )


# Run a small deterministic query set without extracting final answer values.
def run_search_dry_run(
    client: ZmailClient,
    *,
    queries: Sequence[str] = DEFAULT_SEARCH_QUERIES,
    page: int = 1,
    per_page: int = 5,
) -> SearchRunSummary:
    suspicious_thread_ids: set[int | str] = set()
    batches: list[SearchBatch] = []

    for query in queries:
        batch = search_once(
            client,
            query,
            page=page,
            per_page=per_page,
            suspicious_thread_ids=suspicious_thread_ids,
        )
        batches.append(batch)
        for candidate in batch.candidates:
            if candidate.is_promising and candidate.thread_id is not None:
                suspicious_thread_ids.add(candidate.thread_id)

    return SearchRunSummary(batches=tuple(batches))


# Collect safe IDs for message-body fetches without storing message content.
def collect_fetch_ids(candidates: Sequence[MailSearchCandidate]) -> list[int | str]:
    ids: list[int | str] = []
    seen: set[int | str] = set()

    for candidate in candidates:
        if not candidate.is_promising:
            continue

        candidate_id = candidate.message_id or candidate.row_id
        if candidate_id is None or candidate_id in seen:
            continue

        seen.add(candidate_id)
        ids.append(candidate_id)

    return ids


# Fetch full message bodies for selected IDs while leaving storage decisions to callers.
def fetch_messages_for_ids(client: ZmailClient, ids: Sequence[int | str]) -> ZmailResponse | None:
    if not ids:
        return None

    return client.get_messages(list(ids))


# Build a storage-safe report summary with no message bodies, snippets, or subjects.
def build_masked_search_report(summary: SearchRunSummary) -> dict[str, Any]:
    return {
        "batches": [
            {
                "query": batch.query,
                "status_code": batch.status_code,
                "result_count": batch.result_count,
                "promising_count": sum(1 for candidate in batch.candidates if candidate.is_promising),
                "candidates": [
                    {
                        "row_id": candidate.row_id,
                        "message_id": candidate.message_id,
                        "thread_id": candidate.thread_id,
                        "score": candidate.score,
                        "reasons": list(candidate.reasons),
                        "is_promising": candidate.is_promising,
                        "is_high_priority": candidate.is_high_priority,
                    }
                    for candidate in batch.candidates
                    if candidate.is_promising
                ],
            }
            for batch in summary.batches
        ]
    }
