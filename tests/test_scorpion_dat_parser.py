from thelpviewer.converter.readers.allegro_dat import (
    ALLEGRO_DAT_MAGIC,
    ALLEGRO_F_NOPACK_MAGIC,
)
from thelpviewer.converter.readers.scorpion_dat_parser import (
    parse_scorpion_dat_articles,
    parse_scorpion_dat_records,
)


def _property(name: bytes, value: bytes) -> bytes:
    return b"prop" + name + len(value).to_bytes(4, "big") + value


def _object(type_id: bytes, payload: bytes, *properties: bytes, unpacked_size: int | None = None) -> bytes:
    return b"".join(
        (
            *properties,
            type_id,
            len(payload).to_bytes(4, "big", signed=True),
            (len(payload) if unpacked_size is None else unpacked_size).to_bytes(4, "big", signed=True),
            payload,
        )
    )


def _literal_lzss(data: bytes) -> bytes:
    chunks: list[bytes] = []
    for start in range(0, len(data), 8):
        chunk = data[start:start + 8]
        chunks.append(bytes([(1 << len(chunk)) - 1]) + chunk)
    return b"".join(chunks)


def _dat_body(*objects: bytes) -> bytes:
    return ALLEGRO_F_NOPACK_MAGIC + ALLEGRO_DAT_MAGIC + len(objects).to_bytes(4, "big") + b"".join(objects)


def test_scorpion_parser_prefers_decoded_payload_after_allegro_decompression():
    decoded = b"[R010]\r\nArticle text"
    packed = _literal_lzss(decoded)
    payload = _dat_body(
        _object(
            b"DATA",
            packed,
            _property(b"NAME", b"kecy"),
            unpacked_size=-len(decoded),
        )
    )

    records = parse_scorpion_dat_records(payload)

    assert len(records) == 1
    assert records[0].name == "kecy"
    assert records[0].payload_source == "decoded"
    assert records[0].payload == decoded
    assert records[0].page_tag == "R010"


def test_scorpion_parser_uses_decoded_payload_when_only_decoded_has_markers():
    decoded = b"abcdef[R010]\r\nArticle text"
    packed = _literal_lzss(decoded)
    payload = _dat_body(
        _object(
            b"DATA",
            packed,
            _property(b"NAME", b"kecy"),
            unpacked_size=-len(decoded),
        )
    )

    records = parse_scorpion_dat_records(payload)

    assert len(records) == 1
    assert records[0].payload_source == "decoded"
    assert records[0].payload == decoded


def test_scorpion_parser_splits_articles_on_literal_page_markers():
    decoded = b"[R010]\r\nFirst\xfa[R222]\r\nSecond"
    packed = _literal_lzss(decoded)
    payload = _dat_body(
        _object(
            b"DATA",
            packed,
            _property(b"NAME", b"kecy2"),
            unpacked_size=-len(decoded),
        )
    )

    articles = parse_scorpion_dat_articles(payload)

    assert [(article.page_tag, article.payload) for article in articles] == [
        ("R010", b"[R010]\r\nFirst\xfa"),
        ("R222", b"[R222]\r\nSecond"),
    ]
    assert articles[0].file_start is None
