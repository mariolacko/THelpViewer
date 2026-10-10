from thelpviewer.server.converter.readers.allegro_dat import (
    ALLEGRO_DAT_MAGIC,
    ALLEGRO_F_NOPACK_MAGIC,
    ALLEGRO_F_PACK_MAGIC,
    ALLEGRO_TYPE_DATA,
    AllegroDatafileError,
    allegro_lzss_decompress,
    extract_allegro_data_objects,
    extract_allegro_datafile_entries,
    parse_allegro_datafile,
)


OLD_CRYPT_TEST_PASSWORD = b"akrab"
OLD_CRYPT_TEST_NOPACK_MAGIC = b"\x12\x1E\x03-"


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


def _old_crypt_literal_lzss(data: bytes, password: bytes) -> bytes:
    chunks: list[bytes] = []
    password_offset = 0
    for start in range(0, len(data), 8):
        chunk = data[start:start + 8]
        flag = ((1 << len(chunk)) - 1) ^ password[password_offset]
        password_offset = (password_offset + 1) % len(password)
        chunks.append(bytes([flag]) + chunk)
    return b"".join(chunks)


def _dat_body(*objects: bytes) -> bytes:
    return ALLEGRO_DAT_MAGIC + len(objects).to_bytes(4, "big") + b"".join(objects)


def test_allegro_dat_parser_reads_standard_unpacked_object_table():
    payload = ALLEGRO_F_NOPACK_MAGIC + _dat_body(
        _object(
            b"DATA",
            b"hello",
            _property(b"NAME", b"greeting"),
        )
    )

    document = parse_allegro_datafile(payload)

    assert document.pack_magic == ALLEGRO_F_NOPACK_MAGIC
    assert len(document.objects) == 1
    assert document.objects[0].type_id == ALLEGRO_TYPE_DATA
    assert document.objects[0].properties["NAME"] == b"greeting"
    assert document.objects[0].payload == b"hello"


def test_allegro_lzss_decompresses_literal_tokens():
    assert allegro_lzss_decompress(_literal_lzss(b"abcdefghi"), 9) == b"abcdefghi"


def test_allegro_lzss_decompresses_back_reference_tokens():
    payload = b"\x07ABC\xee\xf3"

    assert allegro_lzss_decompress(payload, 9) == b"ABCABCABC"


def test_allegro_lzss_initial_dictionary_is_zero_filled():
    payload = b"\x00\xee\xf3"

    assert allegro_lzss_decompress(payload, 6) == b"\x00" * 6


def test_allegro_lzss_decrypts_old_crypt_flag_bytes():
    unpacked = b"Binary Data\x00"
    packed = _old_crypt_literal_lzss(unpacked, OLD_CRYPT_TEST_PASSWORD)

    assert (
        allegro_lzss_decompress(
            packed,
            len(unpacked),
            old_crypt_password=OLD_CRYPT_TEST_PASSWORD,
        )
        == unpacked
    )


def test_allegro_dat_parser_decompresses_compressed_object_payload():
    unpacked = b"[R010]\r\n"
    packed = _literal_lzss(unpacked)
    payload = ALLEGRO_F_NOPACK_MAGIC + _dat_body(
        _object(
            b"DATA",
            packed,
            _property(b"NAME", b"page"),
            unpacked_size=-len(unpacked),
        )
    )

    document = parse_allegro_datafile(payload)

    assert document.objects[0].packed_payload == packed
    assert document.objects[0].payload == unpacked
    assert document.objects[0].payload_is_compressed


def test_allegro_dat_parser_reads_old_crypt_chunks_with_supplied_password():
    unpacked = b"[3001]\r\nAFTER LIFE\r\n"
    packed = _old_crypt_literal_lzss(unpacked, OLD_CRYPT_TEST_PASSWORD)
    payload = OLD_CRYPT_TEST_NOPACK_MAGIC + _dat_body(
        _object(
            b"DATA",
            packed,
            _property(b"NAME", b"ch05"),
            unpacked_size=-len(unpacked),
        )
    )

    document = parse_allegro_datafile(
        payload,
        packfile_password=OLD_CRYPT_TEST_PASSWORD,
        old_crypt_chunk_local=True,
    )

    assert document.pack_magic == OLD_CRYPT_TEST_NOPACK_MAGIC
    assert document.decoded_pack_magic == ALLEGRO_F_NOPACK_MAGIC
    assert document.uses_old_crypt
    assert document.packfile_password == OLD_CRYPT_TEST_PASSWORD
    assert document.old_crypt_chunk_local
    assert document.objects[0].payload == unpacked


def test_allegro_dat_parser_rejects_truncated_compressed_object_payload():
    unpacked = b"[R010]\r\n"
    packed = _literal_lzss(unpacked[:-1])
    payload = ALLEGRO_F_NOPACK_MAGIC + _dat_body(
        _object(
            b"DATA",
            packed,
            unpacked_size=-len(unpacked),
        )
    )

    try:
        parse_allegro_datafile(payload, strict_chunks=True)
    except AllegroDatafileError:
        return
    raise AssertionError("truncated Allegro chunk was accepted")


def test_allegro_dat_parser_decompresses_top_level_packfile_payload():
    body = _dat_body(_object(b"DATA", b"plain"))

    document = parse_allegro_datafile(ALLEGRO_F_PACK_MAGIC + _literal_lzss(body))

    assert document.payload_is_compressed
    assert document.objects[0].payload == b"plain"


def test_allegro_dat_parser_rejects_unknown_pack_magic():
    try:
        parse_allegro_datafile(b"bad!" + _dat_body(_object(b"DATA", b"plain")))
    except AllegroDatafileError:
        return
    raise AssertionError("unknown Allegro magic was accepted")


def test_allegro_data_extractor_exposes_stored_and_decoded_payloads():
    unpacked = b"[R010]\r\n"
    packed = _literal_lzss(unpacked)
    payload = ALLEGRO_F_NOPACK_MAGIC + _dat_body(
        _object(
            b"DATA",
            packed,
            _property(b"NAME", b"page"),
            _property(b"DATE", b"2024-01-02"),
            _property(b"ORIG", b"source.bin"),
            unpacked_size=-len(unpacked),
        ),
        _object(
            b"info",
            b"For internal use by the grabber",
            _property(b"NAME", b"GrabberInfo"),
        ),
    )

    entries = extract_allegro_data_objects(payload)

    assert len(entries) == 1
    assert entries[0].object_path == (0,)
    assert entries[0].type_id == ALLEGRO_TYPE_DATA
    assert entries[0].name == "page"
    assert entries[0].date == "2024-01-02"
    assert entries[0].origin == "source.bin"
    assert entries[0].stored_payload == packed
    assert entries[0].decoded_payload == unpacked
    assert entries[0].stored_size == len(packed)
    assert entries[0].decoded_size == len(unpacked)
    assert entries[0].payload_is_compressed


def test_allegro_data_extractor_flattens_nested_file_objects():
    nested_payload = (1).to_bytes(4, "big") + _object(
        b"DATA",
        b"nested",
        _property(b"NAME", b"nested-page"),
    )
    payload = ALLEGRO_F_NOPACK_MAGIC + _dat_body(
        _object(
            b"FILE",
            nested_payload,
            _property(b"NAME", b"folder"),
        )
    )

    entries = extract_allegro_datafile_entries(payload, include_types=ALLEGRO_TYPE_DATA)

    assert len(entries) == 1
    assert entries[0].object_path == (0, 0)
    assert entries[0].name == "nested-page"
    assert entries[0].decoded_payload == b"nested"
