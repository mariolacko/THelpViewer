"""Shared in-memory data model for parsed help documents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass(slots=True)
class PositionedKeyword:
    """Clickable range stored by old-format THELP keyword records."""

    target_context: int
    line: int
    first_column: int
    last_column: int
    navigation: tuple[int | None, int | None, int | None, int | None] = (
        None,
        None,
        None,
        None,
    )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of one positional THELP keyword record."""
        return {
            "target_context": self.target_context,
            "line": self.line,
            "first_column": self.first_column,
            "last_column": self.last_column,
            "navigation": list(self.navigation),
        }


@dataclass(slots=True)
class TopicRecord:
    """One logical help topic with raw text and hyperlink metadata."""

    context_id: int
    raw_lines: list[bytes]
    index_terms: list[bytes] = field(default_factory=list)
    alias_contexts: list[int] = field(default_factory=list)
    sequential_keywords: list[int] = field(default_factory=list)
    positional_keywords: list[PositionedKeyword] = field(default_factory=list)
    is_main_index: bool = False
    up_context: int | None = None
    down_context: int | None = None
    names: list[str] = field(default_factory=list)

    def to_dict(self, text_encoding: str = "latin1") -> dict[str, object]:
        """Return a JSON-safe view of one normalized help topic."""
        return {
            "context_id": self.context_id,
            "names": list(self.names),
            "raw_lines": [_serialize_bytes(line, text_encoding) for line in self.raw_lines],
            "index_terms": [_serialize_bytes(term, text_encoding) for term in self.index_terms],
            "alias_contexts": list(self.alias_contexts),
            "sequential_keywords": list(self.sequential_keywords),
            "positional_keywords": [keyword.to_dict() for keyword in self.positional_keywords],
            "is_main_index": self.is_main_index,
            "up_context": self.up_context,
            "down_context": self.down_context,
        }


@dataclass(slots=True)
class IndexEntry:
    """One index label pointing to a topic context id."""

    label: bytes
    context_id: int

    def to_dict(self, text_encoding: str = "latin1") -> dict[str, object]:
        """Return a JSON-safe view of one visible index entry."""
        return {
            "label": _serialize_bytes(self.label, text_encoding),
            "context_id": self.context_id,
        }


@dataclass(slots=True)
class CommentRecord:
    """One preserved source comment, optionally scoped to a specific topic."""

    text: str
    topic_context: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of one preserved source comment."""
        return {
            "text": self.text,
            "topic_context": self.topic_context,
        }


@dataclass(slots=True)
class HelpDocument:
    """Normalized document model shared by all readers and renderers."""

    format_name: str
    source_name: str
    topics: list[TopicRecord]
    index_entries: list[IndexEntry]
    comments: list[CommentRecord] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    binary_data: bytes | None = None

    @property
    def display_name(self) -> str:
        """Short source name used in generated page headers."""
        return Path(self.source_name).name.lower()

    @staticmethod
    def topic_filename(context_id: int) -> str:
        """Map a numeric context id to a stable HTML file name."""
        return f"{context_id:04X}.html"

    def to_dict(
        self,
        text_encoding: str = "latin1",
        include_binary_data: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-safe snapshot of the normalized help document."""
        payload = {
            "format_name": self.format_name,
            "source_name": self.source_name,
            "display_name": self.display_name,
            "text_encoding": text_encoding,
            "topic_count": len(self.topics),
            "index_entry_count": len(self.index_entries),
            "comment_count": len(self.comments),
            "topics": [topic.to_dict(text_encoding=text_encoding) for topic in self.topics],
            "index_entries": [entry.to_dict(text_encoding=text_encoding) for entry in self.index_entries],
            "comments": [comment.to_dict() for comment in self.comments],
            "metadata": _json_safe(self.metadata, text_encoding),
        }
        if include_binary_data and self.binary_data is not None:
            payload["binary_data"] = {
                "size": len(self.binary_data),
                "hex": self.binary_data.hex(),
            }
        return payload

    def to_json(
        self,
        text_encoding: str = "latin1",
        include_binary_data: bool = False,
        indent: int = 2,
    ) -> str:
        """Serialize the document model to formatted JSON text."""
        return json.dumps(
            self.to_dict(text_encoding=text_encoding, include_binary_data=include_binary_data),
            ensure_ascii=False,
            indent=indent,
        )

    def write_json(
        self,
        path: str | Path,
        text_encoding: str = "latin1",
        include_binary_data: bool = False,
        indent: int = 2,
    ) -> Path:
        """Write the document model to a JSON file and return its path."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            self.to_json(
                text_encoding=text_encoding,
                include_binary_data=include_binary_data,
                indent=indent,
            ),
            encoding="utf-8",
        )
        return target_path


class HelpReaderBase(ABC):
    """Common interface shared by binary and textual help readers."""

    def __init__(
        self,
        source_name: str = "input.hlp",
        text_encoding: str = "latin1",
        source_path: str | Path | None = None,
    ):
        self.source_name = source_name
        self.text_encoding = text_encoding
        self.source_path = Path(source_path) if source_path is not None else None

    @abstractmethod
    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read raw file bytes and return the normalized document model."""

    def read_path(self, path: str | Path) -> HelpDocument:
        """Load bytes from disk and delegate to ``read_bytes``."""
        source_path = Path(path)
        self.source_name = source_path.name
        self.source_path = source_path
        return self.read_bytes(source_path.read_bytes())


def _decode_bytes(value: bytes, text_encoding: str) -> str:
    """Decode raw help text for human-readable JSON inspection."""
    if text_encoding == "utf-8":
        return value.decode("utf-8", errors="replace")
    try:
        return value.decode(text_encoding, errors="replace")
    except LookupError:
        from .codepages import decode_bytes

        return decode_bytes(value, text_encoding)


def _serialize_bytes(value: bytes, text_encoding: str) -> dict[str, str]:
    """Expose both decoded text and raw bytes for lossless JSON export."""
    return {
        "text": _decode_bytes(value, text_encoding),
        "hex": value.hex(),
    }


def _json_safe(value: object, text_encoding: str) -> object:
    """Convert nested document metadata to values accepted by ``json``."""
    if isinstance(value, bytes):
        return _serialize_bytes(value, text_encoding)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item, text_encoding) for item in value]
    if isinstance(value, list):
        return [_json_safe(item, text_encoding) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item, text_encoding) for key, item in value.items()}
    return value
