# This module defines narrow agent tools and the bounded mailbox workbench toolbox.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, cast

from openai.types.responses.function_tool_param import FunctionToolParam
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.apps.L9_mailbox.config import AppConfig
from src.apps.L9_mailbox.extractor import (
    build_extraction_report,
    build_masked_extraction_report,
    collect_message_text,
    extract_from_messages_payload,
    extract_message_records,
    get_message_identifier,
)
from src.apps.L9_mailbox.hub_client import (
    HubClient,
    build_verify_payload,
    extract_flag,
    mask_payload_for_storage,
)
from src.apps.L9_mailbox.validator import MailboxAnswer, validate_mailbox_answer
from src.apps.L9_mailbox.workbench_search import (
    DEFAULT_SEARCH_QUERIES,
    SearchBatch,
    SearchRunSummary,
    build_candidate,
    build_masked_search_report,
    collect_fetch_ids,
    extract_records,
)
from src.apps.L9_mailbox.zmail_client import ZmailClient


ALLOWED_FINISH_STATUSES = {"solved", "partial", "blocked"}
ALLOWED_EVIDENCE_FIELDS = {"date", "password", "confirmation_code"}
SEARCH_PREVIEW_FIELDS = (
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
MESSAGE_PREVIEW_FIELDS = (
    "from",
    "to",
    "sender",
    "subject",
    "date",
    "threadID",
    "threadId",
    "thread_id",
)


# Validate arguments for one mailbox search tool call.
class SearchMessagesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=5, ge=1, le=20)

    # Keep search queries compact and intentional before they reach the mailbox API.
    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("query must not be empty.")
        return cleaned_value


# Validate arguments for one thread-inspection tool call.
class GetThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str

    # Keep thread identifiers as non-empty strings before numeric conversion.
    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("thread_id must not be empty.")
        return cleaned_value


