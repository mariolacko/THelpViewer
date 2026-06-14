import gzip
import json
from pathlib import Path

from thelpviewer.converter.base import ContentNode, HelpDocument, IndexEntry, TopicRecord
from thelpviewer.converter.help_database import HelpDatabaseEntry, crc32_file
from thelpviewer.converter.writers import bundle as bundle_writer


def test_export_bundle_tree_prefers_tdh_candidate_with_more_topics(tmp_path, monkeypatch):
    legacy_source = Path("sources") / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_source = Path("sources") / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    assert legacy_source.exists(), f"Source TDH not found: {legacy_source}"
    assert later_source.exists(), f"Source TDH not found: {later_source}"

    input_root = tmp_path / "sources"
    legacy_copy = input_root / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_copy = input_root / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    legacy_copy.parent.mkdir(parents=True, exist_ok=True)
    later_copy.parent.mkdir(parents=True, exist_ok=True)
    legacy_copy.write_bytes(legacy_source.read_bytes())
    later_copy.write_bytes(later_source.read_bytes())

    lookup = {
        legacy_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(legacy_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
            text_encoding="cp437",
            help_contents_topic_id=1,
        ),
        later_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(later_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
        ),
    }

    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(
        bundle_writer,
        "lookup_help_database_entry",
        lambda path, _database: lookup[Path(path).resolve()],
    )

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert len(results) == 1
    result = results[0]
    assert result.input_path == later_copy
    assert result.topic_count == 596
    assert result.json_path == output_dir / "Borland Turbo Debugger/Profiler/Assembler" / "tdhelp.json.gz"

    payload = json.loads(gzip.decompress(result.json_path.read_bytes()).decode("utf-8"))
    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) == 596

    catalog = json.loads((output_dir / "catalog.json").read_text(encoding="utf-8"))
    assert catalog == [
        {
            "group": "Borland Turbo Debugger/Profiler/Assembler",
            "file": "Borland Turbo Debugger/Profiler/Assembler/tdhelp.json.gz",
            "source_file": "TDHELP.TDH",
            "source_files": ["TDHELP.TDH"],
            "name": "Turbo Debugger Help",
            "format": "borland",
            "topics": 596,
        }
    ]


