"""DOS manifest rules shared by package choices and actual disk preparation."""

from pathlib import Path
import re

from ..content_config import read_source_manifest
from .paths import DosError, ID_RE


def load_dos_config(path: Path | None) -> dict:
    try:
        data = read_source_manifest(path, "DOS", ID_RE)
    except ValueError as error:
        raise DosError(str(error)) from error
    if any(key in data for key in ("initial_files", "autoexec.bat", "config.sys")):
        raise DosError("Use files entries with path and text/base64 instead of initial_files/autoexec.bat/config.sys")
    if any(not isinstance(source.get("language", "und"), str)
           or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", source.get("language", "und")) for source in data["sources"]):
        raise DosError("DOS package language must be a language code such as cs, en or en-GB")
    if any(not isinstance(source.get("required", False), bool) for source in data["sources"]):
        raise DosError("DOS package required must be a boolean")
    categories = data.get("categories", [])
    if not isinstance(categories, list):
        raise DosError("DOS categories must be a list")
    ids = [item.get("id") if isinstance(item, dict) else None for item in categories]
    if (any(not isinstance(ident, str) or not ID_RE.fullmatch(ident) for ident in ids)
            or len(set(ids)) != len(ids)
            or any(not isinstance(item.get("label"), str) or not item["label"].strip() for item in categories)):
        raise DosError("DOS categories need unique valid IDs and labels")
    if any(not isinstance(source.get("category", "other"), str)
           or source.get("category", "other") not in {*ids, "other"} for source in data["sources"]):
        raise DosError("Unknown DOS package category")
    if any(source.get("category", "other") == "other" for source in data["sources"]) and "other" not in ids:
        categories = [*categories, {"id": "other", "label": "Other"}]
    return {**data, "categories": categories}


def select_dos_packages(config: dict, source_ids: list[str]) -> list[str]:
    """Return required packages first, retaining manifest order within each group."""
    if set(source_ids) - {source["id"] for source in config["sources"]}:
        raise DosError("Unknown DOS package")
    selected = set(source_ids)
    return [source["id"] for source in sorted(config["sources"], key=lambda source: not source.get("required", False))
            if source["id"] in selected or source.get("required", False)]
