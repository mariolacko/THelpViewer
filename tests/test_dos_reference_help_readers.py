"""HelpPC and FreeDOS HTML import behaviour."""

import gzip
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile

import pytest

from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.readers.freedos_html import FreeDOSHtmlReader, _PageParser
from thelpviewer.server.converter.readers.helppc import HelpPCReader
from thelpviewer.server.converter.uhf_markup import parse_uhf_link_target
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.help_database import load_help_database, lookup_help_database_entry


def test_helppc_exports_separate_databases_with_cross_file_links(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "ASM.TXT").write_bytes(b"@Assembly\r\n:first:alias\r\n^First\r\n See ~second~ and ~~ literal\r\n")
    (sources / "C.TXT").write_bytes(b"@C\r\n:second\r\n%Second\r\n")

    results = export_bundle_tree(sources, tmp_path / "out", layout="helps")
    assert {result.json_path.name for result in results} == {"asm.json.gz", "c.json.gz"}
    assert {result.format_name for result in results} == {"helppc"}
    payload = json.loads(gzip.decompress((tmp_path / "out" / "asm.json.gz").read_bytes()))
    assert len(payload["topics"]) == 1
    first = payload["topics"]["1"]
    assert any("[link:file=C.TXT,topic=1]second[/link]" in line for line in first["content"])
    assert any("~ literal" in line for line in first["content"])
    assert len(payload["index"]) == 2
    catalog = json.loads((tmp_path / "out" / "catalog.json").read_text(encoding="utf-8"))
    assert {entry["source_file"] for entry in catalog} == {"ASM.TXT", "C.TXT"}


def test_helppc_links_match_keys_with_repeated_spaces(tmp_path):
    (tmp_path / "ASM.TXT").write_bytes(
        b"@Assembly\r\n:First  Key\r\n See ~first key~ and ~SECOND KEY~ and ~second   key~\r\n"
    )
    (tmp_path / "C.TXT").write_bytes(b"@C\r\n:Second  Key\r\n Text\r\n")

    document = load_document(tmp_path / "ASM.TXT")
    line = document.topics[0].uhf_content[0]
    assert "[link:topic=1]first key[/link]" in line
    assert "[link:file=C.TXT,topic=1]SECOND KEY[/link]" in line
    assert "[link:file=C.TXT,topic=1]second   key[/link]" in line


@pytest.mark.parametrize("source,plain", [
    (b"^Title", b" " * 37 + b"Title"),
    (b"^PORTS\tCommon I/O Port Addresses", b" " * 24 + b"PORTS   Common I/O Port Addresses"),
    (b"%Title", b" Title"),
    (b"\tText", b"        Text"),
    (b" X\tY", b" X      Y"),
    (b"^~Key~\tText", b" " * 35 + b"Key  Text"),
    (b"%~Key~\tText", b" Key    Text"),
    (b" ~~\tText", b" ~      Text"),
    (b"^T\tT", b" " * 38 + b"T T"),
    (b"^" + b"X" * 79, b"X" * 79),
    (b"^" + b"X" * 80, b"X" * 80),
    (b"\tSee ~unterminated", b"        See unterminated"),
    (b"\tSee ~literal~~key~", b"        See literal~key"),
    (b"^\x80\xc4", b" " * 39 + b"\x80\xc4"),
    (b"", b""),
])
def test_helppc_columns_match_original_com_renderer(source, plain):
    # Measured by executing the renderer at 129Ch..1426h in HELPPC.COM
    # CRC32 8D6D7C24. No native runtime dependency is needed for these fixtures.
    document = HelpPCReader(source_name="TEST.TXT").read_bytes(
        b"@Example\r\n:Key\r\n" + source + b"\r\n"
    )
    assert document.topics[0].raw_lines == [plain]
    assert document.metadata["display_width"] == 80
    payload = HelpJsonRenderer(document).render_document()
    assert payload["metadata"]["display"]["cols"] == 80


def test_helppc_centering_escapes_markup_and_keeps_highlighting_after_the_margin():
    document = HelpPCReader().read_bytes(b"@Example\r\n:Key\r\n^Title [x]\r\n%Title [x]\r\n")
    assert document.topics[0].uhf_content == [
        " " * 35 + "[b]Title [[x][/b]", " [b]Title [[x][/b]",
    ]


