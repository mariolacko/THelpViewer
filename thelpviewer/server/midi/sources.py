"""Validate source manifests and extract stable album/track identities from HTML."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from ..content_config import read_source_manifest

MAX_HTML_BYTES = 4 * 1024 * 1024
SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def safe_filename(value: str) -> str:
    name = re.sub(r"[^\w. -]", "_", unquote(value), flags=re.UNICODE).strip(" .")
    return name[:100] or "track.mid"


class MidiIndexParser(HTMLParser):
    """Extract tracks using one of the declarative HTML layouts."""

    def __init__(self, rules: dict[str, object]):
        super().__init__(convert_charrefs=True)
        self.rules = rules
        self.pattern = re.compile(str(rules.get("href_pattern", r"\.(?:mid|midi|zip)$")), re.I)
        self.mode = str(rules.get("mode", "anchors"))
        if self.mode not in ("table_rows", "anchors", "download_then_heading", "selectors"):
            raise ValueError(f"Unsupported MIDI HTML extraction mode: {self.mode}")
        self._html_parts: list[str] = []
        self.items: list[dict[str, str]] = []
        self.game = ""
        self.row_class = ""
        self.cells: list[str] | None = None
        self.row_links: list[tuple[str, str]] = []
        self.anchor_href: str | None = None
        self.anchor_text: list[str] = []
        self.heading_text: list[str] | None = None
        self.pending: tuple[str, str] | None = None

    def feed(self, data: str) -> None:
        if self.mode == "selectors":
            self._html_parts.append(data)
        else:
            super().feed(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "tr" and self.mode == "table_rows":
            self._finish_row()
            self.row_class = values.get("class") or ""
            self.cells, self.row_links = [], []
        elif tag == "td" and self.cells is not None:
            self.cells.append("")
        elif tag == "a":
            self.anchor_href = values.get("href")
            self.anchor_text = []
        elif tag == self.rules.get("game_heading_tag") and self.mode == "download_then_heading":
            self.heading_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.anchor_href is not None:
            text = _clean_text("".join(self.anchor_text))
            href = self.anchor_href
            if self.pattern.search(urlsplit(href).path):
                if self.mode == "table_rows":
                    self.row_links.append((href, text))
                elif self.mode == "anchors":
                    self.items.append({"href": href, "game": "", "title": text, "sequencer": ""})
                elif text.casefold() == str(self.rules.get("download_link_text", "Download")).casefold():
                    self.pending = (href, text)
            self.anchor_href = None
            self.anchor_text = []
        elif tag == "tr" and self.mode == "table_rows":
            self._finish_row()
        elif tag == self.rules.get("game_heading_tag") and self.heading_text is not None:
            text = _clean_text("".join(self.heading_text))
            prefix = str(self.rules.get("game_prefix", "Game:"))
            if self.pending and text.casefold().startswith(prefix.casefold()):
                href, _label = self.pending
                game = _clean_text(text[len(prefix):])
                self.items.append({"href": href, "game": game, "title": game, "sequencer": ""})
                self.pending = None
            self.heading_text = None

    def handle_data(self, data: str) -> None:
        if self.cells:
            self.cells[-1] += data
        if self.anchor_href is not None:
            self.anchor_text.append(data)
        if self.heading_text is not None:
            self.heading_text.append(data)

    def _finish_row(self) -> None:
        if self.cells is None:
            return
        cells = [_clean_text(value) for value in self.cells]
        group_class = str(self.rules.get("group_row_class", ""))
        if group_class and group_class in self.row_class.split():
            index = int(self.rules.get("group_cell", 0))
            if index < len(cells):
                self.game = cells[index]
        elif self.row_links:
            href, title = self.row_links[0]
            author_index = int(self.rules.get("author_cell", -1))
            author = cells[author_index] if 0 <= author_index < len(cells) else ""
            self.items.append({"href": href, "game": self.game, "title": title, "sequencer": author})
        self.cells, self.row_links, self.row_class = None, [], ""

    def finish(self) -> list[dict[str, str]]:
        if self.mode == "selectors":
            return self._selector_items()
        self._finish_row()
        return self.items

    def _selector_items(self) -> list[dict[str, str]]:
        item_selector = str(self.rules.get("item_selector", ""))
        link_selector = str(self.rules.get("link_selector", "a[href]"))
        if not item_selector:
            raise ValueError("MIDI selector extraction needs item_selector")
        page = BeautifulSoup("".join(self._html_parts), "html.parser")
        for item in page.select(item_selector):
            link = item.select_one(link_selector)
            if link is None:
                continue
            href = str(link.get(str(self.rules.get("link_attr", "href")), ""))
            if not self.pattern.search(urlsplit(href).path):
                continue

            def field(name: str, fallback: str = "") -> str:
                selector = str(self.rules.get(f"{name}_selector", ""))
                element = item.select_one(selector) if selector else None
                if element is None:
                    return fallback
                attribute = str(self.rules.get(f"{name}_attr", ""))
                return _clean_text(str(element.get(attribute, "")) if attribute
                                   else element.get_text(" ", strip=True))

            self.items.append({
                "href": href,
                "game": field("game", str(self.rules.get("game", ""))),
                "title": field("title", _clean_text(link.get_text(" ", strip=True))),
                "sequencer": field("sequencer"),
            })
        return self.items


def configured_sources(sources_path: Path | None) -> list[dict[str, object]]:
    configured = read_source_manifest(sources_path, "MIDI", SOURCE_ID_RE)["sources"]
    for source in configured:
        if not isinstance(source.get("name"), str) or not source["name"].strip():
            raise ValueError("Invalid MIDI source name")
    return configured


def source_selection(selection_path: Path | None) -> list[str] | None:
    if selection_path is None or not selection_path.exists():
        return None
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if (not isinstance(selection, dict) or "sources" not in selection or set(selection) - {"sources", "albums"}
            or not isinstance(selection["sources"], list)
            or any(not isinstance(item, str) for item in selection["sources"])):
        raise ValueError("Invalid saved MIDI source selection")
    return selection["sources"]


def album_selection(selection_path: Path | None) -> dict[str, list[str] | None]:
    if selection_path is None or not selection_path.exists():
        return {}
    albums = json.loads(selection_path.read_text(encoding="utf-8")).get("albums", {})
    if (not isinstance(albums, dict) or any(not isinstance(key, str) or (value is not None
            and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)))
            for key, value in albums.items())):
        raise ValueError("Invalid saved MIDI album selection")
    return albums


def album_id(item: dict[str, object]) -> str:
    name = str(item.get("game") or item["title"])
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:24]


def album_enabled(item, source, albums) -> bool:
    selected = albums.get(source["provider_id"])
    return selected is None or album_id(item) in selected


def expand_sources(sources_path: Path | None, selection_path: Path | None, selected: list[str] | None = None) -> list[dict[str, object]]:
    if selected is None:
        selected = source_selection(selection_path)
    sources: list[dict[str, object]] = []
    for source in configured_sources(sources_path):
        if (source["id"] not in selected if selected is not None else source.get("enabled") is False):
            continue
        pages = source.get("pages")
        if not isinstance(pages, list) or not pages or not all(isinstance(page, str) for page in pages):
            raise ValueError(f"MIDI source {source.get('id')} needs a nonempty pages list")
        page_tokens = []
        for page in pages:
            url = urlsplit(page)
            last_path = url.path.rstrip("/").rsplit("/", 1)[-1]
            page_name = f"{last_path}-{url.query}" if url.query else last_path
            slug = re.sub(r"[^a-z0-9]+", "-", unquote(page_name).casefold()).strip("-")
            page_tokens.append(slug.split("-"))
        common_count = 0
        if len(pages) > 1:
            for tokens in zip(*page_tokens):
                if len(set(tokens)) != 1:
                    break
                common_count += 1
        for page, tokens in zip(pages, page_tokens):
            suffix = "-".join(tokens[common_count:]) or "0"
            sources.append({
                **{key: value for key, value in source.items() if key != "pages"},
                "id": f"{source['id']}-{suffix}" if len(pages) > 1 else source["id"],
                "name": f"{source['name']} {'#' if suffix == '0' else suffix.upper()}"
                if len(pages) > 1 else source["name"],
                "index_url": page,
                "provider_id": source["id"],
                "source_page": page if len(pages) > 1 else source.get("source_page", page),
            })
    seen_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or not SOURCE_ID_RE.fullmatch(str(source.get("id", ""))):
            raise ValueError("Invalid MIDI source ID")
        if source["id"] in seen_ids:
            raise ValueError(f"Duplicate MIDI source ID: {source['id']}")
        seen_ids.add(str(source["id"]))
        if not isinstance(source.get("extract"), dict):
            raise ValueError(f"MIDI source {source['id']} has no extraction rules")
        hosts = source.get("allowed_hosts")
        parsed = urlsplit(str(source.get("index_url", "")))
        if parsed.scheme != "https" or not isinstance(hosts, list) or parsed.hostname not in hosts:
            raise ValueError(f"MIDI source {source['id']} needs an HTTPS URL and matching allowed_hosts")
    return sources


def index_source(source: dict[str, object], fetch) -> list[dict[str, object]]:
    hosts = set(source["allowed_hosts"])
    page = str(source["index_url"])
    html = fetch(page, hosts, MAX_HTML_BYTES).decode("utf-8", errors="replace")
    parser = MidiIndexParser(source["extract"])
    parser.feed(html)
    results: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in parser.finish():
        url = urljoin(page, item["href"])
        parts = urlsplit(url)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
        if parts.scheme != "https" or parts.hostname not in hosts or url in seen:
            continue
        seen.add(url)
        kind = "zip" if parts.path.lower().endswith(".zip") else "midi"
        ident = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        basename = safe_filename(Path(unquote(parts.path)).name)
        if kind == "midi":
            filename = f"{ident}-{basename}"
        else:
            filename = ""
        results.append({
            "id": ident, "source_id": source["id"], "url": url, "kind": kind,
            "game": item["game"], "title": item["title"] or basename,
            "sequencer": item["sequencer"], "filename": filename, "members": [],
        })
    if not results:
        raise ValueError(f"No MIDI/ZIP links found for {source['id']}")
    return results