# Validate arguments for one message-fetch tool call.
class GetMessagesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[str] = Field(min_length=1, max_length=10)

    # Keep every message identifier non-empty before lookup or fetch.
    @field_validator("ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        cleaned_values = [item.strip() for item in value if item.strip()]
        if not cleaned_values:
            raise ValueError("ids must contain at least one non-empty identifier.")
        return cleaned_values


# Validate arguments for one deterministic answer-proposal tool call.
class ProposeAnswerArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[str] = Field(default_factory=list, max_length=10)

    # Keep optional message identifiers normalized before selecting cached messages.
    @field_validator("ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


# Store one model-visible answer snapshot.
class FoundValuesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str | None = None
    password: str | None = None
    confirmation_code: str | None = None


# Store one traceable evidence pointer in the finish payload.
class EvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal["date", "password", "confirmation_code"]
    message_id: str | None = None
    reason: str

    # Keep evidence reasons human-readable and non-empty in the final report.
    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("reason must not be empty.")
        return cleaned_value


# Validate the model-requested finish payload before the loop can stop.
class FinishArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["solved", "partial", "blocked"]
    found_values: FoundValuesPayload
    evidence: list[EvidencePayload] = Field(default_factory=list, max_length=12)
    uncertainties: list[str] = Field(default_factory=list, max_length=12)
    next_queries: list[str] = Field(default_factory=list, max_length=5)

    # Keep uncertainty notes readable and compact for runtime reports.
    @field_validator("uncertainties")
    @classmethod
    def validate_uncertainties(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    # Keep follow-up queries non-empty and ready for the next bounded retry.
    @field_validator("next_queries")
    @classmethod
    def validate_next_queries(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


# Validate arguments for one guarded Hub submission tool call.
class SubmitAnswerArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    password: str
    confirmation_code: str

    # Keep submit values normalized before deterministic validation runs.
    @field_validator("date", "password", "confirmation_code")
    @classmethod
    def validate_text_field(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("submit values must not be empty.")
        return cleaned_value


# Store one stable tool execution result for the agent loop and local tests.
@dataclass(frozen=True)
class MailboxToolResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any]

    # Convert the tool result into a JSON-ready dictionary for OpenAI tool outputs.
    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "payload": self.payload,
        }


# Build a stable string identifier from a mailbox row ID or message ID.
def stringify_identifier(value: Any) -> str | None:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        cleaned_value = value.strip()
        return cleaned_value or None
    return None


# Turn one string identifier back into an API-friendly row ID or message ID value.
def normalize_identifier_argument(value: str) -> int | str:
    cleaned_value = value.strip()
    if cleaned_value.isdigit():
        return int(cleaned_value)
    return cleaned_value


# Extract all mailbox identifiers that can point back to the same message payload.
def collect_message_aliases(message: Mapping[str, Any]) -> list[str]:
    aliases: list[str] = []
    for field_name in ("messageID", "messageId", "message_id", "rowID", "rowId", "row_id", "id"):
        alias = stringify_identifier(message.get(field_name))
        if alias and alias not in aliases:
            aliases.append(alias)
    return aliases


# Trim long free-text values before sending them back into the model context.
def truncate_text(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[: max_chars - 3]}..."


# Build one compact metadata preview from a mailbox search record.
def build_search_metadata_preview(
    record: Mapping[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    preview: dict[str, Any] = {}
    for field_name in SEARCH_PREVIEW_FIELDS:
        value = record.get(field_name)
        if isinstance(value, str) and value.strip():
            preview[field_name] = truncate_text(value.strip(), max_chars=max_chars)
    return preview


# Build one compact message preview that the model can inspect safely.
def build_message_preview(
    message: Mapping[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    preview: dict[str, Any] = {}
    for field_name in MESSAGE_PREVIEW_FIELDS:
        value = message.get(field_name)
        if isinstance(value, (int, str)):
            preview[field_name] = value

    message_id = stringify_identifier(get_message_identifier(message))
    if message_id is not None:
        preview["message_id"] = message_id

    preview["text"] = truncate_text(
        collect_message_text(message),
        max_chars=max_chars,
    )
    return preview


# Convert one extraction report into the evidence shape expected by the finish payload.
def build_finish_evidence_from_report(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence_items: list[dict[str, Any]] = []
    seen_fields: set[str] = set()

    for candidate in report.get("candidates", []):
        if not isinstance(candidate, Mapping):
            continue

        field = candidate.get("field")
        if field not in ALLOWED_EVIDENCE_FIELDS or field in seen_fields:
            continue

        evidence_items.append(
            {
                "field": field,
                "message_id": stringify_identifier(candidate.get("message_id")),
                "reason": candidate.get("reason", "candidate extracted from message text"),
            }
        )
        seen_fields.add(cast(str, field))

    return evidence_items


# Build a stable error result when one tool call fails validation or execution.
def build_error_result(tool_name: str, error: Exception) -> MailboxToolResult:
    return MailboxToolResult(
        tool_name=tool_name,
        ok=False,
        payload={"error": str(error)},
    )


# Normalize a Pydantic JSON schema into the stricter OpenAI function-tool shape.
def build_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized_schema = dict(schema)

    if normalized_schema.get("type") == "object":
        properties = normalized_schema.get("properties", {})
        if isinstance(properties, dict):
            normalized_schema["properties"] = {
                key: build_openai_strict_schema(value) if isinstance(value, dict) else value
                for key, value in properties.items()
            }
            normalized_schema["required"] = list(properties.keys())
        normalized_schema["additionalProperties"] = False

    items = normalized_schema.get("items")
    if isinstance(items, dict):
        normalized_schema["items"] = build_openai_strict_schema(items)

    for keyword in ("anyOf", "allOf", "oneOf"):
        values = normalized_schema.get(keyword)
        if isinstance(values, list):
            normalized_schema[keyword] = [
                build_openai_strict_schema(value) if isinstance(value, dict) else value
                for value in values
            ]

    for defs_key in ("$defs", "definitions"):
        defs_value = normalized_schema.get(defs_key)
        if isinstance(defs_value, dict):
            normalized_schema[defs_key] = {
                key: build_openai_strict_schema(value) if isinstance(value, dict) else value
                for key, value in defs_value.items()
            }

    return normalized_schema


# Return the narrow tool schemas exposed to the mailbox investigator model.
def build_tool_definitions(*, submission_enabled: bool) -> list[FunctionToolParam]:
    tools: list[FunctionToolParam] = [
        cast(FunctionToolParam, {
            "type": "function",
            "name": "search_messages",
            "description": (
                "Search mailbox metadata with one targeted query. "
                "Use this to discover promising message or thread identifiers."
            ),
            "parameters": build_openai_strict_schema(SearchMessagesArgs.model_json_schema()),
            "strict": True,
        }),
        cast(FunctionToolParam, {
            "type": "function",
            "name": "get_thread",
            "description": (
                "Inspect message identifiers for one thread without fetching message bodies."
            ),
            "parameters": build_openai_strict_schema(GetThreadArgs.model_json_schema()),
            "strict": True,
        }),
        cast(FunctionToolParam, {
            "type": "function",
            "name": "get_messages",
            "description": (
                "Fetch full message bodies for selected row IDs or message IDs."
            ),
            "parameters": build_openai_strict_schema(GetMessagesArgs.model_json_schema()),
            "strict": True,
        }),
        cast(FunctionToolParam, {
            "type": "function",
            "name": "propose_answer",
            "description": (
                "Run deterministic extraction and validation on already fetched messages."
            ),
            "parameters": build_openai_strict_schema(ProposeAnswerArgs.model_json_schema()),
            "strict": True,
        }),
    ]
    if submission_enabled:
        tools.append(
            cast(FunctionToolParam, {
                "type": "function",
                "name": "submit_answer",
                "description": (
                    "Submit a locally valid answer to the Hub only after evidence is grounded "
                    "in fetched messages. Use this only in submission mode."
                ),
                "parameters": build_openai_strict_schema(SubmitAnswerArgs.model_json_schema()),
                "strict": True,
            })
        )
    tools.append(
        cast(FunctionToolParam, {
            "type": "function",
            "name": "finish",
            "description": (
                "Stop the run with solved, partial, or blocked status and a structured result."
            ),
            "parameters": build_openai_strict_schema(FinishArgs.model_json_schema()),
            "strict": True,
        })
    )
    return tools


# This toolbox owns mailbox-side state, tool execution, and finish validation.
class MailboxInvestigatorToolbox:
    # This initializer wires app config and a read-only mailbox client into the toolbox.
    def __init__(
        self,
        config: AppConfig,
        client: ZmailClient,
        *,
        submit_enabled: bool = False,
        hub_client: HubClient | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.submit_enabled = submit_enabled
        self.hub_client = hub_client
        self.search_batches: list[SearchBatch] = []
        self.queries_run: list[str] = []
        self.suspicious_thread_ids: set[int | str] = set()
        self.messages_by_id: dict[str, Mapping[str, Any]] = {}
        self.tool_call_count = 0
        self.last_extraction_report: dict[str, Any] | None = None
        self.finished_payload: dict[str, Any] | None = None
        self.last_submission_payload: dict[str, Any] | None = None
        self.last_submission_response: dict[str, Any] | None = None
        self.successful_submit_count = 0

    # This method validates arguments, dispatches one supported tool, and captures state.
    def dispatch_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> MailboxToolResult:
        self.tool_call_count += 1

        try:
            if tool_name == "search_messages":
                parsed_arguments = SearchMessagesArgs.model_validate(arguments)
                return self._search_messages(parsed_arguments)

            if tool_name == "get_thread":
                parsed_arguments = GetThreadArgs.model_validate(arguments)
                return self._get_thread(parsed_arguments)

            if tool_name == "get_messages":
                parsed_arguments = GetMessagesArgs.model_validate(arguments)
                return self._get_messages(parsed_arguments)

            if tool_name == "propose_answer":
                parsed_arguments = ProposeAnswerArgs.model_validate(arguments)
                return self._propose_answer(parsed_arguments)

            if tool_name == "submit_answer":
                parsed_arguments = SubmitAnswerArgs.model_validate(arguments)
                return self._submit_answer(parsed_arguments)

            if tool_name == "finish":
                parsed_arguments = FinishArgs.model_validate(arguments)
                return self._finish(parsed_arguments)

            raise ValueError(f"Unsupported tool: {tool_name}")
        except ValidationError as error:
            return build_error_result(tool_name, ValueError(f"Tool arguments failed validation: {error}"))
        except Exception as error:
            return build_error_result(tool_name, error)

    # This method searches mailbox metadata and returns promising IDs with compact previews.
    def _search_messages(self, arguments: SearchMessagesArgs) -> MailboxToolResult:
        response = self.client.search(
            arguments.query,
            page=arguments.page,
            per_page=arguments.per_page,
        )
        records = extract_records(response.payload)
        candidates = [
            build_candidate(
                record,
                source_query=arguments.query,
                suspicious_thread_ids=self.suspicious_thread_ids,
            )
            for record in records
        ]
        batch = SearchBatch(
            query=arguments.query,
            status_code=response.status_code,
            result_count=len(records),
            candidates=tuple(candidates),
        )

        self.search_batches.append(batch)
        self.queries_run.append(arguments.query)
        for candidate in candidates:
            if candidate.is_promising and candidate.thread_id is not None:
                self.suspicious_thread_ids.add(candidate.thread_id)

        candidate_payload = []
        for record, candidate in zip(records, candidates, strict=False):
            candidate_payload.append(
                {
                    "row_id": stringify_identifier(candidate.row_id),
                    "message_id": stringify_identifier(candidate.message_id),
                    "thread_id": stringify_identifier(candidate.thread_id),
                    "score": candidate.score,
                    "reasons": list(candidate.reasons),
                    "is_promising": candidate.is_promising,
                    "is_high_priority": candidate.is_high_priority,
                    "metadata_preview": build_search_metadata_preview(
                        record,
                        max_chars=240,
                    ),
                }
            )

        return MailboxToolResult(
            tool_name="search_messages",
            ok=True,
            payload={
                "query": arguments.query,
                "page": arguments.page,
                "per_page": arguments.per_page,
                "status_code": response.status_code,
                "result_count": len(records),
                "candidates": candidate_payload,
                "fetch_hint_ids": [
                    stringify_identifier(item)
                    for item in collect_fetch_ids(candidates)
                    if stringify_identifier(item) is not None
                ],
                "queries_run_count": len(self.queries_run),
                "known_suspicious_thread_count": len(self.suspicious_thread_ids),
            },
        )

    # This method reads one mailbox thread and returns the message identifiers it exposes.
    def _get_thread(self, arguments: GetThreadArgs) -> MailboxToolResult:
        thread_id = normalize_identifier_argument(arguments.thread_id)
        if not isinstance(thread_id, int):
            raise ValueError("thread_id must be numeric for get_thread.")

        response = self.client.get_thread(thread_id)
        records = extract_records(response.payload)
        ids: list[str] = []

        for record in records:
            for field_name in ("rowID", "rowId", "row_id", "messageID", "messageId", "message_id"):
                identifier = stringify_identifier(record.get(field_name))
                if identifier and identifier not in ids:
                    ids.append(identifier)

        return MailboxToolResult(
            tool_name="get_thread",
            ok=True,
            payload={
                "thread_id": str(thread_id),
                "status_code": response.status_code,
                "message_count": len(ids),
                "ids": ids,
            },
        )

    # This method fetches full message bodies and reuses already cached messages when possible.
    def _get_messages(self, arguments: GetMessagesArgs) -> MailboxToolResult:
        requested_ids = [normalize_identifier_argument(item) for item in arguments.ids]
        cached_ids: list[str] = []
        missing_ids: list[int | str] = []

        for requested_id, raw_argument in zip(requested_ids, arguments.ids, strict=False):
            identifier = stringify_identifier(requested_id)
            if identifier is None:
                continue

            if identifier in self.messages_by_id:
                cached_ids.append(identifier)
            else:
                missing_ids.append(requested_id)

        fetched_records: list[Mapping[str, Any]] = []
        status_code: int | None = None
        if missing_ids:
            response = self.client.get_messages(missing_ids)
            status_code = response.status_code
            fetched_records = extract_message_records(response.payload)
            for message in fetched_records:
                aliases = collect_message_aliases(message)
                if not aliases:
                    continue
                for alias in aliases:
                    self.messages_by_id[alias] = message

        selected_messages: list[Mapping[str, Any]] = []
        selected_ids: list[str] = []
        for raw_argument in arguments.ids:
            if raw_argument in self.messages_by_id and raw_argument not in selected_ids:
                selected_messages.append(self.messages_by_id[raw_argument])
                selected_ids.append(raw_argument)
                continue

            normalized_argument = stringify_identifier(normalize_identifier_argument(raw_argument))
            if normalized_argument and normalized_argument in self.messages_by_id and normalized_argument not in selected_ids:
                selected_messages.append(self.messages_by_id[normalized_argument])
                selected_ids.append(normalized_argument)

        return MailboxToolResult(
            tool_name="get_messages",
            ok=True,
            payload={
                "status_code": status_code,
                "requested_ids": arguments.ids,
                "cached_ids": cached_ids,
                "fetched_count": len(fetched_records),
                "message_count": len(selected_messages),
                "messages": [
                    build_message_preview(
                        message,
                        max_chars=self.config.runtime.max_message_chars_per_tool_result,
                    )
                    for message in selected_messages
                ],
                "known_message_count": len({id(message) for message in self.messages_by_id.values()}),
            },
        )

    # This method runs deterministic extraction on selected cached messages only.
    def _propose_answer(self, arguments: ProposeAnswerArgs) -> MailboxToolResult:
        selected_messages = self._select_messages_for_extraction(arguments.ids)
        if not selected_messages:
            raise ValueError(
                "propose_answer requires at least one fetched message. "
                "Fetch messages first or pass cached ids."
            )

        extraction_result = extract_from_messages_payload(selected_messages)
        extraction_report = build_extraction_report(extraction_result)
        extraction_report["selected_message_ids"] = [
            stringify_identifier(get_message_identifier(message))
            for message in selected_messages
        ]
        extraction_report["answer_is_valid"] = not extraction_report["validation_errors"]
        self.last_extraction_report = extraction_report

        return MailboxToolResult(
            tool_name="propose_answer",
            ok=True,
            payload=extraction_report,
        )

    # This method submits one locally valid answer to the Hub behind an explicit runtime guard.
    def _submit_answer(self, arguments: SubmitAnswerArgs) -> MailboxToolResult:
        if not self.submit_enabled:
            raise ValueError("submit_answer is disabled for this run.")
        if self.hub_client is None:
            raise ValueError("Hub client is required when submission mode is enabled.")

        answer = MailboxAnswer(
            password=arguments.password,
            date=arguments.date,
            confirmation_code=arguments.confirmation_code,
        )
        validation_result = validate_mailbox_answer(answer)
        if not validation_result.is_valid:
            raise ValueError(
                "submit_answer requires a locally valid answer: "
                + "; ".join(validation_result.errors)
            )

        self._validate_finished_values_are_grounded(answer)
        hub_response = self.hub_client.verify_answer(answer)
        self.successful_submit_count += 1
        if self.config.external_api is None:
            raise ValueError("External API config is required for submit payload reporting.")
        self.last_submission_payload = mask_payload_for_storage(
            build_verify_payload(self.config.external_api, answer)
        )
        flag = extract_flag(hub_response.payload) or extract_flag(hub_response.text)
        accepted = hub_response.status_code < 400 and flag is not None
        self.last_submission_response = {
            "status_code": hub_response.status_code,
            "payload": hub_response.payload,
            "text": hub_response.text,
            "flag": flag,
            "accepted": accepted,
            "submit_requests_used": (
                self.hub_client.guard.used_requests
                if hasattr(self.hub_client, "guard")
                else None
            ),
        }

        return MailboxToolResult(
            tool_name="submit_answer",
            ok=True,
            payload=self.last_submission_response,
        )

    # This method validates the final structured result before the loop can stop.
    def _finish(self, arguments: FinishArgs) -> MailboxToolResult:
        normalized_payload = {
            "status": arguments.status,
            "found_values": {
                "date": arguments.found_values.date,
                "password": arguments.found_values.password,
                "confirmation_code": arguments.found_values.confirmation_code,
            },
            "evidence": [
                {
                    "field": item.field,
                    "message_id": item.message_id,
                    "reason": item.reason,
                }
                for item in arguments.evidence
            ],
            "uncertainties": arguments.uncertainties,
            "next_queries": arguments.next_queries,
        }

        answer = MailboxAnswer(
            password=arguments.found_values.password,
            date=arguments.found_values.date,
            confirmation_code=arguments.found_values.confirmation_code,
        )
        validation_result = validate_mailbox_answer(answer)

        if arguments.status == "solved" and not validation_result.is_valid:
            raise ValueError(
                "finish status 'solved' requires a locally valid answer: "
                + "; ".join(validation_result.errors)
            )

        if arguments.status == "solved":
            self._validate_finished_values_are_grounded(answer)
            if self.submit_enabled:
                if self.last_submission_response is None:
                    raise ValueError(
                        "submission mode requires submit_answer before finish can stop as solved."
                    )
                if not self.last_submission_response.get("accepted"):
                    raise ValueError(
                        "submission mode requires an accepted Hub submission before finish can stop as solved."
                    )

        for evidence_item in arguments.evidence:
            if evidence_item.message_id and evidence_item.message_id not in self.messages_by_id:
                raise ValueError(
                    f"finish evidence message_id is unknown to the workbench: {evidence_item.message_id}"
                )

        self.finished_payload = {
            **normalized_payload,
            "validation_errors": list(validation_result.errors),
            "finished": True,
            "submission_enabled": self.submit_enabled,
            "last_submission_response": self.last_submission_response,
        }
        return MailboxToolResult(
            tool_name="finish",
            ok=True,
            payload=self.finished_payload,
        )

    # This method deterministically expands all suspicious threads discovered during the run.
    def expand_suspicious_threads(self) -> dict[str, Any]:
        expanded_thread_ids: list[str] = []
        fetched_id_count = 0

        for raw_thread_id in sorted(self.suspicious_thread_ids, key=str):
            thread_id = stringify_identifier(raw_thread_id)
            if thread_id is None:
                continue

            thread_result = self._get_thread(GetThreadArgs(thread_id=thread_id))
            if not thread_result.ok:
                continue

            expanded_thread_ids.append(thread_id)
            ids = thread_result.payload.get("ids", [])
            if isinstance(ids, list) and ids:
                fetched_id_count += len(ids)
                self._get_messages(GetMessagesArgs(ids=[str(item) for item in ids]))

        return {
            "expanded_thread_ids": expanded_thread_ids,
            "fetched_id_count": fetched_id_count,
            "known_message_count": len({id(message) for message in self.messages_by_id.values()}),
        }

    # This method runs a deterministic fallback search plan for still-missing fields.
    def run_recovery_queries(self, queries: list[str]) -> list[dict[str, Any]]:
        recovery_steps: list[dict[str, Any]] = []

        for query in queries:
            if query in self.queries_run:
                continue

            search_result = self._search_messages(
                SearchMessagesArgs(
                    query=query,
                    page=1,
                    per_page=self.config.runtime.default_search_page_size,
                )
            )
            fetch_hint_ids = search_result.payload.get("fetch_hint_ids", [])
            if isinstance(fetch_hint_ids, list) and fetch_hint_ids:
                self._get_messages(GetMessagesArgs(ids=[str(item) for item in fetch_hint_ids]))

            recovery_steps.append(
                {
                    "query": query,
                    "status_code": search_result.payload.get("status_code"),
                    "result_count": search_result.payload.get("result_count"),
                    "fetch_hint_ids": fetch_hint_ids,
                }
            )

        return recovery_steps

    # This method reruns deterministic extraction across every fetched message currently cached.
    def propose_answer_from_all_cached_messages(self) -> dict[str, Any]:
        result = self._propose_answer(ProposeAnswerArgs(ids=[]))
        if not result.ok:
            raise ValueError("Deterministic recovery failed to build an answer proposal.")
        return result.payload

    # This method builds a solved finish payload directly from the current extraction report.
    def build_finish_payload_from_last_extraction(
        self,
        *,
        status: Literal["solved", "partial", "blocked"],
        extra_uncertainties: list[str] | None = None,
    ) -> dict[str, Any]:
        if self.last_extraction_report is None:
            raise ValueError("No extraction report is available for finish payload construction.")

        uncertainties = list(self.last_extraction_report.get("uncertainties", []))
        for uncertainty in extra_uncertainties or []:
            if uncertainty not in uncertainties:
                uncertainties.append(uncertainty)

        return {
            "status": status,
            "found_values": dict(self.last_extraction_report["proposed_answer"]),
            "evidence": build_finish_evidence_from_report(self.last_extraction_report),
            "uncertainties": uncertainties,
            "next_queries": [],
        }

    # This method submits the current extracted answer without requiring the model to call the tool.
    def submit_last_extraction_answer(self) -> dict[str, Any]:
        if self.last_extraction_report is None:
            raise ValueError("No extraction report is available for submission.")

        proposed_answer = self.last_extraction_report["proposed_answer"]
        result = self._submit_answer(
            SubmitAnswerArgs(
                date=proposed_answer["date"],
                password=proposed_answer["password"],
                confirmation_code=proposed_answer["confirmation_code"],
            )
        )
        if not result.ok:
            raise ValueError("Deterministic recovery failed during Hub submission.")
        return result.payload

    # This method selects cached messages for extraction by ids or falls back to all cached messages.
    def _select_messages_for_extraction(self, ids: list[str]) -> list[Mapping[str, Any]]:
        if not ids:
            return self._all_unique_messages()

        selected_messages: list[Mapping[str, Any]] = []
        seen_keys: set[int] = set()
        for message_id in ids:
            message = self.messages_by_id.get(message_id)
            if message is None:
                continue

            object_key = id(message)
            if object_key in seen_keys:
                continue

            seen_keys.add(object_key)
            selected_messages.append(message)

        return selected_messages

    # This method returns unique cached messages without duplicate aliases.
    def _all_unique_messages(self) -> list[Mapping[str, Any]]:
        unique_messages: list[Mapping[str, Any]] = []
        seen_keys: set[int] = set()
        for message in self.messages_by_id.values():
            object_key = id(message)
            if object_key in seen_keys:
                continue

            seen_keys.add(object_key)
            unique_messages.append(message)

        return unique_messages

    # This method returns every unique fetched message in a stable value-bearing archive shape.
    def build_full_message_archive(self) -> list[dict[str, Any]]:
        archived_messages: list[dict[str, Any]] = []

        for message in self._all_unique_messages():
            archived_messages.append(
                {
                    "message_id": stringify_identifier(get_message_identifier(message)),
                    "aliases": collect_message_aliases(message),
                    "payload": dict(message),
                }
            )

        return archived_messages

    # This method proves that solved values are present in fetched message text, not guessed.
    def _validate_finished_values_are_grounded(self, answer: MailboxAnswer) -> None:
        known_texts = [collect_message_text(message) for message in self._all_unique_messages()]
        for field_name, value in (
            ("date", answer.date),
            ("password", answer.password),
            ("confirmation_code", answer.confirmation_code),
        ):
            if value is None:
                raise ValueError(f"finish missing required field: {field_name}")

            if not any(value in text for text in known_texts):
                raise ValueError(
                    f"finish value for {field_name} was not found in fetched message text."
                )

    # This method builds a deterministic fallback result when the loop stops without finish.
    def build_fallback_finish_payload(
        self,
        *,
        status: Literal["partial", "blocked"],
        uncertainty: str,
    ) -> dict[str, Any]:
        if status not in {"partial", "blocked"}:
            raise ValueError("Fallback status must be partial or blocked.")

        extraction_report = self.last_extraction_report or {
            "proposed_answer": {
                "date": None,
                "password": None,
                "confirmation_code": None,
            },
            "uncertainties": [],
            "validation_errors": [],
            "candidates": [],
        }
        uncertainties = list(extraction_report.get("uncertainties", []))
        if uncertainty not in uncertainties:
            uncertainties.append(uncertainty)

        next_queries = [
            query
            for query in DEFAULT_SEARCH_QUERIES
            if query not in self.queries_run
        ][:3]

        return {
            "status": status,
            "found_values": extraction_report["proposed_answer"],
            "evidence": build_finish_evidence_from_report(extraction_report),
            "uncertainties": uncertainties,
            "next_queries": next_queries,
            "validation_errors": list(extraction_report.get("validation_errors", [])),
            "finished": False,
            "submission_enabled": self.submit_enabled,
            "last_submission_response": self.last_submission_response,
        }

    # This method exposes compact runtime state for reports and debugging.
    def build_runtime_summary(self) -> dict[str, Any]:
        return {
            "queries_run": list(self.queries_run),
            "tool_call_count": self.tool_call_count,
            "known_suspicious_thread_count": len(self.suspicious_thread_ids),
            "known_message_count": len({id(message) for message in self.messages_by_id.values()}),
            "search_report": build_masked_search_report(
                SearchRunSummary(batches=tuple(self.search_batches))
            ),
            "last_extraction_report": self.last_extraction_report,
            "last_masked_extraction_report": (
                build_masked_extraction_report(
                    extract_from_messages_payload(self._all_unique_messages())
                )
                if self._all_unique_messages()
                else None
            ),
            "fetched_messages_path": str(self.config.paths.fetched_messages_file),
            "fetched_messages": self.build_full_message_archive(),
            "submit_enabled": self.submit_enabled,
            "submit_requests_used": (
                self.hub_client.guard.used_requests
                if self.hub_client is not None and hasattr(self.hub_client, "guard")
                else 0
            ),
            "last_submission_payload": self.last_submission_payload,
            "last_submission_response": self.last_submission_response,
            "finished_payload": self.finished_payload,
        }