def test_helppc_links_with_centering_tabs_and_escaped_tildes_keep_real_targets(tmp_path):
    source = tmp_path / "ASM.TXT"
    source.write_bytes(b"@Assembly\r\n:First\r\n^See ~Second~\tend\r\n See ~literal~~key~\r\n See ~First\r\n")
    (tmp_path / "C.TXT").write_bytes(b"@C\r\n:Second\r\n Text\r\n:literal~key\r\n Text\r\n")
    document = load_document(source)
    topic = document.topics[0]
    assert topic.raw_lines[0] == b" " * 32 + b"See Second      end"
    assert "[link:file=C.TXT,topic=1]Second[/link]" in topic.uhf_content[0]
    assert "[link:file=C.TXT,topic=2]literal~key[/link]" in topic.uhf_content[1]
    assert topic.uhf_content[2] == " See First"  # Incomplete syntax has no invented hotspot.


def test_helppc_overlong_centering_fails_but_ordinary_text_is_not_clipped():
    reader = HelpPCReader()
    with pytest.raises(ValueError, match="centered line exceeds"):
        reader.read_bytes(b"@Example\r\n:Key\r\n^" + b"X" * 81 + b"\r\n")
    document = reader.read_bytes(b"@Example\r\n:Key\r\n%" + b"X" * 81 + b"\r\n")
    assert document.topics[0].raw_lines == [b" " + b"X" * 81]
    assert document.topics[0].uhf_content == [" [b]" + "X" * 81 + "[/b]"]


def test_helppc_corpus_retains_topics_links_and_native_center_origins():
    root = Path("var/sources/HelpPC 2.10")
    files = [root / name for name in ("ASM.TXT", "C.TXT", "HARDWARE.TXT", "INTERRUP.TXT", "MISC.TXT", "TABLES.TXT")]
    if not all(path.is_file() for path in files):
        pytest.skip("HelpPC originals not available")
    originals = {path: path.read_bytes() for path in files}
    documents = [load_document(path) for path in files]
    assert [len(document.topics) for document in documents] == [161, 410, 20, 358, 14, 43]
    target_ids = {path.name: {topic.context_id for topic in document.topics}
                  for path, document in zip(files, documents)}
    links = []
    centered = tabs = 0
    for path, document in zip(files, documents):
        topic_index, display_index = -1, 0
        for raw in originals[path].splitlines():
            if raw.startswith(b":"):
                topic_index += 1
                display_index = 0
                continue
            if topic_index < 0 or raw[:1] not in (b"^", b"%", b" ", b"\t", b""):
                continue
            if raw.startswith(b"^"):
                body = raw[1:]
                origin = (80 - len(body)) // 2
                assert document.topics[topic_index].raw_lines[display_index] == (b" " * origin + body).expandtabs(8)
                centered += 1
                tabs += b"\t" in body
            display_index += 1
        for topic in document.topics:
            for row in topic.uhf_content:
                _assert_balanced_uhf_inline(row)
                for match in re.finditer(r"\[\[|\[link:([^\]]+)\]", row):
                    if match.group(1) is not None:
                        target = parse_uhf_link_target(match.group(1))
                        assert target["topic_id"] in target_ids[target.get("source_file", path.name)]
                        links.append(target)
        assert document.metadata["display_width"] == 80
        assert path.read_bytes() == originals[path]
    assert centered == 1075 and tabs == 20
    assert len(links) == 1786
    assert set(target.get("source_file") for target in links if target.get("source_file")) <= {path.name for path in files}


def test_freedos_zip_import_keeps_internal_links_and_preformatted_text(tmp_path):
    source = tmp_path / "HHSTNDRD.ZIP"
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("help/index.htm", "<html><head><title>Contents</title></head><body><pre>Read <a href='../base/foo.htm'>foo</a> now.\n  Next</pre></body></html>")
        archive.writestr("base/foo.htm", "<html><head><title>Foo</title></head><body><h1>Foo</h1><p>Done.</p></body></html>")
    source.write_bytes(buffer.getvalue())

    assert detect_format_handler(source).name == "freedos-html"
    document = load_document(source)
    assert len(document.topics) == 2
    index_topic = next(topic for topic in document.topics if topic.is_help_contents)
    foo_topic = next(topic for topic in document.topics if topic.names == ["Foo"])
    assert any(f"[link:topic={foo_topic.context_id}]foo[/link]" in line for line in index_topic.uhf_content)
    assert any(line.startswith("  Next") for line in index_topic.uhf_content)
    assert "[b]Foo[/b]" in foo_topic.uhf_content

    results = export_bundle_tree(tmp_path, tmp_path / "out", layout="helps")
    assert len(results) == 1
    payload = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    assert payload["metadata"]["help_contents_topic_id"] == index_topic.context_id


