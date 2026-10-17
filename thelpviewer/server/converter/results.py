"""Explicit conversion results; format names never encode an operation failure."""

from dataclasses import dataclass
from pathlib import Path


class ConversionError(ValueError):
    """A source or generated bundle failed conversion/validation."""

    def __init__(self, message, *, package_id=None):
        super().__init__(message)
        self.package_id = package_id


@dataclass(frozen=True, slots=True)
class BundleResult:
    input_path: Path
    json_path: Path
    format_name: str
    topic_count: int
    display_name: str
    source_files: tuple[str, ...] = ()
    product: str = ""
    product_name: str = ""
    version: str = ""
    error: str = ""
