# HTML parsing helpers for deterministic OKO state extraction.

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

from src.apps.L16_okoeditor.models import RecordDetail, RecordLink


ANCHOR_PATTERN = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
STRONG_PATTERN = re.compile(r"<strong[^>]*>(.*?)</strong>", re.IGNORECASE | re.DOTALL)
PARAGRAPH_PATTERN = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")
SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
WHITESPACE_PATTERN = re.compile(r"\s+")
CODE_PREFIX_PATTERN = re.compile(r"^([A-Z]{3,5}\d{2})\s+(.*)$")


# Convert HTML into visible text without script or style noise.
def html_to_text(html: str) -> str:
    text = SCRIPT_STYLE_PATTERN.sub(" ", html)
    text = TAG_PATTERN.sub(" ", text)
    text = unescape(WHITESPACE_PATTERN.sub(" ", text)).strip()
    return text


# Extract the document title from one HTML page.
def extract_document_title(html: str) -> str:
    match = TITLE_PATTERN.search(html)
    if not match:
        return ""
    return unescape(WHITESPACE_PATTERN.sub(" ", match.group(1))).strip()


# Split one record title into the code prefix and the human part.
def split_title_code(title: str) -> tuple[str | None, str]:
    normalized = WHITESPACE_PATTERN.sub(" ", title).strip()
    match = CODE_PREFIX_PATTERN.match(normalized)
    if not match:
        return None, normalized
    return match.group(1), match.group(2).strip()


# Parse one list page into deterministic record links.
def parse_list_page(page: str, html: str, *, base_url: str) -> tuple[RecordLink, ...]:
    records: list[RecordLink] = []
    seen_ids: set[str] = set()
    link_pattern = re.compile(rf"^/(?:oko/)?{re.escape(page)}/([a-f0-9]{{32}})/?$", re.IGNORECASE)

    for href, inner_html in ANCHOR_PATTERN.findall(html):
        match = link_pattern.match(href.strip())
        if not match:
            continue
        record_id = match.group(1).lower()
        if record_id in seen_ids:
            continue

        anchor_text = html_to_text(inner_html)
        strong_match = STRONG_PATTERN.search(inner_html)
        title = html_to_text(strong_match.group(1)) if strong_match else anchor_text
        paragraph_match = PARAGRAPH_PATTERN.search(inner_html)
        preview = html_to_text(paragraph_match.group(1)) if paragraph_match else anchor_text

        records.append(
            RecordLink(
                page=page,
                record_id=record_id,
                url=urljoin(base_url, href.lstrip("/")),
                title=title,
                preview=preview,
                anchor_text=anchor_text,
            )
        )
        seen_ids.add(record_id)

    return tuple(records)


# Parse one detail page into a normalized record.
def parse_detail_page(page: str, record_id: str, html: str, *, url: str) -> RecordDetail:
    document_title = extract_document_title(html)
    visible_text = html_to_text(html)
    title = document_title.removeprefix("OKO | ").strip() or record_id
    code, title_without_code = split_title_code(title)
    body_text = extract_body_text(visible_text, title)
    status_label = extract_status_label(body_text) if page == "zadania" else None
    is_done = None
    if status_label == "niewykonane":
        is_done = False
    elif status_label == "wykonane":
        is_done = True

    return RecordDetail(
        page=page,
        record_id=record_id,
        url=url,
        title=title,
        code=code,
        title_without_code=title_without_code,
        visible_text=visible_text,
        body_text=body_text,
        status_label=status_label,
        is_done=is_done,
    )


# Extract the most relevant body text from one detail page.
def extract_body_text(visible_text: str, title: str) -> str:
    normalized = WHITESPACE_PATTERN.sub(" ", visible_text).strip()
    if not title:
        return normalized

    title_occurrences = [match.start() for match in re.finditer(re.escape(title), normalized)]
    if title_occurrences:
        start = title_occurrences[-1] + len(title)
        normalized = normalized[start:].strip()

    if normalized.endswith("Wstecz"):
        normalized = normalized[: -len("Wstecz")].strip()
    return normalized


# Extract the visible task status from one task detail page.
def extract_status_label(text: str) -> str | None:
    lowered = text.casefold()
    if "niewykonane" in lowered:
        return "niewykonane"
    if "wykonane" in lowered:
        return "wykonane"
    return None