def _freedos_document(pages):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, html in pages.items():
            archive.writestr(name, html)
    return FreeDOSHtmlReader(source_name="HHSTNDRD.ZIP").read_bytes(buffer.getvalue())


def test_freedos_fragments_resolve_forward_same_page_and_cross_page_anchors():
    document = _freedos_document({
        "help/index.htm": """<html><head><title>Contents</title></head><body>
        <p><a href="../base/foo.htm#target">Cross page</a>
        <a href="#later">Forward</a></p>
        <p>Intro</p><br><br><a name="later"></a><h2>Later section</h2>
        <pre>  Fixed text</pre></body></html>""",
        "base/foo.htm": """<html><head><title>Foo</title></head><body>
        <h1>Foo</h1><p>Intro</p><h2 id="target">Target section</h2>
        <p><a href="../HELP/./INDEX.HTM?ignored=1#later">Back</a></p></body></html>""",
    })
    index, foo = (next(topic for topic in document.topics if topic.names == [name])
                  for name in ("Contents", "Foo"))
    index_line = index.uhf_content.index("[b]Later section[/b]") + 1
    foo_line = foo.uhf_content.index("[b]Target section[/b]") + 1
    assert foo_line == index_line == 5  # Includes compacted separator rows.
    assert any(f"[link:topic={foo.context_id},line={foo_line}]Cross page[/link]" in line
               for line in index.uhf_content)
    assert any(f"[link:topic={index.context_id},line={index_line}]Forward[/link]" in line
               for line in index.uhf_content)
    assert any(f"[link:topic={index.context_id},line={index_line}]Back[/link]" in line
               for line in foo.uhf_content)
    assert not any("[link:" in line for line in index.uhf_content[index_line - 1:])
    assert "  Fixed text" in index.uhf_content


def test_freedos_bookmark_names_remain_text_and_do_not_create_self_links():
    document = _freedos_document({"help/index.htm": """<body><pre>
  <a name="section">[Section]</a>
  <a href="#section">Go</a>
  Text<a name="inline"></a> continued
  <a href="#inline">Inline</a>
</pre></body>"""})
    topic = document.topics[0]
    assert topic.uhf_content[0] == "  [[Section]"
    assert topic.uhf_content[2] == "  Text continued"
    assert f"[link:topic={topic.context_id},line=1]Go[/link]" in topic.uhf_content[1]
    assert f"[link:topic={topic.context_id},line=3]Inline[/link]" in topic.uhf_content[3]


def test_freedos_fragment_identifiers_are_decoded_once_and_case_sensitive():
    document = _freedos_document({
        "help/index.htm": """<body><p>
        <a href="../base/Foo%20Bar.htm#c%C3%ADe%C4%BE">Unicode</a>
        <a href="../base/Foo%20Bar.htm#Target">Case exact</a>
        <a href="../base/Foo%20Bar.htm#target">Case mismatch</a>
        <a href="../base/Foo%20Bar.htm#%2520">Percent</a></p></body>""",
        "base/Foo Bar.htm": """<body><h2 id="cíeľ">Unicode target</h2>
        <h2 id="Target">Uppercase target</h2><h2 id="%20">Percent target</h2></body>""",
    })
    target, source = document.topics
    for label, heading in (("Unicode", "Unicode target"), ("Case exact", "Uppercase target"),
                           ("Percent", "Percent target")):
        line = target.uhf_content.index(f"[b]{heading}[/b]") + 1
        assert any(f"[link:topic={target.context_id},line={line}]{label}[/link]" in row
                   for row in source.uhf_content)
    assert any(f"[link:topic={target.context_id}]Case mismatch[/link]" in row
               for row in source.uhf_content)


def test_freedos_duplicate_bookmarks_take_first_definition_and_ids_precede_names():
    document = _freedos_document({"help/index.htm": """<body>
    <p><a href="#same">Same</a><a href="#named">Named</a></p>
    <h2><a name="same">Old name</a></h2>
    <h2 id="same">First id</h2><h2 id="same">Second id</h2>
    <h2><a name="named">First name</a></h2><h2><a name="named">Second name</a></h2>
    </body>"""})
    topic = document.topics[0]
    for label, heading in (("Same", "First id"), ("Named", "First name")):
        line = topic.uhf_content.index(f"[b]{heading}[/b]") + 1
        assert f"[link:topic={topic.context_id},line={line}]{label}[/link]" in topic.uhf_content[0]


