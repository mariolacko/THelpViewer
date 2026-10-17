"""Structural validation of generated UHF before catalogue publication."""

import gzip
import json

from .results import ConversionError


def load_bundle(path):
    try:
        payload = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    except (OSError, EOFError, ValueError) as error:
        raise ConversionError(f"Invalid UHF bundle {path.name}: {error}") from error
    if (not isinstance(payload, dict) or payload.get("uhf_version") != "2.0"
            or not isinstance(payload.get("metadata"), dict)
            or not isinstance(payload.get("topics"), dict)
            or not isinstance(payload.get("contents"), list)
            or not isinstance(payload.get("index"), list)):
        raise ConversionError(f"Invalid UHF structure: {path.name}")
    for ident, topic in payload["topics"].items():
        if (not isinstance(topic, dict) or str(topic.get("id")) != ident
                or not isinstance(topic.get("content"), list)
                or any(not isinstance(line, str) for line in topic["content"])):
            raise ConversionError(f"Invalid UHF topic {ident}: {path.name}")
    return payload
