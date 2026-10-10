"""Allowlisted Python documentation sources and local HTML parsing."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import re
import unicodedata
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class DocumentSource:
    url: str
    title: str


@dataclass(frozen=True, slots=True)
class DocumentSection:
    title: str | None
    text: str


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    doc_id: str
    source: str
    title: str
    url: str
    text: str
    sections: tuple[DocumentSection, ...]


SOURCE_NAME = "Python documentation"
ALLOWED_DOCUMENTS = (
    DocumentSource(
        url="https://docs.python.org/3/tutorial/controlflow.html",
        title="The Python Tutorial: More Control Flow Tools",
    ),
    DocumentSource(
        url="https://docs.python.org/3/library/json.html",
        title="Python Standard Library: json",
    ),
    DocumentSource(
        url="https://docs.python.org/3/library/pathlib.html",
        title="Python Standard Library: pathlib",
    ),
)
_SOURCES_BY_URL = {source.url: source for source in ALLOWED_DOCUMENTS}
_BLOCK_TAGS = {
    "article",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
_IGNORED_TAGS = {"footer", "header", "nav", "noscript", "script", "style", "svg"}
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_HEADING_TAGS = {f"h{level}" for level in range(1, 7)}


def clean_text(text: str) -> str:
    """Normalize Unicode and whitespace while retaining paragraph breaks."""
    normalized = unicodedata.normalize("NFKC", unescape(text)).replace("\xa0", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\t\f\v ]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


class _DocumentationHTMLParser(HTMLParser):
    """Extract visible text in heading-delimited sections."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page_title_parts: list[str] = []
        self.section_title_parts: list[str] = []
        self.sections: list[DocumentSection] = []
        self.current_section_title: str | None = None
        self.current_section_parts: list[str] = []
        self.ignored_depth = 0
        self.in_page_title = False
        self.in_heading: str | None = None
        self.page_heading: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.ignored_depth:
            if tag not in _VOID_TAGS:
                self.ignored_depth += 1
            return

        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag in _IGNORED_TAGS or classes.intersection({"related", "sphinxsidebar"}):
            self.ignored_depth = 0 if tag in _VOID_TAGS else 1
            return
        if tag == "title":
            self.in_page_title = True
        elif tag in _HEADING_TAGS:
            self.in_heading = tag
            self.section_title_parts = []
        elif tag in _BLOCK_TAGS:
            self.current_section_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.ignored_depth:
            if tag not in _VOID_TAGS:
                self.ignored_depth -= 1
            return
        if tag == "title":
            self.in_page_title = False
        elif self.in_heading == tag:
            heading = clean_text("".join(self.section_title_parts)) or None
            if tag == "h1" and heading:
                self.page_heading = heading
            self._flush_section()
            self.current_section_title = heading
            self.section_title_parts = []
            self.in_heading = None
        elif tag in _BLOCK_TAGS:
            self.current_section_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.in_page_title:
            self.page_title_parts.append(data)
        elif self.in_heading:
            self.section_title_parts.append(data)
        else:
            self.current_section_parts.append(data)

    def _flush_section(self) -> None:
        text = clean_text("".join(self.current_section_parts))
        if text:
            self.sections.append(DocumentSection(self.current_section_title, text))
        self.current_section_parts = []


def parse_document(url: str, html_text: str) -> DocumentRecord:
    """Parse fixture or fetched HTML for one allowlisted documentation URL."""
    source_spec = _SOURCES_BY_URL.get(url)
    if source_spec is None:
        raise ValueError("URL is not in the Python documentation allowlist")

    parser = _DocumentationHTMLParser()
    parser.feed(html_text)
    parser.close()
    parser._flush_section()

    page_title = clean_text(" ".join(parser.page_title_parts))
    title = page_title or parser.page_heading or source_spec.title
    sections = tuple(parser.sections)
    text = "\n\n".join(section.text for section in sections)
    doc_id = sha256(url.encode("utf-8")).hexdigest()
    return DocumentRecord(
        doc_id=doc_id,
        source=SOURCE_NAME,
        title=title,
        url=url,
        text=text,
        sections=sections,
    )


def fetch_document_html(url: str, timeout_seconds: float = 15.0) -> str:
    """Fetch HTML for an allowlisted URL; parsing remains a separate operation."""
    if url not in _SOURCES_BY_URL:
        raise ValueError("URL is not in the Python documentation allowlist")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")

    request = Request(url, headers={"User-Agent": "SoftServe-Lab12-RAG/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")