def test_freedos_missing_fragment_keeps_the_real_page_without_an_invented_line():
    document = _freedos_document({"help/index.htm": """<html><head>
    <title>Contents</title><meta id="head-only"></head><body>
    <script id="script-only">ignored</script><style id="style-only">ignored</style>
    <p><a href="#missing">Missing anchor</a>
    <a href="#head-only">Head</a><a href="#script-only">Script</a>
    <a href="#style-only">Style</a><a href="missing.htm#target">Missing page</a>
    <a href="https://example.org/#target">External</a>
    <a href="http://[">Malformed</a><a href="">Empty href</a></p></body></html>"""})
    topic = document.topics[0]
    content = "\n".join(topic.uhf_content)
    for label in ("Missing anchor", "Head", "Script", "Style", "Empty href"):
        assert f"[link:topic={topic.context_id}]{label}[/link]" in content
    assert ",line=" not in content
    for label in ("Missing page", "External", "Malformed"):
        assert label in content and f"]{label}[/link]" not in content


def test_freedos_bookmarks_at_end_and_in_empty_pages_do_not_exceed_content():
    document = _freedos_document({
        "help/index.htm": '<body><p><a href="empty.htm#empty">Empty</a><a href="#end">End</a></p><a name="end"></a></body>',
        "help/empty.htm": '<body><a name="empty"></a></body>',
    })
    empty, source = document.topics
    assert empty.uhf_content == []
    assert f"[link:topic={empty.context_id}]Empty[/link]" in source.uhf_content[0]
    assert f"[link:topic={source.context_id},line={len(source.uhf_content)}]End[/link]" in source.uhf_content[0]


def test_freedos_case_colliding_member_paths_fail_without_silent_topic_loss():
    with pytest.raises(ValueError, match="Ambiguous FreeDOS HTML member names"):
        _freedos_document({"help/index.htm": '<p>First</p>', "HELP/INDEX.HTM": '<p>Second</p>'})


def _assert_balanced_uhf_inline(row):
    stack = []
    for match in re.finditer(r"\[\[|\[(b|/b|link:[^\]]+|/link)\]", row):
        tag = match.group(1)
        if tag is None:  # A literal '[' consumes exactly the escaped pair.
            continue
        if tag.startswith("/"):
            assert stack and stack.pop() == tag[1:], row
        else:
            stack.append("link" if tag.startswith("link:") else tag)
    assert not stack, row


def test_freedos_multiline_pre_styles_close_and_reopen_on_every_uhf_row():
    document = _freedos_document({"help/index.htm":
        '<body><pre><b>First\n  Second\nThird</b> normal</pre></body>'})
    assert document.topics[0].uhf_content == [
        "[b]First[/b]", "[b]  Second[/b]", "[b]Third[/b] normal",
    ]


def test_freedos_styles_across_blocks_do_not_create_markup_only_rows():
    document = _freedos_document({"help/index.htm":
        '<body><b><p>First</p><p>Second</p></b></body>'})
    assert document.topics[0].uhf_content == ["[b]First[/b]", "", "[b]Second[/b]"]


_FLOWING_HTML_CASES = [
    ('Before <b>bold</b> after <a href="">link</a> text.',
     'Before [b]bold[/b] after [link:topic=1]link[/link] text.'),
    ('<b>bold </b>after', '[b]bold [/b]after'),
    ('<b>bold</b> <strong> next</strong>', '[b]bold[/b] [b]next[/b]'),
    ('one <a name="mark"></a><!-- ignored -->two', 'one two'),
    ('one<b>two</b>three', 'one[b]two[/b]three'),
    (' \t<b>bold </b>\n ', '[b]bold[/b]'),
    ('a&nbsp;&nbsp;<b>b</b>&nbsp;', 'a\u00a0\u00a0[b]b[/b]\u00a0'),
    ('&nbsp;', '\u00a0'),
    ('a\u2003b', 'a\u2003b'),
    ('one \t\r\n <b>two</b>', 'one [b]two[/b]'),
    ('one \f <b>two</b>', 'one \f [b]two[/b]'),
]


