"""MIDI payload boundaries and safe extraction from source containers."""

import pytest

from thelpviewer.server.midi.format import standard_midi

MIDI = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60MTrk\x00\x00\x00\x04\x00\xff\x2f\x00"


def chunk(kind, data):
    return kind + len(data).to_bytes(4, "little") + data + (b"\0" if len(data) & 1 else b"")


def rmid(*chunks):
    data = b"RMID" + b"".join(chunks)
    return b"RIFF" + len(data).to_bytes(4, "little") + data


@pytest.mark.parametrize("data", [MIDI, rmid(chunk(b"data", MIDI)),
    rmid(chunk(b"JUNK", b"odd"), chunk(b"data", MIDI), chunk(b"LIST", b"INFO")),
    len(MIDI).to_bytes(2, "little") + MIDI,
    len(MIDI).to_bytes(2, "little") + MIDI + b"opaque DOS metadata",
    MIDI + b"opaque DOS metadata"])
def test_supported_containers_return_only_the_standard_midi(data):
    assert standard_midi(data, limit=1024) == MIDI


@pytest.mark.parametrize("data", [b"", b"MThd", b"<html>not music</html>", b"(2/60)\r\n(2/4,3/104)",
    b"RIFF" + (4).to_bytes(4, "little") + b"WAVE", rmid(),
    rmid(chunk(b"data", b"not a MIDI")), rmid(chunk(b"data", MIDI), chunk(b"data", MIDI)),
    rmid(chunk(b"data", MIDI))[:-1], rmid(b"data" + (100).to_bytes(4, "little") + MIDI),
    rmid(b"JUNK"), rmid(b"JUNK" + (1).to_bytes(4, "little") + b"x"),
    (100).to_bytes(2, "little") + MIDI, (1).to_bytes(2, "little") + MIDI,
    (len(MIDI) + 3).to_bytes(2, "little") + MIDI + b"bad",
    MIDI[:4] + (100).to_bytes(4, "big") + MIDI[8:],
    MIDI[:8] + b"\0\3" + MIDI[10:], MIDI[:10] + b"\0\0" + MIDI[12:],
    MIDI[:12] + b"\0\0" + MIDI[14:], MIDI[:-1], MIDI + MIDI[14:],
    MIDI[:8] + b"\0\1\0\2" + MIDI[12:],
])
def test_invalid_or_truncated_payloads_are_not_published(data):
    with pytest.raises(ValueError):
        standard_midi(data, limit=1024)


def test_size_limits_include_the_container():
    with pytest.raises(ValueError, match="size limit"):
        standard_midi(rmid(chunk(b"data", MIDI)), limit=len(MIDI))


def test_midi_chunk_lengths_are_big_endian_without_riff_word_padding():
    track = b"\0\xff\x01\x01X\0\xff\x2f\0"
    midi = MIDI[:14] + b"MTrk" + len(track).to_bytes(4, "big") + track
    assert len(track) & 1
    assert standard_midi(rmid(chunk(b"data", midi)), limit=1024) == midi