def test_export_bundle_tree_uses_versioned_bundle_stems_for_tdh_variants(tmp_path, monkeypatch):
    legacy_source = Path("sources") / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_source = Path("sources") / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    assert legacy_source.exists(), f"Source TDH not found: {legacy_source}"
    assert later_source.exists(), f"Source TDH not found: {later_source}"

    input_root = tmp_path / "sources"
    legacy_copy = input_root / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_copy = input_root / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    legacy_copy.parent.mkdir(parents=True, exist_ok=True)
    later_copy.parent.mkdir(parents=True, exist_ok=True)
    legacy_copy.write_bytes(legacy_source.read_bytes())
    later_copy.write_bytes(later_source.read_bytes())

    lookup = {
        legacy_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(legacy_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
            bundle_stem="tdhelp-1.0",
            text_encoding="cp437",
            help_contents_topic_id=1,
        ),
        later_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(later_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
            bundle_stem="tdhelp-2.x",
        ),
    }

    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(
        bundle_writer,
        "lookup_help_database_entry",
        lambda path, _database: lookup[Path(path).resolve()],
    )

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert len(results) == 2

    result_by_name = {result.json_path.name: result for result in results}
    assert set(result_by_name) == {"tdhelp-1.0.json.gz", "tdhelp-2.x.json.gz"}
    assert result_by_name["tdhelp-1.0.json.gz"].topic_count == 530
    assert result_by_name["tdhelp-2.x.json.gz"].topic_count == 596

    catalog = json.loads((output_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog_by_file = {item["file"]: item for item in catalog}
    assert set(catalog_by_file) == {
        "Borland Turbo Debugger/Profiler/Assembler/tdhelp-1.0.json.gz",
        "Borland Turbo Debugger/Profiler/Assembler/tdhelp-2.x.json.gz",
    }
    assert catalog_by_file["Borland Turbo Debugger/Profiler/Assembler/tdhelp-1.0.json.gz"]["topics"] == 530
    assert catalog_by_file["Borland Turbo Debugger/Profiler/Assembler/tdhelp-2.x.json.gz"]["topics"] == 596


def test_export_bundle_tree_splits_scorpion_v3_sections(tmp_path, monkeypatch):
    input_root = tmp_path / "sources"
    source = input_root / "Scorpions Cheater 3" / "CHEATER.DAT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic")

    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name="CHEATER.DAT",
        topics=[
            TopicRecord(
                context_id=0x100001,
                raw_lines=[b"Manual"],
                index_terms=[b"Manual"],
                alias_strings=["manuals"],
                names=["Manual"],
                uhf_content=["Manual"],
            ),
            TopicRecord(
                context_id=1,
                raw_lines=[b"Cheat"],
                index_terms=[b"Cheat"],
                alias_strings=["cheats"],
                names=["Cheat"],
                uhf_content=["Cheat"],
            ),
            TopicRecord(
                context_id=0x200001,
                raw_lines=[b"Joke"],
                index_terms=[b"Joke"],
                alias_strings=["jokes"],
                names=["Joke"],
                uhf_content=["Joke"],
            ),
        ],
        index_entries=[
            IndexEntry(label=b"Manual", context_id=0x100001),
            IndexEntry(label=b"Cheat", context_id=1),
            IndexEntry(label=b"Joke", context_id=0x200001),
        ],
        metadata={
            "title": "Scorpions Cheater 3 - CHEATER.DAT",
            "text_encoding": "kamenicky",
            "scorpion_parser": "v3-rar-member-topics",
        },
    )

    monkeypatch.setattr(bundle_writer, "iter_help_files", lambda _root: [source])
    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(bundle_writer, "lookup_help_database_entry", lambda _path, _database: None)
    monkeypatch.setattr(bundle_writer, "load_document", lambda _path: document)
    monkeypatch.setattr(bundle_writer, "select_display_encoding", lambda *_args, **_kwargs: "utf-8")
    monkeypatch.setattr(bundle_writer, "fix_metadata_encoding", lambda *_args, **_kwargs: None)

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert {result.json_path.name for result in results} == {
        "navody.json.gz",
        "cheaty.json.gz",
        "vtipy.json.gz",
    }
    assert not (output_dir / "Scorpions Cheater 3" / "cheater.json.gz").exists()

    catalog = json.loads((output_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog_by_file = {item["file"]: item for item in catalog}
    assert set(catalog_by_file) == {
        "Scorpions Cheater 3/navody.json.gz",
        "Scorpions Cheater 3/cheaty.json.gz",
        "Scorpions Cheater 3/vtipy.json.gz",
    }
    assert catalog_by_file["Scorpions Cheater 3/navody.json.gz"]["topics"] == 1
    assert catalog_by_file["Scorpions Cheater 3/cheaty.json.gz"]["topics"] == 1
    assert catalog_by_file["Scorpions Cheater 3/vtipy.json.gz"]["topics"] == 1
    assert catalog_by_file["Scorpions Cheater 3/navody.json.gz"]["name"] == "Scorpions Cheater 3 - Návody"
    assert catalog_by_file["Scorpions Cheater 3/cheaty.json.gz"]["name"] == "Scorpions Cheater 3 - Cheaty"
    assert catalog_by_file["Scorpions Cheater 3/vtipy.json.gz"]["name"] == "Scorpions Cheater 3 - Vtipy"


def test_export_bundle_tree_merges_scorpion_sco_data_files_into_cheats(tmp_path, monkeypatch):
    input_root = tmp_path / "sources"
    group_dir = input_root / "Scorpions Cheater 4"
    data1 = group_dir / "DATA1.SCO"
    data2 = group_dir / "DATA2.SCO"
    dataa = group_dir / "DATAA.SCO"
    group_dir.mkdir(parents=True)
    data1.write_bytes(b"data1")
    data2.write_bytes(b"data2")
    dataa.write_bytes(b"index")

    def scorpion_data_document(source_name: str, marker: str, title: str) -> HelpDocument:
        return HelpDocument(
            format_name="scorpion-legacy",
            source_name=source_name,
            topics=[
                TopicRecord(
                    context_id=1,
                    raw_lines=[title.encode("utf-8")],
                    index_terms=[title.encode("utf-8")],
                    alias_strings=["cheats", marker, source_name],
                    names=[title],
                    uhf_content=[title],
                )
            ],
            index_entries=[IndexEntry(label=title.encode("utf-8"), context_id=1)],
            contents=[ContentNode(label=title, topic_id=1)],
            metadata={
                "title": f"Scorpions Cheater 4 - {source_name}",
                "text_encoding": "utf-8",
                "scorpion_parser": "v4-sco-huffman",
                "scorpion_sco_role": "cheats",
                "scorpion_sco_marker_topic_count": 1,
            },
        )

    documents = {
        data1: scorpion_data_document("DATA1.SCO", "0001", "First cheat"),
        data2: scorpion_data_document("DATA2.SCO", "0002", "Second cheat"),
        dataa: HelpDocument(
            format_name="scorpion-legacy",
            source_name="DATAA.SCO",
            topics=[
                TopicRecord(
                    context_id=0,
                    raw_lines=[
                        b"Index",
                        b"Indexed first cheat,[0001]-r",
                        b"Program \xae,[R001]\xaf-",
                    ],
                    index_terms=[b"Index"],
                    names=["Index cheatů"],
                    uhf_content=[
                        "Index",
                        "Indexed first cheat,[[0001]-r",
                        "Program «,[[R001]»-",
                    ],
                )
            ],
            index_entries=[IndexEntry(label=b"Index", context_id=0)],
            metadata={
                "title": "Scorpions Cheater 4 - Index cheatů",
                "text_encoding": "utf-8",
                "scorpion_parser": "v4-sco-huffman",
                "scorpion_sco_role": "cheat-index",
                "scorpion_sco_index_entries": [
                    {
                        "kind": "entry",
                        "target_id": "0001",
                        "label": "Indexed first cheat",
                        "flag": "-",
                        "status": "plain",
                    },
                    {
                        "kind": "entry",
                        "target_id": "0002",
                        "label": "Indexed second cheat",
                        "flag": "!",
                        "status": "supplement",
                    },
                ],
            },
        ),
    }

    monkeypatch.setattr(bundle_writer, "iter_help_files", lambda _root: [data1, data2, dataa])
    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(bundle_writer, "lookup_help_database_entry", lambda _path, _database: None)
    monkeypatch.setattr(bundle_writer, "load_document", lambda path: documents[Path(path)])
    monkeypatch.setattr(bundle_writer, "select_display_encoding", lambda *_args, **_kwargs: "utf-8")
    monkeypatch.setattr(bundle_writer, "fix_metadata_encoding", lambda *_args, **_kwargs: None)

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert {result.json_path.name for result in results} == {"cheaty.json.gz"}
    assert not (output_dir / "Scorpions Cheater 4" / "data1.json.gz").exists()
    assert not (output_dir / "Scorpions Cheater 4" / "data2.json.gz").exists()
    assert not (output_dir / "Scorpions Cheater 4" / "dataa.json.gz").exists()

    payload = json.loads(
        gzip.decompress((output_dir / "Scorpions Cheater 4" / "cheaty.json.gz").read_bytes()).decode("utf-8")
    )
    assert payload["metadata"]["name"] == "Scorpions Cheater 4 - Cheaty"
    assert payload["metadata"]["scorpion_sco_role"] == "cheats"
    assert payload["metadata"]["scorpion_sco_merged_category"] == "cheats"
    assert payload["metadata"]["scorpion_sco_source_files"] == ["DATAA.SCO", "DATA1.SCO", "DATA2.SCO"]
    assert payload["metadata"]["scorpion_sco_index_status_counts"] == {"plain": 1, "supplement": 1}
    assert payload["metadata"]["scorpion_sco_index_flag_counts"] == {"-": 1, "!": 1}
    assert [topic["title"] for topic in payload["topics"].values()] == [
        "Index cheatů",
        "Indexed first cheat",
        "Indexed second cheat",
    ]
    assert "[link:topic=1]Indexed first cheat,[[0001]-r[/link]" in payload["topics"]["0"]["content"]
    assert (
        "[link:file=Scorpions Cheater 4/program.json.gz,alias=R001]Program «,[[R001]»-[/link]"
        in payload["topics"]["0"]["content"]
    )

    catalog = json.loads((output_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog_by_file = {item["file"]: item for item in catalog}
    assert set(catalog_by_file) == {"Scorpions Cheater 4/cheaty.json.gz"}
    assert catalog_by_file["Scorpions Cheater 4/cheaty.json.gz"]["source_files"] == [
        "DATAA.SCO",
        "DATA1.SCO",
        "DATA2.SCO",
    ]
    assert catalog_by_file["Scorpions Cheater 4/cheaty.json.gz"]["topics"] == 3


def test_export_bundle_tree_merges_scorpion_scd_data_files_into_cheats(tmp_path, monkeypatch):
    input_root = tmp_path / "sources"
    group_dir = input_root / "Scorpions Cheater 6 _shareware_"
    data1 = group_dir / "DATA1.SCD"
    data2 = group_dir / "DATA2.SCD"
    group_dir.mkdir(parents=True)
    data1.write_bytes(b"data1")
    data2.write_bytes(b"data2")

    def scorpion_data_document(source_name: str, marker: str, title: str) -> HelpDocument:
        return HelpDocument(
            format_name="scorpion-legacy",
            source_name=source_name,
            topics=[
                TopicRecord(
                    context_id=1,
                    raw_lines=[title.encode("utf-8")],
                    index_terms=[title.encode("utf-8")],
                    alias_strings=["cheats", marker, source_name],
                    names=[title],
                    uhf_content=[title],
                )
            ],
            index_entries=[IndexEntry(label=title.encode("utf-8"), context_id=1)],
            contents=[ContentNode(label=title, topic_id=1)],
            metadata={
                "title": f"Scorpions Cheater 6 - {source_name}",
                "text_encoding": "utf-8",
                "scorpion_parser": "sco-lzhuf",
                "scorpion_sco_role": "cheats",
                "scorpion_sco_marker_topic_count": 1,
            },
        )

    documents = {
        data1: scorpion_data_document("DATA1.SCD", "0001", "First SCD cheat"),
        data2: scorpion_data_document("DATA2.SCD", "0002", "Second SCD cheat"),
    }

    monkeypatch.setattr(bundle_writer, "iter_help_files", lambda _root: [data1, data2])
    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(bundle_writer, "lookup_help_database_entry", lambda _path, _database: None)
    monkeypatch.setattr(bundle_writer, "load_document", lambda path: documents[Path(path)])
    monkeypatch.setattr(bundle_writer, "select_display_encoding", lambda *_args, **_kwargs: "utf-8")
    monkeypatch.setattr(bundle_writer, "fix_metadata_encoding", lambda *_args, **_kwargs: None)

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert {result.json_path.name for result in results} == {"cheaty.json.gz"}
    assert not (output_dir / "Scorpions Cheater 6 _shareware_" / "data1.json.gz").exists()
    assert not (output_dir / "Scorpions Cheater 6 _shareware_" / "data2.json.gz").exists()

    payload = json.loads(
        gzip.decompress((output_dir / "Scorpions Cheater 6 _shareware_" / "cheaty.json.gz").read_bytes()).decode("utf-8")
    )
    assert payload["metadata"]["scorpion_sco_source_files"] == ["DATA1.SCD", "DATA2.SCD"]
    assert [topic["title"] for topic in payload["topics"].values()] == ["First SCD cheat", "Second SCD cheat"]


def test_export_bundle_tree_merges_scorpion_navody_files_and_uses_index_titles(tmp_path, monkeypatch):
    input_root = tmp_path / "sources"
    group_dir = input_root / "Scorpions Cheater 12"
    navody2 = group_dir / "NAVODY2.SCO"
    navody3 = group_dir / "NAVODY3.SCO"
    navody4 = group_dir / "NAVODY4.SCO"
    group_dir.mkdir(parents=True)
    navody2.write_bytes(b"navody2")
    navody3.write_bytes(b"navody3")
    navody4.write_bytes(b"navody4")

    def manual_document(source_name: str, marker: str, title: str, *, with_index: bool = False) -> HelpDocument:
        topics = []
        if with_index:
            topics.append(
                TopicRecord(
                    context_id=0,
                    raw_lines=[
                        b"Index",
                        b"Indexed first manual,[N001]-",
                        b"Indexed second manual,[N030]-",
                        b"Indexed third manual,[NA40]-r",
                    ],
                    index_terms=[b"Index"],
                    alias_strings=["12", source_name, "manual-index"],
                    names=["Index návodů"],
                    uhf_content=[
                        "Index",
                        "Indexed first manual,[[N001]-",
                        "Indexed second manual,[[N030]-",
                        "Indexed third manual,[[NA40]-r",
                    ],
                )
            )
        topics.append(
            TopicRecord(
                context_id=1,
                raw_lines=[title.encode("utf-8")],
                index_terms=[title.encode("utf-8")],
                alias_strings=["manuals", marker, source_name],
                names=[title],
                uhf_content=[title],
            )
        )
        metadata = {
            "title": f"Scorpions Cheater 12 - {source_name}",
            "text_encoding": "utf-8",
            "scorpion_parser": "sco-lzhuf",
            "scorpion_sco_role": "manuals",
            "scorpion_sco_marker_topic_count": 1,
        }
        if with_index:
            metadata["scorpion_sco_index_entries"] = [
                {"kind": "entry", "target_id": "N001", "label": "Indexed first manual"},
                {"kind": "entry", "target_id": "N030", "label": "Indexed second manual"},
                {"kind": "entry", "target_id": "NA40", "label": "Indexed third manual"},
            ]
        return HelpDocument(
            format_name="scorpion-legacy",
            source_name=source_name,
            topics=topics,
            index_entries=[IndexEntry(label=topic.index_terms[0], context_id=topic.context_id) for topic in topics],
            contents=[ContentNode(label=title, topic_id=1)],
            metadata=metadata,
        )

    documents = {
        navody2: manual_document("NAVODY2.SCO", "N001", "Raw first manual", with_index=True),
        navody3: manual_document("NAVODY3.SCO", "N030", "Raw second manual"),
        navody4: manual_document("NAVODY4.SCO", "NA40", "Raw third manual"),
    }

    monkeypatch.setattr(bundle_writer, "iter_help_files", lambda _root: [navody4, navody2, navody3])
    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(bundle_writer, "lookup_help_database_entry", lambda _path, _database: None)
    monkeypatch.setattr(bundle_writer, "load_document", lambda path: documents[Path(path)])
    monkeypatch.setattr(bundle_writer, "select_display_encoding", lambda *_args, **_kwargs: "utf-8")
    monkeypatch.setattr(bundle_writer, "fix_metadata_encoding", lambda *_args, **_kwargs: None)

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert {result.json_path.name for result in results} == {"navody.json.gz"}
    assert not (output_dir / "Scorpions Cheater 12" / "navody2.json.gz").exists()
    assert not (output_dir / "Scorpions Cheater 12" / "navody3.json.gz").exists()
    assert not (output_dir / "Scorpions Cheater 12" / "navody4.json.gz").exists()

    payload = json.loads(
        gzip.decompress((output_dir / "Scorpions Cheater 12" / "navody.json.gz").read_bytes()).decode("utf-8")
    )
    assert payload["metadata"]["scorpion_sco_role"] == "manuals"
    assert payload["metadata"]["scorpion_sco_merged_category"] == "manuals"
    assert payload["metadata"]["scorpion_sco_source_files"] == [
        "NAVODY2.SCO",
        "NAVODY3.SCO",
        "NAVODY4.SCO",
    ]
    assert [topic["title"] for topic in payload["topics"].values()] == [
        "Index návodů",
        "Indexed first manual",
        "Indexed second manual",
        "Indexed third manual",
    ]
    assert "[link:topic=3]Indexed third manual,[[NA40]-r[/link]" in payload["topics"]["0"]["content"]
