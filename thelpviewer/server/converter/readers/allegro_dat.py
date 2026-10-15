"""Reader helpers for Allegro 2.2-4.4 datafile containers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field


ALLEGRO_F_PACK_MAGIC = b"slh!"
ALLEGRO_F_NOPACK_MAGIC = b"slh."
ALLEGRO_DAT_MAGIC = b"ALL."
ALLEGRO_PROPERTY_MAGIC = b"prop"
ALLEGRO_TYPE_DATA = "DATA"
ALLEGRO_TYPE_FILE = "FILE"
ALLEGRO_TYPE_INFO = "info"
ALLEGRO_STANDARD_PACK_MAGICS = (ALLEGRO_F_PACK_MAGIC, ALLEGRO_F_NOPACK_MAGIC)
ALLEGRO_SUPPORTED_PACK_MAGICS = ALLEGRO_STANDARD_PACK_MAGICS


class AllegroDatafileError(ValueError):
    """Raised when bytes cannot be parsed as the supported Allegro DAT subset."""


@dataclass(frozen=True, slots=True)
class AllegroDatafileObject:
    type_id: str
    properties: dict[str, bytes]
    payload: bytes
    packed_payload: bytes
    compressed_size: int
    uncompressed_size: int
    object_offset: int
    payload_offset: int
    payload_is_compressed: bool
    children: tuple["AllegroDatafileObject", ...] = field(default_factory=tuple)

    @property
    def packed_size(self) -> int:
        return self.compressed_size

    @property
    def unpacked_size(self) -> int:
        return self.uncompressed_size


@dataclass(frozen=True, slots=True)
class AllegroDatafile:
    pack_magic: bytes
    objects: tuple[AllegroDatafileObject, ...]
    payload_is_compressed: bool = False
    decoded_pack_magic: bytes | None = None
    uses_old_crypt: bool = False
    packfile_password: bytes = b""
    old_crypt_chunk_local: bool = False


@dataclass(frozen=True, slots=True)
class AllegroDatafileEntry:
    """Flattened Allegro object payload plus decoded metadata."""

    object_path: tuple[int, ...]
    type_id: str
    properties: dict[str, bytes]
    name: str
    date: str
    origin: str
    stored_payload: bytes
    decoded_payload: bytes
    stored_size: int
    decoded_size: int
    uncompressed_size: int
    object_offset: int
    payload_offset: int
    payload_is_compressed: bool

    @property
    def payload(self) -> bytes:
        return self.decoded_payload

    @property
    def packed_payload(self) -> bytes:
        return self.stored_payload

    @property
    def packed_size(self) -> int:
        return self.stored_size

    @property
    def unpacked_size(self) -> int:
        return self.uncompressed_size


def is_allegro_datafile(
    data: bytes,
    *,
    accepted_pack_magics: tuple[bytes, ...] = ALLEGRO_SUPPORTED_PACK_MAGICS,
    packfile_password: bytes | str | None = None,
) -> bool:
    """Return True when *data* has a supported Allegro datafile header."""
    if len(data) < 12:
        return False
    try:
        decoded_magic, _uses_old_crypt = _decode_packfile_magic(
            data[:4],
            accepted_pack_magics=accepted_pack_magics,
            password=_normalize_packfile_password(packfile_password),
        )
    except AllegroDatafileError:
        return False
    return decoded_magic == ALLEGRO_F_PACK_MAGIC or data[4:8] == ALLEGRO_DAT_MAGIC


def decode_allegro_property(properties: dict[str, bytes], name: str) -> str:
    """Decode one Allegro property value using the byte-preserving fallback."""
    return properties.get(name, b"").decode("latin-1", errors="replace")


def parse_allegro_datafile(
    data: bytes,
    *,
    accepted_pack_magics: tuple[bytes, ...] = ALLEGRO_SUPPORTED_PACK_MAGICS,
    parse_nested: bool = True,
    packfile_password: bytes | str | None = None,
    old_crypt_chunk_local: bool | None = None,
) -> AllegroDatafile:
    """Parse an Allegro datafile and return raw/decoded object payloads.

    Allegro's public format uses ``slh!`` for top-level LZSS-compressed
    packfiles and ``slh.`` for uncompressed packfiles. Password-protected
    Allegro 2.x old-crypt files encrypt the top-level magic and LZSS flag bytes
    with ``packfile_password()``. Pass ``packfile_password`` to enable that
    compatibility path. Some producers reset the old-crypt password stream for
    each object chunk; use ``old_crypt_chunk_local`` for those files.

    Every chunk must supply its declared decoded length; uncompressed chunks
    must have equal stored and decoded sizes. Incomplete objects are errors,
    not short placeholder payloads.
    """
    if len(data) < 12:
        raise AllegroDatafileError("Allegro DAT header is incomplete")

    raw_pack_magic = data[:4]
    password = _normalize_packfile_password(packfile_password)
    decoded_pack_magic, uses_old_crypt = _decode_packfile_magic(
        raw_pack_magic,
        accepted_pack_magics=accepted_pack_magics,
        password=password,
    )
    if old_crypt_chunk_local is None:
        old_crypt_chunk_local = False

    payload_is_compressed = decoded_pack_magic == ALLEGRO_F_PACK_MAGIC
    body = (
        allegro_lzss_decompress(
            data[4:],
            old_crypt_password=password if uses_old_crypt else None,
        )
        if payload_is_compressed
        else data[4:]
    )
    if len(body) < 8 or body[:4] != ALLEGRO_DAT_MAGIC:
        raise AllegroDatafileError("Missing Allegro DAT magic")

    old_crypt_state = _AllegroOldCryptState(
        password=password if uses_old_crypt else b"",
        chunk_local=old_crypt_chunk_local,
    )
    objects, offset = _parse_object_list(
        body,
        4,
        base_offset=4,
        parse_nested=parse_nested,
        old_crypt_state=old_crypt_state,
    )
    if offset != len(body):
        raise AllegroDatafileError("Trailing bytes after Allegro DAT object list")

    return AllegroDatafile(
        pack_magic=raw_pack_magic,
        objects=tuple(objects),
        payload_is_compressed=payload_is_compressed,
        decoded_pack_magic=decoded_pack_magic,
        uses_old_crypt=uses_old_crypt,
        packfile_password=password if uses_old_crypt else b"",
        old_crypt_chunk_local=old_crypt_chunk_local if uses_old_crypt else False,
    )


def parse_allegro_datafile_objects(
    data: bytes,
    *,
    accepted_pack_magics: tuple[bytes, ...] = ALLEGRO_SUPPORTED_PACK_MAGICS,
    parse_nested: bool = True,
    packfile_password: bytes | str | None = None,
    old_crypt_chunk_local: bool | None = None,
) -> list[AllegroDatafileObject]:
    """Parse a DAT file and return the root object list."""
    return list(
        parse_allegro_datafile(
            data,
            accepted_pack_magics=accepted_pack_magics,
            parse_nested=parse_nested,
            packfile_password=packfile_password,
            old_crypt_chunk_local=old_crypt_chunk_local,
        ).objects
    )


def iter_allegro_datafile_objects(
    objects: Iterable[AllegroDatafileObject],
    *,
    prefix: tuple[int, ...] = (),
) -> Iterator[tuple[tuple[int, ...], AllegroDatafileObject]]:
    """Yield root and nested objects with stable tuple paths."""
    for index, item in enumerate(objects):
        object_path = prefix + (index,)
        yield object_path, item
        if item.children:
            yield from iter_allegro_datafile_objects(item.children, prefix=object_path)


def iter_allegro_datafile_entries(
    datafile: AllegroDatafile,
    *,
    include_types: Iterable[str] | str | None = None,
) -> Iterator[AllegroDatafileEntry]:
    """Yield flattened entries for all matching objects in *datafile*."""
    type_filter = _normalize_type_filter(include_types)
    for object_path, item in iter_allegro_datafile_objects(datafile.objects):
        if type_filter is not None and item.type_id not in type_filter:
            continue
        yield _entry_from_object(object_path, item)


def extract_allegro_datafile_entries(
    data: bytes,
    *,
    include_types: Iterable[str] | str | None = None,
    accepted_pack_magics: tuple[bytes, ...] = ALLEGRO_SUPPORTED_PACK_MAGICS,
    parse_nested: bool = True,
    packfile_password: bytes | str | None = None,
    old_crypt_chunk_local: bool | None = None,
) -> list[AllegroDatafileEntry]:
    """Parse a DAT file and return flattened entries for matching objects."""
    datafile = parse_allegro_datafile(
        data,
        accepted_pack_magics=accepted_pack_magics,
        parse_nested=parse_nested,
        packfile_password=packfile_password,
        old_crypt_chunk_local=old_crypt_chunk_local,
    )
    return list(iter_allegro_datafile_entries(datafile, include_types=include_types))


def extract_allegro_data_objects(
    data: bytes,
    *,
    accepted_pack_magics: tuple[bytes, ...] = ALLEGRO_SUPPORTED_PACK_MAGICS,
    parse_nested: bool = True,
    packfile_password: bytes | str | None = None,
    old_crypt_chunk_local: bool | None = None,
) -> list[AllegroDatafileEntry]:
    """Parse a DAT file and return flattened DATA entries."""
    return extract_allegro_datafile_entries(
        data,
        include_types=(ALLEGRO_TYPE_DATA,),
        accepted_pack_magics=accepted_pack_magics,
        parse_nested=parse_nested,
        packfile_password=packfile_password,
        old_crypt_chunk_local=old_crypt_chunk_local,
    )


def allegro_lzss_decompress(
    payload: bytes,
    expected_size: int | None = None,
    *,
    old_crypt_password: bytes | str | None = None,
    password_position: int = 0,
) -> bytes:
    """Decompress Allegro's LZSS packfile stream.

    This follows the Allegro packfile algorithm: a 4096-byte ring buffer,
    initial write index 4078, LSB-first flags, literal tokens when a flag bit is
    set, otherwise a 12-bit back-reference plus a length nibble biased by 3. If
    ``old_crypt_password`` is supplied, only flag bytes are XOR-decoded like
    Allegro's ``PACKFILE_FLAG_OLD_CRYPT`` compatibility mode.
    """
    return _allegro_lzss_decompress(
        payload,
        expected_size,
        old_crypt_password=_normalize_packfile_password(old_crypt_password),
        password_position=password_position,
    )[0]


def _allegro_lzss_decompress(
    payload: bytes,
    expected_size: int | None = None,
    *,
    old_crypt_password: bytes = b"",
    password_position: int = 0,
) -> tuple[bytes, int]:
    """Return decompressed bytes and the updated old-crypt password position.
    """
    if expected_size is not None and expected_size < 0:
        raise AllegroDatafileError("Allegro decoded length must be nonnegative")
    if expected_size == 0:
        return b"", password_position

    window_size = 4096
    max_match = 18
    text_buf = bytearray(window_size + max_match - 1)
    write_pos = window_size - max_match
    flags = 0
    src = 0
    out = bytearray()

    def has_room() -> bool:
        return expected_size is None or len(out) < expected_size

    while src < len(payload) and has_room():
        flags >>= 1
        if (flags & 0x100) == 0:
            flag_byte = payload[src]
            src += 1
            if old_crypt_password:
                flag_byte ^= old_crypt_password[password_position]
                password_position = (password_position + 1) % len(old_crypt_password)
            flags = flag_byte | 0xFF00

        if flags & 1:
            if src >= len(payload):
                break
            value = payload[src]
            src += 1
            out.append(value)
            text_buf[write_pos] = value
            write_pos = (write_pos + 1) & (window_size - 1)
            continue

        if src + 1 >= len(payload):
            break
        index = payload[src]
        value = payload[src + 1]
        src += 2
        index |= (value & 0xF0) << 4
        length = (value & 0x0F) + 3
        for offset in range(length):
            copied = text_buf[(index + offset) & (window_size - 1)]
            out.append(copied)
            text_buf[write_pos] = copied
            write_pos = (write_pos + 1) & (window_size - 1)
            if not has_room():
                break

    if expected_size is not None and len(out) != expected_size:
        raise AllegroDatafileError(
            f"Allegro LZSS stream decoded to {len(out)} bytes, expected {expected_size}"
        )
    return bytes(out), password_position


def _normalize_type_filter(include_types: Iterable[str] | str | None) -> set[str] | None:
    if include_types is None:
        return None
    if isinstance(include_types, str):
        return {include_types}
    return set(include_types)


@dataclass(slots=True)
class _AllegroOldCryptState:
    password: bytes
    chunk_local: bool = False
    position: int = 0

    def chunk_start_position(self) -> int:
        if not self.password or self.chunk_local:
            return 0
        return self.position

    def finish_chunk(self, position: int) -> None:
        if self.password and not self.chunk_local:
            self.position = position % len(self.password)


def _normalize_packfile_password(password: bytes | str | None) -> bytes:
    if password is None:
        return b""
    if isinstance(password, bytes):
        return password[:255]
    return password.encode("latin-1")[:255]


def _allegro_old_crypt_file_magic(magic: bytes, password: bytes) -> bytes:
    # In old-crypt compatibility mode Allegro first XOR-decodes the first four
    # file bytes with the password stream, then compares that value with
    # encrypt_id(magic, FALSE). The password-stream part cancels out, so the raw
    # on-disk magic is the clear magic XOR the first encrypt_id() mask loop.
    old_mask = 0
    for index, value in enumerate(password):
        old_mask ^= value << ((index & 3) * 8)
    value = int.from_bytes(magic, "big") ^ (old_mask & 0xFFFFFFFF)
    return value.to_bytes(4, "big")


def _decode_packfile_magic(
    raw_magic: bytes,
    *,
    accepted_pack_magics: tuple[bytes, ...],
    password: bytes,
) -> tuple[bytes, bool]:
    if password:
        for magic in ALLEGRO_STANDARD_PACK_MAGICS:
            if raw_magic == _allegro_old_crypt_file_magic(magic, password):
                if raw_magic in accepted_pack_magics or magic in accepted_pack_magics:
                    return magic, True

    if raw_magic in accepted_pack_magics:
        return raw_magic, False

    raise AllegroDatafileError(f"Unsupported Allegro pack magic {raw_magic!r}")


def _entry_from_object(
    object_path: tuple[int, ...],
    item: AllegroDatafileObject,
) -> AllegroDatafileEntry:
    return AllegroDatafileEntry(
        object_path=object_path,
        type_id=item.type_id,
        properties=item.properties,
        name=decode_allegro_property(item.properties, "NAME"),
        date=decode_allegro_property(item.properties, "DATE"),
        origin=decode_allegro_property(item.properties, "ORIG"),
        stored_payload=item.packed_payload,
        decoded_payload=item.payload,
        stored_size=item.packed_size,
        decoded_size=len(item.payload),
        uncompressed_size=item.unpacked_size,
        object_offset=item.object_offset,
        payload_offset=item.payload_offset,
        payload_is_compressed=item.payload_is_compressed,
    )


def _parse_object_list(
    data: bytes,
    offset: int,
    *,
    base_offset: int,
    parse_nested: bool,
    old_crypt_state: _AllegroOldCryptState,
) -> tuple[list[AllegroDatafileObject], int]:
    if offset + 4 > len(data):
        raise AllegroDatafileError("Allegro object count is incomplete")

    object_count = int.from_bytes(data[offset:offset + 4], "big")
    offset += 4
    if object_count < 0 or object_count > max(1, len(data) // 12):
        raise AllegroDatafileError("Implausible Allegro object count")

    objects: list[AllegroDatafileObject] = []
    for _index in range(object_count):
        item, offset = _parse_object(
            data,
            offset,
            base_offset=base_offset,
            parse_nested=parse_nested,
            old_crypt_state=old_crypt_state,
        )
        objects.append(item)
    return objects, offset


def _parse_object(
    data: bytes,
    offset: int,
    *,
    base_offset: int,
    parse_nested: bool,
    old_crypt_state: _AllegroOldCryptState,
) -> tuple[AllegroDatafileObject, int]:
    object_offset = base_offset + offset
    properties: dict[str, bytes] = {}

    while data[offset:offset + len(ALLEGRO_PROPERTY_MAGIC)] == ALLEGRO_PROPERTY_MAGIC:
        if offset + 12 > len(data):
            raise AllegroDatafileError("Allegro property header is incomplete")
        property_id = data[offset + 4:offset + 8].decode("latin-1", errors="replace")
        property_size = int.from_bytes(data[offset + 8:offset + 12], "big")
        offset += 12
        property_end = offset + property_size
        if property_size < 0 or property_end > len(data):
            raise AllegroDatafileError("Allegro property points outside the file")
        properties[property_id] = data[offset:property_end]
        offset = property_end

    if offset + 12 > len(data):
        raise AllegroDatafileError("Allegro object header is incomplete")
    type_bytes = data[offset:offset + 4]
    offset += 4
    compressed_size = int.from_bytes(data[offset:offset + 4], "big", signed=True)
    offset += 4
    uncompressed_size = int.from_bytes(data[offset:offset + 4], "big", signed=True)
    offset += 4

    payload_offset = base_offset + offset
    payload_end = offset + compressed_size
    if compressed_size < 0 or payload_end > len(data):
        raise AllegroDatafileError("Allegro object payload points outside the file")

    packed_payload = data[offset:payload_end]
    offset = payload_end

    payload_is_compressed = uncompressed_size < 0
    if payload_is_compressed:
        payload, password_position = _allegro_lzss_decompress(
            packed_payload,
            -uncompressed_size,
            old_crypt_password=old_crypt_state.password,
            password_position=old_crypt_state.chunk_start_position(),
        )
        old_crypt_state.finish_chunk(password_position)
    else:
        payload = packed_payload
    if not payload_is_compressed and uncompressed_size != compressed_size:
        raise AllegroDatafileError(
            "Allegro uncompressed object has mismatched stored and decoded sizes"
        )
    children: tuple[AllegroDatafileObject, ...] = ()
    type_id = type_bytes.decode("latin-1", errors="replace")
    if parse_nested and type_id == ALLEGRO_TYPE_FILE:
        nested, nested_offset = _parse_object_list(
            payload,
            0,
            base_offset=0,
            parse_nested=parse_nested,
            old_crypt_state=old_crypt_state,
        )
        if nested_offset != len(payload):
            raise AllegroDatafileError("Trailing bytes after nested Allegro FILE object")
        children = tuple(nested)

    return (
        AllegroDatafileObject(
            type_id=type_id,
            properties=properties,
            payload=payload,
            packed_payload=packed_payload,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            object_offset=object_offset,
            payload_offset=payload_offset,
            payload_is_compressed=payload_is_compressed,
            children=children,
        ),
        offset,
    )
