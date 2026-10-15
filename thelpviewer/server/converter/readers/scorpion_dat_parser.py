"""Clean parser primitives for modern Scorpion's Cheater DAT payloads."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .allegro_dat import (
    ALLEGRO_DAT_MAGIC,
    AllegroDatafile,
    AllegroDatafileEntry,
    AllegroDatafileObject,
    extract_allegro_data_objects,
    parse_allegro_datafile,
    parse_allegro_datafile_objects,
)


SCORPION_ALLEGRO_PACK_MAGIC = b"\x12\x1E\x03-"
SCORPION_ALLEGRO_PASSWORD = b"akrab"
SCORPION_DAT_SIGNATURE = SCORPION_ALLEGRO_PACK_MAGIC + ALLEGRO_DAT_MAGIC
SCORPION_ARTICLE_TAG_RE = re.compile(rb"\[([A-Z0-9]{4})\]")
SCORPION_IGNORED_ARTICLE_TAGS = frozenset({"CTRL"})


@dataclass(frozen=True, slots=True)
class ScorpionArticleMarker:
    tag: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class ScorpionDatRecord:
    index: int
    object_path: tuple[int, ...]
    name: str
    date: str
    origin: str
    payload: bytes
    payload_source: str
    stored_payload: bytes
    decoded_payload: bytes
    stored_size: int
    decoded_size: int
    uncompressed_size: int
    object_offset: int
    payload_offset: int
    payload_is_compressed: bool
    page_tag: str | None

    @property
    def payload_is_decompressed(self) -> bool:
        return self.payload_source == "decoded"


@dataclass(frozen=True, slots=True)
class ScorpionDatArticle:
    index: int
    record_index: int
    record_name: str
    object_path: tuple[int, ...]
    page_tag: str | None
    payload: bytes
    payload_source: str
    raw_start: int
    raw_end: int
    file_start: int | None
    file_end: int | None


def parse_scorpion_allegro_datafile(data: bytes) -> AllegroDatafile:
    """Parse the Scorpion old-crypt Allegro container variant."""
    return parse_allegro_datafile(
        data,
        packfile_password=SCORPION_ALLEGRO_PASSWORD,
        old_crypt_chunk_local=True,
    )


def parse_scorpion_allegro_objects(data: bytes) -> list[AllegroDatafileObject]:
    """Parse Scorpion Allegro objects with the Scorpion packfile password."""
    return parse_allegro_datafile_objects(
        data,
        packfile_password=SCORPION_ALLEGRO_PASSWORD,
        old_crypt_chunk_local=True,
    )


def extract_scorpion_allegro_data_objects(data: bytes) -> list[AllegroDatafileEntry]:
    """Return Scorpion DATA entries with old-crypt/LZSS already decoded."""
    return extract_allegro_data_objects(
        data,
        packfile_password=SCORPION_ALLEGRO_PASSWORD,
        old_crypt_chunk_local=True,
    )


def find_scorpion_article_markers(payload: bytes) -> list[ScorpionArticleMarker]:
    """Return literal page markers found in a selected Scorpion payload."""
    markers: list[ScorpionArticleMarker] = []
    for match in SCORPION_ARTICLE_TAG_RE.finditer(payload):
        if match.start() > 0 and payload[match.start() - 1] not in (0x0A, 0x0D, 0xFA):
            continue
        tag = match.group(1).decode("ascii", errors="replace")
        if tag in SCORPION_IGNORED_ARTICLE_TAGS:
            continue
        markers.append(ScorpionArticleMarker(tag=tag, start=match.start(), end=match.end()))
    return markers


def select_scorpion_payload(entry: AllegroDatafileEntry) -> tuple[str, bytes]:
    """Select the actual article bytes after validated container decoding.

    The Allegro layer exposes both the stored object bytes and the LZSS-decoded
    payload. Modern password-protected Scorpion files carry LZSS-compressed
    object payloads, so the decompressed bytes are the real article stream.
    Stored bytes are article text only for uncompressed objects; a failed
    compressed stream cannot be interpreted as plain text.
    """
    if entry.payload_is_compressed:
        return "decoded", entry.decoded_payload
    return "stored", entry.stored_payload


def parse_scorpion_dat_records(data: bytes) -> list[ScorpionDatRecord]:
    """Parse one modern Allegro-backed Scorpion DAT file into DATA records."""
    records: list[ScorpionDatRecord] = []
    for index, entry in enumerate(extract_scorpion_allegro_data_objects(data)):
        payload_source, payload = select_scorpion_payload(entry)
        markers = find_scorpion_article_markers(payload)
        record_name = entry.name
        if not record_name:
            record_name = f"legacy{index + 1:04d}" if markers else f"obr{index + 1}"
        records.append(
            ScorpionDatRecord(
                index=index,
                object_path=entry.object_path,
                name=record_name,
                date=entry.date,
                origin=entry.origin,
                payload=payload,
                payload_source=payload_source,
                stored_payload=entry.stored_payload,
                decoded_payload=entry.decoded_payload,
                stored_size=entry.stored_size,
                decoded_size=entry.decoded_size,
                uncompressed_size=entry.uncompressed_size,
                object_offset=entry.object_offset,
                payload_offset=entry.payload_offset,
                payload_is_compressed=entry.payload_is_compressed,
                page_tag=markers[0].tag if markers else None,
            )
        )
    return records


def split_scorpion_record_articles(record: ScorpionDatRecord) -> list[ScorpionDatArticle]:
    """Split one record into article slices by literal page markers."""
    markers = find_scorpion_article_markers(record.payload)
    if not markers:
        return [
            _build_article(
                record,
                index=0,
                page_tag=record.page_tag,
                raw_start=0,
                raw_end=len(record.payload),
            )
        ]

    articles: list[ScorpionDatArticle] = []
    for index, marker in enumerate(markers):
        raw_end = markers[index + 1].start if index + 1 < len(markers) else len(record.payload)
        articles.append(
            _build_article(
                record,
                index=index,
                page_tag=marker.tag,
                raw_start=marker.start,
                raw_end=raw_end,
            )
        )
    return articles


def parse_scorpion_dat_articles(data: bytes) -> list[ScorpionDatArticle]:
    """Parse one modern DAT file and return all article slices."""
    articles: list[ScorpionDatArticle] = []
    for record in parse_scorpion_dat_records(data):
        articles.extend(split_scorpion_record_articles(record))
    return articles


def _build_article(
    record: ScorpionDatRecord,
    *,
    index: int,
    page_tag: str | None,
    raw_start: int,
    raw_end: int,
) -> ScorpionDatArticle:
    file_start = record.payload_offset + raw_start if record.payload_source == "stored" else None
    file_end = record.payload_offset + raw_end if record.payload_source == "stored" else None
    return ScorpionDatArticle(
        index=index,
        record_index=record.index,
        record_name=record.name,
        object_path=record.object_path,
        page_tag=page_tag,
        payload=record.payload[raw_start:raw_end],
        payload_source=record.payload_source,
        raw_start=raw_start,
        raw_end=raw_end,
        file_start=file_start,
        file_end=file_end,
    )
