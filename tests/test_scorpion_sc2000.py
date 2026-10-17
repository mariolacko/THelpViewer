"""Source-scoped SC 2000 catalog links, without guessed prose pagination."""

from dataclasses import replace
import hashlib
from pathlib import Path
import re

import pytest

from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.scorpion_dat_parser import (
    SCORPION_DAT_SIGNATURE, find_scorpion_article_markers, parse_scorpion_dat_records,
)
from thelpviewer.server.converter.readers.scorpion_dat_reader import (
    ScorpionDatReader, is_scorpion_dat_help_binary,
)
from thelpviewer.server.converter.readers.scorpion_sc2000 import (
    catalog_topic, is_sc2000_catalog, is_sc2000_prose,
)
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


SOURCE = Path("var/sources/Scorpions Cheater DOS/Scorpions Cheater 21/TEXTY.DAT")


def _record(payload):
    original = next(r for r in parse_scorpion_dat_records(SOURCE.read_bytes()) if r.name == "txt")
    return replace(original, payload=payload, decoded_payload=payload)


def _datafile(*records):
    objects = []
    for name, payload in records:
        size = len(payload).to_bytes(4, "big")
        objects.append(b"propNAME" + len(name).to_bytes(4, "big") + name
                       + b"DATA" + size + size + payload)
    return SCORPION_DAT_SIGNATURE + len(objects).to_bytes(4, "big") + b"".join(objects)


@pytest.mark.parametrize("prefix", [b"<!K=1>", b"<!K=3>"])
def test_sc2000_prose_cannot_be_reclassified_by_quoted_dos_markers(prefix):
    prose = prefix + b"<!M=1>Title<!M!>\r\n[R010]\r\nNot a DOS article\xfeStill raw\xfe"
    source = _datafile((b"renamed-prose", prose))
    record = parse_scorpion_dat_records(source)[0]
    assert is_sc2000_prose(record)
    assert record.payload == prose  # Container boundaries, not text terminators.
    assert not is_scorpion_dat_help_binary(source)
    with pytest.raises(ValueError, match="no readable articles"):
        ScorpionDatReader(source_name="TEXTY.DAT", source_path=SOURCE).read_bytes(source)

    catalog = b"<<<< Seznam pro SC 2000 >>>>\r\n#Game\r\n--,0,1,*,[0070],\r\n\xfe"
    combined = _datafile((b"renamed-prose", prose), (b"txt", catalog),
                         (b"dos-article", b"[R010]\r\nReal DOS article\r\nText"))
    assert is_scorpion_dat_help_binary(combined)
    document = ScorpionDatReader(source_name="TEXTY.DAT", source_path=SOURCE).read_bytes(combined)
    assert [topic.names[0] for topic in document.topics] == ["Seznam pro SC 2000", "Real DOS article"]
    assert document.metadata["scorpion_unconverted_record_names"] == ["renamed-prose"]
    assert document.metadata["scorpion_resource_record_names"] == []
    assert all("renamed-prose" not in topic.alias_strings for topic in document.topics)


@pytest.mark.parametrize("name,size,digest", [
    ("kontakt", 836, "95f7c860fa9de20cbb1f54768b6fbd2e4e3089319ec630b2d9a6508ec4b86948"),
    ("novezpra", 13990, "e45af00c5f8f9e2d43f754c0012b6a8f16b2c69902a691ecb8e763d2b6e5a9f3"),
    ("oprogramu", 6516, "c754b9691c74c70c75fdd30148c99574e4ec0a0fb10483fbd328dd124863c65a"),
    ("spoluaut", 1593, "ff75220f8fe5c44f1dd9ea8360aa97e0adf2b6600edacaadfbde8eb504411647"),
])
def test_installed_prose_retains_complete_raw_objects_without_encoding_or_fe_guesses(name, size, digest):
    record = next(r for r in parse_scorpion_dat_records(SOURCE.read_bytes()) if r.name == name)
    assert is_sc2000_prose(record)
    assert len(record.payload) == record.decoded_size == size
    assert record.uncompressed_size == -size  # Allegro marks compressed chunks with a signed length.
    assert hashlib.sha256(record.payload).hexdigest() == digest
    assert record.payload == record.decoded_payload
    if name == "spoluaut":
        assert record.payload[20] == 0xF8  # Native source byte; not a guessed DOS degree glyph.
        assert record.payload[665:672] == b"\xfesp\xb0\x9an\xb0"
        assert record.payload[-1:] == b"\xfe" and record.payload.count(b"\xfe") == 2
        assert b"CH2000" in record.payload[666:]  # Do not clip at the in-word FE.
    if name == "novezpra":
        assert b"< !J=1>" in record.payload and b"<!J=1>" not in record.payload


