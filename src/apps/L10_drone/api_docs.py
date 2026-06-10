# Local drone API documentation loading and compaction.

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


MAX_DOC_CONTEXT_CHARS = 12_000
WHITESPACE_PATTERN = re.compile(r"[ \t\f\v]+")
BLANK_LINE_PATTERN = re.compile(r"\n{3,}")


# Extract visible text from HTML while ignoring style and script content.
class VisibleTextExtractor(HTMLParser):
    # Initialize parser state for visible text extraction.
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    # Track elements whose content should not become model context.
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag in {"p", "br", "li", "tr", "h1", "h2", "h3", "pre", "section"}:
            self._parts.append("\n")

    # Stop skipping after hidden/script-like elements end.
    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in {"p", "li", "tr", "h1", "h2", "h3", "pre", "section"}:
            self._parts.append("\n")

    # Collect visible text chunks from the HTML page.
    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = data.strip()
        if cleaned:
            self._parts.append(cleaned)
            self._parts.append(" ")

    # Return normalized visible text for downstream model context.
    def get_text(self) -> str:
        text = "".join(self._parts)
        text = WHITESPACE_PATTERN.sub(" ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = BLANK_LINE_PATTERN.sub("\n\n", text)
        return text.strip()


# Convert one HTML document into compact visible text.
def html_to_text(html: str) -> str:
    parser = VisibleTextExtractor()
    parser.feed(html)
    return parser.get_text()


# Load local drone API documentation from disk.
def load_drone_api_docs(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Drone API docs file is missing: {path}")
    return path.read_text(encoding="utf-8")


# Build bounded model context from local drone API documentation.
def build_docs_context(path: Path, *, max_chars: int = MAX_DOC_CONTEXT_CHARS) -> str:
    text = html_to_text(load_drone_api_docs(path))
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED: documentation context exceeded local limit]"