@pytest.mark.parametrize("html,expected", _FLOWING_HTML_CASES)
def test_freedos_flowing_text_preserves_inline_word_boundaries_and_noncollapsible_spaces(html, expected):
    parser = _PageParser("help/index.htm", {"help/index.htm": 1}, {})
    parser.feed(f"<body><p>{html}</p></body>")
    assert parser.finish()[1] == [expected]
    _assert_balanced_uhf_inline(expected)


def test_freedos_whitespace_results_do_not_depend_on_html_parser_input_chunks():
    html = '<body><p> one <b>bold </b>word &nbsp; <a href="">link</a> done </p><p>next</p></body>'
    results = []
    for size in (1, 2, 5, len(html)):
        parser = _PageParser("help/index.htm", {"help/index.htm": 1}, {})
        for offset in range(0, len(html), size):
            parser.feed(html[offset:offset + size])
        parser.close()
        results.append(parser.finish()[1])
    assert results == [[
        'one [b]bold [/b]word \u00a0 [link:topic=1]link[/link] done', '', 'next',
    ]] * len(results)


def test_freedos_pending_space_does_not_leak_into_blocks_preformatted_text_or_cells():
    document = _freedos_document({"help/index.htm": '<body><p>one </p>'
        '<p><b> two</b> </p><pre>  three\n four</pre><table>'
        '<tr><td> A </td><td> B </td></tr></table><p>C</p></body>'})
    assert document.topics[0].uhf_content == [
        'one', '', '[b]two[/b]', '', '  three', ' four', '', 'A  |  B', '', 'C',
    ]