def test_catalog_keeps_source_fields_and_uses_existing_line_cursor_navigation():
    raw = (b"<<<< Seznam pro SC 2000 >>>>\r\n\r\n"
           b"#Carnage, Inc.\r\n--,0,1,*,[0070],\r\n"
           b"#Other game\r\n-!,Carnage, Inc.\r\n"
           b"-*,1,4,0029-05,trainer,zip,\r\n"
           b"--,1,H,0030-07,hints,txt,\r\n\xfe\xfe\r\n")
    topic, index, contents = catalog_topic(_record(raw), SOURCE, 7)
    assert len(topic.raw_lines) == 8
    assert topic.raw_lines[2] == b"#Carnage, Inc."
    assert topic.uhf_content[3] == (
        "--,0,1,*,[link:file=Scorpions Cheater 21/cheaty.json.gz,alias=0070][[0070][/link],"
    )
    # A comma-bearing title is not padded into a malformed item descriptor.
    # Only the established two-field reference form is linked.
    assert topic.uhf_content[5] == "-!,Carnage, Inc."
    assert topic.uhf_content[6:] == ["-*,1,4,0029-05,trainer,zip,", "--,1,H,0030-07,hints,txt,"]
    assert [(e.label, e.context_id, e.line) for e in index[1:]] == [
        (b"Carnage, Inc.", 7, 3), (b"Other game", 7, 5),
    ]
    assert [(c.label, c.topic_id, c.line) for c in contents] == [
        ("Carnage, Inc.", 7, 3), ("Other game", 7, 5),
    ]


def test_title_reference_cannot_choose_between_duplicate_titles_or_guess_a_missing_one():
    raw = (b"<<<< Seznam pro SC 2000 >>>>\n#A\n--,0,1,*,[A001],\n"
           b"#B\n-!,A\n-!,Missing\n#Duplicate\n#Duplicate\n-!,Duplicate\n"
           b"--,0,2,*,[A001],\n--,0,1,0029-01,[A001],\n")
    topic, _, _ = catalog_topic(_record(raw), SOURCE, 0)
    assert topic.uhf_content[4] == "-!,[link:topic=0,line=2]A[/link]"
    assert topic.uhf_content[5] == "-!,Missing"
    assert topic.uhf_content[8] == "-!,Duplicate"
    assert "[link:" not in topic.uhf_content[9]  # Different source type.
    assert "[link:" not in topic.uhf_content[10]  # Different resource address.


def test_catalog_detection_does_not_mistake_prose_or_arbitrary_comma_text_for_articles():
    assert not is_sc2000_catalog(_record(b"<!K=1><!M=1>Kontakt<!M!>"))
    assert not is_sc2000_catalog(_record(b"#Title\n--,0,1,*,[A001],"))
    with pytest.raises(ValueError, match="Not an SC 2000"):
        catalog_topic(_record(b"#Title"), SOURCE, 0)


def test_installed_catalog_all_real_cheat_links_and_redirects_have_their_scoped_targets():
    document = load_document(SOURCE)
    assert len(document.topics) == 1
    assert document.metadata["source_text_encoding"] == "cp1250"
    assert document.metadata["scorpion_resource_record_names"] == []
    assert document.metadata["scorpion_unconverted_record_names"] == [
        "kontakt", "novezpra", "oprogramu", "spoluaut",
    ]
    topic = document.topics[0]
    assert not any("<!" in row for row in topic.uhf_content)
    # There are 2,349 physical # rows, including two distinct Die Hard 2
    # entries (2,348 unique captions). Their different line targets survive.
    assert len(document.index_entries) == 2350
    assert len(document.contents[0].children) == 2350
    assert b"Bust a Move 2" in topic.raw_lines  # Original unmarked row stays intact.
    assert "Návod" in "\n".join(row.decode("utf-8") for row in topic.raw_lines)
    aliases = {m.tag for r in parse_scorpion_dat_records(SOURCE.with_name("CHEATY.DAT").read_bytes())
               for m in find_scorpion_article_markers(r.payload)}
    links = re.findall(r"\[link:file=Scorpions Cheater 21/cheaty.json.gz,alias=([A-Z0-9]{4})\]",
                       "\n".join(topic.uhf_content))
    assert len(links) == 1800 and set(links) <= aliases
    short = re.findall(r"\[link:topic=0,line=(\d+)\](.*?)\[/link\]", "\n".join(topic.uhf_content))
    assert len(short) == 6
    assert all(topic.raw_lines[int(line) - 1].decode("utf-8") == "#" + label for line, label in short)
    payload = HelpJsonRenderer(document, "utf-8").render_document()
    assert payload["topics"]["0"]["content"] == topic.uhf_content
    entries = [e for group in payload["index"] for e in group["entries"]]
    assert len(entries) == 2350
    duplicate = [e for e in entries if e["label"] == "Die Hard 2"]
    assert len(duplicate) == 2 and duplicate[0]["line"] != duplicate[1]["line"]
    assert payload["metadata"]["scorpion_unconverted_record_names"] == document.metadata["scorpion_unconverted_record_names"]
