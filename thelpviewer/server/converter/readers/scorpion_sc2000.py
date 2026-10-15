"""Verified SC 2000 catalog records inside an Allegro Scorpion datafile.

The prose viewer's pixel pagination/font macros are a different grammar.
Do not interpret those objects with the DOS article control-byte alphabet.
"""

from collections import Counter
from pathlib import Path
import re

from ..base import ContentNode, IndexEntry, TopicRecord
from ..codepages import decode_bytes
from ..uhf_markup import escape_uhf_text, format_uhf_link
from .scorpion_dat_parser import ScorpionDatRecord


CATALOG_HEADER_RE = re.compile(rb"^<+ Seznam pro SC 2000 >+(?:\r\n|\n|\r)")
CHEAT_ROW_RE = re.compile(rb"^(--|-\*|-!|-b),[01],1,\*,\[([A-Z0-9]{4})\],([^,]*)$")


def is_sc2000_catalog(record: ScorpionDatRecord) -> bool:
    return record.name == "txt" and CATALOG_HEADER_RE.match(record.payload) is not None


def is_sc2000_prose(record: ScorpionDatRecord) -> bool:
    """Identify the separate angle-bracket grammar, not DOS marker articles."""
    return record.payload.startswith(b"<!K=")


def catalog_topic(record: ScorpionDatRecord, source_path: Path, context_id: int):
    """Keep every row; link only the native cheat and title-reference forms.

    CHEATER v21's CH2000 export writes `#title` followed by
    `-*,0,1,*,[marker],` from its cheat library. `marker` is scoped to
    CHEATY, not every DAT sharing that numeric marker. Library-member
    descriptors retain their literal fields, including ambiguous commas.
    """
    if not is_sc2000_catalog(record):
        raise ValueError("Not an SC 2000 catalog record")
    body = record.payload.split(b"\xfe", 1)[0]
    raw_rows = re.split(rb"\r\n|\r|\n", body)
    while raw_rows and not raw_rows[-1]:
        raw_rows.pop()
    rows = [decode_bytes(row, "cp1250") for row in raw_rows]
    titles = [(index + 1, row[1:]) for index, row in enumerate(rows) if row.startswith("#")]
    counts = Counter(title for _, title in titles)
    title_lines = {title: line for line, title in titles if counts[title] == 1}
    # This is the existing version directory, not a newly invented product root.
    group = source_path.parent.name
    source_file = f"{group}/cheaty.json.gz" if group else "cheaty.json.gz"
    content = []
    for raw, text in zip(raw_rows, rows):
        match = CHEAT_ROW_RE.fullmatch(raw)
        if match:
            marker = match.group(2).decode("ascii")
            start = text.index(f"[{marker}]")
            end = start + len(marker) + 2
            content.append(escape_uhf_text(text[:start]) + format_uhf_link(
                escape_uhf_text(text[start:end]), source_file=source_file, alias=marker,
            ) + escape_uhf_text(text[end:]))
        elif text.startswith("-!,") and text.count(",") == 1 and text[3:] in title_lines:
            content.append("-!," + format_uhf_link(
                escape_uhf_text(text[3:]), topic_id=context_id, line=title_lines[text[3:]],
            ))
        else:
            content.append(escape_uhf_text(text))
    title = "Seznam pro SC 2000"
    topic = TopicRecord(
        context_id=context_id, raw_lines=[text.encode("utf-8") for text in rows],
        names=[title], alias_strings=[record.name], uhf_content=content,
    )
    index = [IndexEntry(label=title.encode("utf-8"), context_id=context_id)]
    index.extend(IndexEntry(label=label.encode("utf-8"), context_id=context_id, line=line)
                 for line, label in titles)
    contents = [ContentNode(label=label, topic_id=context_id, line=line) for line, label in titles]
    return topic, index, contents