def test_freedos_flowing_text_matches_real_browser_whitespace(tmp_path):
    from test_browser_smoke import CHROME, NODE, _wait_for_file

    if not CHROME or not NODE:
        pytest.skip("Chrome and Node.js are required")
    chrome = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0",
        f"--user-data-dir={tmp_path / 'chrome'}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = _wait_for_file(tmp_path / "chrome/DevToolsActivePort").splitlines()[0]
        cases = []
        for html, _expected in _FLOWING_HTML_CASES:
            parser = _PageParser("help/index.htm", {"help/index.htm": 1}, {})
            parser.feed(f"<body><p>{html}</p></body>")
            row, = parser.finish()[1]
            plain = re.sub(r"\[/?b\]|\[link:[^\]]+\]|\[/link\]", "", row)
            cases.append({"html": html, "plain": plain})
        script = r'''
const [port,rawCases]=process.argv.slice(1),assert=require('node:assert/strict');
(async()=>{
 const target=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let sequence=0;const pending=new Map();
 socket.onmessage=event=>{const message=JSON.parse(String(event.data)),call=pending.get(message.id);
  if(call){pending.delete(message.id);message.error?call.reject(Error(message.error.message)):call.resolve(message.result);}};
 const send=(method,params)=>new Promise((resolve,reject)=>{const id=++sequence;
  pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 try{
  for(const testCase of JSON.parse(rawCases)){
   const result=await send('Runtime.evaluate',{returnByValue:true,expression:`(()=>{
    document.body.innerHTML='<p id="probe">'+${JSON.stringify(testCase.html)}+'</p>';
    return document.getElementById('probe').innerText;
   })()`});
   if(result.exceptionDetails)throw Error(result.exceptionDetails.text);
   assert.equal(result.result.value,testCase.plain,testCase.html);
  }
 }finally{socket.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([NODE, "-e", script, port, json.dumps(cases)],
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
    finally:
        chrome.terminate()
        chrome.wait(timeout=10)


def test_freedos_multiline_links_keep_the_same_target_and_nested_styles():
    document = _freedos_document({"help/index.htm": """<body><pre><a href="#later"><b>First
Second</b>
Third</a></pre><h2 id="later">Target</h2></body>"""})
    topic = document.topics[0]
    target_line = topic.uhf_content.index("[b]Target[/b]") + 1
    assert target_line == 5
    opening = f"[link:topic={topic.context_id},line={target_line}]"
    assert topic.uhf_content[:3] == [
        opening + "[b]First[/b][/link]", opening + "[b]Second[/b][/link]",
        opening + "Third[/link]",
    ]
    for row in topic.uhf_content:
        _assert_balanced_uhf_inline(row)


def test_freedos_crossed_and_unmatched_source_tags_do_not_corrupt_uhf():
    document = _freedos_document({"help/index.htm":
        '<body><pre></b><a href=""><b>one</a>two</b></pre></body>'})
    topic = document.topics[0]
    assert topic.uhf_content == [f"[link:topic={topic.context_id}][b]one[/b][/link][b]two[/b]"]
    _assert_balanced_uhf_inline(topic.uhf_content[0])


def test_freedos_corpus_keeps_all_real_links_and_resolves_fragment_lines():
    source = Path("var/sources/FreeDOS HTML Help 1.1.1a/HHSTNDRD.ZIP")
    if not source.is_file():
        pytest.skip("FreeDOS original not available")
    before = source.read_bytes()
    document = load_document(source)
    topics = {topic.context_id: topic for topic in document.topics}
    references = []
    for topic in document.topics:
        for row in topic.uhf_content:
            _assert_balanced_uhf_inline(row)
            assert not re.search(r"\[link:[^\]]+\]\[/link\]", row)
            for match in re.finditer(r"\[\[|\[link:([^\]]+)\]", row):
                if match.group(1) is None:
                    continue
                target = parse_uhf_link_target(match[1])
                assert target["topic_id"] in topics
                if target.get("line"):
                    assert 1 <= target["line"] <= len(topics[target["topic_id"]].uhf_content)
                references.append(target)
    assert len(topics) == 354
    assert len(references) == 4132  # Excludes 154 destinations misread as links.
    assert sum("line" in target for target in references) == 112
    debug = next(topic for topic in document.topics if topic.names == ["FreeDOS command: debug"])
    assert "[b]Program Execution:[/b]" in debug.uhf_content[116]
    assert any(f"[link:topic={debug.context_id},line=117]Program Execution[/link]" in row
               for row in debug.uhf_content)
    memory = next(topic for topic in document.topics if topic.names == ["The DOS memory management:"])
    assert memory.uhf_content[98] == "[b]DOS Extenders:[/b]"
    assert sum(row.count("\ufffd") for topic in document.topics for row in topic.uhf_content) == 1
    assert source.read_bytes() == before


def test_reference_crc_records_match_downloaded_files_when_present():
    root = Path("var/sources")
    paths = [
        *(root / "HelpPC 2.10" / name for name in (
            "ASM.TXT", "C.TXT", "HARDWARE.TXT", "INTERRUP.TXT", "MISC.TXT", "TABLES.TXT"
        )),
        root / "FreeDOS HTML Help 1.1.1a" / "HHSTNDRD.ZIP",
        root / "Microsoft MS-DOS 6.22" / "HELP.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45QCK.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45ADVR.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45ENER.HLP",
    ]
    database = load_help_database()
    for path in paths:
        if path.exists():
            entry = lookup_help_database_entry(path, database)
            assert entry is not None
            assert entry.product_key in {"freedos-help", "helppc", "msdos622", "qb45"}


def test_downloaded_reference_help_exports_into_help_files_catalog(tmp_path):
    root = Path("var/sources")
    required = (
        root / "FreeDOS HTML Help 1.1.1a" / "HHSTNDRD.ZIP",
        root / "HelpPC 2.10" / "ASM.TXT",
        root / "Microsoft MS-DOS 6.22" / "HELP.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45QCK.HLP",
    )
    if not all(path.is_file() for path in required):
        pytest.skip("DOS reference help files were not downloaded")

    selected_sources = tmp_path / "sources"
    selected_sources.mkdir()
    for name in (
        "FreeDOS HTML Help 1.1.1a", "HelpPC 2.10",
        "Microsoft MS-DOS 6.22", "Microsoft QuickBASIC 4.5",
    ):
        shutil.copytree(root / name, selected_sources / name)
    results = export_bundle_tree(selected_sources, tmp_path / "helps", layout="helps")
    assert len(results) == 11
    assert all(result.topic_count > 0 for result in results)
    catalog = json.loads((tmp_path / "helps" / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog) == 11
    assert {entry["product"] for entry in catalog} == {
        "freedos-help", "helppc", "msdos622", "qb45",
    }
    assert {entry["group"] for entry in catalog} == {
        "FreeDOS HTML Help 1.1.1a", "HelpPC 2.10",
        "Microsoft MS-DOS 6.22", "Microsoft QuickBASIC 4.5",
    }
    assert all((tmp_path / "helps" / entry["file"]).is_file() for entry in catalog)
