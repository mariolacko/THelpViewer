"""Bounded MIDI container extraction; retain only the Standard MIDI payload."""


def standard_midi(data: bytes, *, limit: int) -> bytes:
    if len(data) > limit:
        raise ValueError("MIDI file exceeds its size limit")
    counted = False
    if data.startswith(b"RIFF"):
        if len(data) < 12 or data[8:12] != b"RMID":
            raise ValueError("RIFF file is not an RMID music container")
        end = 8 + int.from_bytes(data[4:8], "little")
        if end != len(data):
            raise ValueError("RIFF/RMID container length does not match the file")
        payload = None
        position = 12
        while position < end:
            if position + 8 > end:
                raise ValueError("Truncated RIFF/RMID chunk header")
            kind = data[position:position + 4]
            size = int.from_bytes(data[position + 4:position + 8], "little")
            start = position + 8
            position = start + size + (size & 1)
            if position > end:
                raise ValueError("RIFF/RMID chunk exceeds its container")
            if kind == b"data":
                if payload is not None:
                    raise ValueError("RIFF/RMID contains more than one MIDI data chunk")
                payload = data[start:start + size]
        if payload is None:
            raise ValueError("RIFF/RMID contains no MIDI data chunk")
        data = payload
    elif data[2:6] == b"MThd":
        # Counted DOS payload: the leading little-endian word bounds the SMF.
        # A trailer is not part of the MIDI; the original archive is unchanged.
        size = int.from_bytes(data[:2], "little")
        if size < 14 or size + 2 > len(data):
            raise ValueError("Counted MIDI payload length exceeds the file")
        data = data[2:2 + size]
        counted = True

    if len(data) < 14 or data[:4] != b"MThd":
        try:
            text = data.decode("utf-8-sig").rstrip("\x1a\r\n\t ")
        except UnicodeDecodeError:
            text = ""
        if text and all(char.isprintable() or char in "\r\n\t" for char in text):
            raise ValueError("File is not Standard MIDI: source contains plain text instead of MIDI bytes")
        raise ValueError("File is not Standard MIDI or a supported MIDI container")
    header_size = int.from_bytes(data[4:8], "big")
    format_number = int.from_bytes(data[8:10], "big")
    expected_tracks = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    if (header_size < 6 or header_size + 8 > len(data) or format_number not in (0, 1, 2)
            or not expected_tracks or not division or (format_number == 0 and expected_tracks != 1)):
        raise ValueError("Invalid Standard MIDI header")
    position = 8 + header_size
    tracks = 0
    while tracks < expected_tracks:
        if position + 8 > len(data):
            raise ValueError("Truncated Standard MIDI chunk header")
        kind = data[position:position + 4]
        size = int.from_bytes(data[position + 4:position + 8], "big")
        position += 8 + size
        if position > len(data):
            raise ValueError("Standard MIDI chunk exceeds the payload")
        if kind == b"MTrk":
            tracks += 1
    if data[position:position + 4] == b"MTrk":
        raise ValueError("Standard MIDI track count does not match its header")
    if counted and position != len(data):
        raise ValueError("Counted MIDI length does not match its track boundaries")
    # DOS source records may append metadata after the complete declared SMF.
    return data[:position]
